.PHONY: dev check test seed migrate eval lint format typecheck

dev:
	@echo "Starting local environment..."
	docker compose up -d db

check: lint typecheck test

lint:
	cd backend && uv run ruff check app tests
	cd frontend && pnpm lint

format:
	cd backend && uv run ruff format app tests
	cd frontend && pnpm format

typecheck:
	cd backend && uv run mypy app
	cd frontend && pnpm typecheck

test:
	cd backend && uv run pytest tests/unit tests/integration -v

eval:
	cd backend && RUN_LIVE_EVALS=1 uv run pytest tests/evals -v

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python -m app.db.seed

