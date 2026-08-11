import time

import pytest
from fastapi import HTTPException

from services.approval_gate import issue_capability, verify_capability


def _configure(monkeypatch):
    monkeypatch.setenv("PAULI_APPROVAL_SIGNING_KEY", "test-only-signing-key-0123456789-abcdef")


def test_capability_accepts_exact_action_and_scope(monkeypatch):
    _configure(monkeypatch)
    token = issue_capability(
        actor="owner:test",
        action="approve",
        resource_ids=[12, 7, 12],
        nonce="nonce-001",
        ttl_seconds=60,
    )
    capability = verify_capability(token, expected_action="approve", expected_resource_ids=[7, 12])
    assert capability.actor == "owner:test"
    assert capability.action == "approve"
    assert capability.resource_ids == (7, 12)
    assert capability.nonce == "nonce-001"
    assert capability.exp > int(time.time())


def test_capability_rejects_action_mismatch(monkeypatch):
    _configure(monkeypatch)
    token = issue_capability(actor="owner:test", action="approve", resource_ids=[1], nonce="n1")
    with pytest.raises(HTTPException) as exc:
        verify_capability(token, expected_action="publish", expected_resource_ids=[1])
    assert exc.value.status_code == 403


def test_capability_rejects_resource_scope_mismatch(monkeypatch):
    _configure(monkeypatch)
    token = issue_capability(actor="owner:test", action="publish", resource_ids=[1], nonce="n2")
    with pytest.raises(HTTPException) as exc:
        verify_capability(token, expected_action="publish", expected_resource_ids=[1, 2])
    assert exc.value.status_code == 403


def test_capability_rejects_tampering(monkeypatch):
    _configure(monkeypatch)
    token = issue_capability(actor="owner:test", action="reject", resource_ids=[3], nonce="n3")
    encoded, signature = token.split(".", 1)
    tampered = f"{encoded[:-1]}A.{signature}"
    with pytest.raises(HTTPException) as exc:
        verify_capability(tampered, expected_action="reject", expected_resource_ids=[3])
    assert exc.value.status_code == 403


def test_missing_signing_authority_fails_closed(monkeypatch):
    monkeypatch.delenv("PAULI_APPROVAL_SIGNING_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        issue_capability(actor="owner:test", action="approve", resource_ids=[1], nonce="n4")
    assert exc.value.status_code == 503
