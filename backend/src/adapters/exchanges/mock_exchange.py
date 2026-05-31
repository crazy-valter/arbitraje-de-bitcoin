"""
MockExchangeAdapter — adaptador mock que genera order books sintéticos.

Implementa IExchangePort directamente sin ccxt.pro.
Solo usar con Modo Demo activo — nunca en producción.
"""

import asyncio
import random
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog

from adapters.exchanges.mock_scenarios import MockScenario
from core.entities.order_book import OrderBook, OrderBookLevel
from ports.exchange_port import IExchangePort

logger = structlog.get_logger(__name__)


class MockExchangeAdapter(IExchangePort):
    """Adaptador mock — genera order books sintéticos. Solo usar con Modo Demo activo."""

    def __init__(self, exchange_id: str, scenario: MockScenario) -> None:
        self._exchange_id = exchange_id
        self._scenario = scenario
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
        """Milisegundos desde la última actualización recibida. -1 si nunca hubo dato."""
        if self._last_update == 0.0:
            return -1
        return int((asyncio.get_event_loop().time() - self._last_update) * 1000)

    async def connect(self) -> None:
        """Marca el adaptador como conectado y emite warning de modo mock."""
        self._connected = True
        logger.warning(
            "mock_exchange_connected",
            exchange=self._exchange_id,
            scenario=self._scenario.name,
        )

    async def disconnect(self) -> None:
        """Desconecta el adaptador mock."""
        self._connected = False
        logger.info("mock_exchange_disconnected", exchange=self._exchange_id)

    async def watch_order_book(self, symbol: str) -> OrderBook:
        """
        Genera un order book sintético basado en el escenario configurado.

        1. Espera el intervalo del escenario
        2. Aplica jitter aleatorio al precio base
        3. Calcula ask y bid con spread fijo de $1.00
        """
        await asyncio.sleep(self._scenario.interval_seconds)

        base_price = self._scenario.base_price
        premium = self._scenario.bid_premiums.get(self._exchange_id, Decimal("0"))
        jitter_pct = self._scenario.jitter_pct

        # Jitter: variación aleatoria dentro del rango ±jitter_pct%
        raw_jitter = random.uniform(-jitter_pct / 100, jitter_pct / 100)
        jitter = Decimal(str(raw_jitter)) * base_price

        price_mid = base_price + premium + jitter
        ask = price_mid + Decimal("0.50")
        bid = price_mid - Decimal("0.50")

        self._last_update = asyncio.get_event_loop().time()
        self._connected = True

        return OrderBook(
            exchange=self._exchange_id,
            symbol=symbol,
            best_ask=OrderBookLevel(price=ask, quantity=self._scenario.volume_btc),
            best_bid=OrderBookLevel(price=bid, quantity=self._scenario.volume_btc),
            timestamp=datetime.now(UTC),
        )

    async def stream_forever(
        self,
        symbol: str,
        on_update: Any,  # Callable[[OrderBook], Awaitable[None]]
    ) -> None:
        """
        Loop infinito que genera order books sintéticos y llama a on_update.
        Sale limpiamente al recibir CancelledError.
        """
        await self.connect()
        while True:
            try:
                order_book = await self.watch_order_book(symbol)
                await on_update(order_book)
            except asyncio.CancelledError:
                logger.info("mock_exchange_stream_cancelled", exchange=self._exchange_id)
                break
            except Exception as exc:
                logger.error(
                    "mock_exchange_stream_error",
                    exchange=self._exchange_id,
                    error=str(exc),
                )
                await asyncio.sleep(1)
