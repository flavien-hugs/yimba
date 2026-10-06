from datetime import timedelta

import pytest

from tests.conftest import NOW
from yimba.modules.analysis.public import SentimentLabel, build_text_analyzer
from yimba.modules.mentions.adapters.persistence import SqlMentionRepository
from yimba.modules.mentions.application.ports import GroupBy, MentionFilters
from yimba.modules.mentions.application.use_cases import ComputeStats, IncomingMention, IngestMentions, SearchMentions
from yimba.modules.mentions.domain.model import Metrics, anonymize_author, content_hash
from yimba.shared.pagination import PageParams
from yimba.shared.source import SourceKind


def item(external_id, text, source=SourceKind.FACEBOOK, **kw):
    return IncomingMention(source=source, external_id=external_id, text=text, **kw)


@pytest.fixture
def ingest(session, clock):
    return IngestMentions(SqlMentionRepository(session), build_text_analyzer("lexicon"), clock, author_salt="s")


def test_content_hash_ignores_case_spacing_and_links():
    assert content_hash("Vaccin   GRATUIT https://t.co/abc") == content_hash("vaccin gratuit")


def test_authors_are_hashed_with_the_salt():
    assert anonymize_author("@Awa", "s1") == anonymize_author("@awa ", "s1")
    assert anonymize_author("@awa", "s1") != anonymize_author("@awa", "s2")
    assert "awa" not in anonymize_author("@awa", "s1")
    assert anonymize_author(None, "s") is None


async def test_ingest_analyzes_dedupes_and_counts(ingest, session):
    summary = await ingest.execute(
        "w1",
        [
            item("1", "Merci aux agents de santé, très bien 😊", author_handle="@awa", metrics=Metrics(likes=5)),
            item("2", "C'est la honte, rupture de doses"),
            item("2", "same external id again"),
            item("3", "c'est la HONTE, rupture de doses https://x.co/1"),  # same text, other id
            item("4", "   "),
            item("", "no id"),
        ],
    )
    assert (summary.received, summary.skipped, summary.stored, summary.duplicates) == (6, 2, 2, 2)

    again = await ingest.execute("w1", [item("1", "Merci aux agents de santé, très bien 😊")])
    assert (again.stored, again.duplicates) == (0, 1)

    page = await SearchMentions(SqlMentionRepository(session)).execute(MentionFilters("w1"), PageParams())
    by_id = {m.external_id: m for m in page.items}
    assert by_id["1"].sentiment.label is SentimentLabel.POSITIVE and by_id["1"].metrics.likes == 5
    assert by_id["1"].author_ref and "awa" not in by_id["1"].author_ref
    assert by_id["2"].sentiment.label is SentimentLabel.NEGATIVE and by_id["2"].language == "fr"


async def test_same_item_in_two_watches_is_kept_for_each(ingest):
    first = await ingest.execute("w1", [item("1", "Super initiative, bravo")])
    second = await ingest.execute("w2", [item("1", "Super initiative, bravo")])
    assert first.stored == second.stored == 1


async def test_search_filters(ingest, session):
    await ingest.execute(
        "w1",
        [
            item("1", "Bravo, super initiative", published_at=NOW - timedelta(days=2)),
            item("2", "La honte, quelle arnaque", source=SourceKind.NEWS, published_at=NOW - timedelta(hours=1)),
            item("3", "Réunion prévue demain à Abidjan", published_at=NOW),
        ],
    )
    search = SearchMentions(SqlMentionRepository(session))

    async def ids(**filters):
        page = await search.execute(MentionFilters("w1", **filters), PageParams())
        return [m.external_id for m in page.items]

    assert await ids() == ["3", "2", "1"]  # newest first
    assert await ids(sentiment=SentimentLabel.NEGATIVE) == ["2"]
    assert await ids(source=SourceKind.NEWS) == ["2"]
    assert await ids(start=NOW - timedelta(days=1)) == ["3", "2"]
    assert await ids(end=NOW - timedelta(days=1)) == ["1"]
    assert await ids(query="abidjan") == ["3"]


async def test_stats_totals_buckets_and_emotions(ingest, session):
    await ingest.execute(
        "w1",
        [
            item("1", "Bravo, super initiative", published_at=NOW - timedelta(days=1)),
            item("2", "La honte, quelle arnaque", source=SourceKind.NEWS, published_at=NOW),
            item("3", "Colère et honte, scandale", published_at=NOW),
            item("4", "Réunion demain", published_at=NOW),
        ],
    )
    stats = ComputeStats(SqlMentionRepository(session))

    by_day = await stats.execute(MentionFilters("w1"), GroupBy.DAY)
    assert (by_day.totals.total, by_day.totals.positive, by_day.totals.negative, by_day.totals.neutral) == (4, 1, 2, 1)
    assert by_day.totals.negative_share == 0.5
    assert [(b.key, b.counts.total) for b in by_day.buckets] == [("2026-10-05", 1), ("2026-10-06", 3)]
    assert by_day.emotions.get("anger") == 2

    by_source = await stats.execute(MentionFilters("w1"), GroupBy.SOURCE)
    assert {b.key: b.counts.total for b in by_source.buckets} == {"facebook": 3, "news": 1}

    empty = await stats.execute(MentionFilters("nobody"), GroupBy.DAY)
    assert empty.totals.total == 0 and empty.totals.negative_share == 0.0 and empty.buckets == ()
