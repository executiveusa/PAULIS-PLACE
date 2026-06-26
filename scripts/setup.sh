#!/bin/bash
# scripts/setup.sh

echo "🚀 Setting up DigiFactory..."

# Create directories
mkdir -p backend/generated
mkdir -p frontend/src

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Created .env file - please edit with your API keys"
fi

# Build and start services
docker-compose build
docker-compose up -d

# Wait for database
echo "Waiting for database..."
sleep 10

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed initial data
docker-compose exec backend python scripts/seed_data.py

echo "✅ Setup complete!"
echo "🌐 Dashboard: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Restart: docker-compose restart"
echo "3. Click 'Scan Trends' in dashboard"
