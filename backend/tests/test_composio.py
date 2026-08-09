import asyncio
import pytest

from services.composio_service import (
    ComposioGateway,
    ComposioError,
    ScopedApproval,
    pauli_entity_id,
)


def test_entity_ids_are_stable_and_tenant_scoped():
    a = pauli_entity_id("tenant-a", "pauli")
    b = pauli_entity_id("tenant-a", "pauli")
    c = pauli_entity_id("tenant-b", "pauli")
    assert a == b
    assert a != c
    assert a.startswith("pauli_")


def test_missing_key_is_dormant_not_crashing():
    gateway = ComposioGateway(api_key="")
    health = gateway.health()
    assert health["configured"] is False
    assert health["status"] == "waiting_for_credentials"


def test_action_session_fails_closed_without_matching_approval(monkeypatch):
    gateway = ComposioGateway(api_key="test")
    approval = ScopedApproval(
        approval_id="apr_1",
        tenant_id="tenant-a",
        actor_id="pauli",
        action="SEND",
        toolkits=("GMAIL",),
    )

    async def fake_request(*args, **kwargs):
        raise AssertionError("network must not be called for unauthorized toolkit")

    monkeypatch.setattr(gateway, "_request", fake_request)
    with pytest.raises(ComposioError):
        asyncio.run(
            gateway.create_action_session(
                tenant_id="tenant-a",
                actor_id="pauli",
                toolkits=["SLACK"],
                approval=approval,
            )
        )


def test_read_session_uses_read_only_hint_and_allowlist(monkeypatch):
    gateway = ComposioGateway(api_key="test")
    captured = {}

    async def fake_request(method, path, json_body=None):
        captured.update({"method": method, "path": path, "body": json_body})
        return {
            "session_id": "trs_test",
            "mcp": {"url": "https://example.invalid/mcp"},
            "config": {"user_id": pauli_entity_id("tenant-a", "pauli")},
        }

    monkeypatch.setattr(gateway, "_request", fake_request)
    session = asyncio.run(
        gateway.create_read_session(
            tenant_id="tenant-a", actor_id="pauli", toolkits=["gmail", "github"]
        )
    )
    assert session.access_mode == "read"
    assert session.toolkits == ["GMAIL", "GITHUB"]
    assert captured["body"]["tags"] == {"enabled": ["readOnlyHint"]}
    assert captured["body"]["toolkits"] == {"enabled": ["GMAIL", "GITHUB"]}
    assert captured["body"]["workbench"]["enable"] is False


def test_action_session_requires_explicit_toolkits_and_scoped_approval(monkeypatch):
    gateway = ComposioGateway(api_key="test")
    captured = {}
    approval = ScopedApproval(
        approval_id="apr_2",
        tenant_id="tenant-a",
        actor_id="pauli",
        action="SEND",
        toolkits=("GMAIL",),
        max_uses=5,
    )

    async def fake_request(method, path, json_body=None):
        captured["body"] = json_body
        return {
            "session_id": "trs_action",
            "mcp": {"url": "https://example.invalid/action-mcp"},
            "config": {"user_id": pauli_entity_id("tenant-a", "pauli")},
        }

    monkeypatch.setattr(gateway, "_request", fake_request)
    session = asyncio.run(
        gateway.create_action_session(
            tenant_id="tenant-a",
            actor_id="pauli",
            toolkits=["gmail"],
            approval=approval,
        )
    )
    assert session.access_mode == "action"
    assert captured["body"]["toolkits"] == {"enabled": ["GMAIL"]}
    assert "tags" not in captured["body"]
