"""Idempotent upserts into Postgres. Re-running a source updates rows, never duplicates them."""

from collections.abc import Iterator, Sequence
from typing import Any

from sqlalchemy import Connection, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.etl.normalize import JobRecord, company_key, location_key, role_family
from app.models import Company, Job, JobLocation, Location, RawPosting

BATCH_SIZE = 1000


def _batches(items: Sequence[Any]) -> Iterator[Sequence[Any]]:
    for start in range(0, len(items), BATCH_SIZE):
        yield items[start : start + BATCH_SIZE]


def _upsert_companies(conn: Connection, records: list[JobRecord]) -> dict[str, int]:
    rows: dict[str, dict] = {}
    for record in records:
        if not record.company_name:
            continue
        key = company_key(record.company_name)
        row = rows.setdefault(
            key, {"name": record.company_name, "name_key": key, "size_bucket": None}
        )
        row["size_bucket"] = row["size_bucket"] or record.company_size

    for batch in _batches(list(rows.values())):
        statement = insert(Company).values(batch)
        conn.execute(
            statement.on_conflict_do_update(
                index_elements=[Company.name_key],
                set_={
                    "size_bucket": func.coalesce(
                        statement.excluded.size_bucket, Company.size_bucket
                    )
                },
            )
        )
    return dict(conn.execute(select(Company.name_key, Company.id)).tuples().all())


def _upsert_locations(conn: Connection, records: list[JobRecord]) -> dict[str, int]:
    rows: dict[str, dict] = {}
    for record in records:
        for city, region, country in record.locations:
            key = location_key(city, region, country)
            rows[key] = {"city": city, "region": region, "country": country, "location_key": key}

    for batch in _batches(list(rows.values())):
        conn.execute(
            insert(Location)
            .values(batch)
            .on_conflict_do_nothing(index_elements=[Location.location_key])
        )
    return dict(conn.execute(select(Location.location_key, Location.id)).tuples().all())


def _upsert_raw(conn: Connection, records: list[JobRecord]) -> None:
    for batch in _batches(records):
        statement = insert(RawPosting).values(
            [
                {
                    "source": r.source,
                    "source_id": r.source_id,
                    "payload": r.raw,
                    "fetched_at": r.fetched_at,
                }
                for r in batch
            ]
        )
        conn.execute(
            statement.on_conflict_do_update(
                index_elements=[RawPosting.source, RawPosting.source_id],
                set_={
                    "payload": statement.excluded.payload,
                    "fetched_at": statement.excluded.fetched_at,
                },
            )
        )


def _job_row(record: JobRecord, company_ids: dict[str, int]) -> dict[str, Any]:
    company = company_ids.get(company_key(record.company_name)) if record.company_name else None
    return {
        "source": record.source,
        "source_id": record.source_id,
        "title": record.title,
        "role_family": role_family(record.title),
        "description": record.description,
        "skills_raw": record.skills_raw,
        "company_id": company,
        "country": record.country,
        "location_raw": record.location_raw,
        "is_remote": record.is_remote,
        "employment_type": record.employment_type,
        "experience_level": record.experience_level,
        "experience_min_years": record.experience_min_years,
        "experience_max_years": record.experience_max_years,
        "salary_min": record.salary_min,
        "salary_max": record.salary_max,
        "salary_mid": record.salary_mid,
        "salary_currency": record.salary_currency,
        "url": record.url,
        "listed_at": record.listed_at,
        "original_listed_at": record.original_listed_at,
        "first_seen_at": record.first_seen_at or record.fetched_at,
        "last_seen_at": record.fetched_at,
    }


def _upsert_jobs(
    conn: Connection,
    records: list[JobRecord],
    company_ids: dict[str, int],
    location_ids: dict[str, int],
) -> None:
    for batch in _batches(records):
        statement = insert(Job).values([_job_row(r, company_ids) for r in batch])
        keep = {"id", "source", "source_id", "first_seen_at", "last_seen_at"}
        updates = {
            column.name: statement.excluded[column.name]
            for column in Job.__table__.columns
            if column.name not in keep
        }
        updates["first_seen_at"] = func.least(Job.first_seen_at, statement.excluded.first_seen_at)
        updates["last_seen_at"] = func.greatest(Job.last_seen_at, statement.excluded.last_seen_at)
        result = conn.execute(
            statement.on_conflict_do_update(
                index_elements=[Job.source, Job.source_id], set_=updates
            ).returning(Job.id, Job.source_id)
        )
        job_ids = dict(result.tuples().all())
        by_source_id = {source_id: job_id for job_id, source_id in job_ids.items()}

        conn.execute(delete(JobLocation).where(JobLocation.job_id.in_(job_ids)))
        links = {
            (by_source_id[r.source_id], location_ids[location_key(*location)])
            for r in batch
            for location in r.locations
        }
        conn.execute(
            insert(JobLocation).values(
                [{"job_id": job, "location_id": location} for job, location in links]
            )
        )


def load(conn: Connection, records: list[JobRecord]) -> None:
    company_ids = _upsert_companies(conn, records)
    location_ids = _upsert_locations(conn, records)
    _upsert_raw(conn, records)
    _upsert_jobs(conn, records, company_ids, location_ids)
