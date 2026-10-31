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

- **Milestone M3 Complete (AI Layer - Groq Router, Circuit Breaker, Token Budget, Misconception Classification, Ops Telemetry):**
  - Groq async client wrapper with startup model verification in `app/ai/llm/client.py`.
  - In-process Circuit Breaker in `app/ai/llm/breaker.py` with states `closed`, `half_open`, and `open`, cooldown timers, and immediate tripping on RateLimitError (429).
  - In-process Token Budget rate limiter in `app/ai/llm/budget.py` with continuous refill and capacity checks.
  - Non-blocking async telemetry recorder in `app/ai/llm/recorder.py` using `asyncio.Queue` draining to `llm_calls` table with in-memory ring buffer for low-latency ops lookups.
  - Resilient `LLMRouter` in `app/ai/llm/router.py`:
    - Chain traversal: primary model (`openai/gpt-oss-120b`) with fallbacks (`llama-3.3-70b-versatile,llama-3.1-8b-instant`).
    - One repair retry on schema validation failures.
    - One jittered retry on transient timeouts or connection errors.
  - Prompt templates in `app/ai/prompts/`: `misconception_classifier.md`, `judge.md`, `student_persona.md`.
  - Misconception classification agent in `app/ai/agents/misconception_classifier.py` wired to practice submissions without holding open DB transactions across LLM calls.
  - Telemetry endpoint `GET /api/v1/ops/llm-stats` reporting latency percentiles (p50, p95), fallback rates, error rates, circuit breaker statuses, and token budgets.
  - Frontend `/ops` telemetry screen displaying system health with zero backend framework leak.
  - All 40 unit and integration backend tests passing.

---

- **Milestone M4 Complete (Teach-Back Mode with Pip - Persona, Rubric Judge, Interactive Arena):**
  - Rubric judge agent implemented in `backend/app/ai/agents/judge.py` using prompt `app/ai/prompts/judge.md` with structured output schema, rubric checklist evaluation, misconception identification, and keyword-based fallback.
  - Student persona agent implemented in `backend/app/ai/agents/student_persona.py` with calibrated comprehension states (Levels 0 through 3) for Pip the peer learner.
  - Teach-Back service implemented in `backend/app/services/teachback_service.py`:
    - In-process per-session concurrency lock (`_session_locks`) preventing double clicks (`409 turn_in_progress`).
    - Turn limit ceiling (max 4 turns or Level 3) enforcing clean session conclusion (`409 session_closed`).
    - Soft-evidence Bayesian Knowledge Tracing update ($P_{\text{new}} = P_{\text{prior}} + w(P_{\text{bkt}} - P_{\text{prior}})$ with $w = \min(0.7, \text{confidence})$).
    - Zero DB transactions held across LLM calls; atomic write transaction for turn storage and mastery updates.
  - Endpoints `POST /api/v1/teachback/sessions`, `POST /api/v1/teachback/sessions/{id}/turns`, and `GET /api/v1/teachback/sessions/{id}` tested and verified.
  - Interactive Teach-Back Arena UI built at `frontend/src/app/(student)/teach-back/[conceptId]/page.tsx`:
    - Left column: Pip avatar with live comprehension level badges (Level 0: Confused → Level 3: Mastered!) and NCERT rubric checklist with live checkmarks.
    - Right column: Real-time dialogue scroll thread with Pip character speech bubbles, turn score feedback, `VoiceFriendlyTextarea` optimized for voice dictation, and completion celebration card.
  - All 41 unit and integration backend tests passing.

---

## In Progress
- Transitioning to **Milestone M5: Teacher Dashboard & Spaced Reviews (Class Heatmap, Gap Analysis, Review Queue, 30-Student Real-Math Seeder)**.

---

## Next
- **Milestone M5 Plan:**
  1. Spaced review scheduler endpoint in `app/api/v1/endpoints/review.py`:
     - `GET /api/v1/reviews/due`: returns concepts due for SM-2 repetition, ordered by priority.
  2. Teacher classroom analytics in `app/services/teacher_service.py` and `app/api/v1/endpoints/teacher.py`:
     - `GET /api/v1/teacher/classrooms/{id}/heatmap`: $30 \times 20$ student-concept effective mastery matrix.
     - `GET /api/v1/teacher/classrooms/{id}/gaps`: concepts ranked by mean mastery and % students below 50%.
     - `GET /api/v1/teacher/classrooms/{id}/misconceptions`: curriculum misconceptions ranked by prevalence.
     - `GET /api/v1/teacher/classrooms/{id}/at-risk`: students with overall mastery below 0.4 or 3+ overdue concepts.
     - `GET /api/v1/teacher/classrooms/{id}/students/{user_id}`: student drill-down with concept masteries and attempt history.
  3. Expand `app/db/seed.py` with 30 simulated students generated strictly via domain math with back-dated attempts, realistic clusters, and class-wide weak spots.
  4. Build Teacher Heatmap & Insights UI at `frontend/src/app/(teacher)/class/page.tsx` with student/concept hover cards, filter bars, and gap rankings.
  5. Build Review Queue UI at `frontend/src/app/(student)/review/page.tsx`.
  6. Run checks, commit, and push.

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
