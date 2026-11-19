#!/usr/bin/env bash
# ==============================================================================
# Regional Bazaar — Turnkey AWS EC2 Production Deployment Script
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " Starting Regional Bazaar AWS Deployment"
echo "=========================================================="

# 1. Check prerequisites
command -v docker >/dev/null 2>&1 || {
  echo "Docker is not installed. Installing Docker..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed successfully."
}

# 2. Check for .env.prod
if [ ! -f ".env.prod" ]; then
  echo "ERROR: .env.prod file not found!"
  echo "Please create .env.prod with the required variables:"
  echo "  POSTGRES_PASSWORD=..."
  echo "  GROQ_API_KEY=..."
  echo "  AWS_S3_BUCKET_NAME=..."
  echo "  AWS_S3_CUSTOM_DOMAIN=... (optional CloudFront domain)"
  exit 1
fi

# 3. Pull latest base images
echo "Pulling latest Docker base images..."
docker compose -f docker-compose.prod.yml pull postgres redis

# 4. Build backend and frontend production images
echo "Building backend and frontend production images..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# 5. Start database and cache services first
echo "Starting PostgreSQL and Redis..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres redis

# 6. Wait for PostgreSQL to become healthy
echo "Waiting for PostgreSQL database to be healthy..."
until docker compose -f docker-compose.prod.yml exec -T postgres pg_isready; do
  sleep 2
done

# 7. Apply Alembic database migrations
echo "Running database migrations..."
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend alembic upgrade head

# 8. Synchronize products and media to Amazon S3
echo "Synchronizing products and media to Amazon S3..."
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backend python -m scripts.sync_products_to_s3

# 9. Launch all remaining services
echo "Launching application services..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

echo "=========================================================="
echo " Regional Bazaar deployed successfully on AWS!"
echo " Web UI:     http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo 'localhost')"
echo " Backend:    http://localhost:8000/health"
echo "=========================================================="
