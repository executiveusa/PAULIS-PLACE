"""Tests for the voice router (subsystem 08)."""
import asyncio
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_voice_router_module_imports():
    from agents import voice_router as vr
    assert hasattr(vr, "route_voice_command")
    assert hasattr(vr, "ALLOWED_INTENTS")
    assert hasattr(vr, "BANNED_PATTERNS")
    assert hasattr(vr, "register")


def test_voice_allowed_intents_match_registry():
    from agents.voice_router import ALLOWED_INTENTS
    expected = {"who_owns","whats_hot","how_is_money","post_that",
                "whos_paying","tell_about","cut_it","human_moment"}
    assert set(ALLOWED_INTENTS.keys()) == expected


def test_voice_banned_patterns_match_dangerous_phrases():
    from agents.voice_router import BANNED_PATTERNS
    assert BANNED_PATTERNS.search("delete the database")
    assert BANNED_PATTERNS.search("wipe products table")
    assert BANNED_PATTERNS.search("send 1000 usd to paulie")
    assert BANNED_PATTERNS.search("impersonate paulie")
    assert not BANNED_PATTERNS.search("who owns this place")
    assert not BANNED_PATTERNS.search("what's hot tonight")
    assert not BANNED_PATTERNS.search("how's the money")
    assert not BANNED_PATTERNS.search("post that")
    assert not BANNED_PATTERNS.search("human moment")


def test_voice_router_api_endpoint_present():
    from api.voice import router as voice_router_api
    paths = [r.path for r in voice_router_api.routes]
    assert any("/voice/command" in p for p in paths)
    assert any("/lounge/state" in p for p in paths)
    assert any("/lounge/scenes" in p for p in paths)


def test_voice_router_handles_empty_transcript():
    """Empty transcript should return a halt without calling external APIs."""
    from agents.voice_router import route_voice_command
    res = asyncio.run(route_voice_command(""))
    assert res.get("verdict") == "halt" or res.get("judge_verdict") == "halt"