"""Tests for the SSSF agent role wrappers (03)."""
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_sssf_module_imports():
    from agents import sssf
    assert hasattr(sssf, "worker_scan")
    assert hasattr(sssf, "worker_score")
    assert hasattr(sssf, "worker_design")
    assert hasattr(sssf, "worker_publish")
    assert hasattr(sssf, "worker_reconcile")
    assert hasattr(sssf, "register_subscribers")


def test_sssf_register_subscribers_doesnt_throw():
    from agents import sssf
    # Should be idempotent and safe to call multiple times
    sssf.register_subscribers()
    sssf.register_subscribers()


def test_sssf_prompts_are_filled():
    import inspect
    from agents import sssf
    src = inspect.getsource(sssf)
    # Spot-check that the templates reference their placeholders
    assert "{trend_json}" in src
    assert "{approved_idea}" in src
    assert "{product_json}" in src
    assert "{webhook_json}" in src