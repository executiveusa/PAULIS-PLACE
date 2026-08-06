"""PAULIS-PLACE backend CLI — ops utilities.

Usage:
  python -m backend.cli replay <event_id>
  python -m backend.cli sweep
  python -m backend.ci shipcheck
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path

# Allow running from repo root with `python -m backend.cli`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def _replay(event_id: str):
    from services.event_bus import replay, publish
    env = replay(event_id)
    if env is None:
        print(f"NOT FOUND: {event_id}")
        return 1
    env = dict(env)
    env["event_id"] = f"evt_replay_{event_id.replace('evt_','')}"
    await publish(env)
    print(f"republished as {env['event_id']}")
    return 0


def _sweep():
    """Quick route+pytest sweep. Prints results, no failures-throw."""
    import subprocess
    repo_root = Path(__file__).resolve().parents[2]
    tests_dir = repo_root / "backend" / "tests"
    if tests_dir.exists():
        print("[sweep] running pytest...")
        subprocess.run([sys.executable, "-m", "pytest", str(tests_dir), "-x", "-q"],
                       cwd=str(repo_root))
    print("[sweep] running import smoke...")
    smoke = ("python", "-c",
             "import sys; sys.path.insert(0,'backend'); "
             "import main; print('main import OK')")
    subprocess.run(list(smoke), cwd=str(repo_root))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    cmd, *rest = args
    if cmd == "replay":
        if not rest:
            print("usage: replay <event_id>")
            return 1
        return asyncio.run(_replay(rest[0]))
    if cmd == "sweep":
        _sweep()
        return 0
    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main() or 0)