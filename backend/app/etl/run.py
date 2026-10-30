"""Download the Kaggle datasets and load them: python -m app.etl.run"""

import os
from collections import Counter
from pathlib import Path

from app.config import settings
from app.db import engine
from app.etl import linkedin, naukri, naukri_2023, quality
from app.etl.loader import load

# Newest data last: when the same job appears in two datasets the later load wins
SOURCES = [linkedin, naukri_2023, naukri]


def download(dataset: str) -> Path:
    # kagglehub reads credentials from the environment when it is imported
    os.environ.setdefault("KAGGLE_USERNAME", settings.kaggle_username)
    os.environ.setdefault("KAGGLE_KEY", settings.kaggle_key)
    import kagglehub

    return Path(kagglehub.dataset_download(dataset))


def main() -> None:
    stats: dict[str, Counter] = {}
    for source in SOURCES:
        counter = stats.setdefault(source.NAME, Counter())
        records = list(source.read([download(slug) for slug in source.DATASETS], counter))
        with engine.begin() as conn:
            load(conn, records)
        print(f"{source.NAME}: loaded {len(records):,} jobs, {dict(counter)}")

    with engine.connect() as conn:
        print(f"report: {quality.write_report(conn, stats)}")


if __name__ == "__main__":
    main()
