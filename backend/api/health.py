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

from fastapi import APIRouter, HTTPException, Query

from services import hermes
from services.event_bus import publish, replay

router = APIRouter()

WORLD_ROSTER = [
    ("pauli", "Pauli", "Executive agent"),
    ("scout", "Scout", "Research"),
    ("strategist", "Strategist", "Strategy"),
    ("builder", "Builder", "Engineering"),
    ("critic", "Critic", "Gauntlet"),
    ("guardian", "Guardian", "Safety & policy"),
    ("publisher", "Publisher", "Deployment"),
    ("sales", "Sales", "Revenue"),
]
WORLD_POSITIONS = [
    [0.0, 0.0, 0.0], [-3.8, 0.0, -1.5], [3.8, 0.0, -1.5], [-5.4, 0.0, 2.2],
    [5.4, 0.0, 2.2], [-2.7, 0.0, 4.2], [2.7, 0.0, 4.2], [0.0, 0.0, 5.3],
]
WORLD_AGENT_IDS = {agent_id for agent_id, _, _ in WORLD_ROSTER}
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
    if explicit in WORLD_AGENT_IDS:
        return explicit

    profile = str(env.get("worker_profile") or "").lower().strip()
    if profile in WORLD_AGENT_IDS:
        return profile
    return PROFILE_TO_AGENT.get(profile)


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
    """Return only persisted event envelopes, newest event timestamp first."""
    return {"scenes": _recent_envelopes(limit)}


@router.get("/api/lounge/state")
def lounge_state():
    """Project configured identities plus activity inferred only from persisted events."""
    recent = _recent_envelopes(50)
    latest_by_agent: dict[str, dict] = {}
    for env in recent:
        agent_id = _target_agent(env)
        if agent_id and agent_id not in latest_by_agent:
            latest_by_agent[agent_id] = env

    avatars = []
    for index, (agent_id, name, role) in enumerate(WORLD_ROSTER):
        env = latest_by_agent.get(agent_id)
        state = "idle"
        model = "unassigned"
        activity_summary = None
        last_event_at = None
        if env:
            stage = str(env.get("stage") or "").upper()
            state = "blocked" if stage == "HALT" or env.get("halt") else "working"
            model = str(env.get("worker_model") or "unassigned")
            body = env.get("body") if isinstance(env.get("body"), dict) else {}
            activity_summary = body.get("public_summary") or body.get("response_text") or body.get("lounge_scene_intent")
            last_event_at = env.get("ts")

        avatars.append({
            "id": agent_id,
            "name": name,
            "role": role,
            "position": WORLD_POSITIONS[index],
            "model": model,
            "state": state,
            "activity_summary": activity_summary,
            "last_event_at": last_event_at,
        })

    return {
        "lounge": "Pauli's Place",
        "setting": "Operational world · persisted event state",
        "avatars": avatars,
        "schedule_cue": f"{len(recent)} verified events available" if recent else "No verified events yet",
        "source": "icm/memory/ops",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
