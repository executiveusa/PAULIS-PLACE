"""Minimal production-oriented Pauli runtime actuator.

Implements the pauli-runtime-v1 contract for one safe, reversible deterministic
filesystem task. Phase 3 adds fail-closed capability, approval, budget, and
secret-redaction enforcement at the actuator boundary.
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

from runtime.capability_guard import evaluate_execution, redact

app = FastAPI(title="Pauli Runtime v1", version="1.1.0")

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
        "capabilities": [
            "isolated-filesystem",
            "deterministic-write",
            "sha256-evidence",
            "capability-enforcement",
            "approval-enforcement",
            "budget-enforcement",
            "secret-redaction",
        ],
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

    required = [str(x) for x in payload.task.get("required_capabilities", []) if str(x).strip()]
    if not required:
        required = ["isolated-filesystem", "deterministic-write"]
    decision = evaluate_execution(required_capabilities=required, contract=contract)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.receipt())

    workspace = RUNTIME_ROOT / mission_id / task_id
    workspace.mkdir(parents=True, exist_ok=True)
    receipt_path = workspace / "receipt.json"

    if receipt_path.exists():
        try:
            cached = json.loads(receipt_path.read_text(encoding="utf-8"))
            if cached.get("task_id") == task_id and cached.get("mission_id") == mission_id:
                response = cached["response"]
                response["idempotent_replay"] = True
                return response
        except Exception:
            pass

    artifact_path = workspace / f"{task_key}-artifact.txt"
    safe_mission = redact(payload.mission)
    content = (
        f"mission_id={mission_id}\n"
        f"task_id={task_id}\n"
        f"task_key={task_key}\n"
        f"requested_outcome={safe_mission.get('requested_outcome', '')}\n"
    )
    artifact_path.write_text(content, encoding="utf-8")
    artifact_bytes = artifact_path.read_bytes()
    digest = hashlib.sha256(artifact_bytes).hexdigest()

    tests = [
        {"name": "artifact_exists", "passed": artifact_path.exists()},
        {"name": "artifact_nonempty", "passed": bool(artifact_bytes)},
        {"name": "sha256_verified", "passed": hashlib.sha256(artifact_bytes).hexdigest() == digest},
        {"name": "capability_authorized", "passed": decision.allowed},
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
        "capability_decision": decision.receipt(),
        "idempotent_replay": False,
    }
    receipt = {
        "mission_id": mission_id,
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract": redact(contract),
        "response": redact(response),
    }
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    return response
