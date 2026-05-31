"""
Puerto: IEventPublisher.

Contrato para la publicación de eventos al canal SSE via Redis Pub/Sub.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from core.entities.opportunity import ArbitrageOpportunity


class IEventPublisher(ABC):
    """Interfaz para el publicador de eventos SSE."""

    @abstractmethod
    async def publish_orderbook(
        self,
        exchange: str,
        ask: Decimal,
        bid: Decimal,
    ) -> None:
        """
        Publica actualización de order book.
        Aplica throttling de 500ms por exchange antes de publicar en Redis.
        """
        ...

    @abstractmethod
    async def publish_opportunity(self, opportunity: ArbitrageOpportunity) -> None:
        """Publica una oportunidad detectada al canal SSE."""
        ...

    @abstractmethod
    async def publish_trade_executed(self, trade_data: dict[str, object]) -> None:
        """Publica el resultado de un trade simulado."""
        ...

    @abstractmethod
    async def publish_wallet_update(
        self,
        exchange: str,
        currency: str,
        balance: Decimal,
    ) -> None:
        """Publica una actualización de balance de wallet."""
        ...

    @abstractmethod
    async def publish_metrics(self, metrics: dict[str, object]) -> None:
        """Publica métricas agregadas del sistema (cada 5 segundos)."""
        ...
