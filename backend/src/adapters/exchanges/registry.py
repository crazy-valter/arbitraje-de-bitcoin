"""
ExchangeRegistry — registro estático de exchanges soportados.

Define los metadatos de cada exchange (nombre, monedas, fees, tipo core).
Los exchanges core no son desactivables desde la UI.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExchangeMetadata:
    """Metadatos inmutables de un exchange."""

    display_name: str
    currencies: list[str]
    fees_taker: Decimal
    core: bool  # exchanges core no son desactivables desde la UI

    def __post_init__(self) -> None:
        # dataclass frozen=True — validaciones en post_init
        object.__setattr__(self, "currencies", list(self.currencies))


# Registro principal: exchange_id → metadatos
EXCHANGE_REGISTRY: dict[str, ExchangeMetadata] = {
    "binance": ExchangeMetadata(
        display_name="Binance",
        currencies=["USDT", "BTC", "ETH"],
        fees_taker=Decimal("0.001"),
        core=True,
    ),
    "bybit": ExchangeMetadata(
        display_name="Bybit",
        currencies=["USDT", "BTC", "ETH"],
        fees_taker=Decimal("0.001"),
        core=True,
    ),
    "kraken": ExchangeMetadata(
        display_name="Kraken",
        currencies=["USDT", "BTC", "ETH"],
        fees_taker=Decimal("0.0026"),
        core=True,
    ),
}


def list_all() -> dict[str, ExchangeMetadata]:
    """Retorna una copia del registro completo."""
    return dict(EXCHANGE_REGISTRY)


def is_core(exchange_id: str) -> bool:
    """Retorna True si el exchange es core (no desactivable)."""
    meta = EXCHANGE_REGISTRY.get(exchange_id)
    if meta is None:
        return False
    return meta.core


def get(exchange_id: str) -> ExchangeMetadata | None:
    """Retorna los metadatos de un exchange o None si no existe."""
    return EXCHANGE_REGISTRY.get(exchange_id)
