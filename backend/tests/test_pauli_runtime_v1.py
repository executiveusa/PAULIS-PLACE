from fastapi.testclient import TestClient

from runtime.pauli_runtime_v1 import app


client = TestClient(app)


def payload():
    return {
        "mission": {
            "id": "mission-test-001",
            "title": "Runtime proof",
            "intent": "Prove one bounded runtime action",
            "requested_outcome": "Verified deterministic artifact",
        },
        "task": {
            "id": "task-test-001",
            "key": "execute",
            "title": "Execute proof",
            "description": "Create one deterministic artifact",
        },
        "prior_results": [],
        "contract": {
            "protocol": "pauli-runtime-v1",
            "requires_evidence": True,
            "self_certification": False,
        },
    }


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["protocol"] == "pauli-runtime-v1"


def test_execute_returns_verifiable_evidence_and_replays_without_duplicate_effect():
    first = client.post("/execute", json=payload())
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "verified"
    assert body["protocol"] == "pauli-runtime-v1"
    assert body["evidence"]
    assert all(test["passed"] for test in body["tests"])

    second = client.post("/execute", json=payload())
    assert second.status_code == 200
    replay = second.json()
    assert replay["status"] == "verified"
    assert replay["evidence"][0]["sha256"] == body["evidence"][0]["sha256"]


def test_rejects_missing_evidence_contract():
    data = payload()
    data["contract"]["requires_evidence"] = False
    response = client.post("/execute", json=data)
    assert response.status_code == 422
