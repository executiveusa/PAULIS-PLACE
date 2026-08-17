"""Server-side capability verification for consequential Pauli's Place actions.

The browser never gets the signing key. A trusted owner-control surface or future
Supabase-backed approval issuer signs a short-lived capability for one exact
operation. If the signing key is not configured, consequential writes fail closed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Iterable

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class ApprovalCapability:
    actor: str
    action: str
    resource_ids: tuple[int, ...]
    exp: int
    nonce: str


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _signing_key() -> bytes:
    value = os.environ.get("PAULI_APPROVAL_SIGNING_KEY", "").strip()
    if len(value) < 32:
        raise HTTPException(
            status_code=503,
            detail="Approval signing authority is not configured; consequential writes are disabled",
        )
    return value.encode("utf-8")


def issue_capability(*, actor: str, action: str, resource_ids: Iterable[int], nonce: str, ttl_seconds: int = 300) -> str:
    """Internal helper for trusted server-side issuers/tests. Never expose as a public API."""
    now = int(time.time())
    payload = {
        "v": 1,
        "actor": actor,
        "action": action,
        "resource_ids": sorted({int(item) for item in resource_ids}),
        "iat": now,
        "exp": now + max(1, min(int(ttl_seconds), 900)),
        "nonce": nonce,
    }
    encoded = _b64url_encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_signing_key(), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64url_encode(signature)}"


def verify_capability(token: str, *, expected_action: str, expected_resource_ids: Iterable[int]) -> ApprovalCapability:
    try:
        encoded, supplied_signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Malformed approval capability") from exc

    expected_signature = hmac.new(_signing_key(), encoded.encode("ascii"), hashlib.sha256).digest()
    try:
        supplied = _b64url_decode(supplied_signature)
    except Exception as exc:
        raise HTTPException(status_code=403, detail="Malformed approval capability signature") from exc

    if not hmac.compare_digest(expected_signature, supplied):
        raise HTTPException(status_code=403, detail="Invalid approval capability signature")

    try:
        payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=403, detail="Malformed approval capability payload") from exc

    if payload.get("v") != 1:
        raise HTTPException(status_code=403, detail="Unsupported approval capability version")
    if int(payload.get("exp", 0)) <= int(time.time()):
        raise HTTPException(status_code=403, detail="Approval capability expired")
    if payload.get("action") != expected_action:
        raise HTTPException(status_code=403, detail="Approval capability action mismatch")

    expected_ids = sorted({int(item) for item in expected_resource_ids})
    token_ids = sorted({int(item) for item in payload.get("resource_ids", [])})
    if token_ids != expected_ids:
        raise HTTPException(status_code=403, detail="Approval capability resource scope mismatch")

    actor = str(payload.get("actor") or "").strip()
    nonce = str(payload.get("nonce") or "").strip()
    if not actor or not nonce:
        raise HTTPException(status_code=403, detail="Approval capability is missing actor or nonce")

    return ApprovalCapability(
        actor=actor,
        action=expected_action,
        resource_ids=tuple(expected_ids),
        exp=int(payload["exp"]),
        nonce=nonce,
    )


def require_approval_capability(
    *,
    action: str,
    resource_ids: Iterable[int],
    x_pauli_approval: str | None = Header(default=None, alias="X-Pauli-Approval"),
) -> ApprovalCapability:
    if not x_pauli_approval:
        raise HTTPException(status_code=403, detail="Scoped approval capability required")
    return verify_capability(
        x_pauli_approval,
        expected_action=action,
        expected_resource_ids=resource_ids,
    )
