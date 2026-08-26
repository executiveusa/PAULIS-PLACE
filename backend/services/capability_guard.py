"""Capability and approval guard for Pauli's Place.

All external/actuator execution should pass through this deny-by-default layer.
It evaluates task-required capabilities, active grants, risk, persisted approvals,
and mission/grant spend ceilings, then records an auditable decision receipt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy import text


CONSEQUENTIAL_RISKS = {"CAUTION", "DANGEROUS", "CRITICAL"}


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    decision: str
    capability_key: str
    risk_class: str
    reason: str
    grant_id: str | None = None
    approval_id: str | None = None
    estimated_spend_cents: int = 0


def _agent_id_for_task(db, task: dict[str, Any]):
    if task.get("assigned_agent_id"):
        return task["assigned_agent_id"]
    return db.execute(
        text("select id from pauli.agents where organization_id=:org and agent_key='pauli' limit 1"),
        {"org": task["organization_id"]},
    ).scalar_one_or_none()


def _record(db, task: dict[str, Any], agent_id, decision: CapabilityDecision) -> None:
    db.execute(
        text(
            """
            insert into pauli.capability_decisions(
              organization_id, mission_id, task_id, agent_id, capability_key,
              decision, risk_class, reason, grant_id, approval_id, estimated_spend_cents
            ) values(
              :org,:mission,:task,:agent,:capability,:decision,:risk,:reason,
              cast(:grant as uuid),cast(:approval as uuid),:spend
            )
            """
        ),
        {
            "org": task["organization_id"],
            "mission": task["mission_id"],
            "task": task["id"],
            "agent": agent_id,
            "capability": decision.capability_key,
            "decision": decision.decision,
            "risk": decision.risk_class,
            "reason": decision.reason,
            "grant": decision.grant_id,
            "approval": decision.approval_id,
            "spend": decision.estimated_spend_cents,
        },
    )


def evaluate_capability(
    db,
    task: dict[str, Any],
    capability_key: str,
    *,
    estimated_spend_cents: int = 0,
) -> CapabilityDecision:
    agent_id = _agent_id_for_task(db, task)
    grant = db.execute(
        text(
            """
            select id::text, risk_class, max_spend_cents, status
              from pauli.capability_grants
             where organization_id=:org
               and capability_key=:capability
               and status='active'
               and (agent_id is null or agent_id=:agent)
               and (expires_at is null or expires_at > now())
             order by (agent_id is not null) desc, created_at desc
             limit 1
            """
        ),
        {"org": task["organization_id"], "capability": capability_key, "agent": agent_id},
    ).mappings().first()

    if not grant:
        decision = CapabilityDecision(
            allowed=False,
            decision="deny",
            capability_key=capability_key,
            risk_class="SAFE",
            reason="No active capability grant exists for this task/agent.",
            estimated_spend_cents=max(0, int(estimated_spend_cents)),
        )
        _record(db, task, agent_id, decision)
        return decision

    risk = str(grant["risk_class"]).upper()
    spend = max(0, int(estimated_spend_cents))

    mission = db.execute(
        text("select autonomous_budget_cents, spent_cents from pauli.missions where id=:mission"),
        {"mission": task["mission_id"]},
    ).mappings().one()
    remaining = max(0, int(mission["autonomous_budget_cents"] or 0) - int(mission["spent_cents"] or 0))
    if spend > remaining:
        decision = CapabilityDecision(False, "deny", capability_key, risk, "Mission autonomous budget would be exceeded.", grant["id"], None, spend)
        _record(db, task, agent_id, decision)
        return decision

    grant_max = grant["max_spend_cents"]
    if grant_max is not None and spend > int(grant_max):
        decision = CapabilityDecision(False, "deny", capability_key, risk, "Capability grant spend ceiling would be exceeded.", grant["id"], None, spend)
        _record(db, task, agent_id, decision)
        return decision

    approval_id = None
    if risk in CONSEQUENTIAL_RISKS:
        approval = db.execute(
            text(
                """
                select id::text
                  from pauli.approvals
                 where organization_id=:org
                   and (mission_id=:mission or mission_id is null)
                   and (task_id=:task or task_id is null)
                   and action_class=:capability
                   and status='approved'
                   and uses < max_uses
                   and (expires_at is null or expires_at > now())
                   and (max_spend_cents is null or max_spend_cents >= :spend)
                 order by decided_at desc nulls last, created_at desc
                 limit 1
                """
            ),
            {
                "org": task["organization_id"],
                "mission": task["mission_id"],
                "task": task["id"],
                "capability": capability_key,
                "spend": spend,
            },
        ).mappings().first()
        if not approval:
            decision = CapabilityDecision(False, "approval_required", capability_key, risk, "Persisted approval is required for consequential capability use.", grant["id"], None, spend)
            _record(db, task, agent_id, decision)
            return decision
        approval_id = approval["id"]

    decision = CapabilityDecision(True, "allow", capability_key, risk, "Capability grant and execution policy satisfied.", grant["id"], approval_id, spend)
    _record(db, task, agent_id, decision)
    return decision


def authorize_task_capabilities(db, task: dict[str, Any], *, estimated_spend_cents: int = 0) -> list[CapabilityDecision]:
    capabilities: Iterable[str] = task.get("required_capabilities") or []
    decisions: list[CapabilityDecision] = []
    for capability in capabilities:
        decision = evaluate_capability(db, task, str(capability), estimated_spend_cents=estimated_spend_cents)
        decisions.append(decision)
        if not decision.allowed:
            break
    return decisions


def consume_approval_and_spend(db, task: dict[str, Any], decisions: list[CapabilityDecision]) -> None:
    spend = max((d.estimated_spend_cents for d in decisions), default=0)
    approvals = {d.approval_id for d in decisions if d.approval_id}
    for approval_id in approvals:
        db.execute(
            text(
                """
                update pauli.approvals
                   set uses=uses+1,
                       status=case when uses+1 >= max_uses then 'consumed' else status end
                 where id=cast(:id as uuid) and status='approved' and uses < max_uses
                """
            ),
            {"id": approval_id},
        )
    if spend:
        db.execute(text("update pauli.missions set spent_cents=spent_cents+:spend,updated_at=now() where id=:mission"), {"spend": spend, "mission": task["mission_id"]})


def redact_secrets(value: Any) -> Any:
    """Best-effort structural redaction before data enters logs/receipts/prompts."""
    secret_markers = ("secret", "token", "password", "api_key", "apikey", "authorization", "cookie")
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).lower()
            result[key] = "[REDACTED]" if any(marker in normalized for marker in secret_markers) else redact_secrets(item)
        return result
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value
