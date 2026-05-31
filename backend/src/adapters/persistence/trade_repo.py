"""
TradeRepository — implementación PostgreSQL para ITradeRepository.
"""

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.models import Trade as TradeModel
from core.entities.trade import SimulatedTrade, TradeSide, TradeStatus
from ports.trade_repo_port import ITradeRepository

logger = structlog.get_logger(__name__)


def _to_entity(model: TradeModel) -> SimulatedTrade:
    """Convierte el modelo SQLAlchemy a la entidad del dominio."""
    return SimulatedTrade(
        id=model.id,
        opportunity_id=model.opportunity_id,
        side=TradeSide(model.side),
        exchange=model.exchange,
        price=Decimal(str(model.price)),
        volume_btc=Decimal(str(model.volume_btc)),
        fee_usdt=Decimal(str(model.fee_usdt)),
        slippage_usdt=Decimal(str(model.slippage_usdt)),
        executed_at=model.executed_at,
        is_partial=model.is_partial,
        status=TradeStatus.EXECUTED,
        wallet_usdt_before=Decimal(str(model.wallet_usdt_before))
        if model.wallet_usdt_before is not None
        else Decimal("0"),
        wallet_usdt_after=Decimal(str(model.wallet_usdt_after))
        if model.wallet_usdt_after is not None
        else Decimal("0"),
        wallet_btc_before=Decimal(str(model.wallet_btc_before))
        if model.wallet_btc_before is not None
        else Decimal("0"),
        wallet_btc_after=Decimal(str(model.wallet_btc_after))
        if model.wallet_btc_after is not None
        else Decimal("0"),
    )


class TradeRepository(ITradeRepository):
    """Repositorio de trades simulados sobre PostgreSQL async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, trade: SimulatedTrade) -> SimulatedTrade:
        """Persiste un trade simulado."""
        model = TradeModel(
            id=trade.id,
            opportunity_id=trade.opportunity_id,
            side=trade.side.value,
            exchange=trade.exchange,
            price=trade.price,
            volume_btc=trade.volume_btc,
            fee_usdt=trade.fee_usdt,
            slippage_usdt=trade.slippage_usdt,
            executed_at=trade.executed_at,
            is_partial=trade.is_partial,
            wallet_usdt_before=trade.wallet_usdt_before,
            wallet_usdt_after=trade.wallet_usdt_after,
            wallet_btc_before=trade.wallet_btc_before,
            wallet_btc_after=trade.wallet_btc_after,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_by_opportunity(self, opportunity_id: uuid.UUID) -> list[SimulatedTrade]:
        """Lista trades de una oportunidad específica."""
        result = await self._session.execute(
            select(TradeModel)
            .where(TradeModel.opportunity_id == opportunity_id)
            .order_by(TradeModel.executed_at.desc())
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_recent(self, limit: int = 100) -> list[SimulatedTrade]:
        """Lista trades más recientes."""
        result = await self._session.execute(
            select(TradeModel).order_by(TradeModel.executed_at.desc()).limit(limit)
        )
        return [_to_entity(m) for m in result.scalars().all()]
