"""
EVENT BUS — Spec §1.1 backbone
==============================
Redis pub/sub for cross-process events + in-process WebSocket fan-out for
the 3D lounge. Provides:
  - publish(envelope): broadcasts a typed event
  - subscribe(route, handler): registers a coroutine handler for a route
  - replay(event_id): loads an envelope from persistent operational memory

Envelope schema: see icm/context/ENVELOPES.md
"""
from __future__ import annotations
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from services.memory_store import memory_path

# Redis is optional in dev (fallback to in-process). Snap to SETTINGS.redis_url.
_redis = None
_subscriptions: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
_ws_connections: list = []  # WebSocket objects (FastAPI WebSocket)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_redis():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis  # type: ignore
        url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        _redis = redis.from_url(url, decode_responses=True)
        _redis.ping()  # raises if unreachable
    except Exception as e:
        print(f"[event_bus] redis unavailable, using in-process fallback: {e}")
        _redis = None
    return _redis


def new_event_id() -> str:
    return f"evt_{uuid.uuid4()}"


def build_envelope(
    route: str,
    stage: str,
    services_touched: list[str],
    blast_radius_usd: float,
    worker_profile: str,
    worker_model: str,
    body: dict,
    judge_verdict: Optional[str] = None,
    judge_model: Optional[str] = None,
    next_action: Optional[str] = None,
    event_id: Optional[str] = None,
) -> dict:
    return {
        "event_id": event_id or new_event_id(),
        "route": route,
        "stage": stage,
        "ts": _now_iso(),
        "services_touched": services_touched[:3],  # L2 cap = 3
        "blast_radius_usd": float(blast_radius_usd),
        "worker_profile": worker_profile,
        "worker_model": worker_model,
        "judge_verdict": judge_verdict,
        "judge_model": judge_model,
        "envelope_version": "1.0",
        "next_action": next_action,
        "body": body,
    }


def _persist(envelope: dict) -> Path:
    """Persist envelope under the configured shared operational-memory root."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = memory_path("ops", day)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{envelope['event_id']}.json"
    out_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return out_path


async def publish(envelope: dict) -> None:
    """Publish an envelope to all subscribers + WebSocket fans + persist."""
    _persist(envelope)
    route = envelope["route"]

    handlers = list(_subscriptions.get(route, [])) + list(_subscriptions.get("*", []))
    if handlers:
        await asyncio.gather(*(_safe_call(h, envelope) for h in handlers))

    if _ws_connections:
        msg = json.dumps({"type": "event", "envelope": envelope})
        await asyncio.gather(*(_safe_ws_send(ws, msg) for ws in list(_ws_connections)))

    r = _ensure_redis()
    if r is not None:
        try:
            r.publish(f"yappy:{route}", json.dumps(envelope))
        except Exception as e:
            print(f"[event_bus] redis publish failed: {e}")


async def _safe_call(handler: Callable[[dict], Awaitable[None]], env: dict) -> None:
    try:
        await handler(env)
    except Exception as e:
        print(f"[event_bus] handler error: {e}")


async def _safe_ws_send(ws: Any, msg: str) -> None:
    try:
        await ws.send_text(msg)
    except Exception:
        try:
            _ws_connections.remove(ws)
        except ValueError:
            pass


def subscribe(route: str, handler: Callable[[dict], Awaitable[None]]) -> None:
    _subscriptions.setdefault(route, []).append(handler)


def register_websocket(ws: Any) -> None:
    _ws_connections.append(ws)


def unregister_websocket(ws: Any) -> None:
    try:
        _ws_connections.remove(ws)
    except ValueError:
        pass


def replay(event_id: str) -> Optional[dict]:
    """Load an envelope by event_id from persistent operational memory."""
    ops_dir = memory_path("ops")
    if not ops_dir.exists():
        return None
    for day_dir in sorted(ops_dir.iterdir(), reverse=True):
        if not day_dir.is_dir():
            continue
        candidate = day_dir / f"{event_id}.json"
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
    return None
