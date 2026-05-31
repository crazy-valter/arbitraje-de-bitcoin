"""
Router: GET /api/metrics — métricas agregadas del sistema.
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.opportunity_repo import OpportunityRepository
from api.dependencies import get_current_user, get_db
from api.schemas import MetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
async def get_metrics(
    request: Request,
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Retorna métricas actuales del sistema.
    El motor de arbitraje actualiza estas métricas en tiempo real via SSE.
    Este endpoint provee el snapshot inicial al cargar el dashboard.
    """
    repo = OpportunityRepository(session)
    total_pnl = await repo.get_total_pnl()

    # Calcular uptime_seconds desde el arranque del lifespan (almacenado en app.state)
    start_time: float = getattr(request.app.state, "start_time", time.monotonic())
    uptime_seconds = int(time.monotonic() - start_time)

    # Obtener métricas del engine desde app.state.engine (almacenado en lifespan)
    engine = getattr(request.app.state, "engine", None)
    opportunities_detected = engine.opportunities_detected if engine is not None else 0
    trades_simulated = engine.trades_simulated if engine is not None else 0
    connected_exchanges = (
        sum(1 for e in engine._exchanges if e.is_connected)
        if engine is not None
        else 0
    )
    exchange_latencies: dict[str, int] = (
        {e.exchange_id: e.feed_staleness_ms for e in engine._exchanges}
        if engine is not None
        else {}
    )

    # Calcular win_rate desde los contadores del engine
    win_rate = (
        trades_simulated / opportunities_detected * 100
        if opportunities_detected > 0
        else 0.0
    )

    return MetricsResponse(
        opportunities_detected=opportunities_detected,
        trades_simulated=trades_simulated,
        uptime_seconds=uptime_seconds,
        win_rate_pct=round(win_rate, 2),
        total_pnl_usdt=total_pnl,
        connected_exchanges=connected_exchanges,
        exchange_latencies=exchange_latencies,
        timestamp=datetime.now(UTC).isoformat(),
    )
