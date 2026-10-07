from datetime import timedelta

from tests.conftest import NOW, FixedClock
from yimba.modules.collection.application.ports import CollectionWatch, SinkResult
from yimba.modules.collection.application.use_cases import CollectForWatch, PlanCollections, PurgeRawItems
from yimba.modules.collection.domain.model import CollectedItem, CollectionRun, RunStatus, is_due
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind


def watch(**kw):
    values = dict(
        id="w1",
        keywords=("vaccin",),
        sources=(SourceKind.NEWS, SourceKind.BLUESKY),
        languages=("fr",),
        countries=("CI",),
        frequency_minutes=60,
        active=True,
    )
    values.update(kw)
    return CollectionWatch(**values)


class Catalog:
    def __init__(self, *watches):
        self.watches = {w.id: w for w in watches}

    async def get(self, watch_id):
        return self.watches.get(watch_id)

    async def list_active(self):
        return [w for w in self.watches.values() if w.active]


class Runs:
    def __init__(self):
        self.saved: dict[str, CollectionRun] = {}

    async def last_run(self, watch_id, source):
        candidates = [r for r in self.saved.values() if r.watch_id == watch_id and r.source == source]
        return max(candidates, key=lambda r: r.started_at, default=None)

    async def save(self, run):
        self.saved[run.id] = run


class Queue:
    def __init__(self):
        self.jobs = []

    async def enqueue_collection(self, watch_id, source):
        self.jobs.append((watch_id, source))


class Sink:
    def __init__(self):
        self.calls = []

    async def ingest(self, watch_id, items):
        self.calls.append((watch_id, list(items)))
        return SinkResult(stored=len(items), duplicates=0, skipped=0)


class Archive:
    def __init__(self):
        self.kept, self.purged_before = [], None

    async def keep(self, run_id, items, seen_at):
        self.kept.append((run_id, list(items), seen_at))
        return len(items)

    async def purge(self, not_seen_since):
        self.purged_before = not_seen_since
        return 7


class FakeCollector:
    def __init__(self, source, items=(), error=None):
        self.source, self.items, self.error, self.targets = source, list(items), error, []

    async def collect(self, target):
        self.targets.append(target)
        if self.error:
            raise self.error
        return self.items


def run_at(started, status=RunStatus.SUCCEEDED):
    return CollectionRun(id="r", watch_id="w1", source=SourceKind.NEWS, status=status, started_at=started)


def test_is_due_rules():
    assert is_due(None, 60, NOW)
    assert not is_due(run_at(NOW - timedelta(minutes=59)), 60, NOW)
    assert is_due(run_at(NOW - timedelta(minutes=60)), 60, NOW)
    assert not is_due(run_at(NOW - timedelta(minutes=5), RunStatus.RUNNING), 60, NOW)  # still in flight
    assert is_due(run_at(NOW - timedelta(hours=2), RunStatus.RUNNING), 1440, NOW)  # worker died, retry
    assert is_due(run_at(NOW - timedelta(hours=2), RunStatus.FAILED), 60, NOW)
    # A failure is tried again after ten minutes, not after a whole period; a short period still wins.
    assert not is_due(run_at(NOW - timedelta(minutes=9), RunStatus.FAILED), 1440, NOW)
    assert is_due(run_at(NOW - timedelta(minutes=10), RunStatus.FAILED), 1440, NOW)
    assert not is_due(run_at(NOW - timedelta(minutes=4), RunStatus.FAILED), 5, NOW)
    assert is_due(run_at(NOW - timedelta(minutes=5), RunStatus.FAILED), 5, NOW)


async def test_planner_enqueues_only_due_pairs_of_active_watches():
    runs, queue = Runs(), Queue()
    await runs.save(run_at(NOW - timedelta(minutes=10)))  # news of w1 collected recently
    planner = PlanCollections(Catalog(watch(), watch(id="w2", active=False)), runs, queue, FixedClock())
    assert await planner.execute() == 1
    assert queue.jobs == [("w1", SourceKind.BLUESKY)]


async def test_planner_skips_sources_without_a_collector():
    queue = Queue()
    planner = PlanCollections(Catalog(watch()), Runs(), queue, FixedClock(), sources={SourceKind.NEWS})
    assert await planner.execute() == 1
    assert queue.jobs == [("w1", SourceKind.NEWS)]
    assert await planner.execute() == 1  # no run is ever recorded for bluesky: it must still not be enqueued


async def test_collect_stores_items_and_records_a_successful_run():
    item = CollectedItem(source=SourceKind.NEWS, external_id="1", text="Vaccin gratuit")
    collector, sink, runs, archive = FakeCollector(SourceKind.NEWS, [item]), Sink(), Runs(), Archive()
    use_case = CollectForWatch(
        Catalog(watch()), {SourceKind.NEWS: collector}, sink, runs, archive, FixedClock(), limit=10
    )

    run = await use_case.execute("w1", SourceKind.NEWS)

    assert (run.status, run.fetched, run.stored) == (RunStatus.SUCCEEDED, 1, 1)
    assert sink.calls == [("w1", [item])]
    assert archive.kept == [(run.id, [item], NOW)]  # raw payloads are archived before ingestion
    assert collector.targets[0].keywords == ("vaccin",) and collector.targets[0].limit == 10
    assert runs.saved[run.id].finished_at == NOW


async def test_collect_failure_is_recorded_not_raised():
    for error in (ExternalServiceError("quota exceeded"), RuntimeError("boom")):
        runs = Runs()
        use_case = CollectForWatch(
            Catalog(watch()),
            {SourceKind.NEWS: FakeCollector(SourceKind.NEWS, error=error)},
            Sink(),
            runs,
            Archive(),
            FixedClock(),
        )
        run = await use_case.execute("w1", SourceKind.NEWS)
        assert run.status is RunStatus.FAILED and run.error


async def test_collect_ignores_unknown_inactive_or_unconfigured_targets():
    use_case = CollectForWatch(
        Catalog(watch(), watch(id="off", active=False)),
        {SourceKind.NEWS: FakeCollector(SourceKind.NEWS)},
        Sink(),
        Runs(),
        Archive(),
        FixedClock(),
    )
    assert await use_case.execute("missing", SourceKind.NEWS) is None
    assert await use_case.execute("off", SourceKind.NEWS) is None
    assert await use_case.execute("w1", SourceKind.YOUTUBE) is None  # not enabled for the watch
    assert await use_case.execute("w1", SourceKind.BLUESKY) is None  # enabled but no collector configured


async def test_purge_drops_raw_items_not_seen_during_the_retention_period():
    archive = Archive()
    assert await PurgeRawItems(archive, FixedClock(), retention_days=30).execute() == 7
    assert archive.purged_before == NOW - timedelta(days=30)
