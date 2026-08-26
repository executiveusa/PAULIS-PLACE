"""Durable worker lease primitives for Pauli's Place.

These helpers keep task claims restart-safe without moving authority out of
Mission Control. A lease is advisory execution ownership for one bounded task.
"""
from __future__ import annotations

import os
import socket
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

DEFAULT_LEASE_SECONDS = max(30, int(os.getenv("PAULI_WORKER_LEASE_SECONDS", "120")))
WORKER_KEY = os.getenv("PAULI_WORKER_KEY") or f"{socket.gethostname()}:{os.getpid()}"


@dataclass(frozen=True)
class WorkerLease:
    id: str
    task_id: str
    worker_key: str
    lease_token: str
    expires_at: Any


def reclaim_expired_leases(db) -> int:
    rows = db.execute(
        text(
            """
            update pauli.worker_leases
               set status='expired', released_at=now()
             where status='active' and expires_at <= now()
         returning task_id
            """
        )
    ).all()
    for (task_id,) in rows:
        task = db.execute(
            text(
                """
                select t.id, t.organization_id, t.mission_id, m.correlation_id
                  from pauli.mission_tasks t
                  join pauli.missions m on m.id=t.mission_id
                 where t.id=:task
                 for update of t
                """
            ),
            {"task": task_id},
        ).mappings().first()
        if not task:
            continue
        changed = db.execute(
            text(
                """
                update pauli.mission_tasks
                   set status='recovering', updated_at=now()
                 where id=:task and status='running'
                """
            ),
            {"task": task_id},
        )
        if changed.rowcount != 1:
            continue
        db.execute(
            text("update pauli.missions set status='RECOVERING',updated_at=now() where id=:mission and status='EXECUTING'"),
            {"mission": task["mission_id"]},
        )
        db.execute(
            text(
                """
                insert into pauli.mission_events(
                  organization_id,mission_id,task_id,correlation_id,event_type,source,public_summary,payload,idempotency_key
                ) values(
                  :org,:mission,:task,:correlation,'TASK_LEASE_EXPIRED','worker-leases',
                  'Worker lease expired; task entered explicit recovery.',
                  jsonb_build_object('reason','worker_heartbeat_expired'),:idem
                ) on conflict (organization_id,idempotency_key) do nothing
                """
            ),
            {
                "org": task["organization_id"],
                "mission": task["mission_id"],
                "task": task["id"],
                "correlation": task["correlation_id"],
                "idem": f"lease-expired:{task['id']}",
            },
        )
    return len(rows)


def acquire_task_lease(db, task_id, organization_id, worker_key: str = WORKER_KEY, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> WorkerLease | None:
    lease_token = str(uuid.uuid4())
    row = db.execute(
        text(
            """
            insert into pauli.worker_leases(
              organization_id, task_id, worker_key, lease_token, status, expires_at, metadata
            )
            values(:org,:task,:worker,cast(:token as uuid),'active',now() + (:seconds || ' seconds')::interval,
                   jsonb_build_object('pid', :pid))
            on conflict do nothing
            returning id::text, task_id::text, worker_key, lease_token::text, expires_at
            """
        ),
        {
            "org": organization_id,
            "task": task_id,
            "worker": worker_key,
            "token": lease_token,
            "seconds": int(lease_seconds),
            "pid": os.getpid(),
        },
    ).mappings().first()
    return WorkerLease(**dict(row)) if row else None


def heartbeat_task_lease(db, lease: WorkerLease, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> bool:
    updated = db.execute(
        text(
            """
            update pauli.worker_leases
               set heartbeat_at=now(), expires_at=now() + (:seconds || ' seconds')::interval
             where id=cast(:id as uuid)
               and lease_token=cast(:token as uuid)
               and status='active'
            """
        ),
        {"id": lease.id, "token": lease.lease_token, "seconds": int(lease_seconds)},
    )
    return updated.rowcount == 1


def release_task_lease(db, lease: WorkerLease, recovered: bool = False) -> bool:
    updated = db.execute(
        text(
            """
            update pauli.worker_leases
               set status=:status, released_at=now(), heartbeat_at=now()
             where id=cast(:id as uuid)
               and lease_token=cast(:token as uuid)
               and status='active'
            """
        ),
        {"id": lease.id, "token": lease.lease_token, "status": "recovered" if recovered else "released"},
    )
    return updated.rowcount == 1
