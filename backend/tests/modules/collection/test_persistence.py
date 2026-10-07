from datetime import timedelta

from sqlalchemy import func, select

from tests.conftest import NOW
from yimba.modules.collection.adapters.persistence import RawItemRow, SqlRawArchive
from yimba.modules.collection.domain.model import CollectedItem
from yimba.shared.source import SourceKind


def item(external_id, raw, source=SourceKind.YOUTUBE):
    return CollectedItem(source, external_id, "texte", raw=raw)


async def rows(session):
    session.expire_all()
    return {(r.source, r.external_id): r for r in await session.scalars(select(RawItemRow))}


async def test_keep_stores_one_row_per_source_item_and_refreshes_it(session):
    archive = SqlRawArchive(session)
    kept = await archive.keep(
        "run1",
        [item("a", {"v": 1}), item("a", {"v": 2}), item("b", {"v": 1}), item("c", None), item("", {"v": 1})],
        NOW,
    )
    assert kept == 2  # duplicates collapsed, items without payload or id skipped

    later = NOW + timedelta(hours=1)
    await archive.keep("run2", [item("a", {"v": 3}), item("a", {"v": 1}, source=SourceKind.BLUESKY)], later)

    stored = await rows(session)
    assert set(stored) == {("youtube", "a"), ("youtube", "b"), ("bluesky", "a")}
    refreshed = stored[("youtube", "a")]
    assert refreshed.payload == {"v": 3} and refreshed.last_run_id == "run2"
    assert (refreshed.first_seen_at, refreshed.last_seen_at) == (NOW, later)


async def test_keep_handles_large_batches(session):
    archive = SqlRawArchive(session)
    assert await archive.keep("run", [item(str(i), {"i": i}) for i in range(1200)], NOW) == 1200
    assert await session.scalar(select(func.count()).select_from(RawItemRow)) == 1200


async def test_purge_deletes_items_not_seen_since_the_cutoff(session):
    archive = SqlRawArchive(session)
    await archive.keep("old", [item("old", {})], NOW - timedelta(days=40))
    await archive.keep("new", [item("new", {})], NOW)
    assert await archive.purge(NOW - timedelta(days=30)) == 1
    assert set(await rows(session)) == {("youtube", "new")}
