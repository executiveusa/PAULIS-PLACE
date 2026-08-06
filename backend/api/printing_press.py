"""
PRINTED-CLI API — Hermes observability + control for the agent tool surface.
GET  /api/printed-clis                      list all known + their install state
POST /api/printed-clis/{name}/sync          run sync on its SQLite cache
GET  /api/printed-clis/{name}/doctor        verify auth + connectivity
GET  /api/printed-clis/{name}/search?q=...  offline full-text search on local cache
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from services import printed_cli as pc

router = APIRouter(prefix="/api/printed-clis", tags=["printing-press"])


@router.get("")
def list_clis():
    out = []
    for name, spec in pc.PRINTED_REGISTRY.items():
        out.append({
            "name": name,
            "dir": spec["dir"],
            "env_var": spec["env_var"],
            "installed": pc.binary_path(name) is not None,
            "binary_rel": spec["binary_rel"],
            "api_base": spec["api_base"],
            "entry_module": spec["entry_module"],
        })
    return {"clis": out, "installed": pc.list_printed_clis()}


@router.post("/{name}/sync")
async def sync_cli(name: str):
    res = await pc.call_printed(name, ["sync"], timeout_s=300.0)
    if res.get("ok") is None or res.get("ok") is False and res.get("reason") == "not_built":
        raise HTTPException(404, detail=f"{name} not installed")
    return res


@router.get("/{name}/doctor")
async def doctor_cli(name: str):
    res = await pc.call_printed(name, ["doctor"], timeout_s=20.0)
    if res.get("reason") == "not_built":
        raise HTTPException(404, detail=f"{name} not installed")
    return res


@router.get("/{name}/search")
async def search_cli(name: str, q: str = Query(..., min_length=1)):
    res = await pc.call_printed(name, ["search", q, "--json"], timeout_s=15.0)
    return res


@router.get("/{name}/which")
async def which(name: str, capability: Optional[str] = Query(None)):
    """Find the command that implements a capability."""
    args = ["which", capability] if capability else ["which"]
    return await pc.call_printed(name, args, timeout_s=10.0)