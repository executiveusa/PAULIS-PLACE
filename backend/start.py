#!/usr/bin/env python3
"""Backend startup script that loads .env properly before anything else."""
import os
import sys
from pathlib import Path

# Load env vars from .env file manually (only simple KEY=VALUE lines)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            # Skip keys with spaces (SSH keys etc)
            if " " in key or not key.replace("_", "").isalnum():
                continue
            # Only set if not already in environment (env vars take precedence)
            if key not in os.environ:
                os.environ[key] = value

# Ensure required vars have defaults
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://digifactory:digifactory_pass@localhost:5432/digifactory")
os.environ.setdefault("APP_URL", "http://localhost:3000")
os.environ.setdefault("SECRET_KEY", "smoke_test_secret_2026")

print(f"REDIS_URL={os.environ.get('REDIS_URL')}")
print(f"DATABASE_URL={os.environ.get('DATABASE_URL')}")
print(f"OPENROUTER_API_KEY set: {bool(os.environ.get('OPENROUTER_API_KEY'))}")

# Now start uvicorn - import app directly (not as string) so env vars are already loaded
import uvicorn
import main
uvicorn.run(main.app, host="0.0.0.0", port=8000, log_level="info")
