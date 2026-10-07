from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/@ping", summary="Liveness probe")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
