"""
Health, Hermes, and Pauli's World status router.

Truth-only endpoints:
  GET /healthz
  GET /api/hermes/health
  GET /api/envelopes/recent?limit=20
  GET /api/envelopes/{event_id}
  POST /api/envelopes/replay/{event_id}
  GET /api/lounge/state
  GET /api/lounge/scenes?limit=20
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import SETTINGS
from models.base import get_db
from services import hermes
from services.event_bus import publish, replay

router = APIRouter()

PROFILE_TO_AGENT = {
    "executive": "pauli",
    "orchestrator": "pauli",
    "research": "scout",
    "scan": "scout",
    "strategy": "strategist",
    "write_short": "builder",
    "builder": "builder",
    "score": "critic",
    "critic": "critic",
    "judge": "guardian",
    "guardian": "guardian",
    "publish": "publisher",
    "publisher": "publisher",
    "sales": "sales",
    "revenue": "sales",
}
DEFAULT_POSITIONS: list[list[float]] = [
    [0.0, 0.0, 0.0], [-3.8, 0.0, -1.5], [3.8, 0.0, -1.5], [-5.4, 0.0, 2.2],
    [5.4, 0.0, 2.2], [-2.7, 0.0, 4.2], [2.7, 0.0, 4.2], [0.0, 0.0, 5.3],
]


def _ops_root() -> Path:
    return Path(__file__).resolve().parents[2] / "icm" / "memory" / "ops"


def _event_ts(env: dict) -> datetime:
    raw = env.get("ts")
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _recent_envelopes(limit: int) -> list[dict]:
    root = _ops_root()
    if not root.exists():
        return []
    events: list[dict] = []
    for day_dir in root.iterdir():
        if not day_dir.is_dir():
            continue
        for path in day_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    events.append(payload)
            except (OSError, json.JSONDecodeError):
                continue
    events.sort(key=_event_ts, reverse=True)
    return events[:limit]


def _target_agent(env: dict) -> str | None:
    body = env.get("body") if isinstance(env.get("body"), dict) else {}
    explicit = str(body.get("target_avatar") or body.get("agent_id") or "").lower().strip()
    if explicit:
        return explicit
    profile = str(env.get("worker_profile") or "").lower().strip()
    return PROFILE_TO_AGENT.get(profile, profile or None)


def _fallback_position(index: int) -> list[float]:
    return DEFAULT_POSITIONS[index % len(DEFAULT_POSITIONS)]


def _normalize_position(value: Any, index: int) -> list[float]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return [float(value[0]), float(value[1]), float(value[2])]
        except (TypeError, ValueError):
            pass
    if isinstance(value, dict):
        try:
            if all(axis in value for axis in ("x", "y", "z")):
                return [float(value["x"]), float(value["y"]), float(value["z"])]
        except (TypeError, ValueError):
            pass
    return _fallback_position(index)


def _avatar_from_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    state = str(row.get("presence_state") or row.get("agent_status") or "offline")
    last_event_at = row.get("presence_updated_at") or row.get("last_heartbeat_at")
    if last_event_at is not None and not isinstance(last_event_at, str):
        last_event_at = last_event_at.isoformat()
    return {
        "id": str(row.get("agent_key") or row.get("database_id") or "unknown"),
        "database_id": row.get("database_id"),
        "name": str(row.get("name") or row.get("agent_key") or "Agent"),
        "role": str(row.get("role") or "Agent"),
        "position": _normalize_position(row.get("position"), index),
        "model": str(row.get("model_key") or "unassigned"),
        "state": state,
        "activity_summary": row.get("activity_summary"),
        "last_event_at": last_event_at,
        "location": {"key": row.get("location_key") or row.get("world_location_key"), "name": row.get("location_name")},
        "mission": {"id": row.get("mission_id"), "title": row.get("mission_title"), "status": row.get("mission_status")} if row.get("mission_id") else None,
    }


def _canonical_lounge_state(db: Session, organization_slug: str) -> dict[str, Any] | None:
    schema_ready = bool(db.execute(text("select to_regnamespace(:schema) is not null"), {"schema": SETTINGS.pauli_db_schema}).scalar())
    if not schema_ready:
        return None
    organization = db.execute(
        text("select id::text, name from pauli.organizations where slug=:slug and status='active' limit 1"),
        {"slug": organization_slug},
    ).mappings().first()
    if not organization:
        return None
    org_id = organization["id"]
    rows = db.execute(text("""
        select a.id::text as database_id, a.agent_key, a.name, a.role,
               a.status as agent_status, a.world_location_key, a.last_heartbeat_at,
               wp.state as presence_state, wp.position, wp.activity_summary,
               wp.updated_at as presence_updated_at,
               wl.location_key, wl.name as location_name,
               m.id::text as mission_id, m.title as mission_title, m.status as mission_status,
               latest_run.model_key
        from pauli.agents a
        left join pauli.world_presence wp on wp.organization_id=a.organization_id and wp.agent_id=a.id
        left join pauli.world_locations wl on wl.id=wp.location_id
        left join pauli.missions m on m.id=wp.mission_id
        left join lateral (
          select rr.model_key from pauli.runtime_runs rr
          where rr.organization_id=a.organization_id and rr.agent_id=a.id
          order by rr.created_at desc limit 1
        ) latest_run on true
        where a.organization_id=cast(:org_id as uuid)
        order by case when a.agent_key='pauli' then 0 else 1 end, a.name
    """), {"org_id": org_id}).mappings().all()
    counts = db.execute(text("""
        select
          (select count(*) from pauli.missions where organization_id=cast(:org_id as uuid) and status not in ('CLOSED','FAILED','CANCELLED')) as active_missions,
          (select count(*) from pauli.approvals where organization_id=cast(:org_id as uuid) and status='pending') as approvals_pending,
          (select count(*) from pauli.evidence_receipts where organization_id=cast(:org_id as uuid) and status='verified') as verified_evidence
    """), {"org_id": org_id}).mappings().one()
    avatars = [_avatar_from_row(dict(row), index) for index, row in enumerate(rows)]
    return {
        "lounge": "Pauli's Place",
        "setting": f"{organization['name']} · canonical operational state",
        "avatars": avatars,
        "schedule_cue": f"{len(avatars)} agents · {counts['active_missions']} active missions · {counts['approvals_pending']} approvals pending",
        "counts": dict(counts),
        "organization_slug": organization_slug,
        "source": "pauli.control_plane",
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/healthz")
def healthz():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/hermes/health")
def hermes_health():
    return hermes.health()


@router.get("/api/envelopes/recent")
def envelopes_recent(limit: int = Query(20, ge=1, le=200)):
    return {"envelopes": _recent_envelopes(limit)}


@router.get("/api/envelopes/{event_id}")
def envelope_get(event_id: str):
    env = replay(event_id)
    if env is None:
        raise HTTPException(404, detail=f"envelope {event_id} not found")
    return env


@router.post("/api/envelopes/replay/{event_id}")
async def envelope_replay(event_id: str):
    env = replay(event_id)
    if env is None:
        raise HTTPException(404, detail=f"envelope {event_id} not found")
    env = dict(env)
    env["event_id"] = f"evt_replay_{event_id.replace('evt_','')}"
    await publish(env)
    return {"status": "republished", "event_id": env["event_id"]}


@router.get("/api/lounge/scenes")
def lounge_scenes(limit: int = Query(20, ge=1, le=100)):
    return {"scenes": _recent_envelopes(limit), "source": "icm/memory/ops:legacy-feed"}


@router.get("/api/lounge/state")
def lounge_state(organization_slug: str = SETTINGS.pauli_default_org_slug, db: Session = Depends(get_db)):
    try:
        state = _canonical_lounge_state(db, organization_slug)
    except SQLAlchemyError as exc:
        return {
            "lounge": "Pauli's Place",
            "setting": "Operational world · canonical control plane unavailable",
            "avatars": [],
            "schedule_cue": "Control-plane database unavailable",
            "organization_slug": organization_slug,
            "source": "pauli.control_plane",
            "status": "database_degraded",
            "error": type(exc).__name__,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    if state is not None:
        return state
    return {
        "lounge": "Pauli's Place",
        "setting": "Operational world · canonical control plane not bootstrapped",
        "avatars": [],
        "schedule_cue": "No canonical world state available",
        "organization_slug": organization_slug,
        "source": "pauli.control_plane",
        "status": "needs_database_migration_or_bootstrap",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
