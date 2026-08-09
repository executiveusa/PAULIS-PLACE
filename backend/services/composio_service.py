"""Pauli Integrations Bus powered by Composio.

Composio is an integration provider, not the Pauli's Place control plane.
This adapter keeps tenant identity, approval policy, auditability and fail-closed
behavior inside Pauli's Place while using Composio Sessions/MCP for discovery,
authentication and app execution.

Design rules:
- One Composio entity/user id per Pauli tenant + actor.
- Read sessions are autonomous and restricted to readOnlyHint tools.
- Action sessions require a scoped approval object and an explicit toolkit allowlist.
- Secrets are never returned from health/status endpoints.
- Missing Composio credentials make the provider dormant, not fatal.
- Session MCP URLs may be handed to any MCP-capable runtime (Hermes, Claude,
  Codex, OpenHands, Open Interpreter, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional
import hashlib
import re

import httpx

from config import SETTINGS

COMPOSIO_API_BASE = "https://backend.composio.dev/api/v3.1"


class ComposioError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScopedApproval:
    approval_id: str
    tenant_id: str
    actor_id: str
    action: str
    toolkits: tuple[str, ...]
    max_uses: int = 1
    expires_at: Optional[str] = None

    def allows(self, *, tenant_id: str, actor_id: str, toolkit: str) -> bool:
        return (
            bool(self.approval_id)
            and self.tenant_id == tenant_id
            and self.actor_id == actor_id
            and self.action in {"EXTERNAL_WRITE", "SEND", "PUBLISH", "CALL", "FINANCIAL"}
            and toolkit.upper() in {x.upper() for x in self.toolkits}
            and self.max_uses > 0
        )


@dataclass
class ComposioSessionInfo:
    session_id: str
    pauli_entity_id: str
    access_mode: str
    toolkits: list[str]
    mcp_url: Optional[str] = None
    warnings: list[dict[str, Any]] | None = None

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


def pauli_entity_id(tenant_id: str, actor_id: str) -> str:
    """Stable opaque entity ID so tenant/user identities never collide in Composio."""
    raw = f"pauli:{tenant_id}:{actor_id}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:24]
    return f"pauli_{digest}"


def _normalize_toolkits(toolkits: Optional[list[str]]) -> list[str]:
    if not toolkits:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in toolkits:
        slug = re.sub(r"[^A-Za-z0-9_-]", "", str(item)).upper()
        if slug and slug not in seen:
            seen.add(slug)
            out.append(slug)
    return out


class ComposioGateway:
    def __init__(self, api_key: Optional[str] = None, *, timeout: float = 20.0):
        self.api_key = api_key if api_key is not None else getattr(SETTINGS, "composio_api_key", "")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def health(self) -> dict[str, Any]:
        return {
            "provider": "composio",
            "configured": self.configured,
            "status": "ready" if self.configured else "waiting_for_credentials",
            "capabilities": [
                "tool-discovery",
                "oauth-and-api-key-connections",
                "tenant-scoped-sessions",
                "hosted-mcp",
                "read-only-autonomy",
                "approval-gated-actions",
                "triggers",
            ],
        }

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise ComposioError("Composio is not configured (COMPOSIO_API_KEY missing)")
        return {"x-api-key": self.api_key, "content-type": "application/json"}

    async def _request(self, method: str, path: str, *, json_body: Optional[dict] = None) -> dict:
        url = f"{COMPOSIO_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, headers=self._headers(), json=json_body)
        if response.status_code >= 400:
            detail = response.text[:500]
            raise ComposioError(f"Composio {method} {path} failed: {response.status_code} {detail}")
        if not response.content:
            return {}
        return response.json()

    async def create_read_session(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        toolkits: Optional[list[str]] = None,
    ) -> ComposioSessionInfo:
        """Create an autonomous discovery/read session."""
        normalized = _normalize_toolkits(toolkits)
        body: dict[str, Any] = {
            "user_id": pauli_entity_id(tenant_id, actor_id),
            "tags": {"enabled": ["readOnlyHint"]},
            "execute": {"enable_multi_execute": True},
            "manage_connections": {
                "enabled": True,
                "enable_wait_for_connections": False,
                "enable_connection_removal": False,
            },
            "workbench": {"enable": False, "proxy_execution_enabled": False},
        }
        if normalized:
            body["toolkits"] = {"enabled": normalized}

        payload = await self._request("POST", "/tool_router/session", json_body=body)
        return self._session_info(payload, "read", normalized)

    async def create_action_session(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        toolkits: list[str],
        approval: ScopedApproval,
    ) -> ComposioSessionInfo:
        """Create an action-capable session only when a scoped Pauli approval permits it."""
        normalized = _normalize_toolkits(toolkits)
        if not normalized:
            raise ComposioError("Action sessions require an explicit toolkit allowlist")
        for toolkit in normalized:
            if not approval.allows(tenant_id=tenant_id, actor_id=actor_id, toolkit=toolkit):
                raise ComposioError(
                    f"Approval {approval.approval_id or '<missing>'} does not authorize {toolkit}"
                )

        body: dict[str, Any] = {
            "user_id": pauli_entity_id(tenant_id, actor_id),
            "toolkits": {"enabled": normalized},
            "execute": {"enable_multi_execute": True},
            "manage_connections": {
                "enabled": False,
                "enable_wait_for_connections": False,
                "enable_connection_removal": False,
            },
            "workbench": {"enable": False, "proxy_execution_enabled": False},
        }
        payload = await self._request("POST", "/tool_router/session", json_body=body)
        return self._session_info(payload, "action", normalized)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/tool_router/session/{session_id}")

    async def create_connection_link(
        self,
        *,
        session_id: str,
        toolkit: str,
        callback_url: Optional[str] = None,
        alias: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return a Composio auth URL for a human to connect an account once."""
        normalized = _normalize_toolkits([toolkit])
        if not normalized:
            raise ComposioError("Toolkit is required")
        body: dict[str, Any] = {"toolkit": normalized[0]}
        if callback_url:
            body["callback_url"] = callback_url
        if alias:
            body["alias"] = alias
        return await self._request("POST", f"/tool_router/session/{session_id}/link", json_body=body)

    @staticmethod
    def _session_info(payload: dict[str, Any], access_mode: str, toolkits: list[str]) -> ComposioSessionInfo:
        session_id = payload.get("session_id")
        if not session_id:
            raise ComposioError("Composio response did not include session_id")
        mcp = payload.get("mcp") or {}
        config = payload.get("config") or {}
        return ComposioSessionInfo(
            session_id=session_id,
            pauli_entity_id=config.get("user_id", ""),
            access_mode=access_mode,
            toolkits=toolkits,
            mcp_url=mcp.get("url"),
            warnings=payload.get("warnings") or [],
        )


composio_gateway = ComposioGateway()
