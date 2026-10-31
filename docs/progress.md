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

- **Milestone M5 Complete (Teacher Dashboard & Spaced Reviews - Heatmap, Gaps, At-Risk, 30-Student Real-Math Seeder):**
  - Spaced review scheduler in `backend/app/services/review_service.py` and `backend/app/api/v1/endpoints/review.py` (`GET /api/v1/reviews/due`) prioritizing overdue concepts and decayed mastery.
  - Teacher analytics service in `backend/app/services/teacher_service.py` and `backend/app/api/v1/endpoints/teacher.py` (with teacher role check):
    - `GET /api/v1/teacher/classrooms/{id}/heatmap`: $30 \times 20$ student-concept effective mastery matrix.
    - `GET /api/v1/teacher/classrooms/{id}/gaps`: curriculum concepts ranked by failure rate and lowest average mastery.
    - `GET /api/v1/teacher/classrooms/{id}/misconceptions`: ranked prevalence of active misconceptions across the classroom.
    - `GET /api/v1/teacher/classrooms/{id}/at-risk`: students flagged with average mastery $< 45\%$ or $3+$ overdue concepts.
    - `GET /api/v1/teacher/classrooms/{id}/students/{student_id}`: comprehensive student drill-down with concept masteries, active misconceptions, and recent attempts.
  - Seeder expanded in `backend/app/db/seed.py`: 30 simulated students generated strictly via domain math (BKT, Elo, SM-2) with back-dated attempts, realistic clusters (5 high, 18 average, 7 struggling), and active misconception hotspots.
  - Frontend screens:
    - `/class`: Full Instructor Heatmap & Insights with 4 interactive tabs (Knowledge Matrix with hover tooltips, Curriculum Gaps with failure percentage bars, Misconception Hotspots with student counts, and At-Risk Learners with slide-over drill-down drawer).
    - `/review`: Spaced Review Queue with overdue day indicators, progress bars, and one-click launch into practice.
  - All 48 unit and integration backend tests passing.

---

- **Milestone M6 Complete (Speech Fallback via Whisper, Polish, and Full End-to-End Delivery):**
  - Groq Whisper speech-to-text endpoint at `POST /api/v1/speech/transcriptions` in `backend/app/api/v1/endpoints/speech.py` with 5 MB file size boundary and empty audio validation.
  - Interactive browser voice dictation fallback in `frontend/src/components/ui/VoiceFriendlyTextarea.tsx` with MediaRecorder recording states, pulsing indicators, and auto-transcription appending.
  - Strict UI cleanliness verified across all screens: zero technical/framework jargon anywhere in UI text.
  - Complete backend test suite: all 50 unit and integration tests passing (`pytest`).
  - Strict type safety and linting passing 100% on both backend (`ruff`, `mypy`) and frontend (`tsc --noEmit`, Next.js ESLint, `next build`).
  - Production builds verified and all contracts synchronized via `openapi-typescript`.
  - Resolved PostCSS configuration and Next.js CSS stylesheet asset serving (`postcss.config.js` standard CommonJS export, cleared stale `.next` cache, and verified all 7 frontend routes returning 200 OK with full Tailwind utility compilation).

- **Comprehensive Bug-Fixing & Stabilization Pass Complete:**
  - **Database Seeding (`app/db/seed.py`):** Explicit flush after prerequisite insertion (`autoflush=False` fix), deterministic isolated `Random(42)`, valid per-student practice sessions (zero orphan attempts), answer keys aligned with correctness, idempotent repeated execution.
  - **Security & Authorization (`deps.py`, `teacher.py`, `ops.py`, `speech.py`):** `ALLOW_DEMO_AUTH` flag rejecting unauthenticated demo headers in production, `verify_classroom_access` multi-tenant scoping, authenticated speech transcription and ops endpoints, user/speech/teachback rate limiting.
  - **Adaptive Practice & Concurrency (`practice_service.py`, `selector.py`):** Session verification (active, ownership, kind), answer key validation (422 for invalid keys), response timing validation (0 to 600,000ms), idempotent retry handling, `IntegrityError` concurrency safety, 2-pass concept selection preventing 12 consecutive repeats.
  - **Diagnostic Assessment (`diagnostic_service.py`):** Idempotent retries on 15th question, prerequisite skip constraint (<0.30), unlocked recommendation guarantee, full 20-concept baseline with explicit `untested` status.
  - **Teach-Back & AI Router (`teachback_service.py`, `router.py`, `recorder.py`):** Atomic post-LLM mastery row locking, session cleanup, cumulative evaluation across transcripts, shared global request deadline, DB-backed telemetry with ring-buffer fallback.
  - **Question Bank (`questions.json`):** Corrected cross-concept misconceptions and distributed answer keys across choices (A: 23.8%, B: 28.6%, C: 23.8%, D: 23.8%).
  - **Teacher Analytics & Reviews (`teacher_service.py`, `review_service.py`):** Distinct active misconception counts via SQL joins, canonical overdue condition (`now >= next_due_at`).
  - **Frontend Fallback Elimination:** Removed all silent fabricated mocks from Practice, Diagnostic, Teach-Back, Review, Study Map, Teacher Heatmap, and System Health. All failures render authentic error states and retry buttons.
  - **UI/UX & Voice Input:** Voice-friendly textarea with MediaRecorder auto-stop and track cleanup, accessible concept graph keyboard navigation (Tab/Enter/Space/Escape), opaque high-contrast heatmap cells, distinct concept abbreviations.
  - **Build Verification:** 52/52 backend tests passing, `ruff` & `mypy` 0 errors across 68 files, `pnpm typecheck`, `pnpm lint`, and `pnpm build` (12/12 routes) passing.

---

## Complete
All Milestones (M0 through M6) and the Stabilization Pass are completely implemented, verified, and committed:
- **Adaptive Diagnostic & Practice Engine** with BKT Bayesian Knowledge Tracing, Elo item calibration, SM-2 spaced repetition decay, and optimal next-question selection.
- **Resilient AI Layer** with in-process circuit breakers, token budget rate limiting, Groq multi-model fallback chain, and misconception classification from student reasoning.
- **Teach-Back Mode with Pip** featuring autonomous comprehension levels (0 to 3), rubric key point evaluations, soft-evidence Bayesian updates, and voice dictation.
- **Teacher Classroom Analytics** featuring $30 \times 20$ interactive student-by-concept knowledge matrix, curriculum failure gap rankings, misconception hotspots, and at-risk student intervention drill-downs.
- **Spaced Review Queue** with urgency ranking and one-click review launch.
- **Observability Panel (`/ops`)** displaying live latency percentiles (P50/P95), circuit breaker states, token budgets, and invocation logs.
- **Cloud Deployment:**
  - Live Render Backend: `https://dialecto-backend-55qp.onrender.com` (Python 3.12, Alembic migrations, PostgreSQL seeded, health & readiness verified).
  - Vercel Frontend: Connected via `BACKEND_URL` environment variable through Next.js reverse proxy rewrites.
  - Brand Assets: Custom transparent biology-graph emblem generated with anti-aliasing and integrated into Navbar, Landing page, app icons, and favicon.ico.



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
