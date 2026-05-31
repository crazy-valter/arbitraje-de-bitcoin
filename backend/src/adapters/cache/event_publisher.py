"""
RedisEventPublisher — publicador de eventos SSE via Redis Pub/Sub.

Canal: "sse:events"

Throttling de order books: máximo 1 publicación cada 500ms por exchange
para no saturar el canal SSE con ~30 eventos/segundo de feeds de alta frecuencia.
"""

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from redis.asyncio import Redis

from core.entities.opportunity import ArbitrageOpportunity
from ports.event_publisher_port import IEventPublisher

logger = structlog.get_logger(__name__)

_SSE_CHANNEL = "sse:events"
_ORDERBOOK_THROTTLE_SECONDS = 0.5  # 500ms por exchange


class RedisEventPublisher(IEventPublisher):
    """Publica eventos al canal SSE via Redis Pub/Sub."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        # Throttling: guarda el timestamp del último publish por exchange
        self._last_orderbook_publish: dict[str, float] = {}

    async def publish_orderbook(
        self,
        exchange: str,
        ask: Decimal,
        bid: Decimal,
    ) -> None:
        """
        Publica actualización de order book con throttling de 500ms por exchange.
        Si la última publicación fue hace menos de 500ms, descarta silenciosamente.
        """
        now = asyncio.get_event_loop().time()
        last = self._last_orderbook_publish.get(exchange, 0.0)

        if now - last < _ORDERBOOK_THROTTLE_SECONDS:
            return  # throttle activo — descartar esta actualización

        self._last_orderbook_publish[exchange] = now

        event = {
            "type": "orderbook_update",
            "exchange": exchange,
            "ask": str(ask),
            "bid": str(bid),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self._redis.publish(_SSE_CHANNEL, json.dumps(event))

    async def publish_opportunity(self, opportunity: ArbitrageOpportunity) -> None:
        """Publica una oportunidad detectada al canal SSE."""
        event = {
            "type": "opportunity_detected",
            "id": str(opportunity.id),
            "buy_exchange": opportunity.buy_exchange,
            "sell_exchange": opportunity.sell_exchange,
            "buy_price": str(opportunity.buy_price),
            "sell_price": str(opportunity.sell_price),
            "gross_spread_pct": str(opportunity.gross_spread_pct),
            "total_fees_usdt": str(opportunity.total_fees_usdt),
            "slippage_usdt": str(opportunity.slippage_usdt),
            "net_profit_usdt": str(opportunity.net_profit_usdt),
            "net_profit_pct": str(opportunity.net_profit_pct),
            "max_volume_btc": str(opportunity.max_volume_btc),
            "strategy": opportunity.strategy,
            "score": opportunity.score,
            "status": opportunity.status.value,
            "detected_at": opportunity.detected_at.isoformat(),
        }
        await self._redis.publish(_SSE_CHANNEL, json.dumps(event))

    async def publish_trade_executed(self, trade_data: dict[str, object]) -> None:
        """Publica el resultado de un trade simulado."""
        event = {"type": "trade_simulated", **trade_data}
        await self._redis.publish(_SSE_CHANNEL, json.dumps(event))

    async def publish_wallet_update(
        self,
        exchange: str,
        currency: str,
        balance: Decimal,
    ) -> None:
        """Publica una actualización de balance de wallet."""
        event = {
            "type": "wallet_update",
            "exchange": exchange,
            "currency": currency,
            "balance": str(balance),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self._redis.publish(_SSE_CHANNEL, json.dumps(event))

    async def publish_metrics(self, metrics: dict[str, object]) -> None:
        """Publica métricas agregadas del sistema."""
        event = {"type": "metrics_update", **metrics}
        await self._redis.publish(_SSE_CHANNEL, json.dumps(event))
