"""
Entidades del dominio: OrderBook y OrderBookLevel.

Representan el estado actual del mercado para un par en un exchange.
Son inmutables — cada actualización del WS genera nuevas instancias.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class OrderBookLevel:
    """Nivel de precio en el order book (precio + cantidad disponible)."""

    price: Decimal
    quantity: Decimal


@dataclass
class OrderBook:
    """Estado actual del order book de un par en un exchange."""

    exchange: str
    symbol: str  # "BTC/USDT"
    best_ask: OrderBookLevel  # precio más bajo al que alguien vende (compramos aquí)
    best_bid: OrderBookLevel  # precio más alto al que alguien compra (vendemos aquí)
    timestamp: datetime
    is_stale: bool = False  # True si el TTL de Redis expiró (dato desactualizado)
    staleness_ms: int = 0  # milisegundos desde la última actualización del feed WS
