#!/bin/bash
# scripts/run_backend.sh - Run backend with proper env loading
cd /workspaces/PAULIS-PLACE/backend

# Load env vars from .env file (only the simple KEY=VALUE ones)
set -a
while IFS='=' read -r key value; do
    # Skip comments, empty lines, and lines with spaces in key
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue
    # Skip keys with special chars (SSH keys etc)
    [[ "$key" =~ [[:space:]] ]] && continue
    # Export only if value doesn't contain newlines/special chars
    if [[ "$value" =~ ^[a-zA-Z0-9_:./@?=-]+$ ]] || [[ -z "$value" ]]; then
        export "$key=$value"
    fi
done < /workspaces/PAULIS-PLACE/.env
set +a

echo "REDIS_URL=$REDIS_URL"
echo "DATABASE_URL=$DATABASE_URL"
echo "Starting backend..."
exec python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, log_level='info')"
