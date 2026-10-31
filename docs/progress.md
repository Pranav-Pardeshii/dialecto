# Progress: Dialecto

Handoff memory across agent sessions.

---

## Done
- **Phase 0 Documentation:**
  - Read all authoritative docs (`AGENTS.md`, `README.md`, `architecture.md`, `database.md`, `api.md`, `curriculum.md`, `plan.md`).
  - Installed Taste Skill (`design-taste-frontend` v2) in `.agents/skills/design-taste-frontend`.
  - Created Phase 0 docs: `design.md`, `prd.md`, `features.md`, `testing.md`, `setup.md`, `DECISIONS.md`.
  - Enforced strict rule: **Zero mentions of backend frameworks or third-party tools in UI code or copy.**
- **Milestone M0 Complete (Setup, Monorepo Skeleton, Design Foundation):**
  - Scaffolded `backend/`: FastAPI async modular monolith, Python 3.12 with `uv`, `app/core/` (settings, logging, error envelope, tracing middleware, rate limits), `app/api/v1/` (`/health`, `/ready`, `/users`, `/me`), `app/db/` (asyncpg session).
  - Scaffolded `frontend/`: Next.js 15 App Router, TypeScript strict, Tailwind themed per Taste Skill tokens (`Fraunces` + `Plus Jakarta Sans` + `JetBrains Mono`), TanStack Query, generated typed API client (`pnpm gen:api`).
  - Built App Shell with demo identity role switcher (`Aarav` Class 10 student / `Ms. Rao` Biology instructor).
  - Root configuration: `Makefile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`, `backend/Dockerfile`, `frontend/Dockerfile`.
  - Verified: `ruff` (clean), `mypy` (clean), `pytest` (5 passed), `pnpm lint` (clean), `pnpm typecheck` (clean), `pnpm build` (clean).

---

## In Progress
- Transitioning to **Milestone M1: Data & Concept Graph**.

---

## Next
- **Milestone M1 Plan:**
  1. Define SQLAlchemy 2.0 ORM models in `backend/app/models/` matching `docs/database.md` (`Classroom`, `User`, `Concept`, `ConceptPrerequisite`, `Misconception`, `Question`, `Mastery`, `Session`, `Attempt`, `DetectedMisconception`, `TeachbackSession`, `TeachbackTurn`, `LLMCall`).
  2. Setup Alembic async migrations (`alembic init -t async migrations`) and generate initial migration.
  3. Convert `docs/curriculum.md` into `app/content/concepts.json` and `app/content/misconceptions.json`.
  4. Write idempotent seeder `python -m app.db.seed` (loads content JSON, creates classroom and demo users Aarav and Ms. Rao).
  5. Implement `GET /api/v1/concepts` and `GET /api/v1/concepts/{concept_id}` endpoints.
  6. Build interactive Concept Graph in frontend (`src/components/graph/` using `@xyflow/react`) with custom nodes showing chapter, mastery ring, and locked/unlocked state.
  7. Regenerate API types (`pnpm gen:api`), run checks, update `progress.md`, and commit.

---

## Known Bugs / Notes
- Local service `postgresql-x64-18` is running on host port 5432. When using Docker Compose, port 5432 should be used after stopping the local service or configuring credentials, or using a cloud database (Neon) for live deployment.
- Strict UI framework secrecy is active and enforced across all screens.

---

## Useful Commands
```bash
# Quality checks
cd backend && uv run ruff check app tests
cd backend && uv run mypy app
cd backend && uv run pytest tests -v
cd frontend && pnpm lint
cd frontend && pnpm typecheck
cd frontend && pnpm build

# Type generation
cd frontend && pnpm gen:api

# Run dev servers
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev
```
