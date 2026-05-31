"""
StrategyRegistry — registro de estrategias de arbitraje.

Permite activar/desactivar estrategias en tiempo de ejecución
leyendo los feature flags desde la configuración (DB/env).
"""

import structlog

from core.strategies.base import ArbitrageStrategy

logger = structlog.get_logger(__name__)


class StrategyRegistry:
    """Registro de estrategias disponibles y activas."""

    def __init__(self) -> None:
        self._strategies: dict[str, ArbitrageStrategy] = {}

    def register(self, strategy: ArbitrageStrategy) -> None:
        """Registra una estrategia por su strategy_id."""
        self._strategies[strategy.strategy_id] = strategy
        logger.info("strategy_registered", strategy_id=strategy.strategy_id)

    def get_active(self, active_ids: list[str]) -> list[ArbitrageStrategy]:
        """
        Retorna las estrategias activas según la lista de IDs.
        Las estrategias no registradas son ignoradas silenciosamente.
        """
        active = [
            self._strategies[sid]
            for sid in active_ids
            if sid in self._strategies
        ]
        return active

    def get_all(self) -> list[ArbitrageStrategy]:
        """Retorna todas las estrategias registradas."""
        return list(self._strategies.values())

    def list_ids(self) -> list[str]:
        """Retorna los IDs de todas las estrategias registradas."""
        return list(self._strategies.keys())
