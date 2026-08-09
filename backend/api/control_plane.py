"""Pauli's Place control-plane API.

These endpoints expose truthful operational state from the isolated `pauli`
Postgres schema. They deliberately fail soft when the schema has not been
migrated in a developer environment; production never fabricates state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import SETTINGS
from models.base import get_db
from services.agentforge_runtime import agentforge_runtime
from services.composio_service import composio_gateway

router = APIRouter(prefix="/api/control-plane", tags=["control-plane"])


class MissionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    intent: str = Field(min_length=2)
    requested_outcome: str = Field(min_length=2)
    language: str = Field(default="en", pattern="^(en|es-MX|mixed)$")
    mission_type: Optional[str] = None
    required_completion_level: str = "OUTCOME_ACHIEVED"
    autonomous_budget_cents: int = Field(default=0, ge=0, le=2500)
    organization_slug: str = Field(default=SETTINGS.pauli_default_org_slug, min_length=2)


def _schema_available(db: Session) -> bool:
    try:
        return bool(db.execute(text("select to_regnamespace('pauli') is not null")).scalar())
    except SQLAlchemyError:
        return False


def _org_id(db: Session, slug: str) -> Optional[str]:
    row = db.execute(
        text("select id::text from pauli.organizations where slug=:slug and status='active' limit 1"),
        {"slug": slug},
    ).first()
    return row[0] if row else None


@router.get("/status")
async def status(db: Session = Depends(get_db)) -> dict[str, Any]:
    schema_ready = _schema_available(db)
    forge = await agentforge_runtime.health()
    data: dict[str, Any] = {
        "product": "Pauli's Place",
        "status": "ready" if schema_ready else "needs_database_migration",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {"schema": "pauli", "ready": schema_ready},
        "providers": {
            "agentforge": forge.public_dict(),
            "composio": composio_gateway.health(),
        },
        "counts": {"organizations": 0, "agents": 0, "missions": 0, "approvals_pending": 0},
    }
    if not schema_ready:
        return data
    try:
        counts = db.execute(text("""
            select
              (select count(*) from pauli.organizations where status='active') as organizations,
              (select count(*) from pauli.agents) as agents,
              (select count(*) from pauli.missions where status not in ('CLOSED','FAILED','CANCELLED')) as missions,
              (select count(*) from pauli.approvals where status='pending') as approvals_pending
        """)).mappings().one()
        data["counts"] = dict(counts)
    except SQLAlchemyError as exc:
        data["status"] = "database_degraded"
        data["database"]["error"] = type(exc).__name__
    return data


@router.get("/agents")
def list_agents(organization_slug: str = SETTINGS.pauli_default_org_slug, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not _schema_available(db):
        return {"organization_slug": organization_slug, "agents": [], "status": "needs_database_migration"}
    org_id = _org_id(db, organization_slug)
    if not org_id:
        return {"organization_slug": organization_slug, "agents": [], "status": "organization_not_bootstrapped"}
    rows = db.execute(text("""
        select id::text, agent_key, name, role, specialty, status, world_location_key,
               last_heartbeat_at, skill_manifest, model_policy, runtime_policy
        from pauli.agents
        where organization_id = cast(:org_id as uuid)
        order by case when agent_key='pauli' then 0 else 1 end, name
    """), {"org_id": org_id}).mappings().all()
    return {"organization_slug": organization_slug, "agents": [dict(row) for row in rows], "status": "ready"}


@router.get("/missions")
def list_missions(
    organization_slug: str = SETTINGS.pauli_default_org_slug,
    limit: int = 30,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    if not _schema_available(db):
        return {"organization_slug": organization_slug, "missions": [], "status": "needs_database_migration"}
    org_id = _org_id(db, organization_slug)
    if not org_id:
        return {"organization_slug": organization_slug, "missions": [], "status": "organization_not_bootstrapped"}
    rows = db.execute(text("""
        select id::text, title, intent_original, requested_outcome, language, mission_type,
               required_completion_level, status, priority, autonomous_budget_cents, spent_cents,
               attempt_count, created_at, updated_at, started_at, completed_at
        from pauli.missions
        where organization_id = cast(:org_id as uuid)
        order by created_at desc
        limit :limit
    """), {"org_id": org_id, "limit": limit}).mappings().all()
    return {"organization_slug": organization_slug, "missions": [dict(row) for row in rows], "status": "ready"}


@router.post("/missions")
def create_mission(payload: MissionCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not _schema_available(db):
        raise HTTPException(status_code=503, detail="Pauli control-plane schema is not migrated")
    org_id = _org_id(db, payload.organization_slug)
    if not org_id:
        raise HTTPException(status_code=409, detail=f"Organization '{payload.organization_slug}' is not bootstrapped")
    mission_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    db.execute(text("""
        insert into pauli.missions (
          id, organization_id, correlation_id, title, intent_original, intent_normalized,
          language, mission_type, requested_outcome, required_completion_level,
          autonomous_budget_cents, status, policy_snapshot
        ) values (
          cast(:id as uuid), cast(:org_id as uuid), cast(:correlation_id as uuid), :title, :intent, :intent,
          :language, :mission_type, :outcome, :completion, :budget, 'INTENT',
          jsonb_build_object('zero_cost_reversible','AUTO','paid_reversible_ceiling_cents',2500,
            'external_email','HUMAN','outbound_call','HUMAN','production_deploy','HUMAN','frontier_model','HUMAN')
        )
    """), {
        "id": mission_id,
        "org_id": org_id,
        "correlation_id": correlation_id,
        "title": payload.title,
        "intent": payload.intent,
        "language": payload.language,
        "mission_type": payload.mission_type,
        "outcome": payload.requested_outcome,
        "completion": payload.required_completion_level,
        "budget": payload.autonomous_budget_cents,
    })
    db.execute(text("""
        insert into pauli.mission_events (
          organization_id, mission_id, correlation_id, event_type, source,
          public_summary, payload, visibility, idempotency_key
        ) values (
          cast(:org_id as uuid), cast(:mission_id as uuid), cast(:correlation_id as uuid),
          'MISSION.INTENT_RECEIVED', 'human', :summary,
          jsonb_build_object('language', :language), 'tenant', :idem
        )
    """), {
        "org_id": org_id,
        "mission_id": mission_id,
        "correlation_id": correlation_id,
        "summary": payload.intent[:500],
        "language": payload.language,
        "idem": f"intent:{mission_id}",
    })
    db.commit()
    return {
        "mission_id": mission_id,
        "correlation_id": correlation_id,
        "status": "INTENT",
        "title": payload.title,
        "requested_outcome": payload.requested_outcome,
    }


@router.get("/providers/agentforge")
async def agentforge_status() -> dict[str, Any]:
    return (await agentforge_runtime.health()).public_dict()
