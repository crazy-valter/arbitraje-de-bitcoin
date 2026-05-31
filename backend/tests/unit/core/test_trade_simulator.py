"""
Tests unitarios: TradeSimulator.

Verifica la lógica de simulación de trades, wallet tracking y slippage.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.entities.opportunity import ArbitrageOpportunity, OpportunityStatus
from core.entities.trade import SimulatedTrade, TradeSide, TradeStatus
from core.services.trade_simulator import TradeSimulator
from ports.event_publisher_port import IEventPublisher
from ports.opportunity_repo_port import IOpportunityRepository
from ports.trade_repo_port import ITradeRepository
from ports.wallet_repo_port import IWalletRepository


@pytest.fixture
def sample_opportunity() -> ArbitrageOpportunity:
    """Oportunidad de ejemplo con datos realistas."""
    return ArbitrageOpportunity(
        id=uuid.uuid4(),
        buy_exchange="binance",
        sell_exchange="bybit",
        buy_price=Decimal("70000"),
        sell_price=Decimal("70300"),
        gross_spread_pct=Decimal("0.428571"),
        total_fees_usdt=Decimal("14.00000000"),
        slippage_usdt=Decimal("3.50175000"),
        net_profit_usdt=Decimal("12.49825000"),
        net_profit_pct=Decimal("0.178546"),
        max_volume_btc=Decimal("0.1"),
        strategy="cross_exchange",
        score=0.75,
        detected_at=datetime.now(timezone.utc),
        status=OpportunityStatus.DETECTED,
    )


@pytest.fixture
def mock_repos() -> tuple[
    IOpportunityRepository,
    ITradeRepository,
    IWalletRepository,
    IEventPublisher,
]:
    """Mocks de todos los repositorios y el event publisher."""
    opp_repo = AsyncMock(spec=IOpportunityRepository)
    trade_repo = AsyncMock(spec=ITradeRepository)
    wallet_repo = AsyncMock(spec=IWalletRepository)
    event_publisher = AsyncMock(spec=IEventPublisher)

    # La wallet tiene suficiente USDT en el comprador y suficiente BTC en el
    # vendedor para cubrir el volumen completo (orden EXECUTED, no parcial).
    wallet_repo.get_balance = AsyncMock(side_effect=lambda exchange, currency: {
        ("binance", "USDT"): Decimal("10000"),
        ("binance", "BTC"): Decimal("0"),
        ("bybit", "USDT"): Decimal("10000"),
        ("bybit", "BTC"): Decimal("1"),
    }.get((exchange, currency), Decimal("0")))

    # trade_repo.save retorna el mismo trade recibido
    trade_repo.save = AsyncMock(side_effect=lambda t: t)

    return opp_repo, trade_repo, wallet_repo, event_publisher


@pytest.fixture
def simulator(mock_repos: tuple) -> TradeSimulator:
    opp_repo, trade_repo, wallet_repo, event_publisher = mock_repos
    return TradeSimulator(
        opportunity_repo=opp_repo,
        trade_repo=trade_repo,
        wallet_repo=wallet_repo,
        event_publisher=event_publisher,
    )


class TestCalculateSlippage:
    def test_slippage_calculation(self) -> None:
        """Slippage = 0.05% × avg_price × volume."""
        sim = TradeSimulator(
            opportunity_repo=AsyncMock(),
            trade_repo=AsyncMock(),
            wallet_repo=AsyncMock(),
            event_publisher=AsyncMock(),
        )
        slippage = sim.calculate_slippage_usdt(
            buy_price=Decimal("70000"),
            sell_price=Decimal("70200"),
            volume_btc=Decimal("0.1"),
        )
        # avg_price = 70100, slippage = 0.0005 × 70100 × 0.1 = 3.505
        expected = Decimal("3.50500000")
        assert slippage == expected

    def test_slippage_is_decimal(self) -> None:
        """El slippage debe ser Decimal, nunca float."""
        sim = TradeSimulator(
            opportunity_repo=AsyncMock(),
            trade_repo=AsyncMock(),
            wallet_repo=AsyncMock(),
            event_publisher=AsyncMock(),
        )
        slippage = sim.calculate_slippage_usdt(
            buy_price=Decimal("70000"),
            sell_price=Decimal("70300"),
            volume_btc=Decimal("0.1"),
        )
        assert isinstance(slippage, Decimal)


class TestSimulate:
    @pytest.mark.asyncio
    async def test_successful_simulation_returns_two_trades(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
    ) -> None:
        """Una simulación exitosa debe retornar (buy_trade, sell_trade)."""
        result = await simulator.simulate(sample_opportunity)
        assert result is not None
        buy_trade, sell_trade = result
        assert buy_trade.side == TradeSide.BUY
        assert sell_trade.side == TradeSide.SELL
        assert buy_trade.exchange == "binance"
        assert sell_trade.exchange == "bybit"

    @pytest.mark.asyncio
    async def test_returns_none_when_insufficient_balance(
        self,
        mock_repos: tuple,
        sample_opportunity: ArbitrageOpportunity,
    ) -> None:
        """Si el balance USDT es insuficiente, retorna None y marca como REJECTED."""
        opp_repo, trade_repo, wallet_repo, event_publisher = mock_repos
        # Balance insuficiente
        wallet_repo.get_balance = AsyncMock(return_value=Decimal("0"))

        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )
        result = await sim.simulate(sample_opportunity)
        assert result is None
        opp_repo.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_trade_repo_called_twice(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """Se deben persistir exactamente 2 trades (BUY + SELL)."""
        _, trade_repo, _, _ = mock_repos
        await simulator.simulate(sample_opportunity)
        assert trade_repo.save.call_count == 2

    @pytest.mark.asyncio
    async def test_opportunity_status_updated_to_executed(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """La oportunidad debe marcarse como EXECUTED al terminar."""
        opp_repo, _, _, _ = mock_repos
        await simulator.simulate(sample_opportunity)
        opp_repo.update_status.assert_called_with(
            sample_opportunity.id, OpportunityStatus.EXECUTED
        )

    @pytest.mark.asyncio
    async def test_sse_events_published(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """Se deben publicar eventos SSE: trade_simulated + wallet_update(s)."""
        _, _, _, event_publisher = mock_repos
        await simulator.simulate(sample_opportunity)
        event_publisher.publish_trade_executed.assert_called_once()
        assert event_publisher.publish_wallet_update.call_count >= 1

    @pytest.mark.asyncio
    async def test_trade_data_has_no_type_key(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """
        El dict pasado a publish_trade_executed no debe contener la clave 'type'.
        El publisher es responsable de añadir 'type': 'trade_simulated'.
        Si trade_data incluye 'type', el spread en event_publisher.py lo sobrescribiría
        silenciosamente, causando que el evento SSE tenga el type incorrecto (Bug 1).
        """
        _, _, _, event_publisher = mock_repos
        await simulator.simulate(sample_opportunity)
        call_args = event_publisher.publish_trade_executed.call_args
        trade_data: dict[str, object] = call_args[0][0]
        assert "type" not in trade_data, (
            "trade_data no debe incluir 'type' — el publisher lo añade como 'trade_simulated'"
        )

    @pytest.mark.asyncio
    async def test_simulator_btc_debited_from_sell_exchange(
        self,
        mock_repos: tuple,
    ) -> None:
        """
        BUG-1: Tras simulate(), el BTC del exchange vendedor debe debitarse
        en exactamente max_volume_btc — verificar que set_balance recibe
        (sell_exchange, "BTC", btc_before - volume_btc).
        """
        opp_repo, trade_repo, wallet_repo, event_publisher = mock_repos

        # Ajustar el balance BTC de bybit a 1 BTC para este test
        wallet_repo.get_balance = AsyncMock(side_effect=lambda exchange, currency: {
            ("binance", "USDT"): Decimal("10000"),
            ("binance", "BTC"): Decimal("0"),
            ("bybit", "USDT"): Decimal("10000"),
            ("bybit", "BTC"): Decimal("1"),
        }.get((exchange, currency), Decimal("0")))

        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        opportunity = ArbitrageOpportunity(
            id=uuid.uuid4(),
            buy_exchange="binance",
            sell_exchange="bybit",
            buy_price=Decimal("70000"),
            sell_price=Decimal("70300"),
            gross_spread_pct=Decimal("0.428571"),
            total_fees_usdt=Decimal("14.00000000"),
            slippage_usdt=Decimal("3.50175000"),
            net_profit_usdt=Decimal("12.49825000"),
            net_profit_pct=Decimal("0.178546"),
            max_volume_btc=Decimal("0.1"),
            strategy="cross_exchange",
            score=0.75,
            detected_at=datetime.now(timezone.utc),
            status=OpportunityStatus.DETECTED,
        )

        result = await sim.simulate(opportunity)
        assert result is not None

        # Verificar que set_balance fue llamado con el valor correcto para BTC en bybit
        # btc_before = 1, max_volume_btc = 0.1 → esperado = 0.9
        expected_btc_after = Decimal("1") - opportunity.max_volume_btc
        wallet_repo.set_balance.assert_any_call("bybit", "BTC", expected_btc_after)

    @pytest.mark.asyncio
    async def test_simulator_fee_split_asymmetric(
        self,
        mock_repos: tuple,
    ) -> None:
        """
        BUG-2: Los fees deben asignarse asimétricamente según exchange.
        Binance 0.10% (buy) → $7.00, Kraken 0.26% (sell) → $18.20
        Los trades deben reflejar el desglose real, no total_fees/2.
        """
        opp_repo, trade_repo, wallet_repo, event_publisher = mock_repos

        # Balance suficiente para cubrir la compra con los fees reales
        wallet_repo.get_balance = AsyncMock(side_effect=lambda exchange, currency: {
            ("binance", "USDT"): Decimal("20000"),
            ("binance", "BTC"): Decimal("0"),
            ("kraken", "USDT"): Decimal("10000"),
            ("kraken", "BTC"): Decimal("1"),
        }.get((exchange, currency), Decimal("0")))

        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        # Oportunidad con fees desglosados: Binance buy 0.10%, Kraken sell 0.26%
        # 0.1 BTC × $70000 × 0.001 = $7.00 (buy)
        # 0.1 BTC × $70000 × 0.0026 = $18.20 (sell)
        opportunity = ArbitrageOpportunity(
            id=uuid.uuid4(),
            buy_exchange="binance",
            sell_exchange="kraken",
            buy_price=Decimal("70000"),
            sell_price=Decimal("70700"),
            gross_spread_pct=Decimal("1.0"),
            total_fees_usdt=Decimal("25.20000000"),
            slippage_usdt=Decimal("3.50175000"),
            net_profit_usdt=Decimal("41.29825000"),
            net_profit_pct=Decimal("0.59"),
            max_volume_btc=Decimal("0.1"),
            strategy="cross_exchange",
            score=0.85,
            detected_at=datetime.now(timezone.utc),
            status=OpportunityStatus.DETECTED,
            trading_fee_buy_usdt=Decimal("7.00"),
            trading_fee_sell_usdt=Decimal("18.20"),
        )

        result = await sim.simulate(opportunity)
        assert result is not None
        buy_trade, sell_trade = result

        # Verificar que cada trade usa el fee correcto de su exchange
        assert buy_trade.fee_usdt == Decimal("7.00"), (
            f"buy_trade.fee_usdt debe ser 7.00 (Binance 0.10%), got {buy_trade.fee_usdt}"
        )
        assert sell_trade.fee_usdt == Decimal("18.20"), (
            f"sell_trade.fee_usdt debe ser 18.20 (Kraken 0.26%), got {sell_trade.fee_usdt}"
        )

    @pytest.mark.asyncio
    async def test_simulator_buy_cost_uses_buy_fee_only(
        self,
        mock_repos: tuple,
    ) -> None:
        """
        BUG-3: buy_cost_usdt debe usar trading_fee_buy_usdt, no total_fees/2.
        El slippage sigue siendo 50/50.

        buy_cost = buy_price × volume + fee_buy + slippage/2
        Con fee_buy=$7.00, fee_sell=$18.20, slippage=$3.50:
        buy_cost = 70000 × 0.1 + 7.00 + 1.75 = 7008.75
        USDT restante en binance = 10000 - 7008.75 = 2991.25
        """
        opp_repo, trade_repo, wallet_repo, event_publisher = mock_repos

        usdt_inicial = Decimal("10000")
        wallet_repo.get_balance = AsyncMock(side_effect=lambda exchange, currency: {
            ("binance", "USDT"): usdt_inicial,
            ("binance", "BTC"): Decimal("0"),
            ("bybit", "USDT"): Decimal("10000"),
            ("bybit", "BTC"): Decimal("1"),
        }.get((exchange, currency), Decimal("0")))

        sim = TradeSimulator(
            opportunity_repo=opp_repo,
            trade_repo=trade_repo,
            wallet_repo=wallet_repo,
            event_publisher=event_publisher,
        )

        opportunity = ArbitrageOpportunity(
            id=uuid.uuid4(),
            buy_exchange="binance",
            sell_exchange="bybit",
            buy_price=Decimal("70000"),
            sell_price=Decimal("70500"),
            gross_spread_pct=Decimal("0.714286"),
            total_fees_usdt=Decimal("25.20000000"),
            slippage_usdt=Decimal("3.50"),
            net_profit_usdt=Decimal("21.30"),
            net_profit_pct=Decimal("0.30"),
            max_volume_btc=Decimal("0.1"),
            strategy="cross_exchange",
            score=0.80,
            detected_at=datetime.now(timezone.utc),
            status=OpportunityStatus.DETECTED,
            trading_fee_buy_usdt=Decimal("7.00"),
            trading_fee_sell_usdt=Decimal("18.20"),
        )

        result = await sim.simulate(opportunity)
        assert result is not None

        # buy_cost = 70000 × 0.1 + 7.00 + 3.50/2 = 7000 + 7.00 + 1.75 = 7008.75
        expected_buy_cost = Decimal("7008.75000000")
        expected_usdt_after = usdt_inicial - expected_buy_cost

        # Verificar que el débito USDT en binance usa fee_buy, no total_fees/2
        wallet_repo.set_balance.assert_any_call("binance", "USDT", expected_usdt_after)
