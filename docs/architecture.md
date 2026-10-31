# Architecture

Status: authoritative. Changes require a note in `docs/DECISIONS.md`.

## 1. Goals and constraints

- **Goal:** a tutor whose behavior is driven by a real learner model, with an AI layer that stays up when individual LLM calls fail.
- **Constraints:** 9-hour build, one developer, no auth, no Redis or queues. "Production-ready" here means: clean layering, async I/O, migrations, typed config, structured logs, retries and fallbacks, health checks, containers, CI. It does **not** mean Kubernetes or microservices.

## 2. Style: modular monolith

One FastAPI process, one Postgres database, one Next.js app. Modules are separated by directory and by a strict dependency rule so any module could be extracted later.

```text
api  ->  services  ->  repositories  ->  models/db
                  ->  domain          (pure; no I/O)
                  ->  ai              (LLM router, agents, speech)
```

Rules:

1. `api` knows HTTP and schemas only. It calls exactly one service method per route.
2. `services` own use cases and **transaction boundaries**. They orchestrate repositories, domain functions, and agents.
3. `domain` is pure Python: BKT, Elo difficulty calibration, SM-2, selector, graph traversal. It imports nothing from `db`, `ai`, or FastAPI.
4. `ai` never touches the database directly. The `recorder` receives call records through an in-memory queue.
5. Nothing imports upward.

## 3. Runtime topology

- **Frontend:** Next.js on Vercel. Browser calls `/api/*`, which a Next.js rewrite forwards to the backend (no CORS in the browser path; CORS is still configured on the backend for direct tools).
- **Backend:** one container, one uvicorn worker. Reason: the circuit breaker, token budget, and per-user lock are in-process. Scaling out requires moving them to shared storage (see section 12).
- **Database:** PostgreSQL. Local via Docker Compose; production on Neon.
  - asyncpg uses `ssl=require`, not `sslmode`.
  - If a pooled (PgBouncer) Neon endpoint is used, disable the asyncpg statement cache (`connect_args={"statement_cache_size": 0}`).
- **Background work:** only asyncio primitives started in the app lifespan: the `llm_calls` writer task consuming a bounded `asyncio.Queue`. No external queue.

## 4. Backend module responsibilities

| Module | Responsibility |
|---|---|
| `core/config.py` | typed settings (pydantic-settings); single source of environment access |
| `core/errors.py` | `AppError` hierarchy plus global handlers that emit the error envelope |
| `core/middleware.py` | request id, access log with latency, timing header |
| `core/limits.py` | per-user in-process rate limit for LLM-backed routes |
| `api/deps.py` | `get_session`, `get_current_user` (reads `X-Demo-User-Id`; the single place to swap in real auth later) |
| `services/*` | use cases: diagnostic, practice, teachback, review, teacher analytics, misconception handling |
| `repositories/*` | queries only; no business rules |
| `domain/*` | learner-model math (section 6) |
| `ai/llm/*` | Groq client, router, breaker, budget, recorder |
| `ai/agents/*` | persona, judge, misconception classifier, lesson; each = prompt template + Pydantic output schema |

## 5. Key flows

### 5.1 Answer a practice question (no LLM on the happy path)

1. `POST /practice/answers` with `client_attempt_id`.
2. If that id exists, return the stored result (idempotent).
3. One transaction: lock the `(user, concept)` mastery row, load question and params, compute the BKT update, update the question's Elo difficulty, update SM-2, insert the attempt, insert a `detected_misconceptions` row if the chosen distractor is tagged, commit.
4. If the answer was wrong **and** `reasoning` text was given, call the misconception classifier **after** commit (txn 1 already released). Persist its result in a second small transaction. Return the combined response.

### 5.2 Diagnostic

Adaptive, 15 questions. Pick the unasked concept with maximum uncertainty (mastery closest to 0.5), skipping dependents of concepts with mastery below 0.3. A correct answer on a dependent nudges its prerequisites upward with small weight (0.3). The session ends at 15 questions; the result is the per-concept mastery map.

### 5.3 Teach-Back turn

1. Txn 1: load session, concept (key points), misconception catalog, all learner messages so far. Release the connection.
2. Judge call (router, structured output) over the **cumulative** learner explanation.
3. `domain`: compute the score, map it to Pip's `level` (0 to 3), and compute soft-evidence mastery.
4. Persona call with `level`, hidden misconceptions, and `gap_hint`.
5. Txn 2: insert both turns, update mastery and SM-2, insert any detected misconceptions, update session status.
6. A per-session `asyncio.Lock` prevents double-submits; a second concurrent request gets `409 turn_in_progress`.

### 5.4 Review

`GET /reviews/due` lists concepts whose `next_due_at` has passed, ordered by overdue time times (1 minus effective mastery). Review questions come from the same selector with `mode=review`.

## 6. Learner model (authoritative formulas)

**Per-concept BKT** with parameters in `concepts` (defaults `P(L0)=0.30, T=0.15, S=0.10`; `G = 1/num_options` for MCQ).

```text
correct: P(L|c) = P(L)(1-S) / [P(L)(1-S) + (1-P(L))G]
wrong:   P(L|w) = P(L)S     / [P(L)S     + (1-P(L))(1-G)]
learn:   P(L')  = P(L|obs) + (1 - P(L|obs)) T
```

**Difficulty-adjusted slip:** `S_q = S + 0.05 * (d - 2)` for question difficulty bucket `d in {1,2,3}`, clamped to `[0.02, 0.30]`.

**Soft evidence** (Teach-Back, or any lower-trust signal): compute `P_bkt` with the appropriate observation, then `P_new = P_prior + w * (P_bkt - P_prior)` with `w = min(0.7, judge.confidence)`.

**Item difficulty calibration (Elo-style):**

```text
theta = logit(P(L))            # student ability proxy for this concept
expected = sigmoid(theta - b)  # b = question difficulty rating
b <- b + K * (expected - y)    # y = 1 if correct else 0; K = 0.10
```

Only update `b` once a question has at least 5 attempts overall; before that it keeps its seeded difficulty (`b0` from bucket: easy -1.0, medium 0.0, hard 1.0).

**Selector (next question):**

1. Candidate concepts: prerequisites all at `p_effective >= 0.6` (unlocked), or no prerequisites.
2. Score = `(1 - p_effective) * (1 + due_bonus) * (1 + 0.5 * has_active_misconception)`; `due_bonus = 0.5` when overdue.
3. Within the chosen concept, pick the unseen-recently question minimizing `|expected - 0.70|`.
4. Return a human-readable `selection_reason` (shown in the UI as "Why this question?").

**SM-2 per concept:** quality `q`: correct and under 20 s gives 5; correct gives 4; correct but slow (over 60 s) gives 3; wrong gives 1. `EF' = max(1.3, EF + 0.1 - (5-q)(0.08 + (5-q)0.02))`. If `q < 3`: repetitions reset and interval is 1 day; otherwise intervals are 1, 6, then `round(I * EF)` days. `next_due_at = now + interval`.

**Effective mastery:** `p_effective = p_mastery * exp(-max(0, days_overdue) / 14)`.

**Status** shown in the UI: `locked` (prereqs below 0.6), `unlocked` (no attempts), `learning` (p below 0.8), `mastered` (p_effective at least 0.8).

## 7. AI layer

### 7.1 LLM router

`LLMRouter.complete(purpose, messages, schema, max_tokens, temperature, timeout)`:

1. Iterate the configured model chain (`LLM_PRIMARY_MODEL`, then `LLM_FALLBACK_MODELS`).
2. Skip a model whose **circuit breaker** is open.
3. Check the in-process **token budget** for that model (a token bucket sized to its tokens-per-minute limit). If it cannot cover the estimated request, skip to the next model immediately instead of waiting.
4. Call with `asyncio.timeout`. Response format: JSON mode where `schema` is given.
5. Errors:
   - `RateLimitError`: open the breaker for the `retry-after` value (default 20 s), try the next model.
   - Timeout or 5xx: one jittered retry (tenacity), then the next model.
   - JSON or schema validation failure: one **repair retry** on the same model (append "return only valid JSON matching the schema"), then the next model.
6. If every model fails: raise `LLMUnavailableError`. Services degrade (section 8).
7. Every attempt is pushed to the recorder queue (non-blocking; drop-oldest if full).

Notes for the implementer: verify the exact SDK exceptions and the `reasoning_effort` parameter for gpt-oss models against the installed `groq` package and Groq docs; do not assume. Reasoning tokens count toward tokens-per-minute, so use low reasoning effort for Pip and medium for the judge. At startup, call the models endpoint and log which configured models are actually available; drop unavailable ones from the chain with a warning.

### 7.2 Where LLMs are used

| Use | Live or offline | Notes |
|---|---|---|
| Question bank, lessons | offline script, human-spot-checked | never generated per request |
| Misconception classifier | live, only for wrong answers with reasoning text | deterministic distractor tags work without it |
| Teach-Back judge and persona | live | the core differentiator |
| Speech-to-text | live, optional | Groq Whisper fallback for the mic button |

### 7.3 Prompt management

Templates in `app/ai/prompts/*.md` with named placeholders, versioned in git. Each agent module owns its template and its Pydantic output schema. Learner text always appears inside delimiter tags and is described to the model as untrusted content.

## 8. Failure modes and degradation

| Failure | Detection | Behavior |
|---|---|---|
| Primary model rate-limited | RateLimitError or budget exhausted | breaker opens; next model; UI toast "backup model" |
| All models unavailable | `LLMUnavailableError` | diagnostic and practice keep working with deterministic distractor tagging; Teach-Back returns `503 ai_unavailable` with a friendly retry state |
| Invalid LLM JSON | Pydantic validation error | one repair retry, then next model |
| Duplicate submission | unique `client_attempt_id` | return stored result |
| Double-click in Teach-Back | per-session lock | `409 turn_in_progress` |
| DB unavailable | `/ready` fails | `503`; container host restarts unhealthy instance |
| Whisper failure | speech error | UI hides mic, keeps typing path |
| Cold start on free hosting | first request slow | frontend shows a "waking the server" state; ping `/health` before demos |

## 9. Security and abuse (proportionate to scope)

- **No authentication by design.** The `X-Demo-User-Id` header selects a seeded demo identity. All identity access goes through `get_current_user`, so JWT can replace it without touching services.
- Input limits: Teach-Back message at most 2,000 characters; reasoning at most 600; audio upload at most 5 MB.
- Per-user in-process rate limit on LLM-backed routes.
- Prompt-injection hygiene: delimiter tags, schema-validated output, no tool use, the LLM cannot change scores or state directly.
- Secrets only via environment; `.env` is git-ignored; nothing secret in the frontend (all `NEXT_PUBLIC_*` values are public).
- CORS restricted to `CORS_ORIGINS`.

## 10. Observability

- structlog JSON logs with `request_id`, route, status, latency.
- `llm_calls` table: purpose, model, fallback flag, latency, token counts, status, error class.
- `GET /api/v1/ops/llm-stats`: last-hour calls per model, fallback rate, p50 and p95 latency, error counts, breaker states. The frontend `/ops` page renders it (the "AI reliability panel").
- `GET /health` (liveness, no dependencies) and `GET /ready` (DB check plus config sanity).

## 11. Build and delivery

- **Backend image:** multi-stage Dockerfile; `uv sync --frozen --no-dev`; non-root user; `HEALTHCHECK` on `/health`; start command runs `alembic upgrade head` then uvicorn with one worker.
- **CI (GitHub Actions):** backend job (uv, ruff, mypy, pytest with a Postgres service container); frontend job (pnpm install, lint, typecheck, build). Deploys follow `main`.
- **Migrations:** Alembic, async env. Never edit a committed migration; add a new one.
- **Environments:** `local` (Compose), `production` (container host, Neon, Vercel). Same image everywhere.

## 12. Scale path (what we would change, and why we are not doing it now)

| Today | At scale |
|---|---|
| In-process breaker, token budget, user locks, one worker | Redis for shared state; multiple workers or replicas |
| asyncio recorder queue | durable queue and worker for `llm_calls` and analytics |
| Header-based demo identity | real auth (OIDC or JWT) behind `get_current_user` |
| Teacher aggregates computed on read | materialized views or periodic rollups |
| Pre-generated question bank | authoring tool plus review workflow |

## 13. Architecture decision records

1. **Modular monolith over microservices.** One deployable, fewer moving parts, boundaries enforced by the dependency rule.
2. **Postgres over SQLite.** Real concurrency, `FOR UPDATE` locking, JSONB, and it matches production.
3. **BKT plus Elo-style calibration over LLM-judged mastery.** Mastery must be explainable and reproducible. LLMs supply evidence only.
4. **In-process resilience primitives.** The right size for one instance; the scale path is documented.
5. **Contract-first, vertical slices.** `api.md` is the contract; each slice ships backend and UI together, and API types are regenerated after every slice so the two never drift.
6. **Pre-generate content, call the LLM live only where reasoning matters.** Protects latency, rate limits, and demo reliability.
7. **Wispr Flow as client-side dictation.** No public API; the UI is designed so dictation works flawlessly.
8. **Backend-controlled Pip.** The state machine sets Pip's `level`; the LLM only phrases the reply.
