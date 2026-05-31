from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"message": "pong", "timestamp": datetime.now(UTC).isoformat()}
