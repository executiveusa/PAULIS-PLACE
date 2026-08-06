"""
ADVERSARIAL COUNCIL — Spec §02 (3-turn debate, locked ruling)
==============================================================
Strictly 3 turns:
  Turn 1 — ADVOCATE speaks  (profile write_short: grok-4.5 / glm-5.2 fast)
  Turn 2 — CRITIC  speaks   (profile score:        qwen-3.5 / llama-70b)
  Turn 3 — JUDGE   rules    (profile judge:         claude-fable-5 / glm-4.6 high-thinking)

Hard rule: judge model MUST differ from both advocate and critic models (spec §8).
Output envelope: R-03 COUNCIL.DEBATE_REQUEST (locked ruling).
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from services.profile_router import call_profile, resolve_profile, ensure_distinct_profiles
from services.event_bus import build_envelope, publish


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_decision(debate_id: str, payload: dict) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = repo_root / "icm" / "memory" / "decisions" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{debate_id}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _strip_to_json(content) -> dict:
    if isinstance(content, dict):
        return content
    s = str(content).strip()
    # Trim code fences if present
    if s.startswith("```"):
        s = s.split("```", 2)
        if len(s) >= 2:
            s = s[1].lstrip("json").strip()
        else:
            s = s[0].strip("`json").strip()
    try:
        return json.loads(s)
    except Exception:
        # Last resort: extract first {...} block
        first, last = s.find("{"), s.rfind("}")
        if first >= 0 and last > first:
            try:
                return json.loads(s[first:last+1])
            except Exception:
                pass
        return {"raw": s[:512]}


ADVOCATE_PROMPT = """You are the ADVOCATE in the Yappyverse Council.
Argue FOR this proposal. Give ONE sentence thesis + 3 supporting points.

PROPOSAL:
{proposal}

CONTEXT:
{context}

Return JSON:
{{
  "thesis": "<one sentence>",
  "supports": ["point 1", "point 2", "point 3"]
}}
"""

CRITIC_PROMPT = """You are the CRITIC in the Yappyverse Council.
Argue AGAINST this proposal. Find every flaw and risk.

PROPOSAL:
{proposal}

ADVOCATE ARGUMENT:
{advocate_arg}

CONTEXT:
{context}

Return JSON:
{{
  "antithesis": "<one sentence>",
  "risks": ["risk 1", "risk 2", "risk 3"]
}}
"""

JUDGE_PROMPT = """You are the JUDGE in the Yappyverse Council.
Lock the ruling. Synthesize the advocate + critic. You cannot ask for more turns.

PROPOSAL:
{proposal}

ADVOCATE ARGUMENT:
{advocate_arg}

CRITIC ARGUMENT:
{critic_arg}

CONTEXT:
{context}

Return JSON for your locked ruling:
{{
  "ruling": "APPROVE" | "REJECT" | "MODIFY",
  "modifications": <null or updated proposal text if MODIFY>,
  "judge_reasoning": "<one paragraph>",
  "expires_at": "<ISO date when re-debate is allowed, e.g. +24h>"
}}
"""


async def debate(
    *,
    proposal: str,
    context: str = "",
    advocate_profile: str = "write_short",
    critic_profile: str = "score",
    judge_profile: str = "judge",
) -> dict:
    """Run the strict 3-turn adversarial debate. Returns the locked ruling
       envelope and persists the debate to icm/memory/decisions/<date>/<debate_id>.json.
    """
    # Spec §8 — judge model must differ from worker models
    ensure_distinct_profiles(advocate_profile, judge_profile)
    ensure_distinct_profiles(critic_profile, judge_profile)

    # Turn 1 — Advocate
    adv_res = await call_profile(
        advocate_profile,
        prompt=ADVOCATE_PROMPT.format(proposal=proposal, context=context),
        system_prompt="You are a ruthless but fair advocate. No marketing fluff.",
        temperature=0.5,
        response_format_json=True,
    )
    advocate_payload = _strip_to_json(adv_res.get("content"))
    advocate_arg = advocate_payload.get("thesis", "") + " | " + json.dumps(advocate_payload.get("supports", []))

    # Turn 2 — Critic (sees proposal + advocate output)
    crit_res = await call_profile(
        critic_profile,
        prompt=CRITIC_PROMPT.format(proposal=proposal, advocate_arg=advocate_arg, context=context),
        system_prompt="You are a brutal but intellectually honest critic. Find flaws. Be specific.",
        temperature=0.3,
        response_format_json=True,
    )
    critic_payload = _strip_to_json(crit_res.get("content"))
    critic_arg = critic_payload.get("antithesis", "") + " | " + json.dumps(critic_payload.get("risks", []))

    # Turn 3 — Judge (sees proposal + advocate + critic)
    judge_res = await call_profile(
        judge_profile,
        prompt=JUDGE_PROMPT.format(proposal=proposal, advocate_arg=advocate_arg,
                                   critic_arg=critic_arg, context=context),
        system_prompt="You are the senior judge. Your ruling is FINAL.",
        temperature=0.2,
        response_format_json=True,
    )
    judge_payload = _strip_to_json(judge_res.get("content"))

    debate_id = f"deb_{uuid.uuid4()}"
    payload = {
        "debate_id": debate_id,
        "proposal": proposal,
        "advocate_arg": advocate_payload,
        "critic_arg": critic_payload,
        "ruling": judge_payload.get("ruling", "REJECT"),
        "modifications": judge_payload.get("modifications"),
        "judge_reasoning": judge_payload.get("judge_reasoning", ""),
        "expires_at": judge_payload.get("expires_at"),
        "judge_model": judge_res.get("model"),
        "advocate_model": adv_res.get("model"),
        "critic_model": crit_res.get("model"),
        "ts": _now_iso(),
    }
    _persist_decision(debate_id, payload)

    # Emit the R-03 envelope
    env = build_envelope(
        route="R-03.COUNCIL.DEBATE_REQUEST",
        stage="LOCK",
        services_touched=["paulis-place"],
        blast_radius_usd=0.02,
        worker_profile="judge",
        worker_model=judge_res.get("model", "unknown"),
        body=payload,
        judge_verdict=judge_payload.get("ruling", "").lower(),
        judge_model=judge_res.get("model"),
        next_action="ENACT_OR_DROP",
    )
    env["body"]["debate_id"] = debate_id
    await publish(env)
    return env


async def handle_debate_event(envelope: dict) -> None:
    """Subscriber for R-03 COUNCIL.DEBATE_REQUEST events emitted from other routes."""
    body = envelope.get("body", {}) or {}
    proposal = body.get("proposal") or body.get("reason", "")
    ctx = body.get("context", "")
    if isinstance(ctx, dict):
        ctx = json.dumps(ctx)
    if not proposal:
        return
    await debate(proposal=proposal, context=ctx)


def register() -> None:
    from services.event_bus import subscribe
    subscribe("R-03.COUNCIL.DEBATE_REQUEST", handle_debate_event)