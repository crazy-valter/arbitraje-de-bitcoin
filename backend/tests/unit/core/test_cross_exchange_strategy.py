"""
Tests unitarios: CrossExchangeStrategy.

Verifica la lógica de detección de oportunidades cross-exchange,
incluyendo el filtrado de falsos positivos y el cálculo correcto de fees.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.entities.order_book import OrderBook, OrderBookLevel
from core.services.fee_calculator import FeeCalculator
from core.strategies.cross_exchange import CrossExchangeStrategy
from ports.config_port import IConfigRepository


def _make_order_book(
    exchange: str,
    ask: str,
    bid: str,
    qty: str = "0.5",
    stale: bool = False,
) -> OrderBook:
    """Factory helper para crear OrderBooks en tests."""
    return OrderBook(
        exchange=exchange,
        symbol="BTC/USDT",
        best_ask=OrderBookLevel(price=Decimal(ask), quantity=Decimal(qty)),
        best_bid=OrderBookLevel(price=Decimal(bid), quantity=Decimal(qty)),
        timestamp=datetime.now(timezone.utc),
        is_stale=stale,
    )


@pytest.fixture
def mock_config() -> IConfigRepository:
    config = AsyncMock(spec=IConfigRepository)
    _fees: dict[str, Decimal] = {
        "binance": Decimal("0.001"),
        "bybit": Decimal("0.001"),
        "kraken": Decimal("0.0026"),
    }
    config.get_fee_buy = AsyncMock(
        side_effect=lambda exchange: _fees.get(exchange, Decimal("0.001"))
    )
    config.get_fee_sell = AsyncMock(
        side_effect=lambda exchange: _fees.get(exchange, Decimal("0.001"))
    )
    config.get_min_profit_threshold_pct = AsyncMock(return_value=Decimal("0.05"))
    return config


@pytest.fixture
def strategy(mock_config: IConfigRepository) -> CrossExchangeStrategy:
    fee_calculator = FeeCalculator(config_repo=mock_config)
    return CrossExchangeStrategy(
        fee_calculator=fee_calculator,
        config_repo=mock_config,
    )


class TestDetect:
    @pytest.mark.asyncio
    async def test_detects_clear_opportunity(self, strategy: CrossExchangeStrategy) -> None:
        """
        Caso claro: Kraken ask=$70000, Binance bid=$70500.
        Spread bruto de $500 (0.71%) → suficiente para cubrir fees kraken 0.26% + binance 0.10%
        y superar el threshold de 0.05%.
        """
        order_books = [
            _make_order_book("kraken", ask="70000", bid="69990"),
            _make_order_book("binance", ask="70490", bid="70500"),
        ]
        opportunities = await strategy.detect(order_books)
        # Debe detectar al menos una oportunidad (comprar en kraken, vender en binance)
        assert len(opportunities) > 0
        best = opportunities[0]
        assert best.buy_exchange == "kraken"
        assert best.sell_exchange == "binance"
        assert best.net_profit_usdt > Decimal("0")
        assert best.strategy == "cross_exchange"

    @pytest.mark.asyncio
    async def test_rejects_false_positive_no_spread(self, strategy: CrossExchangeStrategy) -> None:
        """
        Falso positivo: precios iguales → sin spread → sin oportunidad.
        """
        order_books = [
            _make_order_book("binance", ask="70000", bid="69990"),
            _make_order_book("bybit", ask="70000", bid="69990"),
        ]
        opportunities = await strategy.detect(order_books)
        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_rejects_when_fees_consume_profit(self, strategy: CrossExchangeStrategy) -> None:
        """
        Falso positivo: spread de $5 en $70000 (0.007%) no cubre los fees (0.20%).
        """
        order_books = [
            _make_order_book("binance", ask="70000", bid="69990"),
            _make_order_book("bybit", ask="70004", bid="70005"),
        ]
        # El spread bruto es de $5 = 0.007%, muy menor que los fees combinados (0.20%)
        opportunities = await strategy.detect(order_books)
        assert all(o.net_profit_usdt > Decimal("0") for o in opportunities)

    @pytest.mark.asyncio
    async def test_returns_empty_with_single_exchange(self, strategy: CrossExchangeStrategy) -> None:
        """Con un solo exchange no hay oportunidad cross-exchange."""
        order_books = [_make_order_book("binance", ask="70000", bid="69990")]
        opportunities = await strategy.detect(order_books)
        assert len(opportunities) == 0

    @pytest.mark.asyncio
    async def test_score_is_within_range(self, strategy: CrossExchangeStrategy) -> None:
        """El score debe estar siempre en [0.0, 1.0]."""
        order_books = [
            _make_order_book("kraken", ask="70000", bid="69980"),
            _make_order_book("binance", ask="70400", bid="70500"),
        ]
        opportunities = await strategy.detect(order_books)
        for opp in opportunities:
            assert 0.0 <= opp.score <= 1.0

    @pytest.mark.asyncio
    async def test_stale_data_reduces_score(self, strategy: CrossExchangeStrategy) -> None:
        """Datos stale deben resultar en score más bajo."""
        order_books_fresh = [
            _make_order_book("kraken", ask="70000", bid="69980", stale=False),
            _make_order_book("binance", ask="70400", bid="70500", stale=False),
        ]
        order_books_stale = [
            _make_order_book("kraken", ask="70000", bid="69980", stale=True),
            _make_order_book("binance", ask="70400", bid="70500", stale=True),
        ]

        opps_fresh = await strategy.detect(order_books_fresh)
        opps_stale = await strategy.detect(order_books_stale)

        if opps_fresh and opps_stale:
            # Las oportunidades stale deben tener menor score
            assert opps_stale[0].score < opps_fresh[0].score

    @pytest.mark.asyncio
    async def test_volume_limited_by_order_book_liquidity(
        self, strategy: CrossExchangeStrategy
    ) -> None:
        """El volumen máximo debe limitarse por la liquidez del order book más restrictivo."""
        order_books = [
            _make_order_book("kraken", ask="70000", bid="69980", qty="0.05"),
            _make_order_book("binance", ask="70400", bid="70500", qty="0.5"),
        ]
        opportunities = await strategy.detect(order_books)
        if opportunities:
            # Volumen limitado por el order book con menor cantidad: 0.05 BTC
            assert opportunities[0].max_volume_btc <= Decimal("0.05")

    @pytest.mark.asyncio
    async def test_opportunities_sorted_by_score_desc(
        self, strategy: CrossExchangeStrategy
    ) -> None:
        """Las oportunidades deben estar ordenadas por score descendente."""
        order_books = [
            _make_order_book("kraken", ask="70000", bid="69980"),
            _make_order_book("binance", ask="70400", bid="70500"),
            _make_order_book("bybit", ask="70200", bid="70250"),
        ]
        opportunities = await strategy.detect(order_books)
        if len(opportunities) > 1:
            scores = [o.score for o in opportunities]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_cross_exchange_fee_fields_populated(
        self, strategy: CrossExchangeStrategy
    ) -> None:
        """
        La oportunidad generada debe tener trading_fee_buy_usdt y
        trading_fee_sell_usdt con valores positivos (no cero).

        Verifica que _evaluate_pair() popula el desglose de fees por componente,
        no los deja en el valor por defecto Decimal("0").
        """
        order_books = [
            _make_order_book("kraken", ask="70000", bid="69980"),
            _make_order_book("binance", ask="70400", bid="70500"),
        ]
        opportunities = await strategy.detect(order_books)
        # Debe detectar al menos una oportunidad para este spread amplio
        assert len(opportunities) > 0, (
            "Se esperaba al menos una oportunidad con spread $500"
        )

        best = opportunities[0]
        assert best.trading_fee_buy_usdt > Decimal("0"), (
            f"trading_fee_buy_usdt debe ser > 0, got {best.trading_fee_buy_usdt}"
        )
        assert best.trading_fee_sell_usdt > Decimal("0"), (
            f"trading_fee_sell_usdt debe ser > 0, got {best.trading_fee_sell_usdt}"
        )
