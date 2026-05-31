"""
Calculadora de fees para operaciones de arbitraje.

Todos los cálculos usan Decimal con precisión explícita.
Los fees se leen desde IConfigRepository (tabla exchange_fees en DB),
nunca desde constantes hardcodeadas.

Fees de referencia (defaults en DB):
- Binance: 0.10% taker
- Bybit:   0.10% taker
- Kraken:  0.26% taker
"""

from decimal import ROUND_HALF_UP, Decimal

import structlog

from ports.config_port import IConfigRepository

logger = structlog.get_logger(__name__)

# Precisión para redondeo de fees en USDT
_FEE_PRECISION = Decimal("0.00000001")


class FeeCalculator:
    """Calcula fees y costos netos de una operación de arbitraje."""

    def __init__(self, config_repo: IConfigRepository) -> None:
        self._config = config_repo

    async def calculate_total_fees_usdt(
        self,
        buy_exchange: str,
        sell_exchange: str,
        volume_btc: Decimal,
        buy_price: Decimal,
        sell_price: Decimal,
    ) -> Decimal:
        """
        Calcula el total de fees en USDT para la operacion de arbitraje completa.

        Fee compra = volume_btc * buy_price * buy_taker_fee_pct
        Fee venta  = volume_btc * sell_price * sell_taker_fee_pct
        Total      = fee_compra + fee_venta
        """
        buy_fee_pct = await self._config.get_fee_buy(buy_exchange)
        sell_fee_pct = await self._config.get_fee_sell(sell_exchange)

        buy_cost = volume_btc * buy_price
        sell_revenue = volume_btc * sell_price

        fee_buy = (buy_cost * buy_fee_pct).quantize(_FEE_PRECISION, rounding=ROUND_HALF_UP)
        fee_sell = (sell_revenue * sell_fee_pct).quantize(_FEE_PRECISION, rounding=ROUND_HALF_UP)

        total_fees = fee_buy + fee_sell

        logger.debug(
            "fees_calculated",
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_fee_pct=float(buy_fee_pct),
            sell_fee_pct=float(sell_fee_pct),
            fee_buy_usdt=float(fee_buy),
            fee_sell_usdt=float(fee_sell),
            total_fees_usdt=float(total_fees),
        )
        return total_fees

    async def calculate_fee_breakdown(
        self,
        buy_exchange: str,
        sell_exchange: str,
        volume_btc: Decimal,
        buy_price: Decimal,
        sell_price: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Retorna el desglose de fees: (trading_fee_buy_usdt, trading_fee_sell_usdt).

        Permite a la UI mostrar el costo por componente en lugar de un solo total.
        """
        buy_fee_pct = await self._config.get_fee_buy(buy_exchange)
        sell_fee_pct = await self._config.get_fee_sell(sell_exchange)

        buy_cost = volume_btc * buy_price
        sell_revenue = volume_btc * sell_price

        fee_buy = (buy_cost * buy_fee_pct).quantize(_FEE_PRECISION, rounding=ROUND_HALF_UP)
        fee_sell = (sell_revenue * sell_fee_pct).quantize(_FEE_PRECISION, rounding=ROUND_HALF_UP)

        logger.debug(
            "fee_breakdown_calculated",
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            trading_fee_buy_usdt=float(fee_buy),
            trading_fee_sell_usdt=float(fee_sell),
        )
        return fee_buy, fee_sell

    async def calculate_net_profit_usdt(
        self,
        buy_exchange: str,
        sell_exchange: str,
        volume_btc: Decimal,
        buy_price: Decimal,
        sell_price: Decimal,
        slippage_usdt: Decimal,
    ) -> Decimal:
        """
        Calcula el profit neto en USDT descontando fees y slippage.

        gross_profit = (sell_price - buy_price) * volume_btc
        net_profit   = gross_profit - total_fees - slippage
        """
        gross_profit = (sell_price - buy_price) * volume_btc
        total_fees = await self.calculate_total_fees_usdt(
            buy_exchange, sell_exchange, volume_btc, buy_price, sell_price
        )
        net_profit = (gross_profit - total_fees - slippage_usdt).quantize(
            _FEE_PRECISION, rounding=ROUND_HALF_UP
        )
        return net_profit

    @staticmethod
    def calculate_gross_spread_pct(buy_price: Decimal, sell_price: Decimal) -> Decimal:
        """
        Calcula el spread bruto como porcentaje del precio de compra.

        spread_pct = (sell_price - buy_price) / buy_price * 100
        """
        if buy_price == Decimal("0"):
            return Decimal("0")
        spread_pct = (sell_price - buy_price) / buy_price * Decimal("100")
        return spread_pct.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_net_profit_pct(
        net_profit_usdt: Decimal,
        buy_price: Decimal,
        volume_btc: Decimal,
    ) -> Decimal:
        """
        Calcula el profit neto como porcentaje del capital invertido.

        net_profit_pct = net_profit_usdt / (buy_price * volume_btc) * 100
        """
        capital_invested = buy_price * volume_btc
        if capital_invested == Decimal("0"):
            return Decimal("0")
        pct = net_profit_usdt / capital_invested * Decimal("100")
        return pct.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
