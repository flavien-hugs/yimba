from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from yimba.entrypoints.api import deps, permissions
from yimba.entrypoints.api.schemas import PageOut, WatchCreate, WatchOut, WatchUpdate, page_of
from yimba.modules.identity.public import Principal
from yimba.modules.watches.application.use_cases import (
    CreateWatch,
    CreateWatchCommand,
    DeleteWatch,
    GetWatch,
    ListWatches,
    UpdateWatch,
    UpdateWatchCommand,
)
from yimba.shared.pagination import PageParams

router = APIRouter(prefix="/watches", tags=["Watches"])


@router.post("", response_model=WatchOut, status_code=status.HTTP_201_CREATED, summary="Create a watch")
async def create(
    payload: WatchCreate,
    principal: Principal = Depends(deps.require(permissions.WATCH_CREATE)),
    use_case: CreateWatch = Depends(deps.create_watch),
) -> WatchOut:
    watch = await use_case.execute(
        CreateWatchCommand(
            owner_id=principal.id,
            name=payload.name,
            keywords=payload.keywords,
            sources=payload.sources,
            languages=payload.languages,
            countries=payload.countries,
            frequency_minutes=payload.frequency_minutes,
            alert_negative_share=payload.alert_negative_share,
            alert_min_mentions=payload.alert_min_mentions,
        )
    )
    return WatchOut.of(watch)


@router.get("", response_model=PageOut[WatchOut], summary="List my watches")
async def list_all(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter by name"),
    active: bool | None = Query(None, description="Only the active watches (true) or the paused ones (false)"),
    principal: Principal = Depends(deps.require(permissions.WATCH_READ)),
    use_case: ListWatches = Depends(deps.list_watches),
):
    result = await use_case.execute(principal.id, PageParams(page, size), search, active)
    return page_of(result, WatchOut.of)


@router.get("/{watch_id}", response_model=WatchOut, summary="Get a watch")
async def read(
    watch_id: str,
    principal: Principal = Depends(deps.require(permissions.WATCH_READ)),
    use_case: GetWatch = Depends(deps.get_watch),
) -> WatchOut:
    return WatchOut.of(await use_case.execute(principal.id, watch_id))


@router.patch("/{watch_id}", response_model=WatchOut, summary="Update a watch")
async def update(
    watch_id: str,
    payload: WatchUpdate,
    principal: Principal = Depends(deps.require(permissions.WATCH_UPDATE)),
    use_case: UpdateWatch = Depends(deps.update_watch),
) -> WatchOut:
    changes = payload.model_dump(exclude_unset=True)
    watch = await use_case.execute(UpdateWatchCommand(owner_id=principal.id, watch_id=watch_id, **changes))
    return WatchOut.of(watch)


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a watch")
async def delete(
    watch_id: str,
    principal: Principal = Depends(deps.require(permissions.WATCH_DELETE)),
    use_case: DeleteWatch = Depends(deps.delete_watch),
) -> Response:
    await use_case.execute(principal.id, watch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
