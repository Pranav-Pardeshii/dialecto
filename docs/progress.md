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

- **Master Feature Implementation (Four Major Capabilities & Interactive Biology Lab):**
  - **Feature 1: Teacher Intervention Planner:**
    - Domain service `app/services/intervention_service.py` analyzing classroom analytics to recommend targeted clinics (threshold: concept failure rate $\ge 35\%$ or mean mastery $< 0.50$, or $\ge 3$ students sharing an active misconception).
    - Database models `Intervention` and `InterventionAssignment` tracked through migration `002_authoring_diagrams.py`.
    - 1-click cohort assignment, student completion endpoint (`POST /api/v1/learner/interventions/{id}/complete`), and pre/post intervention outcome measurement reporting mean mastery gain and statistical distribution.
    - Teacher UI in `frontend/src/components/teacher/InterventionPlannerTab.tsx` with recommendation triage, custom clinic creation with Wispr dictation, live assignment progress, and outcome measurement drawer.
    - Student dashboard alert banner in `frontend/src/app/(student)/dashboard/page.tsx` displaying assigned interventions with direct task launch and completion triggers.
  - **Feature 2: Explainable Mastery and Confidence:**
    - Pure domain math in `app/domain/explainable_mastery.py` strictly separating BKT mastery $P(L)$ from Evidence Confidence score $S \in [0.0, 1.0]$ based on sample size $n$, question difficulty variance, recency decay, and evaluation diversity (practice, diagnostic, teach-back, diagram lab).
    - Categorical evidence strength classification: `insufficient` ($n=0$), `low` ($S < 0.35$), `moderate` ($0.35 \le S < 0.70$), `high` ($S \ge 0.70$).
    - Deterministic state-derived narrative generation reflecting current mastery, SM-2 decay, active misconceptions, prerequisite blockers, and trajectory trend (`improving`, `declining`, `stable`, `insufficient_data`).
    - API endpoints `GET /api/v1/learner/concepts/{id}/explainable` and `GET /api/v1/teacher/students/{id}/concepts/{cid}/explainable`.
    - UI in `frontend/src/components/graph/ConceptDetailModal.tsx` displaying evidence strength badges, confidence metrics, trend arrows, state narratives, active misconception warnings, and complete chronological evidence timelines.
  - **Feature 3: AI-Powered Question Generation & Authoring Pipeline:**
    - Curriculum-grounded generation in `app/services/question_authoring_service.py` using prompt `app/ai/prompts/question_generator.md` via `LLMRouter` with deterministic repair retry.
    - Pure pedagogical validator in `app/domain/question_validator.py` verifying non-empty stems, distinct options, answer key presence, bucket ranges (1-3), and rejecting cross-concept misconception associations.
    - Database versioning and review workflow: `review_status` (`draft`, `approved`, `rejected`), `version`, `parent_id`, and immutable historical attempt preservation (branching a new version if $n\_attempts > 0$).
    - Student question bank protection: `question_repo.py` strictly filters `verified = True` AND `review_status = 'approved'`, preventing unreviewed drafts from ever being served.
    - Teacher UI in `frontend/src/app/(teacher)/authoring/page.tsx` with generation parameters form, live draft list, review/approval/rejection controls, and manual authoring modal with Wispr dictation support.
  - **Feature 4: Interactive Diagram Lab (Voice-First Flagship Experience):**
    - Scientific anatomical manifests in `app/content/diagram_manifest.json` for Human Heart (`heart`), Nephron (`nephron`), and Animal Cell (`animal_cell`) with anatomical structures, aliases, pathways, and CC-BY-4.0 licensing attribution.
    - 3D Anatomical Renderer in `frontend/src/components/lab/Biological3DViewer.tsx` powered by Three.js and `@react-three/fiber` with procedural geometry, heartbeat pulsation, orbit controls, structure isolation, and glow highlights.
    - 2D Interactive Scientific Atlas in `frontend/src/components/lab/Biological2DAtlas.tsx` as an accessible SVG fallback with clickable structures, accessible focus, tooltips, and pathway flows.
    - Voice command interpreter in `app/services/diagram_command_service.py` parsing spoken natural language commands (`HIGHLIGHT_STRUCTURE`, `TRACE_PATHWAY`, `ISOLATE_STRUCTURE`, `RESET_VIEW`, `CLARIFY`, `START_ASSESSMENT`) with ambiguity handling (prompting clarification for generic terms like "ventricle"), prompt injection defense, and assessment safety guard (blocking answer leakage during active tests).
    - Diagram assessment engine in `app/services/diagram_assessment_service.py` supporting identification, sequence, and explanation tasks with atomic BKT and SM-2 single-transaction updates under `SELECT ... FOR UPDATE` row locks.
    - Lab UI in `frontend/src/app/(student)/lab/page.tsx` with 3D/2D toggle, exploration vs. assessment modes, Wispr command input box with live interpretation feedback, structure inspector, and assessment submission with mastery delta reveals.
    - Dedicated voice-first input component in `frontend/src/components/ui/WisprCommandInput.tsx` compliant with native focusable `<textarea>`, keyboard shortcuts (`Enter` / `Ctrl+Enter`), error preservation, and browser mic fallback.
  - **Testing & Quality Assurance:**
    - 73/73 backend tests passing (`pytest tests -v`).
    - 0 errors across 112 backend files in `ruff` and `mypy`.
    - Next.js production build (`pnpm build`) passing across all 13 routes with 0 ESLint warnings or errors and 0 TypeScript errors.
  - **Cell Architecture Studio Source Replacement & Biological Diagram Integration:**
    - Completely replaced all AI-generated or substitute biological diagrams with authentic source code and permitted 3D assets from `https://github.com/cclank/cell-architecture-studio`.
    - Enforced strict 7-specimen whitelist matching source `src/data/cells.ts`:
      1. **Plant Cell (`plant`)**: Production GLB `/models/plant-cell-first001.glb` (scale 2.36, rotation [0.08, -1.42, -0.02], exposure 1.08, native materials) mapped to photosynthesis (`lp-photosynthesis`).
      2. **White Blood Cell (`whiteBlood`)**: Production GLB `/models/white-blood-cell-user.glb` (scale 3.18, rotation [0.02, -0.18, 0], exposure 1.08, native materials) mapped to circulation and immune defense (`lp-circulation`).
      3. **Animal Cell (`animal`)**: Production GLB `/models/animal-cell-nih.glb` (scale 0.044, rotation [0.24, -0.08, 0.03], exposure 1.12, NIH 3DPX-015797) mapped to cellular respiration (`lp-respiration`).
      4. **Neuron (`neuron`)**: Production GLB `/models/neuron-nih.glb` (scale 3.15, rotation [0.18, -0.24, -0.18], exposure 1.05, NIH 3DPX-015796) mapped to nerve transmission (`cc-neuron`).
      5. **Bacterial Cell Wall (`bacteria`)**: Production GLB `/models/bacteria-wall-nih.glb` (scale 0.00185, rotation [0.08, -0.44, -0.08], exposure 1.1, NIH 3DPX-010752) mapped to prokaryotic nutrition (`lp-nutrition`).
      6. **Epithelial Cell (`epithelial`)**: Authentic source repository procedural columnar architecture (`EpithelialModel` with microvilli brush border and tight junctions) mapped to digestion and absorption (`lp-digestion`).
      7. **Muscle Cell (`muscle`)**: Authentic source repository procedural skeletal fiber architecture (`MuscleModel` with sarcomere myofibril bundles and interfibrillar mitochondria) mapped to contractile respiration (`lp-respiration`).
    - Prohibited and permanently eliminated all invented placeholder diagrams (Heart, Nephron, Kidney, Lungs, DNA, or external 3D models).
    - Ported source material shaders `frontend/src/lib/cellMaterials.ts` (`applyAssetVertexColors`, `createAssetMaterial`, `createNativeAssetMaterial`, `createSolidAssetMaterial`).
    - Ported specimen metadata `frontend/src/data/cells.ts` preserving organelle attributes, clinical notes, and biological facts while sanitizing all developer local filesystem paths.
    - Integrated authentic `Biological3DViewer.tsx` with `CellScene` renderer, R3F, Drei, ACES Filmic tone mapping, Mesh/Focus modes, cutaway cross-section, auto-rotation, `ModelLoadingOverlay`, and `ModelErrorBoundary` for graceful asset unavailability states without geometric fabrication.
    - Updated `Biological2DAtlas.tsx` with dedicated, accessible 2D SVG schematics for all 7 whitelisted specimens.
    - Documented asset provenance, creators, and redistribution licenses in `docs/ASSETS_ATTRIBUTION.md`.
    - Synchronized backend `backend/app/content/diagram_manifest.json` and `backend/app/services/diagram_command_service.py` to support all 7 specimen IDs, voice command interpretation, ambiguity resolution, and BKT/SM-2 assessments.
    - Verified all 73 backend tests passing (`pytest tests -v`), 0 ruff & mypy errors, frontend `pnpm typecheck` (0 errors), `pnpm lint` (0 warnings or errors), and Next.js production build (`pnpm build` across all 13 routes) passing cleanly.
- **Milestone M7 Complete (Cell Architecture Studio 3D Interaction Fix, Pip Teaching Integration & Taste UI Polish):**
  - **Resolved 3D Biological Structure Interaction Defects:**
    - Single combined meshes in GLBs (`plant`, `whiteBlood`, `animal`, `neuron`, `bacteria`) augmented with validated, model-local 3D anatomical hotspot pins anchored in normalized coordinate space in `frontend/src/data/cells.ts`.
    - Pins rotate and scale synchronously with the specimen, support hover enlargement, pointer cursor, Drei `<Html>` contextual label tooltips, and active emerald pulse rings upon selection.
    - Added direct mesh raycast pointer and click event listeners to procedural Three.js geometries in `EpithelialModel` and `MuscleModel` (microvilli, tight junction toruses/tubes, sarcolemma capsule, myofibril bundles, and nuclei).
    - Attached `onPointerMissed` canvas handler to gracefully clear selection to an empty exploration state when clicking open viewport space.
    - **Real GLB Mesh Picking & Coordinate Anchor Fix:**
      - Wired `onPointerDown` and `onClick` with a 6px drag threshold to distinguish camera rotation from clicks directly on the biological 3D mesh (`primitive object={clonedScene}`).
      - Transformed raycast intersection surface points into mesh-local coordinates (`mesh.worldToLocal(event.point.clone())`) to accurately resolve biological organelle structures.
      - Fixed marker coordinate misalignment: anchored precision anatomical pins INSIDE the `<Center>` group within `AssetCellModel` so they inherit the exact transformations, centering, rotation, and scaling of the model.
      - Removed all disconnected/floating markers outside the specimen bounds.
      - Added automated regression test `test_glb_geometry_integrity_and_bounds` verifying all 5 production GLBs, mesh primitives, and physical bounding box containment.
  - **Removed Interface Clutter & UI Noise:**
    - Completely removed `WisprCommandInput` and the `Voice Command Interpreter` section from `/lab`.
    - Removed redundant bottom organelle quick-selector chip bars under the canvas.
    - Elevated 3D viewport proportions into a spacious, calm biological stage (`min-h-[520px]`) with warm paper ground (`#fbf7ee`) and subtle 1px borders (`#E5E3D8`).
  - **Contextual "Teach this to Pip" Integration:**
    - Implemented `frontend/src/components/lab/PipTeachSlideOver.tsx` opening directly from any selected biological structure.
    - Pip starts at Level 0 ("Confused") with tailored instructional inquiry regarding the organelle's cellular function.
    - Displays real-time Pip comprehension level progress (Level 0 Confused ➔ Level 1 Curious ➔ Level 2 Connecting Dots ➔ Level 3 Mastered).
    - Rubric checklist dynamically updates with checkmarks as the learner covers key points.
    - Integrated with `VoiceFriendlyTextarea` for natural dictation or typed explanations.
    - Wired to real backend endpoints (`api.startTeachback` and `api.submitTeachbackTurn`) updating learner BKT mastery without holding transactions open.
  - **Taste Skill Polish (`design-taste-frontend` v2):**
    - Adhered strictly to `docs/design.md` warm botanical design tokens: `#FAF9F5` canvas, `#FFFFFF` surface cards, `#E5E3D8` borders, `#191A15` deep slate ink, `#2E7D32` emerald accents.
    - Provided structured side-rail directory of cell structures with color badges and keyboard accessibility.
    - Strict UI Cleanliness & Framework Secrecy: zero mentions of backend frameworks or internal tools in user-facing copy.

  - **Console Unmount Race Condition & removeChild Fix:**
    - Resolved React 19 synchronous root unmount race condition and `DOMException: Failed to execute 'removeChild' on 'Node': The node to be removed is not a child of this node` in `frontend/src/components/lab/Biological3DViewer.tsx`.
    - Eliminated conditional JSX mounting (`{(hovered || isSelected) && <Html ...>}`) inside `OrganelleHotspotPin`. `<Html>` is now persistently mounted with CSS `opacity` and `visibility` transitions, preventing Drei from calling `createRoot()` and `root.unmount()` / `removeChild()` during R3F render passes.
    - Added safe client-side DOM reconciliation patch for `Node.prototype.removeChild` to prevent third-party canvas overlay unmount collisions.
    - Verified all 13 Next.js routes, `pnpm typecheck` (0 errors), `pnpm lint` (0 errors), and all 74 backend tests passing.

---

## Complete
All Milestones (M0 through M6), the Stabilization Pass, and the Master Feature Implementation are completely implemented, verified, and committed:
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
