"""Voice command + observation dashboard endpoints.
POST /api/voice/command   — R-04 entry, takes {transcript}, returns the envelope
GET  /api/lounge/state     — current avatar positions + recent scenes
GET  /api/lounge/scenes    — recent R-02 PUBLISH_DONE + R-05 CELEBRATE events
"""
from __future__ import annotations
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.voice_router import route_voice_command

router = APIRouter()


class VoiceCommandRequest(BaseModel):
    transcript: str


@router.post("/api/voice/command")
async def post_voice_command(req: VoiceCommandRequest):
    """Spec §08 voice endpoint. Routes through SAFETY_JUDGE + nearest avatar
    under Hermes (L1-L4 enforced). Returns the published envelope."""
    env = await route_voice_command(req.transcript)
    return env


@router.get("/api/lounge/state")
def lounge_state():
    """Static placeholder for the lounge client. Avatars + idle positions."""
    from importlib import import_module
    return {
        "lounge": "Paulie's Place",
        "setting": "Seattle 2056, jazz-room, dark oak + brass fixtures, vinyl crates on the wall, neon 'NO SOLICITORS' sign at the door",
        "avatars": [
            {"id": "av_paulie", "name": "Paulie 'The Plaque' Fontaine",
             "position": [0, 0, 0], "model": "glb/paulie.glb", "state": "host"},
            {"id": "av_zia", "name": "Zia 'Numbers' Navarro",
             "position": [3, 0, -1], "model": "glb/zia.glb", "state": "ledger_idle"},
            {"id": "av_marco", "name": "Marco 'Trender' Lee",
             "position": [-3, 0, -1], "model": "glb/marco.glb", "state": "trend_idle"},
            {"id": "av_dex", "name": "Dex 'Words' Holloway",
             "position": [-2, 0, 3], "model": "glb/dex.glb", "state": "bar_idle"},
            {"id": "av_sasha", "name": "Sasha 'Pixels' Ortiz",
             "position": [2, 0, 3], "model": "glb/sasha.glb", "state": "stage_idle"},
            {"id": "av_wren", "name": "Wren 'The Vault' Yamasaki",
             "position": [4, 0, 4], "model": "glb/wren.glb", "state": "vault_idle"},
            {"id": "av_niko", "name": "Niko 'Fable' Kowalski",
             "position": [-4, 0, 4], "model": "glb/niko.glb", "state": "smoke_idle"},
            {"id": "av_mira", "name": "Mira 'The Hand' Singh",
             "position": [0, 0, -3], "model": "glb/mira.glb", "state": "host_idle"},
        ],
        "schedule_cue": "Tip the band. Two-drink minimum. Don't trust the trend report on Tuesdays.",
    }


@router.get("/api/lounge/scenes")
def lounge_scenes(limit: int = 20):
    """Most recent PUBLISH_DONE + CELEBRATE events for the lounge to render."""
    root = Path(__file__).resolve().parents[2] / "icm" / "memory" / "ops"
    if not root.exists():
        return {"scenes": []}
    keep = ["R-02.REVENUE.PRODUCT_CREATED.PUBLISH_DONE",
            "R-05.PAYMENT.SETTLED.CELEBRATE",
            "R-04.WORLD.HUMAN_VOICE_COMMAND.AVATAR_REACT"]
    scenes = []
    for day_dir in sorted(root.iterdir(), reverse=True):
        for f in sorted(day_dir.glob("*.json"), reverse=True):
            try:
                env = json.loads(f.read_text(encoding="utf-8"))
                route_stage = f"{env.get('route','')}.{env.get('stage','')}"
                if any(keep_term in route_stage for keep_term in keep):
                    scenes.append(env)
                    if len(scenes) >= limit:
                        return {"scenes": scenes}
            except Exception:
                continue
    return {"scenes": scenes}