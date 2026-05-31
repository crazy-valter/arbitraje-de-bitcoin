"""
Entidades del dominio: Wallet y Balance.

Representan los balances simulados del operador en cada exchange.
El wallet tracking permite simular el efecto real de cada trade
sobre el capital disponible.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Balance:
    """Balance de una moneda específica en un exchange."""

    exchange: str
    currency: str   # "USDT" | "BTC"
    amount: Decimal

    def is_sufficient(self, required: Decimal) -> bool:
        """Verifica si el balance alcanza para cubrir el monto requerido."""
        return self.amount >= required


@dataclass
class Wallet:
    """Wallet simulada del operador — agrega balances por exchange y moneda."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    balances: dict[str, dict[str, Balance]] = field(default_factory=dict)
    # estructura: balances[exchange][currency] = Balance

    def get_balance(self, exchange: str, currency: str) -> Decimal:
        """Retorna el balance disponible. Devuelve cero si no existe."""
        default = Balance(exchange, currency, Decimal("0"))
        return self.balances.get(exchange, {}).get(currency, default).amount

    def set_balance(self, exchange: str, currency: str, amount: Decimal) -> None:
        """Actualiza el balance de una moneda en un exchange."""
        if exchange not in self.balances:
            self.balances[exchange] = {}
        self.balances[exchange][currency] = Balance(exchange, currency, amount)

    def debit(self, exchange: str, currency: str, amount: Decimal) -> bool:
        """
        Descuenta el monto del balance.
        Retorna False si el balance es insuficiente (no ejecuta el débito).
        """
        current = self.get_balance(exchange, currency)
        if current < amount:
            return False
        self.set_balance(exchange, currency, current - amount)
        return True

    def credit(self, exchange: str, currency: str, amount: Decimal) -> None:
        """Acredita el monto al balance."""
        current = self.get_balance(exchange, currency)
        self.set_balance(exchange, currency, current + amount)
