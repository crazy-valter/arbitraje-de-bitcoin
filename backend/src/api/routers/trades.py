"""
Router: GET /api/trades — historial de trades simulados.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.trade_repo import TradeRepository
from api.dependencies import get_current_user, get_db
from api.schemas import TradeResponse, TradesListResponse

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=TradesListResponse)
async def list_trades(
    limit: int = Query(default=100, ge=1, le=500),
    opportunity_id: uuid.UUID | None = Query(default=None),
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TradesListResponse:
    """
    Lista trades simulados. Filtra por opportunity_id si se proporciona,
    de lo contrario devuelve los mas recientes ordenados por executed_at DESC.
    """
    repo = TradeRepository(session)
    if opportunity_id is not None:
        items = await repo.list_by_opportunity(opportunity_id)
    else:
        items = await repo.list_recent(limit=limit)
    return TradesListResponse(
        items=[
            TradeResponse(
                id=t.id,
                opportunity_id=t.opportunity_id,
                side=t.side.value,
                exchange=t.exchange,
                price=str(t.price),
                volume_btc=str(t.volume_btc),
                fee_usdt=str(t.fee_usdt),
                slippage_usdt=str(t.slippage_usdt),
                executed_at=t.executed_at,
                is_partial=t.is_partial,
                status=t.status.value,
                wallet_usdt_before=str(t.wallet_usdt_before),
                wallet_usdt_after=str(t.wallet_usdt_after),
                wallet_btc_before=str(t.wallet_btc_before),
                wallet_btc_after=str(t.wallet_btc_after),
            )
            for t in items
        ],
        total=len(items),
    )
