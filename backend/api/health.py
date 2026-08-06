"""
Health & Hermes status router.
Endpoints:
  GET /healthz          — basic liveness for Vercel/hosting
  GET /api/hermes/health — full Hermes status (L1/L2/L3/L4 state, spend)
  GET /api/envelopes/recent?limit=20 — recent envelopes from icm/memory/ops/
  GET /api/envelopes/{event_id}     — load one envelope by id
  POST /api/envelopes/replay/{event_id}  — replay that route+stage
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services import hermes
from services.event_bus import replay, publish

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/api/hermes/health")
def hermes_health():
    return hermes.health()


def _ops_root() -> Path:
    return Path(__file__).resolve().parents[2] / "icm" / "memory" / "ops"


@router.get("/api/envelopes/recent")
def envelopes_recent(limit: int = Query(20, ge=1, le=200)):
    root = _ops_root()
    out: list[dict] = []
    if not root.exists():
        return {"envelopes": []}
    for day_dir in sorted(root.iterdir(), reverse=True):
        for f in sorted(day_dir.glob("*.json"), reverse=True):
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
                if len(out) >= limit:
                    return {"envelopes": out}
            except Exception:
                continue
    return {"envelopes": out}


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