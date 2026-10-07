from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from yimba.entrypoints.api import deps, permissions
from yimba.entrypoints.api.schemas import AlertOut, PageOut, page_of
from yimba.modules.alerts.public import AcknowledgeAlert, ListAlerts
from yimba.modules.identity.public import Principal
from yimba.modules.watches.application.use_cases import GetWatch
from yimba.shared.pagination import PageParams

router = APIRouter(prefix="/watches/{watch_id}/alerts", tags=["Alerts"])


@router.get("", response_model=PageOut[AlertOut], summary="Alerts raised for a watch")
async def list_for_watch(
    watch_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(deps.require(permissions.ALERT_READ)),
    watches: GetWatch = Depends(deps.get_watch),
    use_case: ListAlerts = Depends(deps.list_alerts),
):
    await watches.execute(principal.id, watch_id)
    return page_of(await use_case.execute(watch_id, PageParams(page, size)), AlertOut.of)


@router.post("/{alert_id}/acknowledge", response_model=AlertOut, summary="Mark an alert as handled")
async def acknowledge(
    watch_id: str,
    alert_id: str,
    principal: Principal = Depends(deps.require(permissions.ALERT_ACKNOWLEDGE)),
    watches: GetWatch = Depends(deps.get_watch),
    use_case: AcknowledgeAlert = Depends(deps.acknowledge_alert),
) -> AlertOut:
    await watches.execute(principal.id, watch_id)
    return AlertOut.of(await use_case.execute(watch_id, alert_id))
