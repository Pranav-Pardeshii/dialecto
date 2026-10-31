# AGENTS.md: standing rules for every AI agent in this repo

**Project:** Dialecto, an adaptive CBSE Class 10 Biology tutor with a real learner model and a Teach-Back mode.
**Context:** a 9-hour hackathon build by one developer working solo with AI agents. Quality over quantity: fewer features, done properly.

Read this file at the start of **every** session, then read `docs/progress.md`. Sessions do not share memory; `progress.md` is the only handoff.

## 1. Session protocol

1. Read `AGENTS.md`, `docs/progress.md`, then the docs relevant to the task (`architecture`, `api`, `database`, `agents`, `curriculum`).
2. State a plan in at most 10 lines. Wait for a human "go" if the work changes a contract (API shape, DB schema, dependency list, folder structure).
3. Build in small vertical slices. Run `make check` before declaring anything done.
4. Update `docs/progress.md`: Done / In progress / Next / Known bugs / Useful commands.
5. Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`). One logical change per commit.

## 2. Ask, don't assume

Stop and ask when a requirement is ambiguous, a doc contradicts another doc, a library or model behaves differently from the docs, or a P0 feature must be cut. Record decisions in `docs/DECISIONS.md` (date, decision, reason).

## 3. Fixed stack

| Area | Choice |
|------|--------|
| Backend | Python 3.12, FastAPI, asyncio, Pydantic v2, pydantic-settings |
| DB | PostgreSQL, SQLAlchemy 2.0 async (asyncpg), Alembic |
| Packages | **uv** only (`uv add`, `uv sync`, `uv run`). Never `pip` |
| AI | Groq via the official `groq` async SDK; models set in config; Groq Whisper for speech |
| Resilience | tenacity (retries), in-process circuit breaker and token budget |
| Logging | structlog (JSON) with `request_id` |
| Frontend | Next.js (App Router), TypeScript strict, Tailwind, shadcn/ui, TanStack Query, React Flow (concept graph), Recharts, Motion (Framer Motion) for animation |
| Tooling | ruff, mypy, pytest, pytest-asyncio, respx; ESLint, Prettier; GitHub Actions; Docker |

**Forbidden:** Redis, Celery or any queue, microservices, authentication, ORMs other than SQLAlchemy, `requests`, sync DB drivers.

## 4. Backend rules

- **Layering (dependency rule):** `api` calls `services`; `services` call `repositories`, `domain`, and `ai`. Never import upward. Routers contain **no** business logic.
- `domain/` is **pure**: no I/O, no imports from `app.db`, `app.ai`, or FastAPI. All learner math lives here and is unit-tested.
- Everything that does I/O is `async`. No blocking calls (`time.sleep`, sync HTTP, sync file reads) in request paths.
- SQLAlchemy 2.0 style: `Mapped[]`, `mapped_column`, `select()`, `AsyncSession`, `expire_on_commit=False`. No legacy `Query`.
- **Never hold a DB transaction open across an LLM call.** Pattern: read (txn 1) then call the LLM then write (txn 2).
- One answer submission = one transaction updating `attempts`, `mastery`, and SM-2 fields. Lock the mastery row (`SELECT ... FOR UPDATE`).
- Pydantic v2 schemas for all input and output; `response_model` on every route; never return ORM objects.
- Idempotency: answer endpoints take `client_attempt_id` (UUID). A duplicate returns the stored result.
- Errors: raise `AppError` subclasses. A global handler returns the envelope in `docs/api.md`.
- Config only through `core/config.py`. No `os.environ` elsewhere. No hard-coded model names outside config.
- Never log secrets. Log learner free text only at DEBUG.
- Full type hints. `ruff` and `mypy` must pass.

## 5. AI-layer rules

- Every LLM call goes through `LLMRouter`. No direct SDK calls from services or agents.
- Prompts live in `app/ai/prompts/*.md` with named placeholders. They are not inline strings.
- Every LLM response is validated against a Pydantic schema. On failure: one repair retry, then the next model, then degrade gracefully.
- **LLMs never do the math.** Mastery, scheduling, and difficulty calibration come only from `domain/`. The LLM produces evidence (judge output), and `domain/` turns it into updates.
- Learner text is untrusted. Wrap it in tags (`<tutor_message>...</tutor_message>`), never let it alter instructions, and never execute or eval it.
- Log every attempt (model, latency, tokens, status, fallback flag) to `llm_calls`.
- Pre-generate what can be pre-generated (questions, lessons). Spend live LLM calls only where reasoning is required.

## 6. Frontend rules

- **All UI work uses the Taste Skill** (`design-taste-frontend`, from github.com/Leonxlnx/taste-skill). Read it before building or changing any screen, and follow `docs/design.md` (colors, type, spacing, motion tokens). Never improvise colors or fonts per screen. Use one primary design direction only; mixing visual skills causes drift.
- **Precedence:** the functional rules below (dictation-friendly textarea, accessibility, loading/empty/error states, typed API client, performance) win over aesthetics when they conflict.
- shadcn/ui is the primitive layer and must be themed from the design tokens. An unstyled default shadcn look is a defect.
- Motion: CSS transitions plus the Motion (Framer Motion) library only. Use motion to explain state changes (mastery, unlocks, Pip's level), honor `prefers-reduced-motion`, and avoid GSAP, WebGL, and scroll-jacking unless asked.
- Run the Taste redesign/audit skill once at milestone M7 and fix the highest-impact issues.
- TypeScript strict, no `any`. API types are **generated** (`pnpm gen:api`) from the backend OpenAPI. Never hand-write them.
- Server Components by default; `"use client"` only for interactivity. Server state goes through TanStack Query.
- Call the backend through the Next.js rewrite (`/api/*`), never with hard-coded absolute URLs.
- **Dictation-friendly input (Wispr Flow):** the teach-back and reasoning inputs are plain `<textarea>` elements. No contenteditable, no rich-text editors, no input masking. `autoFocus`; at least 8 rows; word counter; `Ctrl/Cmd+Enter` submits; plain `Enter` inserts a newline; do not intercept other key events or re-render the field in a way that drops the cursor.
- Every screen needs loading (skeleton), empty, and error states. Responsive layout. Mastery colors must also show the percentage (color is never the only signal). Visible focus rings.
- Show AI fallback honestly: a small toast such as "Tutor is busy, using backup model".
- **Strict UI Cleanliness & Framework Secrecy:** NEVER mention backend frameworks, internal architecture, or third-party tools in any user-facing UI code or copy (e.g. absolutely no "FastAPI-powered", "identity validation", "Wispr Flow", "Groq", etc. anywhere in UI text, labels, footers, tooltips, or watermarks). Keep all user-facing copy natural, clean, minimal, beautiful, and focused entirely on the user experience (e.g. "Speak or type your explanation here...").

## 7. Content rules (biology correctness)

- Biology facts come only from `docs/curriculum.md` or content JSON with `"verified": true`.
- Anything LLM-generated is `"verified": false` until a human flips it. Unverified items are never served to users.
- Never invent NCERT page numbers or quotes. If unsure, say so and flag the item.

## 8. Testing rules

- Unit tests for all of `domain/` (BKT, Elo, SM-2, selector, graph) with hand-computed expected values.
- Integration tests for each endpoint using a real Postgres (compose service or CI service container) and a **mocked Groq** (respx). Tests must never call the live API.
- Judge eval harness (`make eval`) is the only place that may hit the live API, and only when `RUN_LIVE_EVALS=1`.
- Never disable or weaken a test to make it pass.

## 9. Never

Commit secrets; add auth; add Redis or queues; fake the learner model in the demo; leave an untracked TODO (write it into `progress.md`); rewrite the authoritative docs without approval.
