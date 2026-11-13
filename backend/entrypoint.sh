#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Seeding demo customers and orders..."
python scripts/seed.py

echo "Ingesting policy knowledge..."
python scripts/ingest_policy.py

echo "Starting product catalog ingestion in background..."
python scripts/ingest_products.py &

echo "Starting Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
