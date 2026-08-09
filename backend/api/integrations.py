"""Integration control-plane endpoints.

These endpoints deliberately expose connection/session management, not an arbitrary
"execute any third-party action" endpoint. External writes remain governed by Pauli
mission approvals and are created internally through action-scoped sessions.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.composio_service import composio_gateway, ComposioError

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class ReadSessionRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    actor_id: str = Field(min_length=1, max_length=128)
    toolkits: list[str] = []


class ConnectionLinkRequest(BaseModel):
    toolkit: str = Field(min_length=1, max_length=128)
    callback_url: Optional[str] = None
    alias: Optional[str] = Field(default=None, max_length=128)


@router.get("/composio/status")
def composio_status():
    return composio_gateway.health()


@router.post("/composio/sessions/read")
async def create_composio_read_session(req: ReadSessionRequest):
    try:
        session = await composio_gateway.create_read_session(
            tenant_id=req.tenant_id,
            actor_id=req.actor_id,
            toolkits=req.toolkits or None,
        )
        return session.public_dict()
    except ComposioError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/composio/sessions/{session_id}/connect")
async def connect_composio_toolkit(session_id: str, req: ConnectionLinkRequest):
    try:
        return await composio_gateway.create_connection_link(
            session_id=session_id,
            toolkit=req.toolkit,
            callback_url=req.callback_url,
            alias=req.alias,
        )
    except (ComposioError, IndexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
