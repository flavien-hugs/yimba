from datetime import date

import pandas as pd
from quality.checks import validate

DAY = pd.Timestamp(date(2026, 10, 5))


def frames(**overrides):
    base = {
        "fct_sentiment_daily": pd.DataFrame(
            [
                {
                    "published_day": DAY,
                    "watch_id": "w1",
                    "source": "news",
                    "language": "fr",
                    "mentions": 10,
                    "positive": 2,
                    "neutral": 5,
                    "negative": 3,
                    "negative_share": 0.3,
                }
            ]
        ),
        "fct_data_quality_daily": pd.DataFrame(
            [
                {
                    "collected_day": DAY,
                    "source": "youtube",
                    "mentions": 50,
                    "published_at_missing_share": 0.0,
                    "undetermined_language_share": 0.2,
                }
            ]
        ),
        "fct_collection_health_daily": pd.DataFrame(
            [{"run_day": DAY, "watch_id": "w1", "source": "gdelt", "runs": 10, "success_rate": 0.9}]
        ),
    }
    for name, changes in overrides.items():
        for column, value in changes.items():
            base[name].loc[0, column] = value
    return base


def test_healthy_marts_pass():
    assert validate(frames()) == []


def test_empty_marts_pass():
    assert validate({name: frame.iloc[0:0] for name, frame in frames().items()}) == []


def test_counts_must_add_up_and_sources_be_known():
    (problem,) = validate(frames(fct_sentiment_daily={"neutral": 4, "source": "myspace"}))
    assert "positive + neutral + negative must equal mentions" in problem and "myspace" in problem


def test_missing_dates_and_unknown_languages_are_flagged():
    (problem,) = validate(
        frames(fct_data_quality_daily={"published_at_missing_share": 0.9, "undetermined_language_share": 0.8})
    )
    assert "dates are missing" in problem and "languages unknown" in problem and "youtube" in problem


def test_a_failing_source_is_flagged():
    (problem,) = validate(frames(fct_collection_health_daily={"success_rate": 0.1}))
    assert "runs succeed" in problem and "gdelt" in problem
