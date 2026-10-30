"""LinkedIn job postings snapshot (Kaggle: arshkon/linkedin-job-postings, CC BY-SA 4.0)."""

from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from app.etl.normalize import (
    LINKEDIN_LEVELS,
    JobRecord,
    clean,
    parse_us_location,
    plausible_salary,
)

SOURCE = "linkedin"
DATASET = "arshkon/linkedin-job-postings/versions/13"

# description is stored on jobs, so it is not repeated in raw_postings
RAW_EXCLUDED = {"description"}
PAY_PERIOD_TO_ANNUAL = {"YEARLY": 1, "MONTHLY": 12, "BIWEEKLY": 26, "WEEKLY": 52, "HOURLY": 2080}


def _timestamp(milliseconds: float | None) -> datetime | None:
    if milliseconds is None:
        return None
    return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)


def _annual(value: float | None, factor: int) -> float | None:
    return None if value is None else value * factor


def read(path: Path, stats: Counter) -> Iterator[JobRecord]:
    postings = pd.read_csv(path / "postings.csv", low_memory=False, encoding_errors="replace")
    companies = pd.read_csv(
        path / "companies" / "companies.csv",
        usecols=["company_id", "company_size"],
        low_memory=False,
    ).drop_duplicates("company_id")
    postings = postings.merge(companies, on="company_id", how="left")
    fetched_at = _timestamp(float(postings["listed_time"].max()))

    seen: set[str] = set()
    for row in postings.to_dict("records"):
        row = {key: clean(value) for key, value in row.items()}
        stats["rows_read"] += 1
        source_id = str(row["job_id"])
        title = row["title"]
        if source_id in seen or not title:
            stats["rows_dropped"] += 1
            continue
        seen.add(source_id)

        low, high, mid, currency = None, None, None, None
        factor = PAY_PERIOD_TO_ANNUAL.get(row["pay_period"])
        has_salary = any(row[col] is not None for col in ("min_salary", "max_salary", "med_salary"))
        if has_salary and factor and row["currency"] == "USD":
            low, high, mid = plausible_salary(
                _annual(row["min_salary"], factor),
                _annual(row["max_salary"], factor),
                _annual(row["med_salary"], factor),
                "USD",
            )
            currency = "USD" if mid is not None else None
        if has_salary and mid is None:
            stats["salaries_rejected"] += 1

        city, region, country = parse_us_location(row["location"])
        size = row["company_size"]
        yield JobRecord(
            source=SOURCE,
            source_id=source_id,
            title=title,
            country=country,
            fetched_at=fetched_at,
            raw={k: v for k, v in row.items() if k not in RAW_EXCLUDED},
            description=row["description"],
            skills_raw=row["skills_desc"],
            company_name=row["company_name"],
            company_size=None if size is None else f"linkedin_{int(size)}",
            location_raw=row["location"],
            locations=[(city, region, country)],
            is_remote=row["remote_allowed"] == 1,
            employment_type=row["formatted_work_type"],
            experience_level=LINKEDIN_LEVELS.get(row["formatted_experience_level"]),
            salary_min=low,
            salary_max=high,
            salary_mid=mid,
            salary_currency=currency,
            url=row["job_posting_url"],
            listed_at=_timestamp(row["listed_time"]),
            original_listed_at=_timestamp(row["original_listed_time"]),
        )
