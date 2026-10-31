#!/usr/bin/env bash
set -e

# Ensure virtualenv binaries are in PATH
if [ -d ".venv/bin" ]; then
    export PATH="$(pwd)/.venv/bin:$PATH"
elif [ -d "/opt/render/project/src/.venv/bin" ]; then
    export PATH="/opt/render/project/src/.venv/bin:$PATH"
elif [ -d "/opt/render/project/src/backend/.venv/bin" ]; then
    export PATH="/opt/render/project/src/backend/.venv/bin:$PATH"
fi

echo "==> Running Alembic database migrations..."
alembic upgrade head

echo "==> Seeding database (idempotent)..."
python -m app.db.seed

echo "==> Starting Uvicorn web server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
