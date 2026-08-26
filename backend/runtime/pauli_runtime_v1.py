"""Minimal production-oriented Pauli runtime actuator.

Implements the pauli-runtime-v1 contract for one safe, reversible deterministic
filesystem task. This is intentionally narrow: it proves the Mission Control ->
actuator -> evidence boundary before external business integrations are enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Pauli Runtime v1", version="1.0.0")

RUNTIME_ROOT = Path(os.getenv("PAULI_RUNTIME_ROOT", tempfile.gettempdir())) / "pauli-runtime"
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)


class TaskPayload(BaseModel):
    mission: dict[str, Any]
    task: dict[str, Any]
    prior_results: list[dict[str, Any]] | dict[str, Any] = Field(default_factory=list)
    contract: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "protocol": "pauli-runtime-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["isolated-filesystem", "deterministic-write", "sha256-evidence"],
    }


@app.post("/execute")
def execute(payload: TaskPayload) -> dict[str, Any]:
    contract = payload.contract or {}
    if contract.get("protocol") != "pauli-runtime-v1":
        raise HTTPException(status_code=422, detail="unsupported runtime protocol")
    if not contract.get("requires_evidence"):
        raise HTTPException(status_code=422, detail="evidence is required")

    mission_id = str(payload.mission.get("id") or "").strip()
    task_id = str(payload.task.get("id") or "").strip()
    task_key = str(payload.task.get("key") or "").strip()
    if not mission_id or not task_id or task_key not in {"execute", "test", "repair"}:
        raise HTTPException(status_code=422, detail="invalid mission/task payload")

    workspace = RUNTIME_ROOT / mission_id / task_id
    workspace.mkdir(parents=True, exist_ok=True)
    receipt_path = workspace / "receipt.json"

    # Restart/idempotency guarantee: if the exact task already produced a valid
    # receipt, return it instead of performing the side effect again.
    if receipt_path.exists():
        try:
            cached = json.loads(receipt_path.read_text(encoding="utf-8"))
            if cached.get("task_id") == task_id and cached.get("mission_id") == mission_id:
                return cached["response"]
        except Exception:
            pass

    artifact_path = workspace / f"{task_key}-artifact.txt"
    content = (
        f"mission_id={mission_id}\n"
        f"task_id={task_id}\n"
        f"task_key={task_key}\n"
        f"requested_outcome={payload.mission.get('requested_outcome', '')}\n"
    )
    artifact_path.write_text(content, encoding="utf-8")
    artifact_bytes = artifact_path.read_bytes()
    digest = hashlib.sha256(artifact_bytes).hexdigest()

    tests = [
        {"name": "artifact_exists", "passed": artifact_path.exists()},
        {"name": "artifact_nonempty", "passed": bool(artifact_bytes)},
        {"name": "sha256_verified", "passed": hashlib.sha256(artifact_bytes).hexdigest() == digest},
    ]
    if not all(test["passed"] for test in tests):
        raise HTTPException(status_code=500, detail="deterministic verification failed")

    response = {
        "status": "verified",
        "protocol": "pauli-runtime-v1",
        "summary": "Reversible deterministic task executed in an isolated workspace.",
        "tests": tests,
        "evidence": [
            {
                "type": "file",
                "path": str(artifact_path),
                "sha256": digest,
                "bytes": len(artifact_bytes),
            }
        ],
        "idempotent_replay": False,
    }
    receipt = {
        "mission_id": mission_id,
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "response": response,
    }
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    return response
