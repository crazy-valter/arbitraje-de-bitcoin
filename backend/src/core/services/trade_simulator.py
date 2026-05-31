"""
Simulador de trades con wallet tracking, slippage y órdenes parciales.

El simulador:
1. Calcula el volumen ejecutable como el MÍNIMO entre liquidez (max_volume_btc),
   saldo USDT financiable del comprador y saldo BTC disponible del vendedor
2. Aplica slippage al precio de ejecución (mercado real es peor que el book)
3. Debita el capital del exchange comprador
4. Acredita el BTC al exchange comprador
5. Debita el BTC del exchange vendedor
6. Acredita el USDT al exchange vendedor
7. Registra los trades en DB y actualiza wallets

Órdenes parciales (RF-05 / CHG-014):
Si el saldo de wallet no cubre el volumen completo (USDT del comprador o BTC del
vendedor), se ejecuta una orden PARCIAL por el máximo volumen viable. Los fees,
slippage y profit se recalculan sobre el volumen REAL ejecutado, nunca prorrateados
linealmente cuando hay un FeeCalculator disponible (única fuente de verdad).

Slippage: 0.05% del valor por defecto (configurable).
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

import structlog

from core.entities.opportunity import ArbitrageOpportunity, OpportunityStatus
from core.entities.trade import SimulatedTrade, TradeSide, TradeStatus
from core.services.fee_calculator import FeeCalculator
from ports.event_publisher_port import IEventPublisher
from ports.opportunity_repo_port import IOpportunityRepository
from ports.trade_repo_port import ITradeRepository
from ports.wallet_repo_port import IWalletRepository

logger = structlog.get_logger(__name__)

# Slippage por defecto: 0.05% del valor de la operación por lado
_DEFAULT_SLIPPAGE_PCT = Decimal("0.0005")
_PRICE_PRECISION = Decimal("0.00000001")
_VOLUME_PRECISION = Decimal("0.00000001")
_ZERO = Decimal("0")


class TradeSimulator:
    """Simula la ejecución de un trade de arbitraje con wallet tracking."""

    def __init__(
        self,
        opportunity_repo: IOpportunityRepository,
        trade_repo: ITradeRepository,
        wallet_repo: IWalletRepository,
        event_publisher: IEventPublisher,
        slippage_pct: Decimal = _DEFAULT_SLIPPAGE_PCT,
        fee_calculator: FeeCalculator | None = None,
    ) -> None:
        self._opportunity_repo = opportunity_repo
        self._trade_repo = trade_repo
        self._wallet_repo = wallet_repo
        self._event_publisher = event_publisher
        self._slippage_pct = slippage_pct
        # FeeCalculator es opcional: si está presente, los fees de una orden
        # parcial se recalculan exactamente sobre el volumen ejecutado (única
        # fuente de verdad). Si es None, se prorratean proporcionalmente.
        self._fee_calculator = fee_calculator

    def calculate_slippage_usdt(
        self,
        buy_price: Decimal,
        sell_price: Decimal,
        volume_btc: Decimal,
    ) -> Decimal:
        """
        Calcula el slippage total estimado en USDT.
        Slippage = slippage_pct * (buy_price + sell_price) * volume_btc / 2
        """
        avg_price = (buy_price + sell_price) / Decimal("2")
        slippage = (self._slippage_pct * avg_price * volume_btc).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )
        return slippage

    @staticmethod
    def _resolve_base_fees(
        opportunity: ArbitrageOpportunity,
    ) -> tuple[Decimal, Decimal]:
        """
        Determina los fees buy/sell de la oportunidad a volumen completo.

        Con desglose (CHG-009) usa trading_fee_buy/sell_usdt; sin desglose
        (compatibilidad hacia atrás) reparte total_fees_usdt al 50/50.
        """
        has_fee_breakdown = (
            opportunity.trading_fee_buy_usdt > _ZERO
            or opportunity.trading_fee_sell_usdt > _ZERO
        )
        if has_fee_breakdown:
            return (
                opportunity.trading_fee_buy_usdt,
                opportunity.trading_fee_sell_usdt,
            )
        half = opportunity.total_fees_usdt / Decimal("2")
        return half, half

    def _financeable_volume_by_usdt(
        self,
        opportunity: ArbitrageOpportunity,
        usdt_balance: Decimal,
    ) -> Decimal:
        """
        Calcula el máximo volumen BTC financiable con el saldo USDT disponible
        del comprador, descontando fees de compra y slippage proporcionales.

        El costo de compra es lineal en el volumen v:
            cost(v) = buy_price * v + fee_buy_rate * v + slippage_buy_rate * v
        donde las tasas se derivan del costo a volumen completo. Por tanto:
            v_max = usdt_balance / cost_per_btc
        """
        max_volume = opportunity.max_volume_btc
        if max_volume <= _ZERO:
            return _ZERO

        fee_buy_full, _ = self._resolve_base_fees(opportunity)
        slippage_buy_full = (opportunity.slippage_usdt / Decimal("2")).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )

        # Costo por BTC a volumen completo (precio + fees + slippage del lado compra)
        full_cost = (
            opportunity.buy_price * max_volume + fee_buy_full + slippage_buy_full
        )
        if full_cost <= _ZERO:
            return _ZERO

        cost_per_btc = full_cost / max_volume
        if cost_per_btc <= _ZERO:
            return _ZERO

        if usdt_balance >= full_cost:
            return max_volume

        financeable = (usdt_balance / cost_per_btc).quantize(
            _VOLUME_PRECISION, rounding=ROUND_HALF_UP
        )
        # Cota de seguridad: nunca exceder el volumen completo
        if financeable > max_volume:
            return max_volume
        return financeable

    async def _compute_fees(
        self,
        opportunity: ArbitrageOpportunity,
        volume_btc: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Calcula (fee_buy_usdt, fee_sell_usdt) para el volumen ejecutado.

        Si hay FeeCalculator, recalcula exactamente sobre el volumen real
        (única fuente de verdad). Si no, prorratea los fees de la oportunidad
        proporcionalmente al volumen ejecutado respecto a max_volume_btc.
        """
        if self._fee_calculator is not None:
            return await self._fee_calculator.calculate_fee_breakdown(
                opportunity.buy_exchange,
                opportunity.sell_exchange,
                volume_btc,
                opportunity.buy_price,
                opportunity.sell_price,
            )

        fee_buy_full, fee_sell_full = self._resolve_base_fees(opportunity)
        if opportunity.max_volume_btc <= _ZERO:
            return _ZERO, _ZERO
        ratio = volume_btc / opportunity.max_volume_btc
        fee_buy = (fee_buy_full * ratio).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )
        fee_sell = (fee_sell_full * ratio).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )
        return fee_buy, fee_sell

    async def simulate(
        self,
        opportunity: ArbitrageOpportunity,
    ) -> tuple[SimulatedTrade, SimulatedTrade] | None:
        """
        Simula la ejecución del arbitraje, soportando órdenes parciales.

        1. Calcula executable_volume_btc = MÍN(liquidez, USDT financiable, BTC vendedor)
        2. Si executable_volume_btc <= 0 → REJECTED, retorna None, sin tocar balances
        3. Recalcula fees/slippage/profit sobre el volumen real ejecutado
        4. Ejecuta BUY y SELL simulados (EXECUTED si == max_volume_btc, PARTIAL si menor)
        5. Actualiza wallets coherentemente (nunca balances negativos)
        6. Publica eventos SSE con el volumen real y el status

        Retorna (buy_trade, sell_trade) o None si no hay volumen ejecutable.
        """
        now = datetime.now(UTC)

        # --- Lectura de saldos relevantes ---
        usdt_before_buy = await self._wallet_repo.get_balance(
            opportunity.buy_exchange, "USDT"
        )
        btc_before_sell = await self._wallet_repo.get_balance(
            opportunity.sell_exchange, "BTC"
        )

        # --- Cálculo del volumen ejecutable: MÍN(liquidez, USDT, BTC vendedor) ---
        max_volume = opportunity.max_volume_btc
        financeable_by_usdt = self._financeable_volume_by_usdt(
            opportunity, usdt_before_buy
        )
        # El saldo BTC del vendedor capa el volumen vendible (nunca negativo)
        btc_cap = btc_before_sell if btc_before_sell > _ZERO else _ZERO

        executable_volume_btc = min(max_volume, financeable_by_usdt, btc_cap)

        # --- Rechazo si no hay volumen ejecutable (sin tocar balances) ---
        if executable_volume_btc <= _ZERO:
            logger.warning(
                "trade_rejected_no_executable_volume",
                opportunity_id=str(opportunity.id),
                buy_exchange=opportunity.buy_exchange,
                sell_exchange=opportunity.sell_exchange,
                max_volume_btc=float(max_volume),
                usdt_available=float(usdt_before_buy),
                btc_available_sell=float(btc_before_sell),
            )
            await self._opportunity_repo.update_status(
                opportunity.id, OpportunityStatus.REJECTED
            )
            return None

        # --- Determinar si es parcial o completo ---
        is_partial = executable_volume_btc < max_volume
        trade_status = TradeStatus.PARTIAL if is_partial else TradeStatus.EXECUTED

        # --- Recalcular fees, slippage y profit sobre el volumen REAL ---
        fee_buy_usdt, fee_sell_usdt = await self._compute_fees(
            opportunity, executable_volume_btc
        )
        # El slippage se prorratea desde el valor de la oportunidad respecto al
        # volumen real ejecutado. En ejecución completa (ratio == 1) coincide
        # exactamente con opportunity.slippage_usdt (comportamiento actual).
        if is_partial and max_volume > _ZERO:
            slippage_total = (
                opportunity.slippage_usdt * executable_volume_btc / max_volume
            ).quantize(_PRICE_PRECISION, rounding=ROUND_HALF_UP)
        else:
            slippage_total = opportunity.slippage_usdt
        slippage_buy = (slippage_total / Decimal("2")).quantize(
            _PRICE_PRECISION, rounding=ROUND_HALF_UP
        )
        slippage_sell = slippage_total - slippage_buy

        # Costo total de la compra (incluye fee de compra y slippage del lado compra)
        buy_cost_usdt = (
            opportunity.buy_price * executable_volume_btc
            + fee_buy_usdt
            + slippage_buy
        ).quantize(_PRICE_PRECISION, rounding=ROUND_HALF_UP)

        # Ingreso neto de la venta (descuenta fee de venta y slippage del lado venta)
        sell_revenue = (
            opportunity.sell_price * executable_volume_btc
            - fee_sell_usdt
            - slippage_sell
        ).quantize(_PRICE_PRECISION, rounding=ROUND_HALF_UP)

        # Profit neto sobre el volumen real ejecutado
        net_profit_usdt = (
            (opportunity.sell_price - opportunity.buy_price) * executable_volume_btc
            - fee_buy_usdt
            - fee_sell_usdt
            - slippage_total
        ).quantize(_PRICE_PRECISION, rounding=ROUND_HALF_UP)

        # --- Invariante de seguridad: validar saldos ANTES de cualquier débito ---
        if buy_cost_usdt > usdt_before_buy:
            # No debería ocurrir tras el sizing, pero protege contra balances negativos
            logger.error(
                "trade_rejected_buy_cost_exceeds_balance",
                opportunity_id=str(opportunity.id),
                buy_cost_usdt=float(buy_cost_usdt),
                usdt_available=float(usdt_before_buy),
            )
            await self._opportunity_repo.update_status(
                opportunity.id, OpportunityStatus.REJECTED
            )
            return None
        if executable_volume_btc > btc_before_sell:
            logger.error(
                "trade_rejected_btc_exceeds_balance",
                opportunity_id=str(opportunity.id),
                volume_btc=float(executable_volume_btc),
                btc_available_sell=float(btc_before_sell),
            )
            await self._opportunity_repo.update_status(
                opportunity.id, OpportunityStatus.REJECTED
            )
            return None

        # --- Crear trades con el volumen, fees, slippage y status reales ---
        buy_trade = SimulatedTrade(
            opportunity_id=opportunity.id,
            side=TradeSide.BUY,
            exchange=opportunity.buy_exchange,
            price=opportunity.buy_price,
            volume_btc=executable_volume_btc,
            fee_usdt=fee_buy_usdt,
            slippage_usdt=slippage_buy,
            executed_at=now,
            status=trade_status,
            is_partial=is_partial,
        )
        sell_trade = SimulatedTrade(
            opportunity_id=opportunity.id,
            side=TradeSide.SELL,
            exchange=opportunity.sell_exchange,
            price=opportunity.sell_price,
            volume_btc=executable_volume_btc,
            fee_usdt=fee_sell_usdt,
            slippage_usdt=slippage_sell,
            executed_at=now,
            status=trade_status,
            is_partial=is_partial,
        )

        # --- Snapshot de wallets ANTES de actualizar (CHG-009) ---
        btc_before_buy = await self._wallet_repo.get_balance(
            opportunity.buy_exchange, "BTC"
        )
        usdt_before_sell = await self._wallet_repo.get_balance(
            opportunity.sell_exchange, "USDT"
        )

        # --- Actualizar wallets con el MISMO executable_volume_btc ---
        # Débito USDT en exchange comprador
        await self._wallet_repo.set_balance(
            opportunity.buy_exchange,
            "USDT",
            usdt_before_buy - buy_cost_usdt,
        )
        # Crédito BTC en exchange comprador
        await self._wallet_repo.set_balance(
            opportunity.buy_exchange,
            "BTC",
            btc_before_buy + executable_volume_btc,
        )
        # Débito BTC en exchange vendedor (validado: nunca negativo)
        await self._wallet_repo.set_balance(
            opportunity.sell_exchange,
            "BTC",
            btc_before_sell - executable_volume_btc,
        )
        # Crédito USDT en exchange vendedor
        await self._wallet_repo.set_balance(
            opportunity.sell_exchange,
            "USDT",
            usdt_before_sell + sell_revenue,
        )

        # --- Snapshot de wallets DESPUES de actualizar (CHG-009) ---
        usdt_after_buy = await self._wallet_repo.get_balance(
            opportunity.buy_exchange, "USDT"
        )
        btc_after_buy = await self._wallet_repo.get_balance(
            opportunity.buy_exchange, "BTC"
        )
        usdt_after_sell = await self._wallet_repo.get_balance(
            opportunity.sell_exchange, "USDT"
        )
        btc_after_sell = await self._wallet_repo.get_balance(
            opportunity.sell_exchange, "BTC"
        )

        # Asignar snapshots a los trades (reflejan el volumen real ejecutado)
        buy_trade.wallet_usdt_before = usdt_before_buy
        buy_trade.wallet_usdt_after = usdt_after_buy
        buy_trade.wallet_btc_before = btc_before_buy
        buy_trade.wallet_btc_after = btc_after_buy

        sell_trade.wallet_usdt_before = usdt_before_sell
        sell_trade.wallet_usdt_after = usdt_after_sell
        sell_trade.wallet_btc_before = btc_before_sell
        sell_trade.wallet_btc_after = btc_after_sell

        # --- Persistir trades ---
        saved_buy = await self._trade_repo.save(buy_trade)
        saved_sell = await self._trade_repo.save(sell_trade)

        # --- Actualizar estado de la oportunidad ---
        # Una orden parcial igual completa la simulación: se marca EXECUTED.
        # El detalle PARTIAL vive en los trades (is_partial / status).
        await self._opportunity_repo.update_status(
            opportunity.id, OpportunityStatus.EXECUTED
        )

        # --- Publicar eventos SSE — sin clave "type": el publisher la añade ---
        await self._event_publisher.publish_trade_executed({
            "opportunity_id": str(opportunity.id),
            "net_profit_usdt": str(net_profit_usdt),
            "net_profit_pct": str(opportunity.net_profit_pct),
            "buy_exchange": opportunity.buy_exchange,
            "sell_exchange": opportunity.sell_exchange,
            "volume_btc": str(executable_volume_btc),
            "is_partial": is_partial,
            "status": trade_status.value,
        })

        # Publicar actualizaciones de wallet (usar balances ya capturados)
        await self._event_publisher.publish_wallet_update(
            opportunity.buy_exchange, "USDT", usdt_after_buy
        )
        await self._event_publisher.publish_wallet_update(
            opportunity.sell_exchange, "USDT", usdt_after_sell
        )

        logger.info(
            "trade_simulated",
            opportunity_id=str(opportunity.id),
            status=trade_status.value,
            is_partial=is_partial,
            volume_btc=float(executable_volume_btc),
            max_volume_btc=float(max_volume),
            net_profit_usdt=float(net_profit_usdt),
            buy_exchange=opportunity.buy_exchange,
            sell_exchange=opportunity.sell_exchange,
        )

        return saved_buy, saved_sell
