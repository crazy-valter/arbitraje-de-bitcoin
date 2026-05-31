"""
Puerto: ITradeRepository.

Contrato para persistencia de trades simulados en PostgreSQL.
"""

import uuid
from abc import ABC, abstractmethod

from core.entities.trade import SimulatedTrade


class ITradeRepository(ABC):
    """Interfaz para el repositorio de trades simulados."""

    @abstractmethod
    async def save(self, trade: SimulatedTrade) -> SimulatedTrade:
        """Persiste un trade. Retorna la entidad con ID asignado."""
        ...

    @abstractmethod
    async def list_by_opportunity(self, opportunity_id: uuid.UUID) -> list[SimulatedTrade]:
        """Lista todos los trades vinculados a una oportunidad."""
        ...

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[SimulatedTrade]:
        """Lista los trades más recientes, ordenados por executed_at DESC."""
        ...
