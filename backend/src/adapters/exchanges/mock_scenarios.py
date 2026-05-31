"""Escenarios de precios para el MockExchangeAdapter."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MockScenario:
    name: str
    bid_premiums: dict[str, Decimal]  # offset sobre base_price para cada exchange
    base_price: Decimal = Decimal("97000.00")
    volume_btc: Decimal = Decimal("0.1")
    interval_seconds: float = 3.0
    jitter_pct: float = 0.05  # ±0.05% variación aleatoria


# Binance = exchange barato (premium=0, buy aquí)
# Bybit y Kraken = exchanges caros (premiums altos, sell aquí)
SPREAD_HIGH = MockScenario(
    name="spread_high",
    bid_premiums={
        "binance": Decimal("0"),
        "bybit": Decimal("600"),
        "kraken": Decimal("500"),
    },
)

SPREAD_MEDIUM = MockScenario(
    name="spread_medium",
    bid_premiums={
        "binance": Decimal("0"),
        "bybit": Decimal("100"),
        "kraken": Decimal("80"),
    },
)

SPREAD_BELOW_THRESHOLD = MockScenario(
    name="spread_below_threshold",
    bid_premiums={
        "binance": Decimal("0"),
        "bybit": Decimal("10"),
        "kraken": Decimal("8"),
    },
)

VOLATILE = MockScenario(
    name="volatile",
    bid_premiums={
        "binance": Decimal("0"),
        "bybit": Decimal("300"),
        "kraken": Decimal("250"),
    },
    jitter_pct=1.0,  # ±1% — genera mezcla de EXECUTED y REJECTED
)
