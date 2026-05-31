"""
Router: GET /api/opportunities — historial de oportunidades detectadas.

Soporta paginacion real (offset + limit), filtros por status, exchanges
y rango de fechas. El campo 'total' refleja el COUNT real desde DB.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.exchanges.registry import EXCHANGE_REGISTRY
from adapters.persistence.opportunity_repo import OpportunityRepository
from api.dependencies import get_current_user, get_db
from api.schemas import OpportunitiesListResponse, OpportunityResponse
from core.entities.opportunity import OpportunityStatus

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

# Rango maximo permitido para filtro de fechas
_MAX_DATE_RANGE_DAYS = 90


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """Normaliza un datetime a UTC naive para asyncpg (TIMESTAMP WITHOUT TIME ZONE)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


@router.get("", response_model=OpportunitiesListResponse)
async def list_opportunities(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    status: list[str] | None = Query(default=None),
    buy_exchange: list[str] | None = Query(default=None),
    sell_exchange: list[str] | None = Query(default=None),
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OpportunitiesListResponse:
    """
    Lista oportunidades detectadas, ordenadas por detected_at DESC.
    Paginacion real con filtros opcionales por status, exchanges y rango de fechas.
    Los filtros de status y exchange aceptan multiples valores (multi-select).
    """
    # Validar cada status contra valores validos
    status_filter: list[OpportunityStatus] | None = None
    if status:
        status_filter = []
        for s in status:
            try:
                status_filter.append(OpportunityStatus(s.upper()))
            except ValueError as err:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estado invalido: '{s}'. "
                    f"Valores validos: {[e.value for e in OpportunityStatus]}",
                ) from err

    # Validar exchanges contra lista blanca
    if buy_exchange is not None:
        for ex in buy_exchange:
            if ex not in EXCHANGE_REGISTRY:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exchange de compra invalido: '{ex}'. "
                    f"Valores validos: {list(EXCHANGE_REGISTRY.keys())}",
                )
    if sell_exchange is not None:
        for ex in sell_exchange:
            if ex not in EXCHANGE_REGISTRY:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exchange de venta invalido: '{ex}'. "
                    f"Valores validos: {list(EXCHANGE_REGISTRY.keys())}",
                )

    # Normalizar datetimes a UTC naive (asyncpg requiere TIMESTAMP WITHOUT TIME ZONE)
    from_dt_naive = _to_naive_utc(from_dt)
    to_dt_naive = _to_naive_utc(to_dt)

    # Validar rango de fechas
    if from_dt_naive is not None and to_dt_naive is not None:
        if from_dt_naive > to_dt_naive:
            raise HTTPException(
                status_code=400,
                detail="from_dt debe ser anterior o igual a to_dt.",
            )
        delta = to_dt_naive - from_dt_naive
        if delta.days > _MAX_DATE_RANGE_DAYS:
            raise HTTPException(
                status_code=400,
                detail=f"El rango de fechas no puede superar {_MAX_DATE_RANGE_DAYS} dias.",
            )

    repo = OpportunityRepository(session)
    items, total = await repo.list_paginated(
        offset=offset,
        limit=limit,
        status=status_filter,
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        from_dt=from_dt_naive,
        to_dt=to_dt_naive,
    )

    return OpportunitiesListResponse(
        items=[
            OpportunityResponse(
                id=o.id,
                buy_exchange=o.buy_exchange,
                sell_exchange=o.sell_exchange,
                buy_price=str(o.buy_price),
                sell_price=str(o.sell_price),
                gross_spread_pct=str(o.gross_spread_pct),
                total_fees_usdt=str(o.total_fees_usdt),
                slippage_usdt=str(o.slippage_usdt),
                net_profit_usdt=str(o.net_profit_usdt),
                net_profit_pct=str(o.net_profit_pct),
                max_volume_btc=str(o.max_volume_btc),
                strategy=o.strategy,
                score=o.score,
                status=o.status.value,
                detected_at=o.detected_at,
                executed_at=o.executed_at,
                trading_fee_buy_usdt=str(o.trading_fee_buy_usdt),
                trading_fee_sell_usdt=str(o.trading_fee_sell_usdt),
                withdrawal_fee_usdt=str(o.withdrawal_fee_usdt),
                network_latency_ms=str(o.network_latency_ms),
            )
            for o in items
        ],
        total=total,
    )
