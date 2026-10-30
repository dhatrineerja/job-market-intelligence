# Job Market Intelligence Platform

Dashboard of in-demand skills and salary trends, a salary prediction model, job-to-skill matching, and an AI agent that reads your resume, finds matching jobs, lists skill gaps and answers career questions. Built on a free stack. See [PLAN.md](PLAN.md) for the checkpoint plan.

## Run locally

Requirements: Docker Desktop, Git. Optional for local development outside Docker: Python 3.12, Node 22.

```bash
cp .env.example .env   # then fill in the values
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs at /docs)
- Postgres (pgvector): localhost:5432

## Develop

```bash
# backend
cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
ruff check . && pytest

# frontend
cd frontend && npm install && npm run lint
```

## Layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI service |
| `frontend/` | Next.js app |
| `ml/` | Training and evaluation code |
| `data/` | Local datasets (git-ignored) |
| `docs/` | Documentation |
