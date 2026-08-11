"""Shared operational-memory location for Pauli's Place.

Production containers may set PAULI_MEMORY_ROOT to a mounted persistent volume.
Local development defaults to the repository's existing icm/memory directory.
No caller should silently choose a separate receipt store.
"""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def memory_root() -> Path:
    configured = os.environ.get("PAULI_MEMORY_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return repo_root() / "icm" / "memory"


def ensure_memory_root() -> Path:
    root = memory_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def memory_path(*parts: str) -> Path:
    return ensure_memory_root().joinpath(*parts)
