"""
Puerto: IExchangePort.

Contrato que deben cumplir todos los adaptadores de exchanges.
El core depende de esta interfaz — nunca de ccxt.pro directamente.
"""

from abc import ABC, abstractmethod
from typing import Any

from core.entities.order_book import OrderBook


class IExchangePort(ABC):
    """Interfaz para adaptadores de exchanges vía WebSocket."""

    @abstractmethod
    async def connect(self) -> None:
        """Establece la conexión WebSocket con el exchange."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cierra la conexión WebSocket gracefully."""
        ...

    @abstractmethod
    async def watch_order_book(self, symbol: str) -> OrderBook:
        """
        Retorna el order book actualizado para el par dado.
        Bloquea hasta recibir la siguiente actualización del WS.
        """
        ...

    @property
    @abstractmethod
    def exchange_id(self) -> str:
        """Identificador del exchange: 'binance' | 'bybit' | 'kraken'."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True si la conexión WebSocket está activa."""
        ...

    @property
    @abstractmethod
    def feed_staleness_ms(self) -> int:
        """Milisegundos desde la última actualización recibida. -1 si nunca hubo dato."""
        ...

    @abstractmethod
    async def stream_forever(
        self,
        symbol: str,
        on_update: Any,  # Callable[[OrderBook], Awaitable[None]]
    ) -> None:
        """
        Bucle infinito que mantiene el feed WebSocket activo.

        Llama a watch_order_book en loop y pasa cada OrderBook a on_update.
        Gestiona la reconexión con backoff exponencial. El engine llama este
        método por exchange como tarea asyncio independiente.
        """
        ...
