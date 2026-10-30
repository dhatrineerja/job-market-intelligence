"""Naukri monthly job scrapes, May-Aug 2023 (Kaggle: riteshmn/naukri-<month>-2023-jobs-data).

Licensed Apache 2.0.

Each dataset is one scrape split into category CSVs, and a job can appear in several
categories and in several months. Rows are merged on the Naukri job id: the latest
snapshot's values win and first_seen_at is the earliest snapshot that contained the job.

Scrape dates are not stated except for July (3 Aug). The latest posting date found in
each file is used as its snapshot date.
"""

import csv
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from app.etl.naukri import URL_ID, listed_at_from_id
from app.etl.normalize import (
    JobRecord,
    clean,
    experience_level_from_years,
    parse_india_location,
    parse_naukri_salary,
    parse_years_range,
    plausible_salary,
)

SOURCE = "naukri"
NAME = "naukri_2023"
SNAPSHOTS = {
    "riteshmn/naukri-may-2023-jobs-data": datetime(2023, 5, 29, tzinfo=UTC),
    "riteshmn/naukri-june-2023-jobs-data": datetime(2023, 7, 6, tzinfo=UTC),
    "riteshmn/naukri-july-2023-jobs-data": datetime(2023, 8, 3, tzinfo=UTC),
    "riteshmn/naukri-aug-2023-jobs-data": datetime(2023, 9, 1, tzinfo=UTC),
}
DATASETS = list(SNAPSHOTS)

# The July dataset also holds two AI/ML-only exports with a different layout
OTHER_LAYOUT = ("AI ML", "AIML")
SKILL_COLUMNS = ["fleft", *(f"fleft {n}" for n in range(2, 9))]
RAW_EXCLUDED = {"ellipsis 4", "title href", "subTitle href", "reviewsCount href"}


def _rows(path: Path, stats: Counter) -> Iterator[dict[str, str]]:
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = [name.strip() for name in next(reader)]
        description = header.index("ellipsis 4")
        for row in reader:
            extra = len(row) - len(header)
            if extra > 0:
                # an unescaped comma in the description spilled it across extra fields
                row[description : description + extra + 1] = [
                    ",".join(row[description : description + extra + 1])
                ]
                stats["rows_repaired"] += 1
            elif extra < 0:
                stats["rows_dropped"] += 1
                continue
            yield {name: value for name, value in zip(header, row, strict=True) if name}


def _record(row: dict[str, str], snapshot: datetime, stats: Counter) -> JobRecord | None:
    row = {key: clean(value) for key, value in row.items()}
    match = URL_ID.search(row.get("title href") or "")
    title = row.get("title")
    if not match or not title:
        stats["rows_dropped"] += 1
        return None
    source_id = match.group(1)

    low, high, mid, currency = None, None, None, None
    parsed = parse_naukri_salary(row.get("ellipsis 2"))
    if parsed:
        low, high, mid = plausible_salary(*parsed, None, "INR")
        currency = "INR" if mid is not None else None
        if mid is None:
            stats["salaries_rejected"] += 1

    years = parse_years_range(row.get("ellipsis"))
    cities, remote = parse_india_location(row.get("ellipsis 3"))
    skills = [row[col] for col in SKILL_COLUMNS if row.get(col)]
    return JobRecord(
        source=SOURCE,
        source_id=source_id,
        title=title,
        country="IN",
        fetched_at=snapshot,
        first_seen_at=snapshot,
        raw={key: value for key, value in row.items() if key not in RAW_EXCLUDED},
        description=(row.get("ellipsis 4") or "").removesuffix("...").strip() or None,
        skills_raw=", ".join(skills) or None,
        company_name=row.get("subTitle"),
        location_raw=row.get("ellipsis 3"),
        locations=[(city, None, "IN") for city in cities] or [(None, None, "IN")],
        is_remote=remote,
        experience_level=experience_level_from_years(years[0] if years else None),
        experience_min_years=years[0] if years else None,
        experience_max_years=years[1] if years else None,
        salary_min=low,
        salary_max=high,
        salary_mid=mid,
        salary_currency=currency,
        url=row.get("title href"),
        listed_at=listed_at_from_id(source_id),
    )


def read(paths: list[Path], stats: Counter) -> Iterator[JobRecord]:
    merged: dict[str, JobRecord] = {}
    # oldest snapshot first, so a later row replaces an earlier one
    for slug, path in sorted(zip(DATASETS, paths, strict=True), key=lambda p: SNAPSHOTS[p[0]]):
        snapshot = SNAPSHOTS[slug]
        for file in sorted(path.rglob("*.csv")):
            if file.name.startswith(OTHER_LAYOUT):
                stats["files_skipped"] += 1
                continue
            for row in _rows(file, stats):
                stats["rows_read"] += 1
                record = _record(row, snapshot, stats)
                if record is None:
                    continue
                earlier = merged.get(record.source_id)
                if earlier:
                    stats["duplicates_merged"] += 1
                    record.first_seen_at = earlier.first_seen_at
                merged[record.source_id] = record
    yield from merged.values()
