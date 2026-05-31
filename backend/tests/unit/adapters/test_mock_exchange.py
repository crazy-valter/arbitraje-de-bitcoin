"""Tests para MockExchangeAdapter y escenarios mock."""

import asyncio
import unittest.mock as mock
from decimal import Decimal

import pytest

from adapters.exchanges.mock_exchange import MockExchangeAdapter
from adapters.exchanges.mock_scenarios import (
    SPREAD_BELOW_THRESHOLD,
    SPREAD_HIGH,
    VOLATILE,
)


@pytest.mark.asyncio
async def test_mock_emits_orderbook_with_scenario_prices() -> None:
    """Verifica que el adaptador emite un OrderBook con precios coherentes."""
    adapter = MockExchangeAdapter("binance", SPREAD_HIGH)
    with mock.patch("asyncio.sleep", return_value=None):
        book = await adapter.watch_order_book("BTC/USDT")

    assert book.exchange == "binance"
    # binance premium=0 → ask ≈ base_price + 0.50 = 97000.50
    assert book.best_ask.price > Decimal("96000")
    assert book.best_bid.price < book.best_ask.price


@pytest.mark.asyncio
async def test_spread_high_generates_profit() -> None:
    """Verifica que SPREAD_HIGH con Binance ask y Bybit bid genera profit neto > 0."""
    with mock.patch("asyncio.sleep", return_value=None):
        binance_book = await MockExchangeAdapter("binance", SPREAD_HIGH).watch_order_book("BTC/USDT")
        bybit_book = await MockExchangeAdapter("bybit", SPREAD_HIGH).watch_order_book("BTC/USDT")

    gross_spread = bybit_book.best_bid.price - binance_book.best_ask.price
    assert gross_spread > Decimal("500"), f"Spread esperado >$500, got {gross_spread}"


@pytest.mark.asyncio
async def test_spread_below_threshold_is_minimal() -> None:
    """Verifica que SPREAD_BELOW_THRESHOLD produce spreads pequeños sin considerar jitter.

    Se parchan asyncio.sleep y random.uniform para hacer el test determinista:
    con jitter=0, bybit.bid = 97009.50, binance.ask = 97000.50 → spread = $9.
    Sin parchear random, el jitter independiente por adaptador puede sumar ±$97,
    haciendo el spread no determinístico y el umbral $20 no fiable.
    """
    with mock.patch("asyncio.sleep", return_value=None), \
         mock.patch("random.uniform", return_value=0.0):
        binance_book = await MockExchangeAdapter("binance", SPREAD_BELOW_THRESHOLD).watch_order_book("BTC/USDT")
        bybit_book = await MockExchangeAdapter("bybit", SPREAD_BELOW_THRESHOLD).watch_order_book("BTC/USDT")

    gross_spread = bybit_book.best_bid.price - binance_book.best_ask.price
    # Con jitter=0: bybit premium=$10 → spread nominal = $10 - $1 = $9
    assert gross_spread < Decimal("20"), f"Spread debería ser pequeño, got {gross_spread}"


@pytest.mark.asyncio
async def test_mock_exchange_connect_sets_connected() -> None:
    """Verifica que connect() marca el adaptador como conectado."""
    adapter = MockExchangeAdapter("kraken", VOLATILE)
    assert adapter.is_connected is False
    await adapter.connect()
    assert adapter.is_connected is True


@pytest.mark.asyncio
async def test_mock_exchange_disconnect_sets_disconnected() -> None:
    """Verifica que disconnect() desmarca la conexión."""
    adapter = MockExchangeAdapter("bybit", VOLATILE)
    await adapter.connect()
    await adapter.disconnect()
    assert adapter.is_connected is False


@pytest.mark.asyncio
async def test_feed_staleness_returns_minus_one_before_first_update() -> None:
    """Verifica que feed_staleness_ms retorna -1 antes del primer order book."""
    adapter = MockExchangeAdapter("binance", SPREAD_HIGH)
    assert adapter.feed_staleness_ms == -1


@pytest.mark.asyncio
async def test_feed_staleness_updates_after_watch() -> None:
    """Verifica que feed_staleness_ms deja de ser -1 tras recibir el primer book."""
    adapter = MockExchangeAdapter("binance", SPREAD_HIGH)
    with mock.patch("asyncio.sleep", return_value=None):
        await adapter.watch_order_book("BTC/USDT")
    assert adapter.feed_staleness_ms >= 0


@pytest.mark.asyncio
async def test_stream_forever_calls_on_update_and_cancels() -> None:
    """Verifica que stream_forever llama a on_update y termina con CancelledError."""
    updates: list[object] = []

    async def collect(book: object) -> None:
        updates.append(book)
        raise asyncio.CancelledError  # cancela después del primer update

    adapter = MockExchangeAdapter("binance", SPREAD_HIGH)
    with mock.patch("asyncio.sleep", return_value=None):
        await adapter.stream_forever("BTC/USDT", collect)

    assert len(updates) == 1


@pytest.mark.asyncio
async def test_orderbook_symbol_is_preserved() -> None:
    """Verifica que el símbolo del OrderBook coincide con el solicitado."""
    adapter = MockExchangeAdapter("binance", SPREAD_MEDIUM := SPREAD_HIGH)
    with mock.patch("asyncio.sleep", return_value=None):
        book = await adapter.watch_order_book("BTC/USDT")
    assert book.symbol == "BTC/USDT"


@pytest.mark.asyncio
async def test_orderbook_volume_matches_scenario() -> None:
    """Verifica que el volumen del OrderBook es el definido en el escenario."""
    adapter = MockExchangeAdapter("binance", SPREAD_HIGH)
    with mock.patch("asyncio.sleep", return_value=None):
        book = await adapter.watch_order_book("BTC/USDT")
    assert book.best_ask.quantity == SPREAD_HIGH.volume_btc
    assert book.best_bid.quantity == SPREAD_HIGH.volume_btc
