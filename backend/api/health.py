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
from services.event_bus import replay, publish

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


def _ops_root() -> Path:
    return Path(__file__).resolve().parents[2] / "icm" / "memory" / "ops"


def _recent_envelopes(limit: int) -> list[dict]:
    root = _ops_root()
    out: list[dict] = []
    if not root.exists():
        return out
    for day_dir in sorted(root.iterdir(), reverse=True):
        if not day_dir.is_dir():
            continue
        for f in sorted(day_dir.glob("*.json"), reverse=True):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
                if len(out) >= limit:
                    return out
            except Exception:
                continue
    return out


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
    """Return only persisted, verified event envelopes. Never fabricate scenes."""
    return {"scenes": _recent_envelopes(limit)}


@router.get("/api/lounge/state")
def lounge_state():
    """Project configured agent identities plus activity inferred only from real persisted events."""
    recent = _recent_envelopes(50)
    latest_by_profile: dict[str, dict] = {}
    for env in recent:
        profile = str(env.get("worker_profile") or "").lower()
        if profile and profile not in latest_by_profile:
            latest_by_profile[profile] = env

    avatars = []
    for index, (agent_id, name, role) in enumerate(WORLD_ROSTER):
        env = latest_by_profile.get(agent_id)
        state = "idle"
        model = "unassigned"
        if env:
            stage = str(env.get("stage") or "").upper()
            state = "blocked" if stage == "HALT" or env.get("halt") else "working"
            model = str(env.get("worker_model") or "unassigned")
        avatars.append({
            "id": agent_id,
            "name": name,
            "role": role,
            "position": WORLD_POSITIONS[index],
            "model": model,
            "state": state,
        })

    return {
        "lounge": "Pauli's Place",
        "setting": "Operational world · persisted event state",
        "avatars": avatars,
        "schedule_cue": f"{len(recent)} verified events available" if recent else "No verified events yet",
        "source": "icm/memory/ops",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
