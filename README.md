# ATS Resume Builder (FastAPI + Redis + Gemini)

Production-focused ATS-friendly resume builder with:
- FastAPI async backend
- Redis draft/session storage + autosave support
- Gemini content enhancement via API
- Lightweight vanilla HTML/CSS/JS frontend with live preview
- PDF export required and DOCX export optional

## Project Structure

```
app/
  main.py
  config.py
  deps.py
  models/
  routers/
  services/
  templates/
static/
  index.html
  css/styles.css
  js/app.js
requirements.txt
.env.example
```

## ATS Rules Enforced

- Standard headings only (`Professional Summary`, `Work Experience`, etc.)
- Text-first output (no tables, no icons, no graphics)
- Left-aligned layout
- Consistent spacing and bullet lists
- Keyword-friendly AI rewrite prompts

## API Endpoints

- `POST /api/session` - create anonymous session cookie
- `GET /api/resume` - fetch current draft
- `PUT /api/resume` - save full resume draft
- `PATCH /api/resume` - update full draft (same payload)
- `POST /api/ai/summary` - AI summary generation
- `POST /api/ai/bullets` - improve experience bullets
- `POST /api/ai/skills` - suggest ATS-relevant skills
- `POST /api/ai/rephrase` - rephrase text for ATS
- `POST /api/ai/project-description` - improve project description
- `POST /api/ai/ats-score` - ATS scoring using current session resume or supplied `resume_data`
- `POST /api/ai/ats-score-upload` - ATS scoring from uploaded PDF (multipart form)
- `GET /api/export/html` - ATS HTML preview
- `GET /api/export/pdf` - PDF download
- `GET /api/export/docx` - optional DOCX download (requires `python-docx`)

## Local Setup

1. Ensure Redis is running locally (default: `localhost:6379`).
2. Create env file:
   - `copy .env.example .env` (Windows)
3. Create virtual environment and install:
   - `python -m venv .venv`
   - `.venv\Scripts\pip install -r requirements.txt`
4. Run app:
   - `.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
5. Open:
   - `http://127.0.0.1:8000`
   - `http://127.0.0.1:8000/ats-checker` (PDF upload ATS checker page)

## Deployment (Production)

This project is deployment-ready with Docker.

### Option A: Render

1. Push project to GitHub.
2. In Render, create a new **Web Service** from the repo.
3. Render will detect `render.yaml` / `Dockerfile`.
4. Set required secrets in Render:
   - `GEMINI_API_KEY`
   - `REDIS_URL` (managed Redis recommended)
5. Deploy and open:
   - `/` for builder
   - `/ats-checker` for PDF ATS page

### Option B: Railway

1. Push project to GitHub.
2. Create a Railway project from repo (or `railway up` if CLI authenticated).
3. It uses `railway.json` + `Dockerfile`.
4. Add environment variables:
   - `GEMINI_API_KEY`
   - `REDIS_URL`
5. Deploy and use the generated public URL.

### Required env vars in production

- `GEMINI_API_KEY`
- `REDIS_URL`
- `CORS_ORIGINS` (set to your public domain)

### Optional

- `GEMINI_MODEL` (default `gemini-2.0-flash`)

## Notes for Python 3.15 Users

Your system Python is currently `3.15`. Many scientific/native Python packages still lag support on brand-new versions.
This project intentionally uses a lightweight dependency path to minimize native build requirements.

If you still hit install issues, install Python `3.12` or `3.13` and recreate `.venv`.

## Redis Usage

- Draft storage key: `resume:draft:{session_id}`
- Session TTL refresh on read/write
- AI route rate limit bucket keys: `rate:ai:{client}:{window}`

## Performance Optimizations

- Debounced autosave from frontend
- Debounced preview refresh
- Redis-backed draft cache and session persistence
- AI calls only on explicit button actions
- Async FastAPI handlers and async HTTP client for Gemini

## Scaling Suggestions

- Move Redis to managed service with TLS
- Add background queue (RQ/Celery) for heavy AI/batch exports
- Add user auth + per-user draft versioning
- Introduce structured observability (OpenTelemetry + centralized logs)
- Add template variants by job family while preserving ATS constraints
- Add test coverage for routers/services and contract tests for Gemini responses
