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

- **Milestone M2 Complete (Learner Core - BKT, Elo, SM-2, Selector, Diagnostic & Practice Flow):**
  - Pure domain mathematics implemented with 100% unit test coverage:
    - `bkt.py`: Bayesian Knowledge Tracing with dynamic slip adjustment ($S_q = S + 0.05(d-2)$), guess rate $G=0.25$, and continuous soft-evidence update.
    - `elo.py`: Question difficulty rating calibration ($b \leftarrow b + K(\text{expected} - y)$).
    - `sm2.py`: SM-2 spaced repetition with quality score $q \in \{1,3,4,5\}$, ease factor updates, repetition intervals, and exponential decay ($p_{\text{eff}} = p \cdot \exp(-\text{days\_overdue}/14)$).
    - `selector.py`: Adaptive next-item selector prioritizing weak unlocked concepts near 70% expected success.
  - Question repository and atomic practice submission in `practice_service.py` with `SELECT ... FOR UPDATE` row locking, `client_attempt_id` idempotency, and single-transaction persistence.
  - 15-question adaptive diagnostic assessment engine in `diagnostic_service.py` with uncertainty sampling.
  - Learner mastery and summary endpoints in `learner_service.py`.
  - Comprehensive unit and integration test suites: all 27 backend tests passing.
  - Next.js interactive screens built with zero backend/framework mentions:
    - `/practice`: Clean MCQ card, `VoiceFriendlyTextarea` optimized for voice dictation, instant animated mastery delta reveal, misconception alerts.
    - `/diagnostic`: Adaptive 15-question exam-prep diagnostic with real-time progress and final concept mastery breakdown.

---

## In Progress
- Transitioning to **Milestone M3: AI Layer (Groq Router, Circuit Breaker, Token Budget, Misconception Classification, Ops Telemetry)**.

---

## Next
- **Milestone M3 Plan:**
  1. Groq async SDK client wrapper in `app/ai/llm/client.py` with startup model check.
  2. In-process Circuit Breaker in `app/ai/llm/breaker.py` tripping on 429 rate limits.
  3. Token budget manager in `app/ai/llm/budget.py`.
  4. Async call telemetry recorder in `app/ai/llm/recorder.py` logging to `llm_calls` table.
  5. `LLMRouter` in `app/ai/llm/router.py` with primary model `openai/gpt-oss-120b`, fallback chain (`llama-3.3-70b-versatile,llama-3.1-8b-instant`), exponential backoff, and JSON repair retry.
  6. Prompt templates in `app/ai/prompts/*.md` (`misconception_classifier.md`, `judge.md`, `student_persona.md`).
  7. Misconception classifier agent in `app/ai/agents/misconception_classifier.py` wired to practice submissions when reasoning is provided.
  8. Telemetry endpoint `GET /api/v1/ops/llm-stats` and frontend ops status display.
  9. Run checks, commit, and push.

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
