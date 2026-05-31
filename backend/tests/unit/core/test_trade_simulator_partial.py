"""
Tests unitarios: TradeSimulator — órdenes parciales (RF-05 / CHG-014).

Verifica que cuando el saldo de wallet (USDT del comprador o BTC del vendedor)
no cubre el volumen completo, se ejecuta una orden PARCIAL por el máximo
volumen viable, recalculando fees/slippage/profit sobre el volumen real y
sin dejar nunca balances negativos.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from core.entities.opportunity import ArbitrageOpportunity, OpportunityStatus
from core.entities.trade import TradeSide, TradeStatus
from core.services.trade_simulator import TradeSimulator
from ports.event_publisher_port import IEventPublisher
from ports.opportunity_repo_port import IOpportunityRepository
from ports.trade_repo_port import ITradeRepository
from ports.wallet_repo_port import IWalletRepository


def _make_opportunity(
    *,
    buy_price: Decimal = Decimal("70000"),
    sell_price: Decimal = Decimal("70700"),
    max_volume_btc: Decimal = Decimal("1.0"),
    trading_fee_buy_usdt: Decimal = Decimal("70.00"),
    trading_fee_sell_usdt: Decimal = Decimal("183.82"),
    slippage_usdt: Decimal = Decimal("35.00"),
) -> ArbitrageOpportunity:
    """Oportunidad con fees desglosados a volumen completo (max_volume_btc)."""
    gross = (sell_price - buy_price) * max_volume_btc
    net = gross - trading_fee_buy_usdt - trading_fee_sell_usdt - slippage_usdt
    return ArbitrageOpportunity(
        id=uuid.uuid4(),
        buy_exchange="binance",
        sell_exchange="kraken",
        buy_price=buy_price,
        sell_price=sell_price,
        gross_spread_pct=Decimal("1.0"),
        total_fees_usdt=trading_fee_buy_usdt + trading_fee_sell_usdt,
        slippage_usdt=slippage_usdt,
        net_profit_usdt=net,
        net_profit_pct=Decimal("0.5"),
        max_volume_btc=max_volume_btc,
        strategy="cross_exchange",
        score=0.85,
        detected_at=datetime.now(timezone.utc),
        status=OpportunityStatus.DETECTED,
        trading_fee_buy_usdt=trading_fee_buy_usdt,
        trading_fee_sell_usdt=trading_fee_sell_usdt,
    )


def _make_repos(
    balances: dict[tuple[str, str], Decimal],
) -> tuple[
    IOpportunityRepository,
    ITradeRepository,
    IWalletRepository,
    IEventPublisher,
    dict[tuple[str, str], Decimal],
]:
    """Mocks con un dict de balances mutable que refleja set_balance."""
    opp_repo = AsyncMock(spec=IOpportunityRepository)
    trade_repo = AsyncMock(spec=ITradeRepository)
    wallet_repo = AsyncMock(spec=IWalletRepository)
    event_publisher = AsyncMock(spec=IEventPublisher)

    state = dict(balances)

    async def _get_balance(exchange: str, currency: str) -> Decimal:
        return state.get((exchange, currency), Decimal("0"))

    async def _set_balance(exchange: str, currency: str, amount: Decimal) -> None:
        state[(exchange, currency)] = amount

    wallet_repo.get_balance = AsyncMock(side_effect=_get_balance)
    wallet_repo.set_balance = AsyncMock(side_effect=_set_balance)
    trade_repo.save = AsyncMock(side_effect=lambda t: t)

    return opp_repo, trade_repo, wallet_repo, event_publisher, state


def _assert_no_negative_balances(state: dict[tuple[str, str], Decimal]) -> None:
    """Invariante global: ningún balance puede quedar negativo."""
    for (exchange, currency), amount in state.items():
        assert amount >= Decimal("0"), (
            f"Balance negativo detectado en {exchange}/{currency}: {amount}"
        )


class TestPartialByUsdt:
    @pytest.mark.asyncio
    async def test_partial_when_usdt_insufficient(self) -> None:
        """
        Test 1: saldo USDT del comprador no cubre max_volume_btc pero sí un
        volumen menor > 0 → orden PARCIAL, balances coherentes, profit recalculado.

        max_volume = 1 BTC; costo full ≈ 70000 + 70 + 17.5 = 70087.5 USDT.
        Con 35043.75 USDT (mitad) el volumen financiable es ~0.5 BTC.
        """
        opp = _make_opportunity()
        # La mitad del costo completo → ~0.5 BTC financiable
        usdt_available = Decimal("35043.75")
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): usdt_available,
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): Decimal("5"),  # BTC de sobra en el vendedor
        })
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        result = await sim.simulate(opp)
        assert result is not None
        buy_trade, sell_trade = result

        # Orden parcial en ambos trades
        assert buy_trade.is_partial is True
        assert sell_trade.is_partial is True
        assert buy_trade.status == TradeStatus.PARTIAL
        assert sell_trade.status == TradeStatus.PARTIAL

        # Volumen reducido y > 0, menor que max_volume
        assert Decimal("0") < buy_trade.volume_btc < opp.max_volume_btc
        assert buy_trade.volume_btc == sell_trade.volume_btc

        # El costo de compra no excede el saldo disponible (no negativo)
        assert state[("binance", "USDT")] >= Decimal("0")
        # Se acreditó BTC al comprador exactamente por el volumen ejecutado
        assert state[("binance", "BTC")] == buy_trade.volume_btc
        # Se debitó BTC del vendedor por el mismo volumen
        assert state[("kraken", "BTC")] == Decimal("5") - buy_trade.volume_btc

        _assert_no_negative_balances(state)

    @pytest.mark.asyncio
    async def test_partial_profit_recalculated_on_real_volume(self) -> None:
        """El net_profit del evento SSE corresponde al volumen real ejecutado."""
        opp = _make_opportunity()
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): Decimal("35043.75"),
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): Decimal("5"),
        })
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        result = await sim.simulate(opp)
        assert result is not None
        buy_trade, _ = result

        # Profit esperado = (sell-buy)*vol - fee_buy - fee_sell - slippage,
        # con fees y slippage prorrateados al volumen real (FeeCalculator=None).
        ratio = buy_trade.volume_btc / opp.max_volume_btc
        fee_buy = (opp.trading_fee_buy_usdt * ratio).quantize(Decimal("0.00000001"))
        fee_sell = (opp.trading_fee_sell_usdt * ratio).quantize(Decimal("0.00000001"))
        slippage = (opp.slippage_usdt * buy_trade.volume_btc / opp.max_volume_btc).quantize(
            Decimal("0.00000001")
        )
        expected_profit = (
            (opp.sell_price - opp.buy_price) * buy_trade.volume_btc
            - fee_buy - fee_sell - slippage
        ).quantize(Decimal("0.00000001"))

        call_args = event_publisher.publish_trade_executed.call_args
        payload: dict[str, object] = call_args[0][0]
        assert payload["status"] == "PARTIAL"
        assert payload["is_partial"] is True
        assert Decimal(str(payload["net_profit_usdt"])) == expected_profit
        assert Decimal(str(payload["volume_btc"])) == buy_trade.volume_btc


class TestPartialBySellerBtc:
    @pytest.mark.asyncio
    async def test_partial_when_seller_btc_insufficient(self) -> None:
        """
        Test 2: el saldo BTC del vendedor no cubre max_volume_btc → volumen
        limitado a dicho saldo (parcial), sin balance BTC negativo.
        """
        opp = _make_opportunity(max_volume_btc=Decimal("1.0"))
        seller_btc = Decimal("0.3")
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): Decimal("1000000"),  # USDT de sobra
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): seller_btc,
        })
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        result = await sim.simulate(opp)
        assert result is not None
        buy_trade, sell_trade = result

        # Volumen limitado exactamente al BTC disponible del vendedor
        assert buy_trade.volume_btc == seller_btc
        assert buy_trade.is_partial is True
        assert sell_trade.status == TradeStatus.PARTIAL

        # BTC del vendedor queda en cero, nunca negativo
        assert state[("kraken", "BTC")] == Decimal("0")
        _assert_no_negative_balances(state)


class TestRejectedZeroVolume:
    @pytest.mark.asyncio
    async def test_rejected_when_no_executable_volume(self) -> None:
        """
        Test 3: volumen ejecutable 0 (saldo nulo) → REJECTED, retorna None,
        sin mutación de balances.
        """
        opp = _make_opportunity()
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): Decimal("0"),
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): Decimal("0"),
        })
        before = dict(state)
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        result = await sim.simulate(opp)
        assert result is None
        opp_repo.update_status.assert_called_once_with(
            opp.id, OpportunityStatus.REJECTED
        )
        # Ningún set_balance ejecutado → balances intactos
        wallet_repo.set_balance.assert_not_called()
        assert state == before
        _assert_no_negative_balances(state)

    @pytest.mark.asyncio
    async def test_rejected_when_seller_has_no_btc(self) -> None:
        """Sin BTC en el vendedor el volumen ejecutable es 0 → REJECTED."""
        opp = _make_opportunity()
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): Decimal("1000000"),
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): Decimal("0"),
        })
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )
        result = await sim.simulate(opp)
        assert result is None
        wallet_repo.set_balance.assert_not_called()


class TestFullExecutionRegression:
    @pytest.mark.asyncio
    async def test_full_execution_marks_executed(self) -> None:
        """
        Test 4: el saldo cubre el volumen completo → EXECUTED, is_partial False.
        """
        opp = _make_opportunity(max_volume_btc=Decimal("1.0"))
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): Decimal("1000000"),
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): Decimal("5"),
        })
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        result = await sim.simulate(opp)
        assert result is not None
        buy_trade, sell_trade = result

        assert buy_trade.volume_btc == opp.max_volume_btc
        assert buy_trade.is_partial is False
        assert sell_trade.is_partial is False
        assert buy_trade.status == TradeStatus.EXECUTED
        assert sell_trade.status == TradeStatus.EXECUTED
        opp_repo.update_status.assert_called_with(
            opp.id, OpportunityStatus.EXECUTED
        )
        _assert_no_negative_balances(state)


class TestNoNegativeBalanceInvariant:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "usdt_buyer,btc_seller",
        [
            (Decimal("0"), Decimal("5")),        # sin USDT → rechazo
            (Decimal("35043.75"), Decimal("5")),  # parcial por USDT
            (Decimal("1000000"), Decimal("0.3")),  # parcial por BTC
            (Decimal("1000000"), Decimal("5")),    # completo
            (Decimal("100"), Decimal("0.001")),    # ambos muy limitados
        ],
    )
    async def test_no_negative_balances_across_scenarios(
        self,
        usdt_buyer: Decimal,
        btc_seller: Decimal,
    ) -> None:
        """Test 5: en todos los escenarios ningún balance queda negativo."""
        opp = _make_opportunity()
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): usdt_buyer,
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): btc_seller,
        })
        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        await sim.simulate(opp)
        _assert_no_negative_balances(state)


class TestFeeCalculatorReuse:
    @pytest.mark.asyncio
    async def test_partial_uses_fee_calculator_when_present(self) -> None:
        """
        Con FeeCalculator inyectado, los fees de una orden parcial se recalculan
        exactamente sobre el volumen ejecutado (única fuente de verdad).
        """
        opp = _make_opportunity()
        opp_repo, trade_repo, wallet_repo, event_publisher, state = _make_repos({
            ("binance", "USDT"): Decimal("35043.75"),
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("0"),
            ("kraken", "BTC"): Decimal("5"),
        })

        # FeeCalculator falso: devuelve fees fijos por volumen para verificar reuso
        fee_calc = AsyncMock()
        fee_calc.calculate_fee_breakdown = AsyncMock(
            return_value=(Decimal("1.11"), Decimal("2.22"))
        )

        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
            fee_calculator=fee_calc,
        )

        result = await sim.simulate(opp)
        assert result is not None
        buy_trade, sell_trade = result

        fee_calc.calculate_fee_breakdown.assert_awaited_once()
        # Se llamó con el volumen REAL ejecutado, no con max_volume_btc
        call = fee_calc.calculate_fee_breakdown.call_args
        assert call.args[2] == buy_trade.volume_btc
        # Los fees del trade provienen del FeeCalculator
        assert buy_trade.fee_usdt == Decimal("1.11")
        assert sell_trade.fee_usdt == Decimal("2.22")
        _assert_no_negative_balances(state)
