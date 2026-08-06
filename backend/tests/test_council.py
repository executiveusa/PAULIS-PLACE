"""Tests for the adversarial council subsystem (02)."""
import asyncio
import os
import sys
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_ensure_distinct_profiles_between_advocate_critic_judge():
    from services.profile_router import ensure_distinct_profiles
    # Should pass — these are all different profiles per spec §8
    ensure_distinct_profiles("write_short", "judge")
    ensure_distinct_profiles("score", "judge")


def test_council_extract_json_helper():
    from agents.council_adversarial import _strip_to_json
    assert _strip_to_json({"x": 1}) == {"x": 1}
    assert _strip_to_json('{"a": 2}') == {"a": 2}
    assert _strip_to_json('```json\n{"b": 3}\n```') == {"b": 3}
    # Robust to extra prose
    parsed = _strip_to_json('Here is the verdict: {"ruling": "APPROVE"} done.')
    assert parsed.get("ruling") == "APPROVE"


def test_council_decision_persisted(tmp_path, monkeypatch):
    """It writes the locked debate to icm/memory/decisions/<date>/<debate_id>.json"""
    from agents import council_adversarial as ca
    # Force the repo-root used by _persist_decision to our tmp_path
    monkeypatch.setattr(Path, "resolve", lambda self: tmp_path / "backend" / "agents" / "x.py")
    out = ca._persist_decision("deb_test123", {"ruling": "APPROVE"})
    assert out.exists()
    assert "deb_test123" in out.name
    import json
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["ruling"] == "APPROVE"