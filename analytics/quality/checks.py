"""Data quality checks with Pandera, run after dbt on the marts of the last days.

dbt tests check rows (keys, accepted values, sums). These check distributions, where a collector or the analysis
degrading silently shows up: dates that no source gave, languages nobody recognises, a source that keeps failing.
"""

from __future__ import annotations

import os
from typing import Mapping

import pandas as pd
import pandera.pandas as pa

SOURCES = ["facebook", "instagram", "youtube", "bluesky", "news", "gdelt"]
DAYS = int(os.environ.get("QUALITY_DAYS", "7"))
# Below this many mentions (or runs) a day, shares are noise: thresholds are not applied.
MIN_SAMPLE = int(os.environ.get("QUALITY_MIN_SAMPLE", "20"))
MAX_MISSING_DATES = float(os.environ.get("QUALITY_MAX_MISSING_DATES", "0.2"))
MAX_UNDETERMINED_LANGUAGE = float(os.environ.get("QUALITY_MAX_UNDETERMINED_LANGUAGE", "0.6"))
MIN_SUCCESS_RATE = float(os.environ.get("QUALITY_MIN_SUCCESS_RATE", "0.5"))

share = pa.Check.in_range(0.0, 1.0)

sentiment_daily = pa.DataFrameSchema(
    {
        "published_day": pa.Column("datetime64[ns]", nullable=False),
        "watch_id": pa.Column(str),
        "source": pa.Column(str, pa.Check.isin(SOURCES)),
        "mentions": pa.Column(int, pa.Check.ge(1)),
        "positive": pa.Column(int, pa.Check.ge(0)),
        "neutral": pa.Column(int, pa.Check.ge(0)),
        "negative": pa.Column(int, pa.Check.ge(0)),
        "negative_share": pa.Column(float, share),
    },
    checks=pa.Check(
        lambda df: df["positive"] + df["neutral"] + df["negative"] == df["mentions"],
        error="positive + neutral + negative must equal mentions",
    ),
    coerce=True,
)

data_quality_daily = pa.DataFrameSchema(
    {
        "collected_day": pa.Column("datetime64[ns]", nullable=False),
        "source": pa.Column(str, pa.Check.isin(SOURCES)),
        "mentions": pa.Column(int, pa.Check.ge(1)),
        "published_at_missing_share": pa.Column(
            float,
            [share, pa.Check.le(MAX_MISSING_DATES, error=f"more than {MAX_MISSING_DATES:.0%} of dates are missing")],
        ),
        "undetermined_language_share": pa.Column(
            float,
            [
                share,
                pa.Check.le(
                    MAX_UNDETERMINED_LANGUAGE, error=f"more than {MAX_UNDETERMINED_LANGUAGE:.0%} of languages unknown"
                ),
            ],
        ),
    },
    coerce=True,
)

collection_health_daily = pa.DataFrameSchema(
    {
        "run_day": pa.Column("datetime64[ns]", nullable=False),
        "source": pa.Column(str, pa.Check.isin(SOURCES)),
        "runs": pa.Column(int, pa.Check.ge(1)),
        "success_rate": pa.Column(
            float, [share, pa.Check.ge(MIN_SUCCESS_RATE, error=f"less than {MIN_SUCCESS_RATE:.0%} of runs succeed")]
        ),
    },
    coerce=True,
)

QUERIES = {
    "fct_sentiment_daily": "select * from analytics.fct_sentiment_daily where published_day >= current_date - %(days)s",
    "fct_data_quality_daily": (
        "select * from analytics.fct_data_quality_daily where collected_day >= current_date - %(days)s"
        " and mentions >= %(min_sample)s"
    ),
    "fct_collection_health_daily": (
        "select * from analytics.fct_collection_health_daily where run_day >= current_date - %(days)s" " and runs >= 3"
    ),
}
SCHEMAS = {
    "fct_sentiment_daily": sentiment_daily,
    "fct_data_quality_daily": data_quality_daily,
    "fct_collection_health_daily": collection_health_daily,
}


def validate(frames: Mapping[str, pd.DataFrame]) -> list[str]:
    """Return one readable report per mart that fails its checks."""
    problems = []
    for name, schema in SCHEMAS.items():
        frame = frames[name]
        if frame.empty:
            continue
        try:
            schema.validate(frame, lazy=True)
        except pa.errors.SchemaErrors as exc:
            cases = exc.failure_cases[["column", "check", "index", "failure_case"]]
            keys = [key for key in ("published_day", "collected_day", "run_day", "watch_id", "source") if key in frame]
            located = cases.join(frame[keys], on="index") if keys else cases
            problems.append(f"{name}\n{located.to_string(index=False)}")
    return problems


def load(engine) -> dict[str, pd.DataFrame]:
    params = {"days": DAYS, "min_sample": MIN_SAMPLE}
    return {name: pd.read_sql_query(query, engine, params=params) for name, query in QUERIES.items()}
