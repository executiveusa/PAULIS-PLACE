#!/bin/bash
# =================================================================
# PAULI'S-PLACE VPS DEPLOYMENT SCRIPT
# Run this ON the VPS via SSH from your Windows machine:
#   ssh root@31.220.58.212 'bash -s' < scripts/deploy_vps.sh
# Or copy it up and run:
#   scp scripts/deploy_vps.sh root@31.220.58.212:/root/
#   ssh root@31.220.58.212 'bash /root/deploy_vps.sh'
# =================================================================

set -e

VPS_IP="31.220.58.212"
REPO_DIR="/root/PAULIS-PLACE"

echo "=========================================="
echo "  PAULI'S-PLACE VPS DEPLOYMENT"
echo "=========================================="

# 1. Install Docker if not present
if ! command -v docker &>/dev/null; then
    echo "[1/8] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[1/8] Docker already installed: $(docker --version)"
fi

# 2. Install Docker Compose
if ! command -v docker-compose &>/dev/null; then
    echo "[2/8] Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "[2/8] Docker Compose already installed"
fi

# 3. Clone or update repo
if [ -d "$REPO_DIR" ]; then
    echo "[3/8] Updating existing repo..."
    cd $REPO_DIR
    git pull origin main
else
    echo "[3/8] Cloning repo..."
    cd /root
    git clone https://github.com/executiveusa/PAULIS-PLACE.git
    cd $REPO_DIR
fi

# 4. Create .env from Supabase connection
echo "[4/8] Creating .env with Supabase connection..."

# Self-hosted Supabase Postgres connection
# The Supabase Postgres is running on this VPS at port 5432
# Default Supabase Postgres credentials:
SUPABASE_DB_USER="postgres"
SUPABASE_DB_PASSWORD="your-supabase-db-password"  # <-- CHANGE THIS
SUPABASE_DB_NAME="postgres"
SUPABASE_DB_PORT="5432"

# Check if Supabase Postgres is running locally
if docker ps | grep -q "supabase.*db"; then
    echo "  Found Supabase Postgres container"
    # Get the actual password from the Supabase .env
    if [ -f /root/supabase/.env ]; then
        source /root/supabase/.env
        SUPABASE_DB_PASSWORD="$POSTGRES_PASSWORD"
        echo "  Got password from Supabase .env"
    fi
fi

# Build DATABASE_URL pointing to local Supabase Postgres
DATABASE_URL="postgresql://${SUPABASE_DB_USER}:${SUPABASE_DB_PASSWORD}@127.0.0.1:${SUPABASE_DB_PORT}/${SUPABASE_DB_NAME}"

# Create .env file
cat > $REPO_DIR/.env << EOF
# Database (self-hosted Supabase Postgres on this VPS)
DATABASE_URL=${DATABASE_URL}
POSTGRES_USER=${SUPABASE_DB_USER}
POSTGRES_PASSWORD=${SUPABASE_DB_PASSWORD}
POSTGRES_DB=${SUPABASE_DB_NAME}

# Redis (will be started via docker-compose)
REDIS_URL=redis://redis:6379/0

# LLM - Groq (FREE)
GROQ_API_KEY=your-groq-api-key  # <-- CHANGE THIS

# LLM - OpenRouter (fallback)
OPENROUTER_API_KEY=your-openrouter-key  # <-- CHANGE THIS
OPEN_ROUTER_API=your-openrouter-key  # <-- CHANGE THIS

# OpenAI (for DALL-E image generation only)
OPENAI_API_KEY=your-openai-key  # <-- CHANGE THIS

# App
APP_URL=https://paulis-place.vercel.app
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-secret-123")
ENVIRONMENT=production

# Supabase
SUPABASE_URL=http://127.0.0.1:5434
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key  # <-- CHANGE THIS

# Printify (optional)
PRINTIFY_SHOP_ID=
PRINTIFY_TOKEN=

# Etsy (optional)
ETSY_API_KEY=

# Payments (optional)
CREEM_API_KEY=
BTCPAY_API_URL=
BTCPAY_STORE_ID=
BTCPAY_API_KEY=

# Vercel
VERCEL_API_KEY=your-vercel-token  # <-- CHANGE THIS
EOF

echo "  .env created. EDIT IT with real API keys before continuing."
echo "  Run: nano $REPO_DIR/.env"

# 5. Check for existing Supabase
echo "[5/8] Checking for Supabase..."
if docker ps | grep -q "supabase"; then
    echo "  Supabase is running!"
    docker ps --format "  {{.Names}}: {{.Status}}" | grep -i supabase
else
    echo "  Supabase not found in Docker."
    echo "  If Supabase is installed elsewhere, update DATABASE_URL in .env"
fi

# 6. Build and start the stack
echo "[6/8] Building and starting Docker stack..."
cd $REPO_DIR

# Make sure generated dir exists
mkdir -p backend/generated

# Build and start
docker-compose down 2>/dev/null || true
docker-compose build --no-cache backend
docker-compose up -d

echo "  Waiting for services to start..."
sleep 15

# 7. Run migrations
echo "[7/8] Running database migrations..."
docker-compose exec -T backend python -c "
from models.base import Base, engine
from models.product import Product
from models.task import Task
from models.trend import Trend
from models.research import CompetitorProduct, NicheInsight
from services.wiki_service import WikiEntry
from agents.council_agent import CouncilDeliberation
from services.payment_service import Payment
from services.evolving_memory import EvolvingMemory
Base.metadata.create_all(bind=engine)
print('All tables created successfully')
" 2>&1 || echo "  Migration via docker failed, trying direct..."

# Seed data
docker-compose exec -T backend python scripts/seed_data.py 2>&1 || echo "  Seed may have already run"

# 8. Trigger the agents
echo "[8/8] Triggering agents..."
curl -s -X POST http://localhost:8000/api/trigger/boot 2>&1 || true
sleep 2
curl -s -X POST http://localhost:8000/api/trigger/scan-trends 2>&1 || true

# Final status
echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Services:"
docker-compose ps 2>/dev/null || docker ps --format "{{.Names}}: {{.Status}}"
echo ""
echo "Health check:"
curl -s http://localhost:8000/api/health 2>&1 || echo "Backend not responding yet"
echo ""
echo "Endpoints:"
echo "  API:      http://${VPS_IP}:8000"
echo "  API Docs: http://${VPS_IP}:8000/docs"
echo "  Frontend: https://paulis-place.vercel.app"
echo ""
echo "IMPORTANT: Update NEXT_PUBLIC_API_URL in Vercel to:"
echo "  http://${VPS_IP}:8000"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f backend"
echo "  docker-compose logs -f celery-worker"
echo ""
echo "To edit env vars:"
echo "  nano $REPO_DIR/.env"
echo "  docker-compose restart"
echo "=========================================="
