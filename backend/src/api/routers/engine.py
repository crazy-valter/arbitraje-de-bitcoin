"""
Router: GET/PUT /api/engine — control del motor de arbitraje (pausar/reanudar).

El estado ENGINE_PAUSED se persiste en system_config para que sobreviva
reinicios del contenedor — el motor arranca en el mismo estado en que quedó.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.config_repo import ConfigRepository
from api.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/engine", tags=["engine"])


class EngineStatusResponse(BaseModel):
    is_running: bool
    is_paused: bool


class EngineControlRequest(BaseModel):
    paused: bool


@router.get("", response_model=EngineStatusResponse)
async def get_engine_status(
    request: Request,
    _: dict[str, object] = Depends(get_current_user),
) -> EngineStatusResponse:
    """Retorna el estado actual del motor de arbitraje."""
    engine = request.app.state.engine
    return EngineStatusResponse(
        is_running=engine._running,
        is_paused=engine.is_paused,
    )


@router.put("", response_model=EngineStatusResponse)
async def control_engine(
    request: Request,
    payload: EngineControlRequest,
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EngineStatusResponse:
    """Pausa o reanuda el motor. Persiste el estado para que sobreviva reinicios."""
    engine = request.app.state.engine

    if payload.paused:
        engine.pause()
    else:
        engine.resume()

    # Persistir en DB — el próximo arranque respeta este estado
    repo = ConfigRepository(session)
    await repo.set("ENGINE_PAUSED", str(payload.paused).lower())

    return EngineStatusResponse(
        is_running=engine._running,
        is_paused=engine.is_paused,
    )
