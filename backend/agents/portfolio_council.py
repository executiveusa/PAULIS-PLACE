"""Pauliverse portfolio council — seven independent perspectives + Hermes synthesis.

The council is deliberately bounded. Each perspective sees the same proposal/context
and writes a structured case. A distinct judge profile then synthesizes without
silencing dissent. Results are persisted as evidence and emitted to the event bus.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.profile_router import call_profile, ensure_distinct_profiles
from services.event_bus import build_envelope, publish

ROLE_PROFILES: tuple[tuple[str, str, str], ...] = (
    ("operator", "plan", "Find the smallest executable external test and concrete operating path."),
    ("cfo", "score", "Evaluate unit economics, cash conversion, capital exposure, support burden, and stop conditions."),
    ("consolidator", "docs", "Find existing repositories, capabilities, assets, or processes that make new build unnecessary."),
    ("red_team", "test", "Attack the thesis. Identify market, technical, security, legal, operational, and reputation failure modes."),
    ("evidence_judge", "score", "Separate observed evidence, owner decisions, assumptions, inference, anecdotes, and unsupported claims."),
    ("mission_guardian", "docs", "Protect social-purpose integrity, entity separation, rights, and public-claim accuracy."),
    ("opportunity_advocate", "write_short", "Make the strongest good-faith case for acting now and identify asymmetric upside."),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _decision_root() -> Path:
    return _repo_root() / "icm" / "memory" / "portfolio-decisions"


def _evidence_ref(path: Path) -> str:
    """Return a stable repo-relative ref when possible, otherwise a truthful path.

    Tests and alternate storage adapters may point the decision store outside the
    repository root. That must not make an otherwise valid receipt disappear.
    """
    try:
        return str(path.relative_to(_repo_root()))
    except ValueError:
        return str(path)


def _parse_json(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text.strip("` ")
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"raw": parsed}
    except Exception:
        first, last = text.find("{"), text.rfind("}")
        if first >= 0 and last > first:
            try:
                parsed = json.loads(text[first:last + 1])
                return parsed if isinstance(parsed, dict) else {"raw": parsed}
            except Exception:
                pass
        return {"raw": text[:2000]}


def _persist(decision_id: str, payload: dict) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _decision_root() / day
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{decision_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def recent_deliberations(limit: int = 20) -> list[dict]:
    root = _decision_root()
    if not root.exists():
        return []
    items: list[dict] = []
    for file in root.glob("*/*.json"):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        payload["_evidence_ref"] = _evidence_ref(file)
        items.append(payload)
    items.sort(key=lambda item: str(item.get("ts") or ""), reverse=True)
    return items[: max(1, min(limit, 100))]


async def deliberate(*, question: str, proposal: str, context: dict | str | None = None) -> dict:
    context_text = json.dumps(context, ensure_ascii=False) if isinstance(context, dict) else str(context or "")
    cases: dict[str, dict] = {}
    models: dict[str, str] = {}

    for role, profile, mandate in ROLE_PROFILES:
        response = await call_profile(
            profile,
            system_prompt=f"You are the {role.replace('_', ' ').upper()} in a bounded portfolio council. Be specific, skeptical, and concise.",
            prompt=(
                f"QUESTION:\n{question}\n\nPROPOSAL:\n{proposal}\n\nCONTEXT:\n{context_text}\n\n"
                f"MANDATE:\n{mandate}\n\n"
                "Return JSON with keys: position, evidence_used, assumptions, risks, recommendation, stop_condition."
            ),
            temperature=0.2,
            response_format_json=True,
        )
        cases[role] = _parse_json(response.get("content"))
        models[role] = str(response.get("model") or "unknown")

    # Judge must use a distinct profile from every perspective profile that could
    # resolve to the same preferred model. The registry currently satisfies this;
    # fail explicitly if that invariant changes later.
    for _, profile, _ in ROLE_PROFILES:
        if profile != "judge":
            ensure_distinct_profiles(profile, "judge")

    synthesis = await call_profile(
        "judge",
        system_prompt="You are Hermes' senior portfolio synthesizer. Preserve material dissent. Do not average objections away.",
        prompt=(
            f"QUESTION:\n{question}\n\nPROPOSAL:\n{proposal}\n\nCONTEXT:\n{context_text}\n\n"
            f"INDEPENDENT CASES:\n{json.dumps(cases, ensure_ascii=False)}\n\n"
            "Return JSON with: decision (ACTIVATE|TEST|CONSOLIDATE|ARCHIVE|REJECT), reasoning, agreements, disagreements, "
            "smallest_test, stop_conditions, owner_gate, financial_route, next_action."
        ),
        temperature=0.15,
        response_format_json=True,
    )
    synthesis_payload = _parse_json(synthesis.get("content"))

    decision_id = f"pc_{uuid.uuid4()}"
    payload = {
        "decision_id": decision_id,
        "question": question,
        "proposal": proposal,
        "context": context if context is not None else {},
        "perspectives": cases,
        "models": models,
        "synthesis": synthesis_payload,
        "synthesis_model": synthesis.get("model"),
        "ts": _now_iso(),
        "status": "PROPOSED" if synthesis_payload.get("owner_gate") else "DECIDED",
    }
    evidence_path = _persist(decision_id, payload)
    payload["evidence_ref"] = _evidence_ref(evidence_path)

    envelope = build_envelope(
        route="R-03.COUNCIL.PORTFOLIO_DECISION",
        stage="LOCK",
        services_touched=["paulis-place", "hermes"],
        blast_radius_usd=0.05,
        worker_profile="judge",
        worker_model=str(synthesis.get("model") or "unknown"),
        body=payload,
        judge_verdict=str(synthesis_payload.get("decision") or "TEST").lower(),
        judge_model=str(synthesis.get("model") or "unknown"),
        next_action=str(synthesis_payload.get("next_action") or "OWNER_REVIEW"),
    )
    await publish(envelope)
    return envelope
