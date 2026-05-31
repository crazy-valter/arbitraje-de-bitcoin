"""
Puerto: IConfigRepository.

Contrato para leer y escribir la configuración del bot en PostgreSQL.
Incluye capital inicial, threshold de profit y fees por exchange.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class IConfigRepository(ABC):
    """Interfaz para el repositorio de configuración del bot."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Obtiene un valor de configuración por clave. Retorna None si no existe."""
        ...

    @abstractmethod
    async def set(self, key: str, value: str) -> None:
        """Persiste o actualiza un valor de configuración."""
        ...

    @abstractmethod
    async def get_capital_usdt(self) -> Decimal:
        """Retorna el capital inicial configurado en USDT."""
        ...

    @abstractmethod
    async def get_min_profit_threshold_pct(self) -> Decimal:
        """Retorna el threshold mínimo de profit en porcentaje."""
        ...

    @abstractmethod
    async def get_fee_buy(self, exchange: str) -> Decimal:
        """
        Retorna el fee de compra del exchange desde la tabla exchange_fees.
        Lanza excepción si el exchange no existe en DB.
        """
        ...

    @abstractmethod
    async def get_fee_sell(self, exchange: str) -> Decimal:
        """
        Retorna el fee de venta del exchange desde la tabla exchange_fees.
        Lanza excepción si el exchange no existe en DB.
        """
        ...

    @abstractmethod
    async def update_fees(
        self, exchange: str, fee_buy: Decimal, fee_sell: Decimal
    ) -> None:
        """Actualiza (upsert) fee_buy y fee_sell de un exchange."""
        ...

    @abstractmethod
    async def get_all_fees(self) -> list[dict[str, object]]:
        """
        Retorna lista con fee_buy y fee_sell para todos los exchanges registrados.
        Cada elemento: {"exchange_id": str, "fee_buy": Decimal, "fee_sell": Decimal}
        """
        ...
