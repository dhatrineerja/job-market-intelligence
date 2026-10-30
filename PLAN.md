# Job Market Intelligence Platform: Build Plan (100% free stack)

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL + pgvector (local Docker; Neon/Supabase free for deploy) |
| ORM / migrations | SQLAlchemy 2 + Alembic |
| Frontend | Next.js (React + TypeScript) + Tailwind + Recharts |
| Auth | Email + password, JWT access/refresh tokens, argon2 |
| ML | pandas, scikit-learn, LightGBM, SHAP, MLflow |
| Embeddings | sentence-transformers, run locally (no key) |
| LLM / agent | LiteLLM provider abstraction: Ollama (local dev, private) -> Groq (demo) -> Gemini (fallback) |
| Infra | Docker Compose, GitHub Actions, Vercel + Render/HF Spaces + Neon |

**Data note:** do not scrape LinkedIn (ToS, fragile). Use the Kaggle LinkedIn Jobs dataset for bulk history and the Adzuna API (supports India) for fresh Bangalore data. Adzuna salaries are often estimated: keep a `salary_is_estimated` flag and train mainly on real salaries.

## Free accounts and keys (get these first, ~15 min)

| Need | Service | Key |
|---|---|---|
| Job data | Adzuna API | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
| Bulk data | Kaggle | API token (`kaggle.json`) |
| LLM (primary demo) | Groq (console.groq.com) | `GROQ_API_KEY` |
| LLM (fallback) | Google AI Studio (Gemini) | `GEMINI_API_KEY` |
| LLM (local, dev, real resumes) | Ollama | none |
| LLM (extra fallback) | OpenRouter `:free` models | optional |
| Embeddings, ML | local libraries | none |
| DB (deploy) | Neon or Supabase | free account |
| Frontend host | Vercel Hobby | free account |
| Backend host | Render free or Hugging Face Spaces | free account |
| File storage | Cloudflare R2 (10 GB) or local disk | optional |
| Cache | Upstash Redis | optional |
| Email | Resend free tier / Mailtrap (testing) | optional |
| Monitoring | Sentry free tier | optional |
| CI | GitHub Actions | free on public repos |

Store keys in `.env` (listed in `.gitignore`). Never commit it. Free-tier limits and terms change: re-check before relying on them.

**Privacy rule:** Gemini's free tier may use data to improve Google products. Never send real resumes to it; use Ollama (or Groq after redaction) for resume content.

---

## Checkpoint 0: Foundation (2-3 days)
**Goal:** one command runs everything.
- Monorepo: `/backend`, `/frontend`, `/ml`, `/data`, `/docs`, `docker-compose.yml`
- ruff, eslint, pre-commit, GitHub Actions skeleton

**Dependencies:** Python 3.11, Node 20+, Docker Desktop, Git, VS Code, Ollama
**Requirements:** GitHub account; Adzuna, Kaggle, Groq, Gemini keys
**Done when:** `docker compose up` starts Postgres, API stub and frontend stub; CI passes.

## Checkpoint 1: Data ingestion and warehouse (1 week)
**Goal:** clean job data in Postgres.
- Kaggle one-off ETL; Adzuna client (pagination, rate limiting, retries, dedup) on a schedule
- Schema: `jobs`, `companies`, `skills`, `job_skills`, `locations`, `raw_postings`
- Cleaning: normalize salary, parse city, standardize titles into role families

**Dependencies:** pandas, httpx, SQLAlchemy, alembic, psycopg, pydantic, tenacity, kagglehub, APScheduler
**Requirements:** DB up; keys; ~2 GB disk; data dictionary
**Done when:** >=100k jobs loaded, quality report written, re-run is idempotent.

## Checkpoint 2: Skill extraction and NLP enrichment (1 week)
**Goal:** structured skills per posting.
- Skills taxonomy with aliases; spaCy PhraseMatcher first; optional LLM pass (free model) only to fill gaps
- Evaluate precision/recall on 200 hand-labelled postings
- Populate `job_skills`; parse experience level and remote/hybrid

**Dependencies:** spaCy, rapidfuzz, litellm (optional)
**Requirements:** CP1 data; labelled sample
**Done when:** extraction F1 is in the README and top-50 skills look sane.

## Checkpoint 3: Backend core and authentication (1 week)
**Goal:** secured API with users.
- `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, password reset
- Tables: `users`, `profiles`, `saved_jobs`, `resumes`; role field (`user`/`admin`)
- Auth guard, CORS, rate limiting, validation, pytest

**Dependencies:** fastapi, uvicorn, pyjwt, argon2-cffi, slowapi, pytest, httpx; email via Resend/Mailtrap (mockable)
**Requirements:** CP1 schema; `.env` secrets; decide on email verification
**Done when:** register/login/protected route work; auth tests pass in CI.

## Checkpoint 4: Analytics API and dashboard (1.5 weeks)
**Goal:** first visible product.
- Endpoints: top skills by role/city, salary distribution/trend, skill co-occurrence, job volume over time
- Frontend: login/signup, protected layout, filtered dashboard (bar charts, box plots, city heatmap, skill network)
- Cache heavy queries (materialized views or Upstash Redis)

**Dependencies:** recharts, @tanstack/react-query, react-hook-form, zod, shadcn/ui, axios; typed client from OpenAPI
**Requirements:** CP2 and CP3 done
**Done when:** a logged-in user filters and sees charts; cached queries <1 s.

## Checkpoint 5: Salary prediction model (1 week)
**Goal:** defensible ML, not just a notebook.
- Features: role family, city, experience, skills, company size, remote flag, title TF-IDF
- Baselines (median by role+city, Ridge) -> LightGBM; k-fold CV, MAE/MAPE, quantile range
- SHAP; MLflow tracking; versioned pipeline; `POST /predict/salary` + frontend estimator

**Dependencies:** scikit-learn, lightgbm, shap, mlflow, optuna, joblib
**Requirements:** CP2 features; enough real-salary rows per city (else fall back to role-by-country); time-based split
**Done when:** model beats baseline by a stated margin; model card documents limits.

## Checkpoint 6: Job-to-skill matching (1 week)
**Goal:** rank jobs for a user's skills.
- Local embeddings (all-MiniLM-L6-v2 or bge-small) in pgvector
- Hybrid score: cosine similarity + weighted skill overlap; matched/missing skills per job
- `/match/jobs`, `/match/skill-gap`; Matches page + profile skill editor
- Evaluate precision@k on synthetic profiles

**Dependencies:** sentence-transformers, pgvector, numpy, faiss (optional)
**Requirements:** CP2 data; CP3 profiles; CPU is enough (one-time batch of 20-40 min)
**Done when:** matching returns ranked jobs with "X% match, missing: A, B, C".

## Checkpoint 7: AI resume agent (1.5 weeks)
**Goal:** the headline feature, on free LLMs.
- Resume upload (PDF/DOCX) -> text -> structured profile. First pass with the spaCy taxonomy matcher; LLM only fills gaps (saves free-tier quota)
- Agent via **LiteLLM** (env var switches Ollama / Groq / Gemini) with few, simple tools: `search_jobs`, `get_market_stats` (parameterized SQL, never free-form), `compute_skill_gap`, `predict_salary`
- Chat UI with streaming; answers use DB numbers and cite jobs/stats
- Small open models call tools less reliably: keep JSON schemas simple, validate arguments strictly, retry once on malformed calls
- Guardrails: per-user **requests-per-day** limit (replaces token budget), prompt-injection handling (resume text is data)
- Eval set of ~30 questions with expected facts; run against each provider

**Dependencies:** litellm, pdfplumber/pypdf, python-docx, python-multipart, SSE in FastAPI
**Requirements:** CP4-CP6 endpoints as tools; Ollama installed (~8 GB RAM) and Groq/Gemini keys; storage decision (local volume -> R2); privacy policy + delete-my-data endpoint; real resumes only via Ollama
**Done when:** upload resume -> matches, ranked skill gaps, correct Q&A; eval pass rate quoted per provider.

## Checkpoint 8: Product polish (1 week)
- Saved jobs, skill-progress tracker, analysis history, settings, account deletion
- Responsive, accessible UI; loading/empty states; dark mode; optional admin page

**Done when:** a new user completes sign up -> resume -> matches -> gaps -> save with no dead ends.

## Checkpoint 9: Quality, security, MLOps (1 week)
- pytest-cov >=70%, Playwright e2e, data-quality checks (pandera)
- OWASP checklist, secret scanning, upload limits, bandit, pip-audit
- Drift check, scheduled retraining, structured logging, Sentry free tier

**Done when:** CI green with tests, lint and security scan on every PR.

## Checkpoint 10: Deployment and portfolio (3-5 days)
- Vercel (frontend), Render or HF Spaces (API), Neon/Supabase (Postgres + pgvector), scheduled ingestion job
- Render free tier sleeps after ~15 min idle (30-60 s cold start): add a "waking up" screen and note it in the README
- README: architecture diagram, screenshots, 2-3 min demo video, model card, key decisions and trade-offs

**Done when:** public URL with a demo account works end to end. Cost: $0.

---

## Timeline
~10-12 weeks part-time. Critical path: CP0 -> CP1 -> CP2. After CP3, backend and frontend overlap. CP5 and CP6 are independent once CP2 is done.

## Risks
- Sparse salary data for Indian cities: check in CP1.
- Resume PII: encrypt at rest, retention limit, deletion endpoint, local LLM for real resumes.
- Free-tier rate limits and model churn: LiteLLM abstraction, daily request caps, fallbacks.
- Weak tool calling on small models: few tools, strict validation, agent evals.
- Scope creep: cut CP8 extras and the admin page first; never cut CP2, CP5, CP7.
