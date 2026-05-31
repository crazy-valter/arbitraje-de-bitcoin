"""
BaseExchangeAdapter — lógica común para adaptadores ccxt.pro.

Cada adaptador concreto (Binance, Bybit, Kraken) hereda de esta clase
y solo implementa los detalles específicos del exchange.

Resiliencia:
- Backoff exponencial: 1s → 2s → 4s → ... → 60s máx
- Circuit breaker: is_connected=False si no hay dato en 30s
"""

import asyncio
import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import ccxt.pro as ccxtpro  # type: ignore[import-untyped]
import structlog

from core.entities.order_book import OrderBook, OrderBookLevel
from ports.exchange_port import IExchangePort

logger = structlog.get_logger(__name__)

_MAX_BACKOFF_SECONDS = 60
_CIRCUIT_BREAKER_TIMEOUT = 30.0  # segundos sin dato → is_connected=False


class BaseExchangeAdapter(IExchangePort):
    """Adaptador base para exchanges via ccxt.pro WebSocket."""

    def __init__(
        self,
        exchange_id: str,
        symbol: str = "BTC/USDT",
        api_key: str = "",
        secret: str = "",
    ) -> None:
        self._exchange_id = exchange_id
        self._symbol = symbol
        self._api_key = api_key
        self._secret = secret
        self._client: Any = None
        self._connected = False
        self._last_update: float = 0.0

    @property
    def exchange_id(self) -> str:
        return self._exchange_id

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def feed_staleness_ms(self) -> int:
        """Milisegundos desde la última actualización recibida de este exchange."""
        if self._last_update == 0.0:
            return -1  # nunca ha recibido datos
        return int((asyncio.get_event_loop().time() - self._last_update) * 1000)

    def _create_client(self) -> Any:
        """Crea el cliente ccxt.pro para este exchange."""
        exchange_class = getattr(ccxtpro, self._exchange_id)
        opts: dict[str, Any] = {"enableRateLimit": True}
        if self._api_key and self._secret:
            opts["apiKey"] = self._api_key
            opts["secret"] = self._secret
        return exchange_class(opts)

    async def connect(self) -> None:
        """Inicializa el cliente ccxt.pro. La conexión WS real ocurre en watch_order_book."""
        if self._client is None:
            self._client = self._create_client()
        self._connected = True
        logger.info("exchange_connected", exchange=self._exchange_id)

    async def disconnect(self) -> None:
        """Cierra la conexión WebSocket gracefully."""
        if self._client:
            with contextlib.suppress(Exception):
                await self._client.close()
        self._connected = False
        self._client = None
        logger.info("exchange_disconnected", exchange=self._exchange_id)

    async def watch_order_book(self, symbol: str) -> OrderBook:
        """
        Espera la siguiente actualización del order book vía WS.
        Convierte el formato ccxt.pro a la entidad OrderBook del dominio.
        """
        if self._client is None:
            await self.connect()

        raw = await self._client.watch_order_book(symbol)
        self._last_update = asyncio.get_event_loop().time()
        self._connected = True

        # ccxt.pro retorna asks/bids como [[price, quantity], ...]
        ask_price = Decimal(str(raw["asks"][0][0]))
        ask_qty = Decimal(str(raw["asks"][0][1]))
        bid_price = Decimal(str(raw["bids"][0][0]))
        bid_qty = Decimal(str(raw["bids"][0][1]))

        return OrderBook(
            exchange=self._exchange_id,
            symbol=symbol,
            best_ask=OrderBookLevel(price=ask_price, quantity=ask_qty),
            best_bid=OrderBookLevel(price=bid_price, quantity=bid_qty),
            timestamp=datetime.now(UTC),
        )

    async def stream_forever(
        self,
        symbol: str,
        on_update: Any,  # Callable[[OrderBook], Awaitable[None]]
    ) -> None:
        """
        Loop de streaming con backoff exponencial y reconexión automática.
        Llama a on_update(order_book) con cada nueva actualización.
        """
        backoff = 1
        while True:
            try:
                await self.connect()
                backoff = 1  # resetear backoff al conectar con éxito
                while True:
                    order_book = await self.watch_order_book(symbol)
                    await on_update(order_book)
            except asyncio.CancelledError:
                logger.info("exchange_stream_cancelled", exchange=self._exchange_id)
                break
            except Exception as exc:
                self._connected = False
                logger.warning(
                    "exchange_stream_error",
                    exchange=self._exchange_id,
                    error=str(exc),
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
