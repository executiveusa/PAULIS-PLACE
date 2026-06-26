#!/usr/bin/env python3
"""Celery worker startup script that loads .env properly."""
import os
import sys
from pathlib import Path

# Load env vars from .env file manually
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
            if " " in key or not key.replace("_", "").isalnum():
                continue
            if key not in os.environ:
                os.environ[key] = value

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://digifactory:digifactory_pass@localhost:5432/digifactory")

print(f"DATABASE_URL={os.environ.get('DATABASE_URL')}")
print(f"REDIS_URL={os.environ.get('REDIS_URL')}")
print(f"GROQ_API_KEY set: {bool(os.environ.get('GROQ_API_KEY'))}")

# Now start celery worker
from celery import Celery
from workers.celery_app import app

if __name__ == "__main__":
    argv = [
        "worker",
        "--loglevel=info",
        "--concurrency=2",
    ]
    app.worker_main(argv)
