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

## Load the data

Requires the stack running and `KAGGLE_USERNAME` and `KAGGLE_KEY` in `.env`. Takes about 5 minutes.

```bash
cd backend
alembic upgrade head
python -m app.etl.run
```

See [docs/data_dictionary.md](docs/data_dictionary.md) and [docs/data_quality.md](docs/data_quality.md).

## Data credits

- [LinkedIn Job Postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) by arshkon, CC BY-SA 4.0
- [India Tech Job Market 2026](https://www.kaggle.com/datasets/shree0910/india-tech-job-market-2026-23k-records) by shree0910, CC BY-SA 4.0

The datasets are not stored in this repository. They were cleaned and normalized as described in the data dictionary.

## Layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI service |
| `frontend/` | Next.js app |
| `ml/` | Training and evaluation code |
| `data/` | Local datasets (git-ignored) |
| `docs/` | Documentation |
