"""
HERMES — God Agent Orchestrator (Spec §3, subsystem 01)
========================================================
Hermes is the runtime orchestrator of the Yappyverse. It does NOT write code.
It plans, delegates, judges, emits.

Public API:
  hermes.dispatch(route, work_item)  -> emits the right envelopes + invokes workers
  hermes.health()                   -> status brief for ops page

Hard laws enforced here:
  L1 — every worker output judged before emit
  L2 — blast-radius check (≤3 services)
  L3 — cost-cap pre-flight check
  L4 — secrets scan on worker input/output
"""
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Any, Callable, Awaitable, Optional

from services.event_bus import build_envelope, publish, new_event_id
from services.profile_router import (
    call_profile, cost_today, cap_remaining, resolve_profile,
)
from services.judge import judge_worker_output

# ----- Hard-law config from env -----
DAILY_CAP_USD = float(os.environ.get("YAPPY_DAILY_SPEND_CAP_USD", "25.00"))
PER_CHANNEL_CAP_USD = float(os.environ.get("YAPPY_PER_CHANNEL_CAP_USD", "0.50"))
HUMAN_BLAST_USD = float(os.environ.get("YAPPY_HUMAN_APPROVAL_BLAST_RADIUS_USD", "10.00"))
MAX_SERVICES_TOUCHED = 3
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"sk-ant-"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"sbp_[A-Za-z0-9]{20,}"),
    re.compile(r"r8_[A-Za-z0-9]{20,}"),
    re.compile(r"pat[A-Za-z0-9]{20,}"),
    re.compile(r"cfk_[A-Za-z0-9]{20,}"),
    re.compile(r"cfut_[A-Za-z0-9]{20,}"),
    re.compile(r"rk_live_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)_SECRET_KEY=([^\s\"']{8,})"),
]


@dataclass
class ActionManifest:
    route: str
    stage: str
    services_touched: list[str]
    blast_radius_usd: float
    worker_profile: str
    worker_prompts: dict[str, str]


def l4_scan(text: str) -> Optional[str]:
    """Returns the first secret match found, or None."""
    if not text:
        return None
    for pat in SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0)[:6] + "..."  # partial, never echo back full
    return None


def l3_preflight(expected_cost: float = 0.10) -> bool:
    remaining = cap_remaining(DAILY_CAP_USD)
    if remaining < expected_cost:
        return False
    return True


def l2_check(services: list[str]) -> bool:
    return len(services) <= MAX_SERVICES_TOUCHED


async def dispatch(
    *,
    route: str,
    stage: str,
    services_touched: list[str],
    blast_radius_usd: float,
    worker_profile: str,
    worker_fn: Callable[[], Awaitable[Any]],
    worker_body_builder: Callable[[Any], dict],
    spec_excerpt: str = "",
    context: str = "",
    judge_profile: str = "judge",
    expected_cost: float = 0.10,
) -> dict:
    """End-to-end Hermes dispatch for one work item.

    Steps:
      1. L4 scan worker input + L2/L3 preflight; halt if violated.
      2. Run worker_fn(); capture output + worker model.
      3. L4 scan worker output.
      4. Judge pass (refuses if any law broken).
      5. If accept → build envelope + publish.
      6. If reject → optional retry baked into judge_loop.
      7. Return envelope + verdict.
    """
    # L4: input scan
    leak = l4_scan(context) or l4_scan(spec_excerpt)
    if leak:
        return await _emit_halt(
            route=route, stage=stage,
            worker_profile=worker_profile,
            reason=f"L4 violation: secret pattern detected in input ({leak})",
        )

    # L2: services touched
    if not l2_check(services_touched):
        return await _emit_halt(
            route=route, stage=stage,
            worker_profile=worker_profile,
            reason=f"L2 violation: {len(services_touched)} services touched (max {MAX_SERVICES_TOUCHED})",
        )

    # L3: cost pre-flight
    if not l3_preflight(expected_cost):
        return await _emit_halt(
            route=route, stage=stage,
            worker_profile=worker_profile,
            reason=f"L3 violation: cost cap reached (spent ${cost_today():.2f} of ${DAILY_CAP_USD:.2f})",
        )

    # Human approval (> $10 blast radius) — emit pending and return
    if blast_radius_usd > HUMAN_BLAST_USD:
        env = build_envelope(
            route=route, stage=stage + ".PENDING_HUMAN",
            services_touched=services_touched,
            blast_radius_usd=blast_radius_usd,
            worker_profile=worker_profile,
            worker_model="n/a",
            body={"reason": "blast_radius_usd above human threshold", "spec_excerpt": spec_excerpt[:1200]},
            next_action="HUMAN_APPROVAL",
        )
        await publish(env)
        return env

    # Worker
    try:
        worker_result = await worker_fn()
    except Exception as e:
        return await _emit_halt(
            route=route, stage=stage,
            worker_profile=worker_profile,
            reason=f"worker exception: {type(e).__name__} {str(e)[:300]}",
        )

    if isinstance(worker_result, dict):
        worker_model = worker_result.get("model", "unknown")
        worker_text_for_l4 = json.dumps(worker_result.get("content", worker_result))
    else:
        worker_model = "unknown"
        worker_text_for_l4 = str(worker_result)

    # L4: output scan
    leak_out = l4_scan(worker_text_for_l4)
    if leak_out:
        return await _emit_halt(
            route=route, stage=stage,
            worker_profile=worker_profile,
            reason=f"L4 violation: secret pattern detected in worker output ({leak_out})",
        )

    # Judge
    context_with_extras = (
        f"{context}\n\n"
        f"Services touched: {services_touched}\n"
        f"Blast radius USD: {blast_radius_usd}\n"
        f"Expected worker model: {resolve_profile(worker_profile).preferred_model}"
    ).strip()

    verdict = await judge_worker_output(
        worker_profile=worker_profile,
        worker_model=worker_model,
        worker_output=worker_result,
        judge_profile=judge_profile,
        spec_excerpt=spec_excerpt,
        context=context_with_extras,
    )

    if verdict["verdict"] == "halt":
        return await _emit_halt(
            route=route, stage=stage,
            worker_profile=worker_profile,
            reason=f"judge halted: {verdict.get('reasoning','')[:400]}",
            judge_verdict=verdict,
        )

    body = worker_body_builder(worker_result) if worker_body_builder else {"raw": worker_text_for_l4[:4000]}

    env = build_envelope(
        route=route, stage=stage,
        services_touched=services_touched,
        blast_radius_usd=blast_radius_usd,
        worker_profile=worker_profile,
        worker_model=worker_model,
        body=body,
        judge_verdict=verdict["verdict"],
        judge_model=verdict.get("judge_model"),
        next_action=_next_action_for(verdict, route, stage),
        event_id=new_event_id(),
    )

    # If judge rejected, mark next_action to REWORK and don't emit downstream effects.
    if verdict["verdict"] == "reject":
        env["next_action"] = "REWORK"
        env["body"]["judge_fixes"] = verdict.get("fixes", [])

    await publish(env)
    return env


def _next_action_for(verdict: dict, route: str, stage: str) -> Optional[str]:
    if verdict["verdict"] != "accept":
        return None
    # Route + stage state machine — see icm/context/EVENT_BUS.md
    table = {
        ("R-01.REVENUE.NEW_TREND", "SCAN"): "SCORE",
        ("R-01.REVENUE.NEW_TREND", "SCORE"): "COUNCIL",
        ("R-01.REVENUE.NEW_TREND", "COUNCIL"): "DESIGN_OR_DROP",
        ("R-02.REVENUE.PRODUCT_CREATED", "DESIGN"): "PUBLISH",
        ("R-02.REVENUE.PRODUCT_CREATED", "PUBLISH"): "LOUNGE_SCENE",
        ("R-05.PAYMENT.SETTLED", "RECONCILE"): "LEDGER",
        ("R-05.PAYMENT.SETTLED", "LEDGER"): "CELEBRATE",
        ("R-06.REVENUE.CHANNEL_TICK", "TICK"): "OUTPUT_JUDGE",
        ("R-07.SYSTEM.SELF_IMPROVE", "ANALYZE"): "PROPOSE_PR",
        ("R-07.SYSTEM.SELF_IMPROVE", "PROPOSE_PR"): "HUMAN_REVIEW_PR",
    }
    return table.get((route, stage))


async def _emit_halt(
    *, route: str, stage: str, worker_profile: str,
    reason: str, judge_verdict: Optional[dict] = None,
) -> dict:
    env = build_envelope(
        route=route, stage="HALT",
        services_touched=[],
        blast_radius_usd=0.0,
        worker_profile=worker_profile,
        worker_model="n/a",
        body={"reason": reason, "judge_verdict": judge_verdict},
        next_action="HUMAN",
    )
    env["halt"] = True
    env["halt_id"] = f"hlt_{env['event_id'].replace('evt_','')}"
    await publish(env)
    # Persist explicit halt file alongside
    return env


def health() -> dict:
    """Quick status for /healthz + observation page."""
    cap = DAILY_CAP_USD
    spent = cost_today()
    return {
        "status": "ok" if spent < cap else "cap_reached",
        "spent_usd": round(spent, 4),
        "cap_usd": cap,
        "remaining_usd": round(max(0.0, cap - spent), 4),
        "routes_known": 7,
        "laws": {"L1": "active", "L2": "active", "L3": "active", "L4": "active"},
    }


# Singleton-ish module-level handle (Hermes is the orchestrator, no class needed)
hermes = type("HermesHandle", (), {
    "dispatch": staticmethod(dispatch),
    "health": staticmethod(health),
    "l4_scan": staticmethod(l4_scan),
    "l3_preflight": staticmethod(l3_preflight),
    "l2_check": staticmethod(l2_check),
})