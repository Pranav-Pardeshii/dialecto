# Environment Setup & Deployment: Dialecto

---

## 1. Prerequisites

Ensure the following tools are installed on your machine:

- **Python:** 3.12+ (managed via `uv`)
- **Package Manager (Python):** `uv` (install via `curl -LsSf https://astral.sh/uv/install.sh` or `winget install astral-sh.uv`)
- **Node.js:** v22.x LTS (or v20.x+)
- **Package Manager (Node):** `pnpm` (install via `npm install -g pnpm`)
- **Container Runtime:** Docker Desktop or Docker engine with Docker Compose
- **Wispr Flow:** Desktop application installed for voice dictation (recommended)

---

## 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

### Environment Variables Reference

| Variable | Description | Default / Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL asyncpg connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/dialecto` |
| `GROQ_API_KEY` | API key from console.groq.com | `gsk_...` |
| `LLM_PRIMARY_MODEL` | Flagship Groq model for reasoning | `openai/gpt-oss-120b` |
| `LLM_FALLBACK_MODELS` | Ordered fallback models if primary 429s | `llama-3.3-70b-versatile,llama-3.1-8b-instant` |
| `WHISPER_MODEL` | Groq Whisper speech model for fallback mic | `whisper-large-v3-turbo` |
| `LLM_TIMEOUT_S` | Per-call timeout in seconds | `15` |
| `CORS_ORIGINS` | Permitted cross-origin hosts | `http://localhost:3000` |
| `BACKEND_URL` | Destination for Next.js `/api/*` rewrites | `http://localhost:8000` |
| `LOG_LEVEL` | Application logging verbosity | `INFO` (use `DEBUG` for prompt inspection) |
| `ENV` | Environment identifier | `development` or `production` |

---

## 3. Local First-Run Commands

### Step 1: Start PostgreSQL
```bash
docker compose up -d db
```

### Step 2: Initialize Backend
```bash
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.db.seed
uv run uvicorn app.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000` (`/health` returns status OK).

### Step 3: Initialize Frontend
```bash
cd ../frontend
pnpm install
pnpm gen:api
pnpm dev
```
Frontend will be live at `http://localhost:3000`.

---

## 4. Wispr Flow Desktop Setup

Wispr Flow provides frictionless, system-wide speech-to-text with exceptional punctuation and biological term recognition:

1. **Install Wispr Flow:** Download from [wisprflow.ai](https://wisprflow.ai) and complete initial setup.
2. **Configure Hotkey:** Set your preferred global dictation trigger (e.g., tap or hold `Ctrl` or `Caps Lock`).
3. **Using in Dialecto:**
   - Navigate to **Practice** or **Teach-Back with Pip**.
   - Dialecto automatically focuses the large, plain `<textarea>`.
   - Trigger your Wispr Flow hotkey, speak your biological reasoning naturally, and release.
   - Text streams directly into the field without cursor jumping.
   - Press `Ctrl + Enter` (or `Cmd + Enter`) to submit immediately.
4. **Fallback:** If Wispr Flow is not running, click the in-app microphone button to record audio via Groq Whisper.

---

## 5. Deployment Guide

### Database (Neon Serverless PostgreSQL)
1. Create a project in [Neon](https://neon.tech).
2. Copy the connection string and append `?ssl=require`.
3. In backend settings, ensure `connect_args={"statement_cache_size": 0}` is set when connecting via pooled port 6543.

### Backend (Container Host: Render / Railway / Fly.io)
1. Deploy using the multi-stage `backend/Dockerfile`.
2. Set container start command:
   ```bash
   uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
3. Set environment variables (`DATABASE_URL`, `GROQ_API_KEY`, etc.).
4. Configure health check probe to point to `/health`.

### Frontend (Vercel)
1. Import `frontend/` directory into Vercel.
2. Set `BACKEND_URL` environment variable to your deployed backend URL.
3. Deploy; Vercel automatically runs `pnpm build` and routes `/api/*` to the backend.

