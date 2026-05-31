"""
Puerto: IOpportunityRepository.

Contrato para persistencia de oportunidades de arbitraje en PostgreSQL.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from core.entities.opportunity import ArbitrageOpportunity, OpportunityStatus


class IOpportunityRepository(ABC):
    """Interfaz para el repositorio de oportunidades."""

    @abstractmethod
    async def save(self, opportunity: ArbitrageOpportunity) -> ArbitrageOpportunity:
        """Persiste una nueva oportunidad. Retorna la entidad con ID asignado."""
        ...

    @abstractmethod
    async def update_status(
        self,
        opportunity_id: uuid.UUID,
        status: OpportunityStatus,
    ) -> None:
        """Actualiza el estado de una oportunidad existente."""
        ...

    @abstractmethod
    async def get_by_id(self, opportunity_id: uuid.UUID) -> ArbitrageOpportunity | None:
        """Busca una oportunidad por su ID."""
        ...

    @abstractmethod
    async def list_recent(
        self,
        limit: int = 100,
        status: OpportunityStatus | None = None,
    ) -> list[ArbitrageOpportunity]:
        """
        Lista oportunidades recientes, ordenadas por detected_at DESC.
        Filtro opcional por estado.
        """
        ...

    @abstractmethod
    async def list_paginated(
        self,
        offset: int,
        limit: int,
        status: list[OpportunityStatus] | None = None,
        buy_exchange: list[str] | None = None,
        sell_exchange: list[str] | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> tuple[list[ArbitrageOpportunity], int]:
        """
        Lista oportunidades con paginacion real y filtros avanzados.

        Retorna (items, total) donde total es el COUNT con los mismos filtros.
        Orden: detected_at DESC. Filtros de status/exchange aceptan listas (IN).
        """
        ...

    @abstractmethod
    async def get_total_pnl(self) -> float:
        """Retorna el P&L total acumulado de todas las oportunidades ejecutadas."""
        ...
