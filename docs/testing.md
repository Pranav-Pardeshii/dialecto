# Testing Strategy & Debugging Playbook: Dialecto

---

## 1. Test Pyramid

Dialecto uses a three-tier test pyramid designed for velocity and rock-solid reliability during rapid development:

```text
       / \
      /   \      Judge Evals (Golden Set, opt-in with RUN_LIVE_EVALS=1)
     /=====\
    /       \    Integration Tests (FastAPI + Real Postgres + Mocked Groq via respx)
   /=========\
  /           \  Unit Tests (Pure Python domain/: BKT, Elo, SM-2, Selector, Graph)
 /=============\
```

### Tier 1: Pure Domain Unit Tests (`backend/tests/unit/`)
- **Scope:** All mathematical and algorithmic functions in `backend/app/domain/` (`bkt.py`, `elo.py`, `sm2.py`, `selector.py`, `graph.py`).
- **Rules:** Zero I/O, zero network, zero database, zero FastAPI imports. Every formula tested against hand-computed expected values.
- **Speed:** Runs in <1 second.

### Tier 2: Integration Tests (`backend/tests/integration/`)
- **Scope:** Endpoint behavior, database transactions, idempotency (`client_attempt_id`), error envelope mapping.
- **Environment:** Real PostgreSQL (Docker Compose locally or GitHub Actions service container).
- **AI Mocking:** Mock Groq client using `respx`. Live external API calls are strictly forbidden during standard test runs.

### Tier 3: Judge Eval Harness (`backend/tests/evals/`)
- **Scope:** Evaluates the Teach-Back judge against a golden benchmark of 15 student explanations (5 strong, 5 partial with misconceptions, 5 completely wrong).
- **Execution:** Runs only when explicitly invoked: `RUN_LIVE_EVALS=1 uv run pytest tests/evals`.

---

## 2. Standard Quality Commands

Execute from repo root or respective app directories:

| Command | Purpose |
|---|---|
| `make check` | Runs full backend and frontend linting, typechecking, and test suites. |
| `make test` | Runs backend unit and integration tests with coverage. |
| `make eval` | Runs live judge evaluation harness against golden dataset. |
| `uv run ruff check .` | Backend Python linter and code formatter. |
| `uv run mypy app` | Backend strict static type checker. |
| `pnpm typecheck` | Frontend TypeScript strict compiler check (`tsc --noEmit`). |
| `pnpm lint` | Frontend Next.js ESLint validation. |

---

## 3. Judge Eval Harness (Golden Explanations)

The Teach-Back judge must reliably distinguish between accurate knowledge, omissions, and active misconceptions without score drift.

- **Benchmark Dataset:** `backend/tests/evals/golden_explanations.json`.
- **Metrics Tracked:**
  - Rubric Recall: Does the judge capture all key points mentioned?
  - Misconception Precision: Does it avoid false positives while catching known misconceptions?
  - Soft-evidence bounds: Does the score clamp properly between 0.0 and 1.0?

---

## 4. Debugging Playbook

### 4.1 Groq 429s & Rate Limits
- **Symptom:** Groq returns HTTP 429 with rate limit messages.
- **Root Cause:** Free-tier limits (typically ~8,000 TPM on flagship models) exceeded.
- **Handling:**
  1. The `LLMRouter` catches `RateLimitError`, extracts `retry-after` header, and trips the model's in-process circuit breaker for that duration.
  2. The router immediately routes the request to the next model in `LLM_FALLBACK_MODELS`.
  3. The frontend receives an indicator toast: *"Tutor is busy, using backup model."*
- **Investigation:** Check `GET /api/v1/ops/llm-stats` to verify breaker states and fallback frequencies.

### 4.2 Malformed JSON from LLM
- **Symptom:** Pydantic `ValidationError` when parsing LLM response.
- **Handling:**
  1. The router executes exactly **one repair retry** on the same model by appending the validation error and instructions to return strict JSON adhering to the schema.
  2. If repair fails, the request fails over to the next fallback model.
  3. If all fail, an `AppError` (`ai_unavailable`, 503) is raised without crashing the server.
- **Verification:** Run `pytest tests/unit/test_router.py -k test_json_repair`.

### 4.3 asyncpg, Neon SSL, and Connection Poolers
- **Symptom:** `sslmode` unrecognized or `prepared statement "..." does not exist` errors.
- **Fixes:**
  - **SSL Requirement:** Neon requires `ssl=require`. In asyncpg, use `postgresql+asyncpg://user:pass@host/db?ssl=require` (never `sslmode=require`).
  - **PgBouncer / Pooled Ports:** If connecting via Neon's pooled endpoint (port 6543), asyncpg's prepared statement cache must be disabled in `session.py`:
    ```python
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"statement_cache_size": 0}
    )
    ```
  - **Transaction Boundaries:** Never call an LLM inside an active `async with session.begin()` block. Use the read-commit-call-write pattern.

### 4.4 CORS & Next.js API Rewrites
- **Symptom:** Browser blocks requests due to CORS errors.
- **Fixes:**
  - The browser must **never** make direct calls to `http://localhost:8000/api/*`.
  - All client requests go to `/api/v1/...` which Next.js rewrites in `next.config.ts`:
    ```typescript
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/:path*`,
        },
      ];
    }
    ```
  - Direct CORS headers are configured in FastAPI middleware only for local inspection tools.

### 4.5 Alembic Autogenerate Pitfalls
- **Symptom:** Missing DB constraints or enums failing to create in Postgres.
- **Checklist:**
  1. Alembic autogenerate often misses custom `CHECK` constraints (e.g. `p_mastery >= 0 AND p_mastery <= 1`). Check the generated migration script manually!
  2. Native Postgres Enums (`session_kind`, `user_role`) must be explicitly created before tables using `sa.Enum.create()`.
  3. Always test migration rollback: `uv run alembic downgrade -1 && uv run alembic upgrade head`.

### 4.6 Inspecting Logs & `llm_calls` Telemetry
- **Structured Logs:** `structlog` outputs JSON with timestamp, log level, event name, and `request_id`.
  - Filter by request ID: `grep '"request_id": "01J..."' app.log`
- **Querying `llm_calls` Table:**
  ```sql
  SELECT purpose, model, fallback_used, latency_ms, status, error_class, created_at 
  FROM llm_calls 
  ORDER BY created_at DESC 
  LIMIT 20;
  ```

