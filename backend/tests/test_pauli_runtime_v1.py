from fastapi.testclient import TestClient

from runtime.capability_guard import redact
from runtime.pauli_runtime_v1 import app


client = TestClient(app)


def payload(task_id: str = "task-test-001"):
    return {
        "mission": {
            "id": "mission-test-001",
            "title": "Runtime proof",
            "intent": "Prove one bounded runtime action",
            "requested_outcome": "Verified deterministic artifact",
        },
        "task": {
            "id": task_id,
            "key": "execute",
            "title": "Execute proof",
            "description": "Create one deterministic artifact",
            "required_capabilities": ["isolated-filesystem", "deterministic-write"],
        },
        "prior_results": [],
        "contract": {
            "protocol": "pauli-runtime-v1",
            "requires_evidence": True,
            "self_certification": False,
            "risk_class": "SAFE",
            "granted_capabilities": ["isolated-filesystem", "deterministic-write"],
            "revoked_capabilities": [],
            "estimated_spend_cents": 0,
            "mission_remaining_budget_cents": 100,
            "action_spend_ceiling_cents": 100,
        },
    }


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["protocol"] == "pauli-runtime-v1"
    assert "capability-enforcement" in body["capabilities"]


def test_execute_returns_verifiable_evidence_and_replays_without_duplicate_effect():
    first = client.post("/execute", json=payload("task-capability-ok"))
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "verified"
    assert body["capability_decision"]["allowed"] is True
    assert body["evidence"]
    assert all(test["passed"] for test in body["tests"])

    second = client.post("/execute", json=payload("task-capability-ok"))
    assert second.status_code == 200
    replay = second.json()
    assert replay["idempotent_replay"] is True
    assert replay["evidence"][0]["sha256"] == body["evidence"][0]["sha256"]


def test_rejects_missing_evidence_contract():
    data = payload("task-no-evidence")
    data["contract"]["requires_evidence"] = False
    response = client.post("/execute", json=data)
    assert response.status_code == 422


def test_denies_missing_or_revoked_capability():
    missing = payload("task-missing-cap")
    missing["contract"]["granted_capabilities"] = ["isolated-filesystem"]
    response = client.post("/execute", json=missing)
    assert response.status_code == 403
    assert "missing_capability" in str(response.json()["detail"]["reason"])

    revoked = payload("task-revoked-cap")
    revoked["contract"]["revoked_capabilities"] = ["deterministic-write"]
    response = client.post("/execute", json=revoked)
    assert response.status_code == 403
    assert "revoked_capability" in str(response.json()["detail"]["reason"])


def test_consequential_action_requires_persisted_approval_receipt():
    data = payload("task-approval")
    data["contract"]["risk_class"] = "CAUTION"
    response = client.post("/execute", json=data)
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "persisted_approval_required"

    data["contract"]["approval"] = {"status": "approved", "approval_id": "approval-001"}
    response = client.post("/execute", json=data)
    assert response.status_code == 200


def test_budget_overflow_is_denied():
    data = payload("task-budget")
    data["contract"]["estimated_spend_cents"] = 101
    response = client.post("/execute", json=data)
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "mission_budget_exceeded"


def test_secret_redaction_is_recursive():
    safe = redact({"api_key": "secret", "nested": {"authorization": "Bearer x", "ok": "value"}})
    assert safe["api_key"] == "[REDACTED]"
    assert safe["nested"]["authorization"] == "[REDACTED]"
    assert safe["nested"]["ok"] == "value"
