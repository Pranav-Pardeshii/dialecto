# Progress: Dialecto

Handoff memory across agent sessions.

---

## Done
- Read and internalized all authoritative documents (`MASTER_PROMPT.md`, `AGENTS.md`, `README.md`, `architecture.md`, `database.md`, `api.md`, `curriculum.md`, `plan.md`).
- Installed Taste Skill (`design-taste-frontend` v2) into `.agents/skills/design-taste-frontend`.
- Completed Phase 0 documentation:
  - `docs/design.md` (Taste Skill design system, tokens, signature moments, dial settings).
  - `docs/prd.md` (Problem statement, personas, user stories, rubric alignment, demo script).
  - `docs/features.md` (P0/P1/P2 feature matrix mapping brief items 1–7 + Teach-Back + Wispr Flow).
  - `docs/testing.md` (Test pyramid, commands, judge eval harness, debugging playbook).
  - `docs/setup.md` (Prerequisites, environment vars, local first-run, deployment, Wispr Flow setup).
  - `docs/DECISIONS.md` (Documented initial findings, missing docs/agents.md, Taste skill variant).
- Initialized git repository.

---

## In Progress
- Waiting for developer approval on `docs/design.md` before starting M0 frontend implementation.

---

## Next
- **Milestone M0 Completion:**
  - Create monorepo skeleton matching README tree (`backend/` and `frontend/`).
  - Create root `Makefile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`.
  - Scaffold FastAPI backend with `uv`.
  - Scaffold Next.js App Router frontend with `pnpm`.
  - Build app shell with demo role switcher (`Aarav` student / `Ms. Rao` teacher) implementing the approved design.
  - Verify `docker compose up db` and `make check`.

---

## Known Bugs / Blockers
- `docs/agents.md` is referenced as authoritative doc #6 in `MASTER_PROMPT.md` and `README.md`, but was missing from the initial file bundle. Standing prompt schemas and evidence rules are tracked in `architecture.md` / `api.md`.
- Upstream `taste-skill` repository does not provide a separate `full-output-enforcement` skill package; its enforcement rules are embedded within `design-taste-frontend`.

---

## Useful Commands
```bash
# Quality checks
make check
uv run ruff check backend
uv run mypy backend/app
pnpm --dir frontend typecheck
pnpm --dir frontend lint

# Local services
docker compose up -d db
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev
```

