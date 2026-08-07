"""
PRINTED-CLI WRAPPER — The agent tool surface (cli-printing-press integration)
=============================================================================
Per spec integration layer: every Yappyverse agent that needs to interact
with an external API SHOULD do so by shelling out to the matching printed
Go CLI built by `cli-printing-press` (github.com/mvanhorn/cli-printing-press).

Why:
  - Token-efficient: agents pipe JSON via stdout, no MCP protocol overhead
  - Agent-native: every printed CLI ships with `--agent` flag (--json --compact --no-input --yes)
  - Local SQLite: each printed CLI holds a cached local copy via `sync`; agents can
    `search` it offline for compound queries (`health`, `bottleneck`, `reconcile`,
    `stale`, `orphans`) that no stateless wrapper could compute
  - Typed exit codes: 0=ok / 2=usage / 3=notfound / 4=auth / 5=api / 7=ratelimited
  - Dual interface: same binary exposes both a Cobra CLI and an MCP server; here
    we use the shell CLI because LLMs were trained on shell interactions.

Installation path: printed-clis/<api_name>/spec. Each printed CLI lives in
its own Go module path which is independent of the Python backend.

Safety net (L4): printed CLIs read auth from env. The wrapper sets the right
env var per CLI from the existing `os.environ` so secrets never cross the
Python<->Go boundary in arguments or files.
"""
from __future__ import annotations
import asyncio
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
PRINTED_DIR = REPO_ROOT / "printed-clis"


# Per-CLI metadata. Each printed CLI announces its binary name via its module path.
# `binary_rel` is the path under printed-clis/<name>/ where the .exe/.bin lives.
# `env_var` is the auth env var the printed CLI reads.
# `entry_module` is the Go main package path under cmd/ (used by `go build`).
PRINTED_REGISTRY: dict[str, dict] = {
    "printify": {
        "binary_rel": "printify-pp-cli.exe" if os.name == "nt" else "printify-pp-cli",
        "dir": "printify",
        "env_var": "PRINTIFY_TOKEN",
        "entry_module": "./cmd/printify2-pp-cli/",
        "api_base": "https://api.printify.com/v1",
    },
    # Future printed CLIs fill in here as they are printed:
    # "etsy": { "binary_rel": "etsy-pp-cli.exe", "dir": "etsy",
    #           "env_var": "ETSY_API_KEY",
    #           "entry_module": "./cmd/etsy-pp-cli/" }
    # "creem": ..., "btcpay": ..., "zernio": ..., "openrouter": ...,
    # "trends": ..., "fiverr": ...
}


def binary_path(name: str) -> Optional[Path]:
    spec = PRINTED_REGISTRY.get(name)
    if spec is None:
        return None
    p = PRINTED_DIR / spec["dir"] / spec["binary_rel"]
    return p if p.exists() else None


def list_printed_clis() -> list[str]:
    """Which CLIs are present and built on disk."""
    return [n for n in PRINTED_REGISTRY if binary_path(n) is not None]


async def call_printed(
    api_name: str,
    args: list[str],
    *,
    stdin: Optional[str] = None,
    timeout_s: float = 30.0,
    agent_mode: bool = True,
    extra_env: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Invoke a printed CLI. Returns a structured result dict.

    If the CLI is not built/installed, returns {"ok": False, "reason": "not_built", ...}.
    On non-zero exit code, surfaces what the printed CLI writes as standard error
    so the calling agent can self-correct (printed CLIs have actionable errors).
    """
    exe = binary_path(api_name)

    final_args = list(args)
    if agent_mode and "--agent" not in final_args:
        final_args.append("--agent")

    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)

    # L4 sanity: verify no secret values are passed in args (LLMs may try this).
    # Run this BEFORE the not-built check so the guard is enforced identically
    # whether or not a CLI binary is installed on this machine.
    for a in final_args:
        for suspect in ("sk-", "ghp_", "sbp_", "r8_", "rk_live_", "Bearer", "token="):
            if suspect in a and not a.startswith("--"):
                return {"ok": False, "reason": "L4_secret_in_args", "argument": a[:40] + "..."}

    if exe is None:
        return {
            "ok": False,
            "reason": "not_built",
            "available_clis": list_printed_clis(),
            "hint": f"Run: cli-printing-press generate --spec <openapi.json> --name {api_name}",
        }

    try:
        proc = await asyncio.create_subprocess_exec(
            str(exe), *final_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
    except Exception as e:
        return {"ok": False, "reason": "spawn_failed", "error": str(e)[:300]}

    if stdin is not None:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(stdin.encode()), timeout=timeout_s)
    else:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)

    out = stdout_b.decode("utf-8", errors="replace")
    err = stderr_b.decode("utf-8", errors="replace")

    # Try to parse stdout as JSON (printed CLIs always emit JSON in --agent mode)
    parsed: Any = out
    try:
        parsed = json.loads(out)
    except Exception:
        pass

    return {
        "ok": proc.returncode == 0,
        "exit": proc.returncode,
        "stdout": parsed if not isinstance(parsed, str) else out.strip(),
        "stderr": err.strip(),
        "raw_stdout": out[:2000],
        "args": final_args,
    }


# Convenience methods per printed CLI helpers

async def printify_list_shops(*, compact: bool = True) -> dict:
    args = ["shops-json"]
    if compact:
        args.append("--compact")
    return await call_printed("printify", args)


async def printify_search(query: str, *, resource: Optional[str] = None) -> dict:
    """Search the local SQLite mirror of Printify data."""
    args = ["search", query]
    if resource:
        args += ["--resource", resource]
    return await call_printed("printify", args)


async def printify_sync() -> dict:
    """Pull API data into the local SQLite cache."""
    return await call_printed("printify", ["sync"], timeout_s=180.0)


async def printify_workflow(name: str, *, params: Optional[dict] = None) -> dict:
    """Compound workflow command (e.g. `bottleneck`, `health` if shipped)."""
    args = ["workflow", name]
    if params:
        for k, v in params.items():
            args += [f"--{k.replace('_','-')}", str(v)]
    return await call_printed("printify", args)


# Auth doctor across all installed printed CLIs
async def doctor_all() -> dict[str, dict]:
    """Run the doctor command on every installed printed CLI."""
    out: dict[str, dict] = {}
    for name in list_printed_clis():
        out[name] = await call_printed(name, ["doctor"], timeout_s=20.0)
    return out