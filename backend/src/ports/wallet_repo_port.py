"""
Puerto: IWalletRepository.

Contrato para persistencia de balances simulados en PostgreSQL.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class IWalletRepository(ABC):
    """Interfaz para el repositorio de wallets simuladas."""

    @abstractmethod
    async def get_balance(self, exchange: str, currency: str) -> Decimal:
        """
        Retorna el balance actual de una moneda en un exchange.
        Devuelve Decimal("0") si no existe.
        """
        ...

    @abstractmethod
    async def set_balance(
        self,
        exchange: str,
        currency: str,
        amount: Decimal,
    ) -> None:
        """
        Actualiza (upsert) el balance de una moneda en un exchange.
        Registra el timestamp de actualización.
        """
        ...

    @abstractmethod
    async def list_all(self) -> list[dict[str, object]]:
        """
        Lista todos los balances.
        Retorna lista de dicts: {"exchange": str, "currency": str, "balance": Decimal}
        """
        ...

    @abstractmethod
    async def initialize_defaults(
        self,
        exchanges: list[str],
        initial_usdt: Decimal,
    ) -> None:
        """
        Inicializa balances por defecto si no existen.
        Cada exchange recibe initial_usdt en USDT y 0 en BTC.
        """
        ...
