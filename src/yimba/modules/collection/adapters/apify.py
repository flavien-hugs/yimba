from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol, Sequence

from yimba.modules.collection.domain.model import CollectedItem, CollectionTarget
from yimba.shared.errors import ExternalServiceError
from yimba.shared.source import SourceKind

ActorInputBuilder = Callable[[CollectionTarget, str], dict[str, Any]]
ItemMapper = Callable[[Mapping[str, Any]], Sequence[CollectedItem]]


class ActorRunner(Protocol):
    async def run(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]: ...


class ApifyActorRunner:
    """Runs an Apify actor and returns its dataset items (non-blocking, unlike the legacy client usage)."""

    def __init__(self, token: str) -> None:
        from apify_client import ApifyClientAsync

        self._client = ApifyClientAsync(token=token)

    async def run(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            run = await self._client.actor(actor_id).call(run_input=run_input)
            if run is None or run.get("status") != "SUCCEEDED":
                raise ExternalServiceError(f"Apify actor {actor_id} did not succeed", code="collection/apify-failed")
            page = await self._client.dataset(run["defaultDatasetId"]).list_items()
            return list(page.items)
        except ExternalServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - provider SDK raises many unrelated types
            raise ExternalServiceError(f"Apify actor {actor_id} failed: {exc}", code="collection/apify-failed") from exc


class ApifyCollector:
    """One generic collector; platform specifics live in the input builder and the item mapper."""

    def __init__(
        self,
        source: SourceKind,
        actor_id: str,
        runner: ActorRunner,
        build_input: ActorInputBuilder,
        map_item: ItemMapper,
    ) -> None:
        self.source = source
        self._actor_id = actor_id
        self._runner = runner
        self._build_input = build_input
        self._map_item = map_item

    async def collect(self, target: CollectionTarget) -> Sequence[CollectedItem]:
        collected: list[CollectedItem] = []
        for keyword in target.keywords:
            raw_items = await self._runner.run(self._actor_id, self._build_input(target, keyword))
            for raw in raw_items:
                collected.extend(self._map_item(raw))
        return collected[: target.limit * max(1, len(target.keywords))]
