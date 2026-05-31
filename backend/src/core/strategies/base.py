"""
Clase base abstracta para estrategias de arbitraje.

Todas las estrategias concretas heredan de ArbitrageStrategy e implementan detect().
El ArbitrageEngine itera sobre las estrategias activas via el StrategyRegistry.
"""

from abc import ABC, abstractmethod

from core.entities.opportunity import ArbitrageOpportunity
from core.entities.order_book import OrderBook


class ArbitrageStrategy(ABC):
    """Interfaz base para algoritmos de detección de arbitraje."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Identificador único de la estrategia: 'cross_exchange' | 'triangular' | etc."""
        ...

    @abstractmethod
    async def detect(
        self,
        order_books: list[OrderBook],
    ) -> list[ArbitrageOpportunity]:
        """
        Analiza los order books disponibles y retorna las oportunidades detectadas.

        Los order books se pasan ya leídos desde Redis — la estrategia no accede
        directamente al store para mantener el core libre de dependencias de infra.

        Solo retorna oportunidades con net_profit_usdt > 0.
        """
        ...
