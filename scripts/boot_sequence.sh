#!/bin/bash
# scripts/boot_sequence.sh
# VPS Self-Boot Harness - Zero-touch startup for PAULI'S-PLACE
# Runs on Hostinger VPS / Docker container startup

set -e

echo "=========================================="
echo "  PAULI'S-PLACE BOOT SEQUENCE INITIATED"
echo "=========================================="
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting..."

# 1. Verify .env exists
if [ ! -f .env ]; then
    echo "[BOOT] FATAL: .env file not found. Copying from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[BOOT] WARNING: .env created from example. Edit with real API keys."
    else
        echo "[BOOT] FATAL: No .env or .env.example found. Aborting."
        exit 1
    fi
fi

# 2. Check required env vars
REQUIRED_VARS=("DATABASE_URL" "REDIS_URL" "OPENROUTER_API_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "[BOOT] WARNING: $var is not set in environment"
    fi
done

# 3. Wait for database to be ready
echo "[$(date -u +%H:%M:%SZ)] Waiting for database..."
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if python -c "import os; from sqlalchemy import create_engine; create_engine(os.environ.get('DATABASE_URL','')).connect()" 2>/dev/null; then
        echo "[BOOT] Database connection established."
        break
    fi
    RETRY=$((RETRY+1))
    echo "[BOOT] Database not ready, retry $RETRY/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "[BOOT] WARNING: Could not connect to database. Continuing anyway..."
fi

# 4. Run Alembic migrations
echo "[$(date -u +%H:%M:%SZ)] Running database migrations..."
if [ -d "backend/alembic" ]; then
    cd backend && alembic upgrade head && cd ..
    echo "[BOOT] Migrations complete."
else
    echo "[BOOT] No alembic directory found. Creating tables directly..."
    python -c "import sys; sys.path.insert(0, 'backend'); from models.base import Base, engine; Base.metadata.create_all(bind=engine); print('[BOOT] Tables created.')"
fi

# 5. Seed initial data
echo "[$(date -u +%H:%M:%SZ)] Seeding initial data..."
python scripts/seed_data.py 2>/dev/null || echo "[BOOT] Seed script skipped (may already be seeded)."

# 6. Start Celery worker (background)
echo "[$(date -u +%H:%M:%SZ)] Starting Celery worker..."
cd backend && celery -A workers.celery_app worker -l info -c 4 --detach 2>/dev/null || \
    celery -A workers.celery_app worker -l info -c 4 &
cd ..
echo "[BOOT] Celery worker started."

# 7. Start Celery beat (background)
echo "[$(date -u +%H:%M:%SZ)] Starting Celery beat scheduler..."
cd backend && celery -A workers.celery_app beat -l info --detach 2>/dev/null || \
    celery -A workers.celery_app beat -l info &
cd ..
echo "[BOOT] Celery beat started."

# 8. Start FastAPI backend (background)
echo "[$(date -u +%H:%M:%SZ)] Starting FastAPI backend..."
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 &
cd ..
echo "[BOOT] Backend started on :8000"

# 9. Wait for backend to be healthy
echo "[$(date -u +%H:%M:%SZ)] Waiting for backend health check..."
RETRY=0
while [ $RETRY -lt 15 ]; do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        echo "[BOOT] Backend is healthy."
        break
    fi
    RETRY=$((RETRY+1))
    sleep 2
done

# 10. Trigger the FIRST AutoResearch task (start the money machine)
echo "[$(date -u +%H:%M:%SZ)] Triggering first trend scan..."
curl -s -X POST http://localhost:8000/api/trigger/scan-trends >/dev/null 2>&1 || true

echo "[$(date -u +%H:%M:%SZ)] Triggering first trend scoring..."
curl -s -X POST http://localhost:8000/api/trigger/score-trends >/dev/null 2>&1 || true

echo "=========================================="
echo "  [BOOT] PAULI'S-PLACE IS LIVE."
echo "  [BOOT] AWAITING OBSERVATION."
echo "=========================================="
echo "  Dashboard:    http://localhost:3000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  Observation:  http://localhost:3000/observation"
echo "=========================================="

# Keep container alive
wait
