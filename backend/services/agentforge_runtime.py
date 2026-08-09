"""AgentForge runtime provider for Pauli's Place.

AgentForge is intentionally kept behind a process boundary. Pauli Mission Control
owns authority, budgets, approvals, evidence and completion. AgentForge provides
an optional cognitive-workflow runtime using its declarative Cogs, persona
namespaces, memory hooks and model-agnostic agents.

This prevents the product from being coupled to AgentForge internals while still
letting Pauli use the production-ready patterns in executiveusa/pauli-Agent-Forge.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

from config import SETTINGS


class AgentForgeRuntimeError(RuntimeError):
    pass


@dataclass
class AgentForgeHealth:
    provider: str = "agentforge"
    configured: bool = False
    installed: bool = False
    status: str = "unconfigured"
    python: str = "python"
    project_dir: str = ".agentforge"
    capabilities: tuple[str, ...] = (
        "declarative-cogs",
        "branching-workflows",
        "persona-namespaces",
        "shared-memory",
        "chat-history",
        "scratchpad",
        "model-agnostic-agents",
        "bounded-loop-guards",
    )
    detail: Optional[str] = None

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentForgeRuntime:
    def __init__(self) -> None:
        self.python = SETTINGS.agentforge_python
        self.project_dir = Path(SETTINGS.agentforge_project_dir)
        self.enabled = SETTINGS.agentforge_enabled
        self.timeout = max(10, int(SETTINGS.agentforge_timeout_seconds))

    async def _run(self, *args: str, cwd: Optional[Path] = None, timeout: int = 20) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            self.python,
            *args,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise AgentForgeRuntimeError("AgentForge process timed out")
        return proc.returncode or 0, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")

    async def health(self) -> AgentForgeHealth:
        if not self.enabled:
            return AgentForgeHealth(
                configured=False,
                installed=False,
                status="disabled",
                python=self.python,
                project_dir=str(self.project_dir),
                detail="AGENTFORGE_ENABLED=false",
            )

        code, out, err = await self._run(
            "-c",
            "import agentforge; print(getattr(agentforge, '__version__', 'installed'))",
            timeout=12,
        )
        installed = code == 0
        project_ready = self.project_dir.exists()
        status = "ready" if installed and project_ready else ("installed_needs_project" if installed else "needs_install")
        detail = out.strip() if installed else (err.strip()[:300] or "agentforge import failed")
        return AgentForgeHealth(
            configured=True,
            installed=installed,
            status=status,
            python=self.python,
            project_dir=str(self.project_dir),
            detail=detail,
        )

    async def run_cog(
        self,
        *,
        cog_name: str,
        context: dict[str, Any],
        persona: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute one AgentForge Cog and return its public result.

        Pauli must create the Mission/task, authorize tools and verify evidence
        outside this method. This method is only a bounded runtime invocation.
        """
        health = await self.health()
        if health.status != "ready":
            raise AgentForgeRuntimeError(f"AgentForge runtime not ready: {health.status}: {health.detail}")

        payload = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
        persona_literal = json.dumps(persona)
        cog_literal = json.dumps(cog_name)
        script = f"""
import json
from agentforge.cogs import Cog
payload = json.loads({json.dumps(payload)})
cog = Cog({cog_literal})
if {persona_literal} is not None:
    payload.setdefault('persona', {persona_literal})
result = cog.run(**payload)
print(json.dumps({{'ok': True, 'result': result}}, default=str, ensure_ascii=False))
"""
        code, out, err = await self._run("-c", script, cwd=self.project_dir.parent, timeout=self.timeout)
        if code != 0:
            raise AgentForgeRuntimeError((err or out or "AgentForge execution failed")[:1200])
        lines = [line for line in out.splitlines() if line.strip()]
        if not lines:
            raise AgentForgeRuntimeError("AgentForge returned no output")
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise AgentForgeRuntimeError(f"AgentForge output was not valid JSON: {lines[-1][:500]}") from exc
        return {
            "provider": "agentforge",
            "cog": cog_name,
            "persona": persona,
            "result": result.get("result"),
        }


agentforge_runtime = AgentForgeRuntime()
