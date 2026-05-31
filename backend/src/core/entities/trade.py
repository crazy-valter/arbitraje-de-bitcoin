"""
Entidades del dominio: SimulatedTrade y TradeStatus.

Un trade simulado representa la compra o venta ejecutada como parte
de una oportunidad de arbitraje. Siempre están vinculados a una oportunidad.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class TradeStatus(StrEnum):
    """Estado de ejecución de un trade simulado."""

    PENDING = "PENDING"        # en cola, no ejecutado aún
    EXECUTED = "EXECUTED"      # ejecutado correctamente
    PARTIAL = "PARTIAL"        # ejecutado parcialmente por liquidez insuficiente
    FAILED = "FAILED"          # error durante la simulación


class TradeSide(StrEnum):
    """Lado del trade: compra o venta."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class SimulatedTrade:
    """Trade simulado vinculado a una oportunidad de arbitraje."""

    opportunity_id: uuid.UUID
    side: TradeSide
    exchange: str
    price: Decimal
    volume_btc: Decimal
    fee_usdt: Decimal
    slippage_usdt: Decimal
    executed_at: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: TradeStatus = TradeStatus.PENDING
    is_partial: bool = False
    # Snapshot de wallet antes/despues de la ejecucion (CHG-009)
    wallet_usdt_before: Decimal = Decimal("0")
    wallet_usdt_after: Decimal = Decimal("0")
    wallet_btc_before: Decimal = Decimal("0")
    wallet_btc_after: Decimal = Decimal("0")

    @property
    def total_cost_usdt(self) -> Decimal:
        """Costo total del trade incluyendo fees y slippage."""
        return self.price * self.volume_btc + self.fee_usdt + self.slippage_usdt
