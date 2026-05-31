"""
WalletRepository — implementación PostgreSQL para IWalletRepository.
"""

from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.exchanges.registry import EXCHANGE_REGISTRY
from adapters.persistence.models import Wallet as WalletModel
from ports.wallet_repo_port import IWalletRepository

logger = structlog.get_logger(__name__)


class WalletRepository(IWalletRepository):
    """Repositorio de balances simulados sobre PostgreSQL async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_balance(self, exchange: str, currency: str) -> Decimal:
        """Retorna el balance actual. Devuelve Decimal("0") si no existe."""
        result = await self._session.execute(
            select(WalletModel).where(
                WalletModel.exchange == exchange,
                WalletModel.currency == currency,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return Decimal("0")
        # format(..., 'f') evita notación científica (ej. 0E-8 → 0.00000000)
        return Decimal(format(model.balance, 'f'))

    async def set_balance(
        self,
        exchange: str,
        currency: str,
        amount: Decimal,
    ) -> None:
        """Upsert del balance para (exchange, currency)."""
        result = await self._session.execute(
            select(WalletModel).where(
                WalletModel.exchange == exchange,
                WalletModel.currency == currency,
            )
        )
        model = result.scalar_one_or_none()

        if model is None:
            model = WalletModel(exchange=exchange, currency=currency, balance=amount)
            self._session.add(model)
        else:
            model.balance = amount  # type: ignore[assignment]

        await self._session.commit()

    async def list_all(self) -> list[dict[str, object]]:
        """Lista todos los balances."""
        result = await self._session.execute(
            select(WalletModel).order_by(WalletModel.exchange, WalletModel.currency)
        )
        return [
            {
                "exchange": m.exchange,
                "currency": m.currency,
                "balance": Decimal(format(m.balance, 'f')),
                "updated_at": m.updated_at,
            }
            for m in result.scalars().all()
        ]

    async def initialize_defaults(
        self,
        exchanges: list[str],
        initial_usdt: Decimal,
    ) -> None:
        """
        Inicializa balances por defecto si no existen.

        Lee las currencies de cada exchange desde EXCHANGE_REGISTRY.
        La primera currency del registro recibe initial_usdt (fiat/stablecoin),
        las restantes se inicializan con 0 (BTC).
        Idempotente — no sobreescribe balances existentes.
        """
        for exchange in exchanges:
            meta = EXCHANGE_REGISTRY.get(exchange)
            # Si no está en el registry, usar USDT+BTC como fallback
            currencies = meta.currencies if meta else ["USDT", "BTC"]

            for idx, currency in enumerate(currencies):
                # Primera moneda (USDT/USD) recibe el capital inicial; resto = 0
                default_amount = initial_usdt if idx == 0 else Decimal("0")
                existing = await self.get_balance(exchange, currency)
                if existing == Decimal("0"):
                    await self.set_balance(exchange, currency, default_amount)
                    logger.info(
                        "wallet_initialized",
                        exchange=exchange,
                        currency=currency,
                        amount=str(default_amount),
                    )
