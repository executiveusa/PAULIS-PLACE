"""
JUDGE — Spec §1.L1 adversarial checker
=====================================
Every worker output goes through a judge pass before acceptance.

Refusal contract (spec §1.5):
  {"verdict": "accept", "reasoning": "..."}
  {"verdict": "reject", "reasoning": "...", "fixes": ["..."]}
  {"verdict": "halt",    "reasoning": "..."}  // escalates to human

Hard rule: judge model MUST differ from worker model (spec §8).
"""
from __future__ import annotations
import json
from typing import Optional

from services.profile_router import call_profile, resolve_profile, ensure_distinct_profiles


JUDGE_SYSTEM_PROMPT = """You are an adversarial judge in the Yappyverse Hermes system.
You review worker output and return one of three verdicts using a strict JSON refusal contract.

VERDICTS:
  "accept" — output meets the spec, no material flaws
  "reject" — output is fixable; list concrete fixes the worker must apply
  "halt"   — output crosses a hard law (L1/L2/L3/L4) and must escalate to human

Return ONLY JSON, no prose:
{
  "verdict": "accept" | "reject" | "halt",
  "reasoning": "one paragraph, facts only, cite spec sections when possible",
  "fixes": ["only if reject, concrete ordered fixes"],
  "laws_violated": ["L1|L2|L3|L4 (only if halt)"]
}

Rules:
- Never accept output that mentions or leaks secrets (sk_, _KEY=, ghp_, r8_, sbp_, pat, cf_).
- Never accept if the worker output contradicts the spec section-10 acceptance for its subsystem.
- Never accept if blast_radius > 3 services touched or spend cap exceeded.
- If unsure, prefer "reject" with specific fixes over "halt".
"""


async def judge_worker_output(
    *,
    worker_profile: str,
    worker_model: str,
    worker_output: dict | str,
    judge_profile: str = "judge",
    spec_excerpt: str = "",
    context: str = "",
) -> dict:
    """Run an adversarial judge pass on a worker's output.

    Enforces:
      - judge_profile model != worker_model
      - returns structured verdict (accept/reject/halt)
    """
    spec = resolve_profile(judge_profile)
    ensure_distinct_profiles(worker_profile, judge_profile)

    if isinstance(worker_output, (dict, list)):
        worker_text = json.dumps(worker_output, indent=2)[:8000]
    else:
        worker_text = str(worker_output)[:8000]

    user_prompt = (
        f"Worker profile: {worker_profile}\n"
        f"Worker model: {worker_model}\n"
        f"Judge model: {spec.preferred_model} (fallback {spec.fallback_model})\n\n"
        f"Spec excerpt:\n{spec_excerpt or '(see subsystem spec)'}\n\n"
        f"Context:\n{context or '(none)'}\n\n"
        f"Worker output to review:\n```\n{worker_text}\n```\n\n"
        f"Return the verdict JSON now."
    )

    result = await call_profile(
        judge_profile,
        prompt=user_prompt,
        system_prompt=JUDGE_SYSTEM_PROMPT,
        temperature=0.1,
        response_format_json=True,
    )

    content = result.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except Exception:
            return {
                "verdict": "halt",
                "reasoning": "judge returned non-JSON output",
                "raw": content[:512],
            }
    # Normalize fields
    if not isinstance(content, dict) or "verdict" not in content:
        return {
            "verdict": "halt",
            "reasoning": "judge output missing 'verdict' field",
            "raw": str(content)[:512],
        }
    content.setdefault("fixes", [])
    content.setdefault("laws_violated", [])
    content["judge_model"] = result.get("model")
    content["judge_profile"] = judge_profile
    return content


async def judge_loop(
    *,
    worker_fn,
    worker_profile: str,
    judge_profile: str = "judge",
    spec_excerpt: str = "",
    context: str = "",
    max_iterations: int = 3,
    accept_on_first_pass: bool = False,
) -> dict:
    """Run the gauntlet loop for a single work item:
       worker runs -> judge reviews -> if reject, fixes loop -> if halt, raise.
       Returns the final accepted worker_output + judge verdict.
    """
    worker_model = None
    last_worker_output = None
    for i in range(max_iterations):
        result = await worker_fn()
        last_worker_output = result
        worker_model = result.get("model") if isinstance(result, dict) else "unknown"
        verdict = await judge_worker_output(
            worker_profile=worker_profile,
            worker_model=worker_model,
            worker_output=result,
            judge_profile=judge_profile,
            spec_excerpt=spec_excerpt,
            context=context,
        )
        if verdict["verdict"] == "accept":
            return {"output": result, "verdict": verdict, "iterations": i + 1}
        if verdict["verdict"] == "halt":
            raise RuntimeError(f"judge halted: {verdict.get('reasoning')}")
        # reject — push fixes back to worker via context
        fixes_str = json.dumps(verdict.get("fixes", []), indent=2)
        context = f"{context}\n\nJudge fixes (iteration {i+1}):\n{fixes_str}".strip()

    # Out of retries — return last attempt with reject verdict
    return {"output": last_worker_output, "verdict": verdict, "iterations": max_iterations}