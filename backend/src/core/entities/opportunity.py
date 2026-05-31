"""
Entidades del dominio: ArbitrageOpportunity y OpportunityStatus.

Una oportunidad representa una divergencia de precios entre exchanges
que —después de descontar fees y slippage— genera profit neto positivo.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class OpportunityStatus(StrEnum):
    """Estado del ciclo de vida de una oportunidad detectada."""

    DETECTED = "DETECTED"      # detectada, aún no ejecutada
    EXECUTING = "EXECUTING"    # simulación en curso
    EXECUTED = "EXECUTED"      # trade simulado completado con éxito
    REJECTED = "REJECTED"      # descartada por scoring o filtros
    FAILED = "FAILED"          # error durante la simulación


@dataclass
class ArbitrageOpportunity:
    """Oportunidad de arbitraje entre dos exchanges."""

    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal        # best ask del exchange comprador
    sell_price: Decimal       # best bid del exchange vendedor
    gross_spread_pct: Decimal
    total_fees_usdt: Decimal
    slippage_usdt: Decimal
    net_profit_usdt: Decimal
    net_profit_pct: Decimal
    max_volume_btc: Decimal   # limitado por liquidez del order book
    strategy: str             # "cross_exchange" | "triangular" | "statistical"
    score: float              # 0.0-1.0, puntaje de prioridad
    detected_at: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: OpportunityStatus = OpportunityStatus.DETECTED
    executed_at: datetime | None = None
    # Desglose de fees por componente (CHG-009)
    trading_fee_buy_usdt: Decimal = Decimal("0")
    trading_fee_sell_usdt: Decimal = Decimal("0")
    withdrawal_fee_usdt: Decimal = Decimal("0")
    network_latency_ms: Decimal = Decimal("0")
