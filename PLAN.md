# Job Market Intelligence Platform: Build Plan (100% free stack)

**Positioning:** not just "what does the job market look like?" but **"what should I do next, and what is it worth?"**

## Signature features

| # | Feature | What it does | Checkpoint | Extra days |
|---|---|---|---|---|
| 1 | Next Best Skill | Ranks skills by how many more jobs each one makes you a strong match for | CP6 | 3 |
| 2 | What-If Simulator | Toggle skills, city or experience; matches and predicted salary update live | CP6 | 3 |
| 3 | Skill Salary Premium | Estimates what each skill adds to pay, controlling for role, city and experience | CP5 | 3 |
| 4 | Job Reality Check | Scores a job description for red flags (entry-level asking 5+ years, unrealistic skill lists, duplicate postings) | CP2, CP4 | 4 |
| 5 | Traceable AI + public evals | Every number in an agent answer expands to its tool call and data; public "How good is this?" page | CP7, CP9 | 4 |

If time gets tight, cut #4 first: it needs its own scoring logic, while the others reuse work the plan already includes.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL + pgvector (local Docker; Neon/Supabase free for deploy) |
| ORM / migrations | SQLAlchemy 2 + Alembic |
| Frontend | Next.js (React + TypeScript) + Tailwind + Recharts |
| Auth | Email + password, JWT access/refresh tokens, argon2 |
| ML | pandas, scikit-learn, LightGBM, SHAP, MLflow |
| Embeddings | sentence-transformers, run locally (no key) |
| LLM / agent | LiteLLM provider abstraction: Ollama (local dev, private) -> Groq (demo) -> Gemini (fallback) |
| Infra | Docker Compose, GitHub Actions, Vercel + Render/HF Spaces + Neon |

**Data note:** do not scrape LinkedIn (ToS, fragile). Kaggle datasets are the primary source: the LinkedIn Jobs dataset for bulk data, plus India job datasets (search "Naukri jobs", "India data science jobs", "Indeed India"). Adzuna is not free: its unpaid plan gives only 25 test calls and full access is £8/month, so use those calls only as an optional ingestion test sample and do not add a card. Jooble is the optional free live source; confirm its terms and India coverage first. Keep a `salary_is_estimated` flag and train mainly on real salaries.

## Free accounts and keys (get these first, ~15 min)

| Need | Service | Key |
|---|---|---|
| Bulk data (required) | Kaggle | `KAGGLE_USERNAME`, `KAGGLE_KEY` (from `kaggle.json`) |
| Live data (optional) | Jooble, requested at jooble.org/api/about | `JOOBLE_API_KEY` |
| Test sample (optional) | Adzuna, 25 free calls only | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
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

## Checkpoint 0: Foundation (3 days) - DONE
**Goal:** one command runs everything.
- Monorepo: `/backend`, `/frontend`, `/ml`, `/data`, `/docs`, `docker-compose.yml`
- ruff, eslint, pre-commit, GitHub Actions skeleton

**Dependencies:** Python 3.12, Node 20+, Docker Desktop, Git, VS Code, Ollama
**Requirements:** GitHub account; Kaggle, Groq, Gemini keys
**Done when:** `docker compose up` starts Postgres, API stub and frontend stub; CI passes.

## Checkpoint 1: Data ingestion and warehouse (8 days) - CORE DONE
**Result:** 144,958 jobs loaded (123,849 US from LinkedIn, 21,109 India from Naukri). Two consecutive loads produced identical tables. See `docs/data_quality.md`.

**Findings that change later checkpoints:**
- LinkedIn has no India data, so the US and India markets are separate and are never pooled on salary
- India has only 2,409 salary rows, 1,023 of them in data roles: CP5 should pool cities rather than model each city and role, and Skill Salary Premium can only cover common skills
- Naukri descriptions are ~87-character snippets: CP2 uses its skill tags, CP6 embeds title + tags for India, and the Job Reality Check uses experience fields rather than description text for India

**Next CP1 task:** add the 2023 Naukri monthly datasets (riteshmn, Apache 2.0) to increase India salary rows. Optional: Jooble collector.

**Goal:** clean job data in Postgres.
- Kaggle one-off ETL (LinkedIn dataset + India datasets), with `source` recorded per row
- Optional: Jooble client (pagination, rate limiting, retries, dedup) for a daily collector, if its terms allow it
- Optional: load an Adzuna sample from the 25 test calls to exercise the client code
- Schema: `jobs`, `companies`, `skills`, `job_skills`, `locations`, `raw_postings`; add `first_seen_at` and `last_seen_at`, needed for repost signals and any future trends
- Cleaning: normalize salary, parse city, standardize titles into role families
- Report real-salary row counts per city and role: this decides how specific the salary model and premium can be

**Dependencies:** pandas, httpx, SQLAlchemy, alembic, psycopg, pydantic, tenacity, kagglehub, APScheduler
**Requirements:** DB up; Kaggle key; ~2 GB disk; data dictionary
**Done when:** >=100k jobs loaded, quality report written, re-run is idempotent.

## Checkpoint 2: Skill extraction, NLP enrichment, Job Reality Check (11 days)
**Goal:** structured skills per posting, plus red-flag scoring.
- Skills taxonomy with aliases; spaCy PhraseMatcher first; optional LLM pass (free model) only to fill gaps
- Evaluate precision/recall on 200 hand-labelled postings
- Populate `job_skills`; parse experience level and remote/hybrid
- **Job Reality Check:** rule-based scorer returning a risk score plus the reasons: stated level vs years required, skill-list size vs role norm, identical descriptions across cities, missing salary. Sanity-check on ~100 hand-reviewed postings. There is no ground truth, so call it a risk score, not a verdict

**Dependencies:** spaCy, rapidfuzz, litellm (optional)
**Requirements:** CP1 data; labelled samples
**Done when:** extraction F1 is in the README, top-50 skills look sane, and each flagged job shows its reasons.

## Checkpoint 3: Backend core and authentication (7 days)
**Goal:** secured API with users.
- `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`, password reset
- Tables: `users`, `profiles`, `saved_jobs`, `resumes`; role field (`user`/`admin`)
- Auth guard, CORS, rate limiting, validation, pytest

**Dependencies:** fastapi, uvicorn, pyjwt, argon2-cffi, slowapi, pytest, httpx; email via Resend/Mailtrap (mockable)
**Requirements:** CP1 schema; `.env` secrets; decide on email verification
**Done when:** register/login/protected route work; auth tests pass in CI.

## Checkpoint 4: Analytics API and dashboard (12 days)
**Goal:** first visible product.
- Endpoints: top skills by role/city, salary distribution, skill co-occurrence, job volume (use `first_seen_at` trends only once real multi-week data exists; do not stitch datasets from different sources into a trend)
- Frontend: login/signup, protected layout, filtered dashboard (bar charts, box plots, city heatmap, skill network)
- **Job Reality Check UI:** `POST /reality-check` and a page to paste any job description and see its score and reasons
- Cache heavy queries (materialized views or Upstash Redis)

**Dependencies:** recharts, @tanstack/react-query, react-hook-form, zod, shadcn/ui, axios; typed client from OpenAPI
**Requirements:** CP2 and CP3 done
**Done when:** a logged-in user filters and sees charts; cached queries <1 s.

## Checkpoint 5: Salary model and Skill Salary Premium (11 days)
**Goal:** defensible ML, not just a notebook.
- Features: role family, city, experience, skills, company size, remote flag, title TF-IDF
- Baselines (median by role+city, Ridge) -> LightGBM; k-fold CV, MAE/MAPE, quantile range
- SHAP; MLflow tracking; versioned pipeline; `POST /predict/salary` + frontend estimator
- **Skill Salary Premium:** regression of log salary on skills, controlling for role, city and experience, with confidence intervals; only show skills with enough rows. Label results as associations, not causes. `/analytics/skill-premium` + dashboard chart

**Dependencies:** scikit-learn, lightgbm, shap, mlflow, optuna, joblib, statsmodels
**Requirements:** CP2 features; enough real-salary rows per city (else fall back to role-by-country); time-based split
**Done when:** model beats baseline by a stated margin; model card documents limits; premiums show intervals.

## Checkpoint 6: Matching, Next Best Skill, What-If Simulator (13 days)
**Goal:** tell a user what to do next, not just what matches.
- Local embeddings (all-MiniLM-L6-v2 or bge-small) in pgvector
- Hybrid score: cosine similarity + weighted skill overlap; matched/missing skills per job
- `/match/jobs`, `/match/skill-gap`; Matches page + profile skill editor
- Evaluate precision@k on synthetic profiles
- **Next Best Skill:** for each candidate skill, count how many extra jobs cross a strong-match threshold (e.g. 70%) if added; rank them. `/match/next-best-skill`. Precompute job embeddings and scores so this stays fast
- **What-If Simulator:** toggle skills, city or experience; matches, Next Best Skill and predicted salary update live (uses the CP5 model). `/match/what-if` + interactive page with debounced requests

**Dependencies:** sentence-transformers, pgvector, numpy, faiss (optional)
**Requirements:** CP2 data; CP3 profiles; CP5 salary model; CPU is enough (one-time batch of 20-40 min)
**Done when:** matching returns ranked jobs with "X% match, missing: A, B, C"; "Learn X: N more jobs" works; a what-if change updates results in under 1 s.

## Checkpoint 7: AI resume agent (14 days)
**Goal:** the headline feature, on free LLMs.
- Resume upload (PDF/DOCX) -> text -> structured profile. First pass with the spaCy taxonomy matcher; LLM only fills gaps (saves free-tier quota)
- Agent via **LiteLLM** (env var switches Ollama / Groq / Gemini) with few, simple tools: `search_jobs`, `get_market_stats` (parameterized SQL, never free-form), `compute_skill_gap`, `predict_salary`, `next_best_skill`
- Chat UI with streaming; answers use DB numbers and cite jobs/stats
- **Traceable answers:** store each tool call, its arguments and result with the message; every number in the reply expands to show them. An answer with a number but no supporting tool call counts as a failed eval
- Small open models call tools less reliably: keep JSON schemas simple, validate arguments strictly, retry once on malformed calls
- Guardrails: per-user **requests-per-day** limit (replaces token budget), prompt-injection handling (resume text is data)
- Eval set of ~30 questions with expected facts; run against each provider

**Dependencies:** litellm, pdfplumber/pypdf, python-docx, python-multipart, SSE in FastAPI
**Requirements:** CP4-CP6 endpoints as tools; Ollama installed (~8 GB RAM) and Groq/Gemini keys; storage decision (local volume -> R2); privacy policy + delete-my-data endpoint; real resumes only via Ollama
**Done when:** upload resume -> matches, ranked skill gaps, correct Q&A with every number traceable; eval pass rate quoted per provider.

## Checkpoint 8: Product polish (7 days)
- Saved jobs, skill-progress tracker, analysis history, settings, account deletion
- Responsive, accessible UI; loading/empty states; dark mode; optional admin page

**Done when:** a new user completes sign up -> resume -> matches -> gaps -> save with no dead ends.

## Checkpoint 9: Quality, security, MLOps, public evals (9 days)
- pytest-cov >=70%, Playwright e2e, data-quality checks (pandera)
- OWASP checklist, secret scanning, upload limits, bandit, pip-audit
- Drift check, scheduled retraining, structured logging, Sentry free tier
- **"How good is this?" page:** public page with agent eval scores per provider, salary model error by city, matching precision@k and skill extraction F1, including where each is weak. Generated from saved eval output so it cannot drift from the real numbers

**Done when:** CI green with tests, lint and security scan on every PR; the public page shows current eval results.

## Checkpoint 10: Deployment and portfolio (4 days)
- Vercel (frontend), Render or HF Spaces (API), Neon/Supabase (Postgres + pgvector), scheduled ingestion job
- Render free tier sleeps after ~15 min idle (30-60 s cold start): add a "waking up" screen and note it in the README
- README: architecture diagram, screenshots, 2-3 min demo video, model card, key decisions and trade-offs

**Done when:** public URL with a demo account works end to end. Cost: $0.

---

## Timeline
About 99 days at 3 hours a day (~14 weeks daily), plus a ~2 week buffer. Critical path: CP0 -> CP1 -> CP2. After CP3, backend and frontend overlap. CP6 now depends on CP5, because the What-If Simulator uses the salary model.

| Checkpoint | Days | Running total |
|---|---|---|
| 0. Foundation (done) | 3 | 3 |
| 1. Data ingestion | 8 | 11 |
| 2. Skills + Job Reality Check | 11 | 22 |
| 3. Backend and login | 7 | 29 |
| 4. Analytics dashboard | 12 | 41 |
| 5. Salary model + Skill Premium | 11 | 52 |
| 6. Matching + Next Best Skill + What-If | 13 | 65 |
| 7. AI agent + traceable answers | 14 | 79 |
| 8. Product polish | 7 | 86 |
| 9. Quality + public evals | 9 | 95 |
| 10. Deploy and portfolio | 4 | 99 |

## Risks
- Sparse salary data for Indian cities: check in CP1. It limits both the salary model and the Skill Salary Premium.
- Skill trends need real multi-week data: Kaggle is mostly snapshots, so rising/declining skills are out of scope unless a free daily collector runs early.
- Job Reality Check has no ground truth: show reasons, call it a risk score, and never present it as proof a job is fake.
- Skill Salary Premium is an association, not a cause: label it clearly.
- Resume PII: encrypt at rest, retention limit, deletion endpoint, local LLM for real resumes.
- Free-tier rate limits and model churn: LiteLLM abstraction, daily request caps, fallbacks.
- Weak tool calling on small models: few tools, strict validation, agent evals.
- Scope creep: cut CP8 extras and the admin page first, then the Job Reality Check; never cut skill extraction, the salary model, Next Best Skill or the agent.
