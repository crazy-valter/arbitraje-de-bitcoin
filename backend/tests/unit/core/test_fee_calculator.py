"""
Tests unitarios: FeeCalculator.

Verifica que los fees se calculen correctamente con Decimal
para los tres exchanges soportados.
"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from core.services.fee_calculator import FeeCalculator
from ports.config_port import IConfigRepository


@pytest.fixture
def mock_config() -> IConfigRepository:
    """Config mock con fees estándar de referencia."""
    config = AsyncMock(spec=IConfigRepository)
    # Binance: 0.10%, Bybit: 0.10%, Kraken: 0.26%
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
    config.get_min_profit_threshold_pct = AsyncMock(return_value=Decimal("0.15"))
    return config


@pytest.fixture
def fee_calculator(mock_config: IConfigRepository) -> FeeCalculator:
    return FeeCalculator(config_repo=mock_config)


class TestCalculateTotalFeesUsdt:
    @pytest.mark.asyncio
    async def test_same_fee_both_exchanges(self, fee_calculator: FeeCalculator) -> None:
        """
        Caso: comprar en Binance (0.10%), vender en Bybit (0.10%).
        0.1 BTC × $70000 × 0.001 = $7.00 por lado → total $14.00
        """
        fees = await fee_calculator.calculate_total_fees_usdt(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        assert fees == Decimal("14.00000000")

    @pytest.mark.asyncio
    async def test_kraken_higher_fee(self, fee_calculator: FeeCalculator) -> None:
        """
        Caso: comprar en Binance (0.10%), vender en Kraken (0.26%).
        Compra: 0.1 × 70000 × 0.001 = 7.00
        Venta:  0.1 × 70200 × 0.0026 = 18.252
        Total: 25.252
        """
        fees = await fee_calculator.calculate_total_fees_usdt(
            buy_exchange="binance",
            sell_exchange="kraken",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70200"),
        )
        # buy_fee = 0.1 * 70000 * 0.001 = 7.00
        # sell_fee = 0.1 * 70200 * 0.0026 = 18.252
        expected_buy_fee = Decimal("7.00000000")
        expected_sell_fee = Decimal("18.25200000")
        assert fees == expected_buy_fee + expected_sell_fee

    @pytest.mark.asyncio
    async def test_zero_volume(self, fee_calculator: FeeCalculator) -> None:
        """Fee con volumen cero debe dar exactamente cero."""
        fees = await fee_calculator.calculate_total_fees_usdt(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        assert fees == Decimal("0")

    @pytest.mark.asyncio
    async def test_precision_with_decimal(self, fee_calculator: FeeCalculator) -> None:
        """Los fees no deben usar float internamente — verificar precisión Decimal."""
        fees = await fee_calculator.calculate_total_fees_usdt(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.00100000"),
            buy_price=Decimal("69999.99"),
            sell_price=Decimal("70001.01"),
        )
        # Resultado debe ser Decimal, no float
        assert isinstance(fees, Decimal)
        # Y debe ser positivo
        assert fees > Decimal("0")

    @pytest.mark.asyncio
    async def test_buy_uses_fee_buy_sell_uses_fee_sell(self) -> None:
        """
        Verifica que el lado compra usa get_fee_buy y el lado venta usa get_fee_sell.

        Con fee_buy=0.001 en binance y fee_sell=0.002 en bybit:
        Compra: 0.1 BTC × $70000 × 0.001 = $7.00
        Venta:  0.1 BTC × $70000 × 0.002 = $14.00
        Total: $21.00
        """
        config = AsyncMock(spec=IConfigRepository)
        config.get_fee_buy = AsyncMock(return_value=Decimal("0.001"))   # compra: 0.10%
        config.get_fee_sell = AsyncMock(return_value=Decimal("0.002"))  # venta: 0.20%

        calculator = FeeCalculator(config_repo=config)
        fees = await calculator.calculate_total_fees_usdt(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )

        # buy_fee = 0.1 × 70000 × 0.001 = 7.00
        # sell_fee = 0.1 × 70000 × 0.002 = 14.00
        # total = 21.00
        assert fees == Decimal("21.00000000")

        # Verificar que se llamó al método correcto para cada lado
        config.get_fee_buy.assert_called_once_with("binance")
        config.get_fee_sell.assert_called_once_with("bybit")


class TestCalculateFeeBreakdown:
    @pytest.mark.asyncio
    async def test_fee_calculator_breakdown_binance_kraken(self) -> None:
        """
        Desglose de fees: Binance buy 0.10%, Kraken sell 0.26%.
        Volumen: 0.1 BTC, precio compra: $70000, precio venta: $70300.

        fee_buy  = 0.1 × 70000 × 0.001  = $7.00
        fee_sell = 0.1 × 70300 × 0.0026 = $18.278
        Se verifica que fee_buy < fee_sell (Kraken cobra más que Binance).
        """
        config = AsyncMock(spec=IConfigRepository)
        config.get_fee_buy = AsyncMock(return_value=Decimal("0.001"))    # Binance 0.10%
        config.get_fee_sell = AsyncMock(return_value=Decimal("0.0026"))  # Kraken 0.26%

        calculator = FeeCalculator(config_repo=config)
        fee_buy, fee_sell = await calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="kraken",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70300"),
        )

        assert fee_buy == Decimal("7.00000000"), (
            f"fee_buy esperado $7.00, got {fee_buy}"
        )
        assert fee_sell == Decimal("18.27800000"), (
            f"fee_sell esperado $18.278, got {fee_sell}"
        )
        assert fee_buy < fee_sell, (
            "Kraken (0.26%) debe cobrar más que Binance (0.10%)"
        )

    @pytest.mark.asyncio
    async def test_fee_calculator_breakdown_zero_volume(self) -> None:
        """
        Con volumen cero, ambos fees del desglose deben ser exactamente cero
        sin lanzar ninguna excepción.
        """
        config = AsyncMock(spec=IConfigRepository)
        config.get_fee_buy = AsyncMock(return_value=Decimal("0.001"))
        config.get_fee_sell = AsyncMock(return_value=Decimal("0.0026"))

        calculator = FeeCalculator(config_repo=config)
        fee_buy, fee_sell = await calculator.calculate_fee_breakdown(
            buy_exchange="binance",
            sell_exchange="kraken",
            volume_btc=Decimal("0"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70300"),
        )

        assert fee_buy == Decimal("0"), f"fee_buy debe ser 0 con volumen 0, got {fee_buy}"
        assert fee_sell == Decimal("0"), f"fee_sell debe ser 0 con volumen 0, got {fee_sell}"


class TestCalculateGrossSpreadPct:
    def test_positive_spread(self) -> None:
        """Spread bruto positivo cuando sell > buy."""
        spread = FeeCalculator.calculate_gross_spread_pct(
            buy_price=Decimal("70000"),
            sell_price=Decimal("70350"),
        )
        # (70350 - 70000) / 70000 * 100 = 0.5%
        assert spread == Decimal("0.500000")

    def test_zero_spread(self) -> None:
        """Spread cero cuando precios son iguales."""
        spread = FeeCalculator.calculate_gross_spread_pct(
            buy_price=Decimal("70000"),
            sell_price=Decimal("70000"),
        )
        assert spread == Decimal("0.000000")

    def test_zero_buy_price(self) -> None:
        """Buy price cero retorna cero para evitar división por cero."""
        spread = FeeCalculator.calculate_gross_spread_pct(
            buy_price=Decimal("0"),
            sell_price=Decimal("70000"),
        )
        assert spread == Decimal("0")


class TestCalculateNetProfitPct:
    def test_net_profit_pct_calculation(self) -> None:
        """
        Profit neto de $10.50 sobre un capital de $7000 (0.1 BTC × $70000) = 0.15%
        """
        pct = FeeCalculator.calculate_net_profit_pct(
            net_profit_usdt=Decimal("10.50"),
            buy_price=Decimal("70000"),
            volume_btc=Decimal("0.1"),
        )
        # 10.50 / 7000 * 100 = 0.15%
        assert pct == Decimal("0.150000")

    def test_zero_capital(self) -> None:
        """Capital cero retorna cero para evitar división por cero."""
        pct = FeeCalculator.calculate_net_profit_pct(
            net_profit_usdt=Decimal("10"),
            buy_price=Decimal("0"),
            volume_btc=Decimal("0.1"),
        )
        assert pct == Decimal("0")

    @pytest.mark.asyncio
    async def test_net_profit_with_fees_and_slippage(self, fee_calculator: FeeCalculator) -> None:
        """
        Integración: profit neto debe ser menor que el gross profit por fees + slippage.

        buy_fee  = 0.1 × 70000 × 0.001 = 7.00000000
        sell_fee = 0.1 × 70300 × 0.001 = 7.03000000
        total_fees = 14.03000000
        gross = (70300 - 70000) × 0.1 = 30 USDT
        net = 30 - 14.03 - 2 = 13.97 USDT
        """
        slippage = Decimal("2.00")
        net = await fee_calculator.calculate_net_profit_usdt(
            buy_exchange="binance",
            sell_exchange="bybit",
            volume_btc=Decimal("0.1"),
            buy_price=Decimal("70000"),
            sell_price=Decimal("70300"),
            slippage_usdt=slippage,
        )
        # Profit neto debe ser positivo y menor que el gross
        assert net > Decimal("0")
        assert net < Decimal("30")
        # Valor preciso: 30 - 14.03 - 2 = 13.97
        assert net == Decimal("13.97000000")
