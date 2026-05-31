"""
OpportunityRepository — implementación PostgreSQL para IOpportunityRepository.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.models import Opportunity as OpportunityModel
from core.entities.opportunity import ArbitrageOpportunity, OpportunityStatus
from ports.opportunity_repo_port import IOpportunityRepository

logger = structlog.get_logger(__name__)


def _to_entity(model: OpportunityModel) -> ArbitrageOpportunity:
    """Convierte el modelo SQLAlchemy a la entidad del dominio."""
    return ArbitrageOpportunity(
        id=model.id,
        buy_exchange=model.buy_exchange,
        sell_exchange=model.sell_exchange,
        buy_price=Decimal(str(model.buy_price)),
        sell_price=Decimal(str(model.sell_price)),
        gross_spread_pct=Decimal(str(model.gross_spread_pct)),
        total_fees_usdt=Decimal(str(model.total_fees_usdt)),
        slippage_usdt=Decimal(str(model.slippage_usdt)),
        net_profit_usdt=Decimal(str(model.net_profit_usdt)),
        net_profit_pct=Decimal(str(model.net_profit_pct)),
        max_volume_btc=Decimal(str(model.max_volume_btc)),
        strategy=model.strategy,
        score=model.score,
        status=OpportunityStatus(model.status),
        detected_at=model.detected_at,
        executed_at=model.executed_at,
        trading_fee_buy_usdt=Decimal(str(model.trading_fee_buy_usdt))
        if model.trading_fee_buy_usdt is not None
        else Decimal("0"),
        trading_fee_sell_usdt=Decimal(str(model.trading_fee_sell_usdt))
        if model.trading_fee_sell_usdt is not None
        else Decimal("0"),
        withdrawal_fee_usdt=Decimal(str(model.withdrawal_fee_usdt))
        if model.withdrawal_fee_usdt is not None
        else Decimal("0"),
        network_latency_ms=Decimal(str(model.network_latency_ms))
        if model.network_latency_ms is not None
        else Decimal("0"),
    )


class OpportunityRepository(IOpportunityRepository):
    """Repositorio de oportunidades sobre PostgreSQL async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, opportunity: ArbitrageOpportunity) -> ArbitrageOpportunity:
        """Persiste una nueva oportunidad."""
        model = OpportunityModel(
            id=opportunity.id,
            buy_exchange=opportunity.buy_exchange,
            sell_exchange=opportunity.sell_exchange,
            buy_price=opportunity.buy_price,
            sell_price=opportunity.sell_price,
            gross_spread_pct=opportunity.gross_spread_pct,
            total_fees_usdt=opportunity.total_fees_usdt,
            slippage_usdt=opportunity.slippage_usdt,
            net_profit_usdt=opportunity.net_profit_usdt,
            net_profit_pct=opportunity.net_profit_pct,
            max_volume_btc=opportunity.max_volume_btc,
            strategy=opportunity.strategy,
            score=opportunity.score,
            status=opportunity.status.value,
            detected_at=opportunity.detected_at,
            trading_fee_buy_usdt=opportunity.trading_fee_buy_usdt,
            trading_fee_sell_usdt=opportunity.trading_fee_sell_usdt,
            withdrawal_fee_usdt=opportunity.withdrawal_fee_usdt,
            network_latency_ms=opportunity.network_latency_ms,
        )
        try:
            self._session.add(model)
            await self._session.commit()
            await self._session.refresh(model)
            return _to_entity(model)
        except Exception:
            await self._session.rollback()
            raise

    async def update_status(
        self,
        opportunity_id: uuid.UUID,
        status: OpportunityStatus,
    ) -> None:
        """Actualiza el estado de una oportunidad."""
        result = await self._session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            logger.warning("opportunity_not_found", id=str(opportunity_id))
            return
        model.status = status.value
        if status == OpportunityStatus.EXECUTED:
            model.executed_at = datetime.now(UTC)
        await self._session.commit()

    async def get_by_id(self, opportunity_id: uuid.UUID) -> ArbitrageOpportunity | None:
        """Busca una oportunidad por ID."""
        result = await self._session.execute(
            select(OpportunityModel).where(OpportunityModel.id == opportunity_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_recent(
        self,
        limit: int = 100,
        status: OpportunityStatus | None = None,
    ) -> list[ArbitrageOpportunity]:
        """Lista oportunidades recientes ordenadas por detected_at DESC."""
        query = select(OpportunityModel).order_by(
            OpportunityModel.detected_at.desc()
        ).limit(limit)
        if status is not None:
            query = query.where(OpportunityModel.status == status.value)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [_to_entity(m) for m in models]

    async def list_paginated(
        self,
        offset: int,
        limit: int,
        status: list[OpportunityStatus] | None = None,
        buy_exchange: list[str] | None = None,
        sell_exchange: list[str] | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> tuple[list[ArbitrageOpportunity], int]:
        """
        Lista oportunidades con paginacion real y filtros avanzados.
        Retorna (items, total) donde total es el COUNT con los mismos filtros.
        Filtros de status/exchange usan IN para soportar multi-seleccion.
        """
        # Construir filtros base
        filters: list = []
        if status:
            filters.append(OpportunityModel.status.in_([s.value for s in status]))
        if buy_exchange:
            filters.append(OpportunityModel.buy_exchange.in_(buy_exchange))
        if sell_exchange:
            filters.append(OpportunityModel.sell_exchange.in_(sell_exchange))
        if from_dt is not None:
            filters.append(OpportunityModel.detected_at >= from_dt)
        if to_dt is not None:
            filters.append(OpportunityModel.detected_at <= to_dt)

        # COUNT query
        count_query = select(func.count(OpportunityModel.id))
        for f in filters:
            count_query = count_query.where(f)
        count_result = await self._session.execute(count_query)
        total = count_result.scalar_one()

        # Data query
        data_query = (
            select(OpportunityModel)
            .order_by(OpportunityModel.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        for f in filters:
            data_query = data_query.where(f)

        result = await self._session.execute(data_query)
        models = result.scalars().all()
        items = [_to_entity(m) for m in models]
        return items, total

    async def get_total_pnl(self) -> float:
        """Retorna el P&L total acumulado de oportunidades ejecutadas."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(OpportunityModel.net_profit_usdt), 0)).where(
                OpportunityModel.status == OpportunityStatus.EXECUTED.value
            )
        )
        total = result.scalar_one()
        return float(total)
