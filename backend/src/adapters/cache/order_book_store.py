"""
OrderBookStore — implementación Redis con TTL de 10 segundos.

El order book se serializa como JSON en Redis con clave:
  orderbook:{exchange}:{symbol}

TTL de 10s: si el exchange deja de enviar datos, el order book expira
y is_stale=True se activa para alertar al motor de arbitraje.
"""

import json
from datetime import datetime
from decimal import Decimal

import structlog
from redis.asyncio import Redis

from core.entities.order_book import OrderBook, OrderBookLevel
from ports.order_book_store_port import IOrderBookStore

logger = structlog.get_logger(__name__)

_TTL_SECONDS = 10
_KEY_PREFIX = "orderbook"
_KNOWN_EXCHANGES = ["binance", "bybit", "kraken"]


class RedisOrderBookStore(IOrderBookStore):
    """Store de order books en Redis con TTL de 10 segundos."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, exchange: str, symbol: str) -> str:
        # Normalizar símbolo para clave Redis: BTC/USDT → BTC_USDT
        safe_symbol = symbol.replace("/", "_")
        return f"{_KEY_PREFIX}:{exchange}:{safe_symbol}"

    async def save(self, order_book: OrderBook) -> None:
        """Serializa y guarda el order book con TTL de 10 segundos."""
        payload = {
            "exchange": order_book.exchange,
            "symbol": order_book.symbol,
            "ask_price": str(order_book.best_ask.price),
            "ask_qty": str(order_book.best_ask.quantity),
            "bid_price": str(order_book.best_bid.price),
            "bid_qty": str(order_book.best_bid.quantity),
            "timestamp": order_book.timestamp.isoformat(),
        }
        key = self._key(order_book.exchange, order_book.symbol)
        await self._redis.setex(key, _TTL_SECONDS, json.dumps(payload))

    async def get(self, exchange: str, symbol: str) -> OrderBook | None:
        """Recupera el order book. Retorna None si no existe o expiró."""
        key = self._key(exchange, symbol)
        raw = await self._redis.get(key)
        if raw is None:
            return None

        data = json.loads(raw)
        # Verificar TTL restante para marcar como stale si está cerca de expirar
        ttl = await self._redis.ttl(key)
        is_stale = ttl <= 2  # últimos 2 segundos del TTL → stale

        return OrderBook(
            exchange=data["exchange"],
            symbol=data["symbol"],
            best_ask=OrderBookLevel(
                price=Decimal(data["ask_price"]),
                quantity=Decimal(data["ask_qty"]),
            ),
            best_bid=OrderBookLevel(
                price=Decimal(data["bid_price"]),
                quantity=Decimal(data["bid_qty"]),
            ),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            is_stale=is_stale,
        )

    async def get_all_exchanges(self, symbol: str) -> list[OrderBook]:
        """Retorna order books de todos los exchanges para un símbolo."""
        order_books: list[OrderBook] = []
        for exchange in _KNOWN_EXCHANGES:
            ob = await self.get(exchange, symbol)
            if ob is not None:
                order_books.append(ob)
        return order_books
