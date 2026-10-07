from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from yimba.entrypoints.api import deps, permissions
from yimba.entrypoints.api.schemas import MentionOut, PageOut, StatsOut, page_of
from yimba.modules.analysis.public import Emotion, SentimentLabel
from yimba.modules.identity.public import Principal
from yimba.modules.mentions.application.ports import GroupBy, MentionFilters
from yimba.modules.mentions.application.use_cases import ComputeStats, SearchMentions
from yimba.modules.watches.application.use_cases import GetWatch
from yimba.shared.pagination import PageParams
from yimba.shared.source import SourceKind

router = APIRouter(prefix="/watches/{watch_id}", tags=["Mentions"])


def _filters(
    watch_id: str,
    source: SourceKind | None,
    language: str | None,
    sentiment: SentimentLabel | None,
    emotion: Emotion | None,
    start: datetime | None,
    end: datetime | None,
    q: str | None,
) -> MentionFilters:
    return MentionFilters(
        watch_id=watch_id,
        source=source,
        language=language,
        sentiment=sentiment,
        emotion=emotion,
        start=start,
        end=end,
        query=q,
    )


@router.get("/mentions", response_model=PageOut[MentionOut], summary="Search the mentions of a watch")
async def list_mentions(
    watch_id: str,
    source: SourceKind | None = None,
    language: str | None = None,
    sentiment: SentimentLabel | None = None,
    emotion: Emotion | None = None,
    start: datetime | None = Query(None, description="Published at or after (ISO 8601)"),
    end: datetime | None = Query(None, description="Published before (ISO 8601)"),
    q: str | None = Query(None, description="Text contains"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(deps.require(permissions.MENTION_READ)),
    watches: GetWatch = Depends(deps.get_watch),
    use_case: SearchMentions = Depends(deps.search_mentions),
):
    await watches.execute(principal.id, watch_id)
    result = await use_case.execute(
        _filters(watch_id, source, language, sentiment, emotion, start, end, q), PageParams(page, size)
    )
    return page_of(result, MentionOut.of)


@router.get("/stats", response_model=StatsOut, summary="Sentiment and emotion statistics of a watch")
async def stats(
    watch_id: str,
    group_by: GroupBy = GroupBy.DAY,
    source: SourceKind | None = None,
    language: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    principal: Principal = Depends(deps.require(permissions.STATISTICS_READ)),
    watches: GetWatch = Depends(deps.get_watch),
    use_case: ComputeStats = Depends(deps.compute_stats),
) -> StatsOut:
    await watches.execute(principal.id, watch_id)
    result = await use_case.execute(_filters(watch_id, source, language, None, None, start, end, None), group_by)
    return StatsOut.of(result)
