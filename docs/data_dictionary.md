# Data dictionary

## Sources

| Source | Kaggle dataset | License | Market | Period | Notes |
|---|---|---|---|---|---|
| `linkedin` | [arshkon/linkedin-job-postings](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) v13 | CC BY-SA 4.0 | US only | Mar-Apr 2024 | All industries, full descriptions, salaries in USD |
| `naukri` | [shree0910/india-tech-job-market-2026-23k-records](https://www.kaggle.com/datasets/shree0910/india-tech-job-market-2026-23k-records) v1 | CC BY-SA 4.0 | India | Mostly 2026 | Tech-leaning, skill tags, salaries in INR |

Run the pipeline from `backend/` with `alembic upgrade head`, then `python -m app.etl.run`. It needs the database running and `KAGGLE_USERNAME` and `KAGGLE_KEY` in `.env`. Files download to `~/.cache/kagglehub`, outside the repo.

## Tables

| Table | Purpose |
|---|---|
| `jobs` | One row per unique posting; the cleaned table everything else reads |
| `raw_postings` | Original source row for lineage, minus the description (kept on `jobs`) and the Naukri dataset author's derived columns |
| `companies` | Unique companies, matched on lowercased name |
| `locations` | Unique city / region / country combinations |
| `job_locations` | Links jobs to locations; a multi-city job has several rows |
| `skills`, `job_skills` | Empty until Checkpoint 2 |

## `jobs` columns

| Column | Meaning |
|---|---|
| `source`, `source_id` | Unique key. LinkedIn job id, or the Naukri URL id (`row-N` for the 53 rows with no URL) |
| `title` | Title as posted |
| `role_family` | Rule-based on the title: `ml_engineer`, `data_scientist`, `data_engineer`, `data_analyst`, `business_analyst`, `product_manager`, `devops_cloud`, `qa_test`, `software_engineer`, `other`. The Naukri `role_category` column is ignored because it reflects the search term, not the job |
| `description` | Posting text. **Naukri descriptions are short snippets, about 87 characters on average** |
| `skills_raw` | Source skill text. Naukri comma-separated tags; rarely filled for LinkedIn |
| `company_id` | Link to `companies` |
| `country` | `US` or `IN` |
| `location_raw` | Location as posted |
| `is_remote` | LinkedIn `remote_allowed`; Naukri `work_mode` or "remote" in the location |
| `employment_type` | Full-time, Contract and so on. LinkedIn only |
| `experience_level` | `intern`, `entry`, `mid`, `senior`, `lead`. Mapped from the LinkedIn level, or from minimum years on Naukri (<=1 entry, <=4 mid, <=9 senior, otherwise lead). The two scales are not exactly equivalent |
| `experience_min_years`, `experience_max_years` | Naukri only |
| `salary_min`, `salary_max`, `salary_mid` | Annual salary in `salary_currency`. `salary_mid` is the stated median, otherwise the midpoint |
| `salary_currency` | `USD` or `INR`. **Never compare across currencies without a deliberate conversion** |
| `salary_is_estimated` | False for both sources: salaries are employer-stated |
| `url` | Link to the original posting |
| `listed_at` | LinkedIn `listed_time`. For Naukri, inferred from the first six digits of the URL id (DDMMYY) |
| `original_listed_at` | LinkedIn only. Earlier than `listed_at` on most rows, so it is not a reliable repost signal alone |
| `first_seen_at`, `last_seen_at` | When the pipeline first and last saw the job. Equal to the snapshot date for static datasets |

## Salary rules

- LinkedIn pay is annualized: hourly x 2080, weekly x 52, biweekly x 26, monthly x 12. Only USD is kept.
- Naukri lakhs are multiplied by 100,000. `/month` rows are also multiplied by 12. The two crore rows are dropped because the dataset misreads them.
- Salaries outside USD 15,000-1,000,000 or INR 100,000-30,000,000 are rejected as data errors. Rejected counts are in `data_quality.md`.

## Known limitations

- **No market overlap:** all US data comes from LinkedIn and all India data from Naukri, so US-vs-India comparisons also compare two sites and two time periods.
- **Thin India salaries:** only about 11% of Naukri rows disclose pay. See `data_quality.md` for counts by city and role.
- **Naukri snapshot date:** the file says `scraped_at` 2025-06-10, but URL ids run to 2026-06-10, so 2026-06-10 is used.
- **Old Naukri listings:** some URL ids date back to 2015. These may be long-running listings, so filter on `listed_at` for current-market analysis.
- **Part-time annualization:** hourly pay x 2080 overstates part-time earnings. Filter on `employment_type` for salary modelling.
- **Wide ranges:** some Naukri ranges are very wide (such as 1-22 lakh), so their midpoints are unreliable.
- **`companies.size_bucket` needs checking before use:** LinkedIn values are `linkedin_0` to `linkedin_7`, a different scale from Naukri's labels. Naukri marks about 93% of its companies as small. The well-known large employers checked are labelled correctly, but that share looks high, so small may be a default for unknown companies.
- **LinkedIn locations:** rows with no recognizable city or state default to the US.
