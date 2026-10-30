"""Naukri India tech jobs (Kaggle: shree0910/india-tech-job-market-2026-23k-records, CC BY-SA 4.0).

The file's scraped_at says 2025-06-10, but job ids in its URLs run up to 10 June 2026,
so 2026-06-10 is used as the snapshot date. Naukri ids start with the posting date as
DDMMYY, which is where listed_at comes from.
"""

import re
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.etl.normalize import (
    JobRecord,
    clean,
    experience_level_from_years,
    parse_india_location,
    parse_naukri_salary,
    plausible_salary,
)

SOURCE = "naukri"
NAME = "naukri_2026"
DATASETS = ["shree0910/india-tech-job-market-2026-23k-records/versions/1"]
FILE_NAME = "indian_tech_jobs_2026.csv"

SNAPSHOT_AT = datetime(2026, 6, 10, tzinfo=UTC)

# job_description is stored on jobs. The rest are the dataset author's derived columns.
RAW_EXCLUDED = {
    "job_description",
    "salary_tier",
    "experience_tier",
    "is_senior",
    "skill_domain",
    "salary_midpoint_lpa",
    "days_since_posted",
    "is_fresher_friendly",
    "salary_negotiable",
}
URL_ID = re.compile(r"-(\d{12})(?:\?|$)")


def listed_at_from_id(source_id: str) -> datetime | None:
    try:
        return datetime.strptime(source_id[:6], "%d%m%y").replace(tzinfo=UTC)
    except ValueError:
        return None


def read(paths: list[Path], stats: Counter) -> Iterator[JobRecord]:
    frame = pd.read_csv(paths[0] / FILE_NAME, low_memory=False, encoding_errors="replace")

    seen: set[str] = set()
    for row in frame.to_dict("records"):
        row = {key: clean(value) for key, value in row.items()}
        stats["rows_read"] += 1
        match = URL_ID.search(row["job_url"] or "")
        source_id = match.group(1) if match else f"row-{row['job_id']}"
        title = row["job_title"]
        # One job is listed once per scraped city, so the URL id is the real key.
        if source_id in seen or not title:
            stats["rows_dropped"] += 1
            continue
        seen.add(source_id)

        low, high, mid, currency = None, None, None, None
        parsed = parse_naukri_salary(row["salary_raw"])
        if parsed:
            low, high, mid = plausible_salary(*parsed, None, "INR")
            currency = "INR" if mid is not None else None
            if mid is None:
                stats["salaries_rejected"] += 1

        cities, remote_in_location = parse_india_location(row["location"])
        skills = row["skills_required"]
        yield JobRecord(
            source=SOURCE,
            source_id=source_id,
            title=title,
            country="IN",
            fetched_at=SNAPSHOT_AT,
            raw={k: v for k, v in row.items() if k not in RAW_EXCLUDED},
            description=row["job_description"],
            skills_raw=None if skills == "Not Available" else skills,
            company_name=row["company_name"],
            company_size=row["company_size_bucket"],
            location_raw=row["location"],
            locations=[(city, None, "IN") for city in cities] or [(None, None, "IN")],
            is_remote=remote_in_location or row["work_mode"] == "Remote",
            experience_level=experience_level_from_years(row["experience_min_yrs"]),
            experience_min_years=row["experience_min_yrs"],
            experience_max_years=row["experience_max_yrs"],
            salary_min=low,
            salary_max=high,
            salary_mid=mid,
            salary_currency=currency,
            url=row["job_url"],
            listed_at=listed_at_from_id(source_id),
        )
