"""
Router: GET/PUT /api/config — configuración del bot (capital, threshold, estrategias).
"""

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.exchanges.registry import EXCHANGE_REGISTRY
from adapters.persistence.config_repo import ConfigRepository
from api.dependencies import get_current_user, get_db
from api.schemas import ConfigResponse, ConfigUpdateRequest

router = APIRouter(prefix="/api/config", tags=["config"])

_logger = structlog.get_logger(__name__)


async def _read_config(repo: ConfigRepository) -> ConfigResponse:
    """Helper interno para leer la configuración actual."""
    capital = await repo.get_capital_usdt()
    threshold = await repo.get_min_profit_threshold_pct()
    cross = await repo.get("STRATEGY_CROSS_EXCHANGE")
    triangular = await repo.get("STRATEGY_TRIANGULAR")
    statistical = await repo.get("STRATEGY_STATISTICAL")
    mock_mode = await repo.get_mock_mode_enabled()

    return ConfigResponse(
        initial_capital_usdt=str(capital),
        min_profit_threshold_pct=str(threshold),
        strategy_cross_exchange=(cross or "true").lower() == "true",
        strategy_triangular=(triangular or "false").lower() == "true",
        strategy_statistical=(statistical or "false").lower() == "true",
        mock_mode_enabled=mock_mode,
    )


@router.get("", response_model=ConfigResponse)
async def get_config(
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConfigResponse:
    """Retorna la configuración actual del bot."""
    repo = ConfigRepository(session)
    return await _read_config(repo)


@router.put("", response_model=ConfigResponse)
async def update_config(
    request: Request,
    payload: ConfigUpdateRequest,
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConfigResponse:
    """Actualiza la configuración del bot. Solo actualiza los campos enviados."""
    repo = ConfigRepository(session)

    if payload.initial_capital_usdt is not None:
        await repo.set("INITIAL_CAPITAL_USDT", str(payload.initial_capital_usdt))

    if payload.min_profit_threshold_pct is not None:
        await repo.set("MIN_PROFIT_THRESHOLD_PCT", str(payload.min_profit_threshold_pct))

    if payload.strategy_cross_exchange is not None:
        await repo.set(
            "STRATEGY_CROSS_EXCHANGE", str(payload.strategy_cross_exchange).lower()
        )

    if payload.strategy_triangular is not None:
        await repo.set(
            "STRATEGY_TRIANGULAR", str(payload.strategy_triangular).lower()
        )

    if payload.strategy_statistical is not None:
        await repo.set(
            "STRATEGY_STATISTICAL", str(payload.strategy_statistical).lower()
        )

    # Hot-swap de adaptadores al cambiar mock_mode_enabled
    if payload.mock_mode_enabled is not None:
        await repo.set("MOCK_MODE_ENABLED", str(payload.mock_mode_enabled).lower())
        engine = request.app.state.engine

        if payload.mock_mode_enabled:
            from adapters.exchanges.mock_exchange import MockExchangeAdapter
            from adapters.exchanges.mock_scenarios import SPREAD_HIGH

            _logger.warning(
                "mock_mode_activated",
                msg="MODO MOCK ACTIVO — no conectado a exchanges reales",
            )
            new_exchanges = [
                MockExchangeAdapter(eid, SPREAD_HIGH)
                for eid in EXCHANGE_REGISTRY
            ]
        else:
            from adapters.exchanges.binance_adapter import BinanceAdapter
            from adapters.exchanges.bybit_adapter import BybitAdapter
            from adapters.exchanges.kraken_adapter import KrakenAdapter

            _adapter_map = {
                "binance": BinanceAdapter,
                "bybit": BybitAdapter,
                "kraken": KrakenAdapter,
            }
            _logger.info("mock_mode_deactivated", msg="Volviendo a exchanges reales")
            new_exchanges = [
                _adapter_map[eid]()
                for eid in EXCHANGE_REGISTRY
                if eid in _adapter_map
            ]

        await engine.reload_exchanges(new_exchanges)

    # Retornar configuración actualizada
    return await _read_config(repo)
