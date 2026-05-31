"""
CrossExchangeStrategy — Fase 1 (activa por defecto).

Detecta oportunidades de arbitraje comprando BTC en el exchange más barato
y vendiéndolo en el más caro, descontando fees y slippage.

Algoritmo:
1. Tomar todos los pares de exchanges con order books disponibles
2. Para cada par (exchange_A, exchange_B):
   - Si ask_A < bid_B → posible compra en A, venta en B
   - Si ask_B < bid_A → posible compra en B, venta en A
3. Calcular gross_spread, fees, slippage y net_profit
4. Filtrar por threshold mínimo de profit
5. Calcular score y retornar oportunidades ordenadas por score DESC
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations

import structlog

from core.entities.opportunity import ArbitrageOpportunity
from core.entities.order_book import OrderBook
from core.services.fee_calculator import FeeCalculator
from core.services.scoring import calculate_score
from core.strategies.base import ArbitrageStrategy
from ports.config_port import IConfigRepository

logger = structlog.get_logger(__name__)

# Slippage estimado: 0.05% por lado
_SLIPPAGE_PCT = Decimal("0.0005")
# Volumen de referencia para cálculo de oportunidad (limitado por liquidez del book)
_MAX_VOLUME_LIMIT_BTC = Decimal("0.1")  # máx 0.1 BTC por operación como safety cap
_PRICE_PRECISION = Decimal("0.00000001")


class CrossExchangeStrategy(ArbitrageStrategy):
    """Estrategia de arbitraje cross-exchange (compra-venta entre exchanges)."""

    def __init__(
        self,
        fee_calculator: FeeCalculator,
        config_repo: IConfigRepository,
    ) -> None:
        self._fee_calc = fee_calculator
        self._config = config_repo

    @property
    def strategy_id(self) -> str:
        return "cross_exchange"

    async def detect(
        self,
        order_books: list[OrderBook],
    ) -> list[ArbitrageOpportunity]:
        """
        Detecta oportunidades cross-exchange entre todos los pares de exchanges.
        """
        if len(order_books) < 2:
            return []

        threshold_pct = await self._config.get_min_profit_threshold_pct()
        opportunities: list[ArbitrageOpportunity] = []

        for ob_a, ob_b in combinations(order_books, 2):
            # Dirección 1: comprar en A, vender en B
            opp = await self._evaluate_pair(
                buy_ob=ob_a,
                sell_ob=ob_b,
                threshold_pct=threshold_pct,
            )
            if opp:
                opportunities.append(opp)

            # Dirección 2: comprar en B, vender en A
            opp = await self._evaluate_pair(
                buy_ob=ob_b,
                sell_ob=ob_a,
                threshold_pct=threshold_pct,
            )
            if opp:
                opportunities.append(opp)

        # Ordenar por score descendente (mejor oportunidad primero)
        opportunities.sort(key=lambda o: o.score, reverse=True)
        return opportunities

    async def _evaluate_pair(
        self,
        buy_ob: OrderBook,
        sell_ob: OrderBook,
        threshold_pct: Decimal,
    ) -> ArbitrageOpportunity | None:
        """
        Evalúa si comprar en buy_ob y vender en sell_ob es rentable.

        La compra se ejecuta al ask de buy_ob.
        La venta se ejecuta al bid de sell_ob.
        Si el spread bruto es negativo, descartamos inmediatamente.
        """
        buy_price = buy_ob.best_ask.price
        sell_price = sell_ob.best_bid.price

        # Spread bruto: si es negativo o cero no hay arbitraje
        if sell_price <= buy_price:
            return None

        # Volumen limitado por la liquidez del order book y el cap de seguridad
        max_volume_btc = min(
            buy_ob.best_ask.quantity,
            sell_ob.best_bid.quantity,
            _MAX_VOLUME_LIMIT_BTC,
        ).quantize(_PRICE_PRECISION, rounding=ROUND_HALF_UP)

        if max_volume_btc <= Decimal("0"):
            return None

        # Slippage estimado
        avg_price = (buy_price + sell_price) / Decimal("2")
        slippage_usdt = (_SLIPPAGE_PCT * avg_price * max_volume_btc).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )

        # Fees
        total_fees_usdt = await self._fee_calc.calculate_total_fees_usdt(
            buy_exchange=buy_ob.exchange,
            sell_exchange=sell_ob.exchange,
            volume_btc=max_volume_btc,
            buy_price=buy_price,
            sell_price=sell_price,
        )

        # Desglose de fees por componente (CHG-009)
        trading_fee_buy_usdt, trading_fee_sell_usdt = (
            await self._fee_calc.calculate_fee_breakdown(
                buy_exchange=buy_ob.exchange,
                sell_exchange=sell_ob.exchange,
                volume_btc=max_volume_btc,
                buy_price=buy_price,
                sell_price=sell_price,
            )
        )

        # Profit neto
        gross_profit = (sell_price - buy_price) * max_volume_btc
        net_profit_usdt = (gross_profit - total_fees_usdt - slippage_usdt).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )

        # Filtrar falsos positivos
        if net_profit_usdt <= Decimal("0"):
            return None

        # Calcular métricas derivadas
        gross_spread_pct = FeeCalculator.calculate_gross_spread_pct(buy_price, sell_price)
        net_profit_pct = FeeCalculator.calculate_net_profit_pct(
            net_profit_usdt, buy_price, max_volume_btc
        )

        # Filtrar por threshold mínimo
        if net_profit_pct < threshold_pct:
            return None

        # Score de prioridad
        has_stale = buy_ob.is_stale or sell_ob.is_stale
        score = calculate_score(
            net_profit_pct=net_profit_pct,
            max_volume_btc=max_volume_btc,
            gross_spread_pct=gross_spread_pct,
            has_stale_data=has_stale,
        )

        # Latencia de red: el peor caso entre los dos order books; -1 indica sin datos → 0
        network_latency_ms = Decimal(max(0, buy_ob.staleness_ms, sell_ob.staleness_ms))

        opportunity = ArbitrageOpportunity(
            buy_exchange=buy_ob.exchange,
            sell_exchange=sell_ob.exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            gross_spread_pct=gross_spread_pct,
            total_fees_usdt=total_fees_usdt,
            slippage_usdt=slippage_usdt,
            net_profit_usdt=net_profit_usdt,
            net_profit_pct=net_profit_pct,
            max_volume_btc=max_volume_btc,
            strategy=self.strategy_id,
            score=score,
            detected_at=datetime.now(UTC),
            trading_fee_buy_usdt=trading_fee_buy_usdt,
            trading_fee_sell_usdt=trading_fee_sell_usdt,
            network_latency_ms=network_latency_ms,
        )

        logger.info(
            "opportunity_detected",
            exchange_buy=buy_ob.exchange,
            exchange_sell=sell_ob.exchange,
            net_profit_pct=float(net_profit_pct),
            net_profit_usdt=float(net_profit_usdt),
            score=score,
        )
        return opportunity
