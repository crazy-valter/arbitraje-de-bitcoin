"""
Puerto: IAdminUserRepository.

Contrato para búsqueda del operador único del sistema en PostgreSQL.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AdminUserRecord:
    """Proyección del operador para uso en el servicio de auth."""

    email: str
    password_hash: str


class IAdminUserRepository(ABC):
    """Interfaz para el repositorio del usuario administrador."""

    @abstractmethod
    async def find_by_email(self, email: str) -> AdminUserRecord | None:
        """
        Busca el usuario por email.
        Retorna None si no existe — el servicio de auth maneja el tiempo constante.
        """
        ...

    @abstractmethod
    async def create(self, email: str, password_hash: str) -> None:
        """
        Crea el usuario administrador.
        No sobreescribe si ya existe (usado por admin_seeder).
        """
        ...
