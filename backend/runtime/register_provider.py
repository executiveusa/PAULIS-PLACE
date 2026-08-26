"""Register and heartbeat the Pauli runtime provider in the control plane."""
from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone

from sqlalchemy import text

from models.base import SessionLocal

PROVIDER_KEY = os.getenv("PAULI_RUNTIME_PROVIDER_KEY", "pauli-runtime-local-v1")
PROVIDER_NAME = os.getenv("PAULI_RUNTIME_PROVIDER_NAME", "Pauli Runtime v1")
ENDPOINT = os.getenv("PAULI_RUNTIME_ENDPOINT", "http://127.0.0.1:8091/execute")


def register_once() -> dict[str, str]:
    db = SessionLocal()
    try:
        capabilities = {
            "isolated-filesystem": True,
            "deterministic-write": True,
            "sha256-evidence": True,
        }
        metadata = {
            "protocol": "pauli-runtime-v1",
            "host": socket.gethostname(),
            "managed_by": "pauli-runtime",
        }
        db.execute(
            text(
                """
                insert into pauli.runtime_providers(
                  provider_key,name,kind,endpoint_ref,capabilities,health_status,metadata,last_healthcheck_at
                ) values(
                  :key,:name,'agent_runtime',:endpoint,cast(:capabilities as jsonb),'healthy',cast(:metadata as jsonb),now()
                )
                on conflict (provider_key) do update set
                  name=excluded.name,
                  kind=excluded.kind,
                  endpoint_ref=excluded.endpoint_ref,
                  capabilities=excluded.capabilities,
                  health_status='healthy',
                  metadata=excluded.metadata,
                  last_healthcheck_at=now(),
                  updated_at=now()
                """
            ),
            {
                "key": PROVIDER_KEY,
                "name": PROVIDER_NAME,
                "endpoint": ENDPOINT,
                "capabilities": json.dumps(capabilities),
                "metadata": json.dumps(metadata),
            },
        )
        db.commit()
        return {
            "provider_key": PROVIDER_KEY,
            "status": "healthy",
            "endpoint": ENDPOINT,
            "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(register_once(), sort_keys=True))
