import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.agentforge_runtime import AgentForgeRuntime


def run(coro):
    return asyncio.run(coro)


def test_agentforge_health_fails_soft_when_python_missing(tmp_path):
    runtime = AgentForgeRuntime()
    runtime.enabled = True
    runtime.python = str(tmp_path / "missing-python")
    runtime.project_dir = tmp_path / ".agentforge"

    health = run(runtime.health())

    assert health.provider == "agentforge"
    assert health.status == "needs_install"
    assert health.installed is False
    assert "unavailable" in (health.detail or "").lower()


def test_agentforge_health_can_be_disabled():
    runtime = AgentForgeRuntime()
    runtime.enabled = False

    health = run(runtime.health())

    assert health.status == "disabled"
    assert health.configured is False
    assert health.installed is False
