"""Tests for the nightly self-improvement loop (subsystem 09)."""
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_self_improve_module_imports():
    from agents import self_improve as si
    assert hasattr(si, "run_nightly")
    assert hasattr(si, "_open_draft_pr")
    assert hasattr(si, "register")


def test_self_improve_analyze_prompt_exists():
    from agents.self_improve import ANALYZE_PROMPT
    assert "{envelopes_json}" in ANALYZE_PROMPT
    assert "weak_axes" in ANALYZE_PROMPT


def test_self_improve_propose_prompt_exists():
    from agents.self_improve import PROPOSE_PR_PROMPT
    assert "{weak_axes_json}" in PROPOSE_PR_PROMPT


def test_self_improve_judge_prompt_exists():
    from agents.self_improve import JUDGE_PROMPT
    assert "{prs_json}" in JUDGE_PROMPT
    assert "no secrets leaked" in JUDGE_PROMPT.lower() or "sk_" in JUDGE_PROMPT


def test_self_improve_pr_pending_writer(tmp_path, monkeypatch):
    """_open_draft_pr must always write a pending-pr file even if gh missing."""
    from agents.self_improve import _open_draft_pr
    out = _open_draft_pr({"repo": "executiveusa/PAULIS-PLACE",
                          "branch": "self/test-19700101",
                          "title": "self-improve test",
                          "body_md": "test body",
                          "diff_suggestion": "- x\n+ y"},
                         gh_token="",
                         repo_root=tmp_path)
    assert out["status"].startswith(("opened_as_draft", "pending_human"))
    if out["status"].startswith("pending_human"):
        ops_dir = tmp_path / "icm" / "memory" / "ops"
        files = list(ops_dir.rglob("pr_pending_self_test-19700101.md"))
        assert len(files) == 1


def test_self_improve_registers_to_event_bus():
    from agents.self_improve import register
    register()  # should not throw
    register()  # idempotent