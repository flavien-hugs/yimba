from __future__ import annotations

from typing import Sequence

from yimba.modules.collection.application.ports import SinkResult
from yimba.modules.collection.domain.model import CollectedItem
from yimba.modules.mentions.public import IncomingMention, MentionIngestor, Metrics


class MentionsItemSink:
    """Hands collected items to the mentions module, translating between the two vocabularies."""

    def __init__(self, ingestor: MentionIngestor) -> None:
        self._ingestor = ingestor

    async def ingest(self, watch_id: str, items: Sequence[CollectedItem]) -> SinkResult:
        incoming = [
            IncomingMention(
                source=item.source,
                external_id=item.external_id,
                text=item.text,
                author_handle=item.author_handle,
                url=item.url,
                published_at=item.published_at,
                metrics=Metrics(item.likes, item.shares, item.views, item.comments),
            )
            for item in items
        ]
        summary = await self._ingestor.ingest(watch_id, incoming)
        return SinkResult(stored=summary.stored, duplicates=summary.duplicates, skipped=summary.skipped)
