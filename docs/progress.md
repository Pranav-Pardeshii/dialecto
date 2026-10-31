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
  - Scaffolded `backend/` and `frontend/` monorepo.
  - App Shell with demo identity role switcher (`Aarav` Class 10 student / `Ms. Rao` Biology instructor).
  - Multi-stage Dockerfiles, root `Makefile`, `docker-compose.yml`, `ci.yml`.
- **Milestone M1 Complete (Data and Concept Graph):**
  - Verified content datasets created: `backend/app/content/concepts.json` (20 concepts across 3 chapters), `misconceptions.json` (23 NCERT misconceptions), `questions.json` (verified starter question bank).
  - Full SQLAlchemy 2.0 ORM models in `backend/app/models/entities.py`.
  - Alembic async migrations configured with baseline migration `001_initial_schema.py`.
  - Pure domain DAG validation with topological sort and prerequisite cycle detection in `backend/app/domain/graph.py` with 100% unit test coverage.
  - Concept repository and service implementing effective mastery decay and status computation.
  - Endpoints `GET /api/v1/concepts` and `GET /api/v1/concepts/{concept_id}` tested and verified.
  - Seeder script `backend/app/db/seed.py` for idempotent data ingestion.
  - Interactive Concept Graph UI built with `@xyflow/react` on `/dashboard` with custom node cards, chapter badges, mastery indicators, and `ConceptDetailModal` lesson reader.
  - Offline question generator script `backend/scripts/generate_questions.py`.

---

## In Progress
- Transitioning to **Milestone M2: Learner Core (BKT, Elo, SM-2, Selector, Diagnostic & Practice Endpoints/Screens)**.

---

## Next
- **Milestone M2 Plan:**
  1. Build pure domain modules in `backend/app/domain/`:
     - `bkt.py`: Bayesian Knowledge Tracing with slip/guess adjustments and soft evidence bounds.
     - `elo.py`: Question difficulty rating calibration ($b \leftarrow b + K(\sigma(\theta - b) - y)$).
     - `sm2.py`: SM-2 spaced repetition scheduler (quality score $q$, $EF'$, repetition intervals, decay).
     - `selector.py`: Next question selector targeting weak, unlocked concepts near 70% expected success.
  2. Implement unit tests with hand-calculated expected values for all domain math.
  3. Implement Practice & Diagnostic services and repositories:
     - `POST /api/v1/diagnostic/sessions`, `POST /api/v1/diagnostic/sessions/{id}/answers`, `GET /api/v1/diagnostic/sessions/{id}/result`.
     - `POST /api/v1/practice/next`, `POST /api/v1/practice/answers` (atomic transaction with `client_attempt_id` idempotency and row lock).
     - `GET /api/v1/learner/mastery`, `GET /api/v1/learner/summary`.
  4. Build full frontend interactive screens:
     - Diagnostic flow on `/diagnostic`: 15 adaptive questions with uncertainty sampler and final mastery profile.
     - Targeted practice on `/practice`: Clean MCQ card, `VoiceFriendlyTextarea` reasoning box, animated mastery delta reveal.
  5. Run checks (`make check`), commit, and push.

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

# Seed database
cd backend && uv run python -m app.db.seed
```
