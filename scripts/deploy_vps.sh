#!/usr/bin/env bash
# PAULI'S PLACE — safe VPS deployment
# This script intentionally NEVER creates or overwrites production secrets.

set -Eeuo pipefail

REPO_DIR="${PAULI_REPO_DIR:-/root/PAULIS-PLACE}"
REPO_URL="https://github.com/executiveusa/PAULIS-PLACE.git"

log() { printf '[pauli-deploy] %s\n' "$*"; }
fail() { printf '[pauli-deploy] ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker is required. Install Docker through your host's supported provisioning path before deploying Pauli."
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  fail "Docker Compose is required."
fi

if [ -d "$REPO_DIR/.git" ]; then
  log "Updating canonical repository"
  git -C "$REPO_DIR" fetch origin main
  git -C "$REPO_DIR" checkout main
  git -C "$REPO_DIR" reset --hard origin/main
else
  log "Cloning canonical repository"
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"

[ -f .env ] || fail ".env is missing. Provision secrets out-of-band; this script will not invent or overwrite them."
chmod 600 .env || true

# Validate only presence, never print secret values.
required=(DATABASE_URL REDIS_URL SECRET_KEY)
for key in "${required[@]}"; do
  if ! grep -Eq "^${key}=.+" .env; then
    fail "Required variable ${key} is not configured in .env"
  fi
done

if ! grep -Eq '^GROQ_API_KEY=.+|^OPENROUTER_API_KEY=.+' .env; then
  log "WARNING: no model provider credential is configured; cognitive tasks will fail closed as BLOCKED."
fi

log "Building production backend and worker images"
"${COMPOSE[@]}" build backend celery-worker celery-beat

log "Starting Redis, API, worker, and scheduler"
"${COMPOSE[@]}" up -d --remove-orphans redis backend celery-worker celery-beat

log "Waiting for API health"
for attempt in $(seq 1 30); do
  if curl --fail --silent --max-time 3 http://127.0.0.1:8000/api/health >/dev/null; then
    log "API healthy"
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    "${COMPOSE[@]}" ps
    fail "API did not become healthy"
  fi
  sleep 2
done

log "Service state"
"${COMPOSE[@]}" ps

log "Recent worker state"
"${COMPOSE[@]}" logs --tail=30 celery-worker || true

log "Deployment completed without modifying secrets."
