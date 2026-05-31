"""
Tests unitarios: FeeCalculator.calculate_fee_breakdown (CHG-009).

Verifica que el metodo retorna la tupla (trading_fee_buy_usdt, trading_fee_sell_usdt)
con precision Decimal correcta para todos los exchanges soportados.
"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from core.services.fee_calculator import FeeCalculator
from ports.config_port import IConfigRepository


@pytest.fixture
def mock_config() -> IConfigRepository:
    """Config mock con fees estandar de referencia."""
    config = AsyncMock(spec=IConfigRepository)
    _fees_buy: dict[str, Decimal] = {
        "binance": Decimal("0.001"),
        "bybit": Decimal("0.001"),
        "kraken": Decimal("0.0026"),
    }
    _fees_sell: dict[str, Decimal] = {
        "binance": Decimal("0.001"),
        "bybit": Decimal("0.001"),
        "kraken": Decimal("0.0026"),
    }
    config.get_fee_buy = AsyncMock(
        side_effect=lambda exchange: _fees_buy.get(exchange, Decimal("0.001"))
    )
    config.get_fee_sell = AsyncMock(
        side_effect=lambda exchange: _fees_sell.get(exchange, Decimal("0.001"))
    )
    return config


@pytest.fixture
def fee_calculator(mock_config: IConfigRepository) -> FeeCalculator:
    return FeeCalculator(config_repo=mock_config)


class TestCalculateFeeBreakdown:
    @pytest.mark.asyncio
    async def test_returns_tuple_of_two_decimals(
        self, fee_calculator: FeeCalculator
    ) -> None:
        """El metodo debe retornar una tupla de exactamente dos Decimals."""
        result = await fee_calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Decimal)
        assert isinstance(result[1], Decimal)

    @pytest.mark.asyncio
    async def test_same_fee_both_exchanges(
        self, fee_calculator: FeeCalculator
    ) -> None:
        """
        Binance (0.10%) y Bybit (0.10%), mismos precios.
        buy_fee  = 0.1 * 70000 * 0.001 = 7.00000000
        sell_fee = 0.1 * 70000 * 0.001 = 7.00000000
        """
        buy_fee, sell_fee = await fee_calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        assert buy_fee == Decimal("7.00000000")
        assert sell_fee == Decimal("7.00000000")

    @pytest.mark.asyncio
    async def test_kraken_higher_fee(self, fee_calculator: FeeCalculator) -> None:
        """
        Comprar en Binance (0.10%), vender en Kraken (0.26%).
        buy_fee  = 0.1 * 70000 * 0.001 = 7.00000000
        sell_fee = 0.1 * 70200 * 0.0026 = 18.25200000
        """
        buy_fee, sell_fee = await fee_calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="kraken",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70200"),
        )
        assert buy_fee == Decimal("7.00000000")
        assert sell_fee == Decimal("18.25200000")

    @pytest.mark.asyncio
    async def test_zero_volume(self, fee_calculator: FeeCalculator) -> None:
        """Con volumen cero ambos fees deben ser exactamente cero."""
        buy_fee, sell_fee = await fee_calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        assert buy_fee == Decimal("0")
        assert sell_fee == Decimal("0")

    @pytest.mark.asyncio
    async def test_sum_equals_total_fees(
        self, fee_calculator: FeeCalculator
    ) -> None:
        """
        La suma del breakdown debe ser igual al total_fees_usdt
        para los mismos parametros.
        """
        buy_exchange = "binance"
        sell_exchange = "kraken"
        volume = Decimal("0.1")
        buy_price = Decimal("70000")
        sell_price = Decimal("70200")

        buy_fee, sell_fee = await fee_calculator.calculate_fee_breakdown(
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            volume_btc=volume,
            buy_price=buy_price,
            sell_price=sell_price,
        )
        total = await fee_calculator.calculate_total_fees_usdt(
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            volume_btc=volume,
            buy_price=buy_price,
            sell_price=sell_price,
        )
        assert buy_fee + sell_fee == total

    @pytest.mark.asyncio
    async def test_buy_uses_fee_buy_sell_uses_fee_sell(self) -> None:
        """
        Verifica que el lado compra usa get_fee_buy y el lado venta usa get_fee_sell.
        """
        config = AsyncMock(spec=IConfigRepository)
        config.get_fee_buy = AsyncMock(return_value=Decimal("0.001"))
        config.get_fee_sell = AsyncMock(return_value=Decimal("0.002"))

        calculator = FeeCalculator(config_repo=config)
        buy_fee, sell_fee = await calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        # buy_fee = 0.1 * 70000 * 0.001 = 7.00
        # sell_fee = 0.1 * 70000 * 0.002 = 14.00
        assert buy_fee == Decimal("7.00000000")
        assert sell_fee == Decimal("14.00000000")

        config.get_fee_buy.assert_called_once_with("binance")
        config.get_fee_sell.assert_called_once_with("bybit")
