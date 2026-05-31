"""
Tests unitarios: TradeSimulator wallet snapshot (CHG-009).

Verifica que simulate() captura los balances de wallet ANTES y DESPUES
de la ejecucion y los asigna a los campos wallet_*_before/after de cada trade.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

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

    # Balances iniciales
    _balances: dict[tuple[str, str], Decimal] = {
        ("binance", "USDT"): Decimal("10000"),
        ("binance", "BTC"): Decimal("0.5"),
        ("bybit", "USDT"): Decimal("8000"),
        ("bybit", "BTC"): Decimal("1.2"),
    }

    call_count: dict[str, int] = {"get_balance": 0}

    async def _get_balance(exchange: str, currency: str) -> Decimal:
        """Retorna balance que cambia despues de set_balance."""
        call_count["get_balance"] += 1
        key = (exchange, currency)
        return _balances.get(key, Decimal("0"))

    async def _set_balance(exchange: str, currency: str, amount: Decimal) -> None:
        _balances[(exchange, currency)] = amount

    wallet_repo.get_balance = AsyncMock(side_effect=_get_balance)
    wallet_repo.set_balance = AsyncMock(side_effect=_set_balance)

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


class TestWalletSnapshot:
    @pytest.mark.asyncio
    async def test_buy_trade_has_wallet_snapshots(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """El buy_trade debe tener wallet_usdt_before y wallet_btc_before poblados."""
        _, trade_repo, _, _ = mock_repos
        result = await simulator.simulate(sample_opportunity)
        assert result is not None
        buy_trade, _ = result

        # wallet_usdt_before debe ser el balance USDT de binance ANTES de la operacion
        assert buy_trade.wallet_usdt_before == Decimal("10000")
        # wallet_btc_before debe ser el balance BTC de binance ANTES
        assert buy_trade.wallet_btc_before == Decimal("0.5")
        # wallet_usdt_after debe ser diferente (se debito USDT)
        assert buy_trade.wallet_usdt_after < Decimal("10000")
        # wallet_btc_after debe ser mayor (se acredito BTC)
        assert buy_trade.wallet_btc_after > Decimal("0.5")

    @pytest.mark.asyncio
    async def test_sell_trade_has_wallet_snapshots(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """El sell_trade debe tener wallet snapshots del exchange vendedor."""
        _, trade_repo, _, _ = mock_repos
        result = await simulator.simulate(sample_opportunity)
        assert result is not None
        _, sell_trade = result

        # wallet_usdt_before de bybit ANTES
        assert sell_trade.wallet_usdt_before == Decimal("8000")
        # wallet_btc_before de bybit ANTES
        assert sell_trade.wallet_btc_before == Decimal("1.2")
        # wallet_usdt_after debe ser mayor (se acredito USDT de la venta)
        assert sell_trade.wallet_usdt_after > Decimal("8000")

    @pytest.mark.asyncio
    async def test_snapshots_are_decimal(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
    ) -> None:
        """Todos los snapshots deben ser Decimal, nunca float."""
        result = await simulator.simulate(sample_opportunity)
        assert result is not None
        buy_trade, sell_trade = result

        for trade in [buy_trade, sell_trade]:
            assert isinstance(trade.wallet_usdt_before, Decimal)
            assert isinstance(trade.wallet_usdt_after, Decimal)
            assert isinstance(trade.wallet_btc_before, Decimal)
            assert isinstance(trade.wallet_btc_after, Decimal)

    @pytest.mark.asyncio
    async def test_snapshots_persisted_in_trade_repo(
        self,
        simulator: TradeSimulator,
        sample_opportunity: ArbitrageOpportunity,
        mock_repos: tuple,
    ) -> None:
        """Los trades pasados a trade_repo.save deben tener los snapshots asignados."""
        _, trade_repo, _, _ = mock_repos
        result = await simulator.simulate(sample_opportunity)
        assert result is not None

        # Verificar que trade_repo.save fue llamado 2 veces con trades que tienen snapshots
        assert trade_repo.save.call_count == 2
        for call in trade_repo.save.call_args_list:
            trade = call[0][0]  # primer argumento posicional
            assert trade.wallet_usdt_before > Decimal("0") or trade.wallet_usdt_before == Decimal("0")
            assert isinstance(trade.wallet_usdt_before, Decimal)
