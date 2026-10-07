import pytest

from yimba.modules.watches.adapters.persistence import SqlWatchRepository
from yimba.modules.watches.application.use_cases import (
    CreateWatch,
    CreateWatchCommand,
    DeleteWatch,
    GetWatch,
    ListWatches,
    UpdateWatch,
    UpdateWatchCommand,
)
from yimba.shared.errors import Conflict, NotFound
from yimba.shared.pagination import PageParams
from yimba.shared.source import SourceKind


def command(owner="u1", name="Santé", **kw):
    return CreateWatchCommand(owner_id=owner, name=name, keywords=["vaccin"], sources=[SourceKind.NEWS], **kw)


async def test_create_get_list_roundtrip(session, clock):
    repo = SqlWatchRepository(session)
    created = await CreateWatch(repo, clock).execute(command(frequency_minutes=15, alert_negative_share=0.5))

    fetched = await GetWatch(repo).execute("u1", created.id)
    assert fetched == created
    assert fetched.frequency.minutes == 15 and fetched.threshold.negative_share == 0.5

    page = await ListWatches(repo).execute("u1", PageParams(1, 10))
    assert [w.id for w in page.items] == [created.id] and page.total == 1


async def test_duplicate_name_for_same_owner_conflicts_but_not_across_owners(session, clock):
    repo = SqlWatchRepository(session)
    use_case = CreateWatch(repo, clock)
    await use_case.execute(command(name="Santé"))
    with pytest.raises(Conflict):
        await use_case.execute(command(name="  santé "))
    await use_case.execute(command(owner="u2", name="Santé"))


async def test_other_owners_watches_look_missing(session, clock):
    repo = SqlWatchRepository(session)
    created = await CreateWatch(repo, clock).execute(command())
    with pytest.raises(NotFound):
        await GetWatch(repo).execute("intruder", created.id)
    with pytest.raises(NotFound):
        await DeleteWatch(repo).execute("intruder", created.id)
    assert (await ListWatches(repo).execute("intruder", PageParams())).total == 0


async def test_update_changes_only_given_fields_and_checks_name_conflicts(session, clock):
    repo = SqlWatchRepository(session)
    first = await CreateWatch(repo, clock).execute(command(name="Santé"))
    await CreateWatch(repo, clock).execute(command(name="Emploi"))

    updated = await UpdateWatch(repo, clock).execute(
        UpdateWatchCommand(owner_id="u1", watch_id=first.id, alert_negative_share=0.6, active=False)
    )
    assert (updated.threshold.negative_share, updated.threshold.min_mentions, updated.active) == (0.6, 20, False)
    assert updated.name == "Santé"

    with pytest.raises(Conflict):
        await UpdateWatch(repo, clock).execute(UpdateWatchCommand(owner_id="u1", watch_id=first.id, name="Emploi"))


async def test_delete_and_list_search(session, clock):
    repo = SqlWatchRepository(session)
    a = await CreateWatch(repo, clock).execute(command(name="Santé"))
    await CreateWatch(repo, clock).execute(command(name="Emploi des jeunes"))
    assert (await ListWatches(repo).execute("u1", PageParams(), search="emploi")).total == 1
    await DeleteWatch(repo).execute("u1", a.id)
    assert await repo.get(a.id) is None


async def test_list_active_excludes_paused_watches(session, clock):
    repo = SqlWatchRepository(session)
    a = await CreateWatch(repo, clock).execute(command(name="Santé"))
    b = await CreateWatch(repo, clock).execute(command(name="Emploi"))
    await UpdateWatch(repo, clock).execute(UpdateWatchCommand(owner_id="u1", watch_id=b.id, active=False))
    assert [w.id for w in await repo.list_active()] == [a.id]
