"""
Puerto: IOrderBookStore.

Contrato para el almacenamiento y recuperación de order books en caché.
La implementación concreta usa Redis con TTL de 10 segundos.
"""

from abc import ABC, abstractmethod

from core.entities.order_book import OrderBook


class IOrderBookStore(ABC):
    """Interfaz para el store de order books en caché."""

    @abstractmethod
    async def save(self, order_book: OrderBook) -> None:
        """Persiste el order book con TTL de 10 segundos."""
        ...

    @abstractmethod
    async def get(self, exchange: str, symbol: str) -> OrderBook | None:
        """
        Recupera el order book más reciente.
        Retorna None si no existe o si el TTL expiró.
        El campo is_stale=True indica que el dato está cerca de expirar.
        """
        ...

    @abstractmethod
    async def get_all_exchanges(self, symbol: str) -> list[OrderBook]:
        """Retorna los order books disponibles de todos los exchanges para un símbolo."""
        ...
