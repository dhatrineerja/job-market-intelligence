from collections import Counter
from datetime import UTC, datetime

from app.etl import naukri_2023

HEADER = ["title", "title href", "subTitle", "ellipsis", "ellipsis 2", "ellipsis 3", "ellipsis 4"]
HEADER += [*naukri_2023.SKILL_COLUMNS, "fleft 9"]


def _write(path, rows):
    # joined without quoting, so a comma inside a value spills into extra fields
    lines = [",".join(HEADER), *(",".join(row) for row in rows)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row(job_id, title="Data Engineer", salary="10-20 Lacs PA", description="Build pipelines..."):
    url = f"https://www.naukri.com/job-listings-x-acme-pune-3-to-5-years-{job_id}"
    return [title, url, "Acme", "3-5 Yrs", salary, "Pune", description, "sql", "python"] + [""] * 7


def test_merges_repeat_jobs_and_repairs_split_descriptions(tmp_path, monkeypatch):
    may, july = tmp_path / "may", tmp_path / "july"
    may.mkdir()
    july.mkdir()
    monkeypatch.setattr(naukri_2023, "DATASETS", ["may", "july"])
    monkeypatch.setattr(
        naukri_2023,
        "SNAPSHOTS",
        {
            "may": datetime(2023, 5, 29, tzinfo=UTC),
            "july": datetime(2023, 8, 3, tzinfo=UTC),
        },
    )
    split_description = _row("150523000001")
    split_description[6:7] = ["Build, test", " deploy..."]  # comma spilled into extra fields
    _write(may / "a.csv", [_row("150523000002"), split_description])
    _write(july / "b.csv", [_row("150523000002", salary="15-25 Lacs PA")])
    (july / "AIML other layout.csv").write_text("x,y\n1,2\n", encoding="utf-8")

    stats = Counter()
    records = {r.source_id: r for r in naukri_2023.read([may, july], stats)}

    assert set(records) == {"150523000001", "150523000002"}
    assert stats["duplicates_merged"] == 1
    assert stats["rows_repaired"] == 1
    assert stats["files_skipped"] == 1
    assert records["150523000001"].description == "Build, test, deploy"
    merged = records["150523000002"]
    assert merged.salary_mid == 2_000_000  # the July row's 15-25 lakh range wins
    assert merged.first_seen_at == datetime(2023, 5, 29, tzinfo=UTC)
    assert merged.fetched_at == datetime(2023, 8, 3, tzinfo=UTC)
    assert merged.skills_raw == "sql, python"
