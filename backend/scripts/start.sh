#!/usr/bin/env bash
set -e

echo "==> Running Alembic database migrations..."
alembic upgrade head

echo "==> Seeding database (idempotent)..."
python -m app.db.seed

echo "==> Starting Uvicorn web server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
