"""
ConfigRepository — implementación PostgreSQL para IConfigRepository.

Lee y escribe configuración del bot desde las tablas:
- system_config: capital, threshold, feature flags
- exchange_fees: fees por exchange
"""

from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.models import ExchangeFee, SystemConfig
from ports.config_port import IConfigRepository

logger = structlog.get_logger(__name__)


class ConfigRepository(IConfigRepository):
    """Repositorio de configuración sobre PostgreSQL async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        """Obtiene un valor de configuración por clave."""
        result = await self._session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        model = result.scalar_one_or_none()
        return model.value if model else None

    async def set(self, key: str, value: str) -> None:
        """Persiste o actualiza un valor de configuración (upsert)."""
        result = await self._session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        model = result.scalar_one_or_none()

        if model is None:
            model = SystemConfig(key=key, value=value)
            self._session.add(model)
        else:
            model.value = value  # type: ignore[assignment]

        await self._session.commit()

    async def get_capital_usdt(self) -> Decimal:
        """Retorna el capital inicial en USDT. Default: 10000."""
        value = await self.get("INITIAL_CAPITAL_USDT")
        return Decimal(value) if value else Decimal("10000.00")

    async def get_min_profit_threshold_pct(self) -> Decimal:
        """Retorna el threshold mínimo de profit. Default: 0.15%."""
        value = await self.get("MIN_PROFIT_THRESHOLD_PCT")
        return Decimal(value) if value else Decimal("0.15")

    async def get_fee_buy(self, exchange: str) -> Decimal:
        """Retorna el fee de compra del exchange. Retorna 0.001 si no existe en DB."""
        result = await self._session.execute(
            select(ExchangeFee).where(ExchangeFee.exchange == exchange.lower())
        )
        fee_model = result.scalar_one_or_none()
        if fee_model is not None:
            return Decimal(str(fee_model.fee_buy))

        logger.warning("exchange_fee_not_in_db", exchange=exchange, field="fee_buy")
        raise ValueError(f"No fee_buy encontrado en DB para exchange: {exchange}")

    async def get_fee_sell(self, exchange: str) -> Decimal:
        """Retorna el fee de venta del exchange. Retorna 0.001 si no existe en DB."""
        result = await self._session.execute(
            select(ExchangeFee).where(ExchangeFee.exchange == exchange.lower())
        )
        fee_model = result.scalar_one_or_none()
        if fee_model is not None:
            return Decimal(str(fee_model.fee_sell))

        logger.warning("exchange_fee_not_in_db", exchange=exchange, field="fee_sell")
        raise ValueError(f"No fee_sell encontrado en DB para exchange: {exchange}")

    async def update_fees(
        self, exchange: str, fee_buy: Decimal, fee_sell: Decimal
    ) -> None:
        """Upsert de fee_buy y fee_sell para un exchange."""
        result = await self._session.execute(
            select(ExchangeFee).where(ExchangeFee.exchange == exchange.lower())
        )
        model = result.scalar_one_or_none()

        if model is None:
            model = ExchangeFee(
                exchange=exchange.lower(),
                fee_buy=fee_buy,
                fee_sell=fee_sell,
            )
            self._session.add(model)
        else:
            model.fee_buy = fee_buy  # type: ignore[assignment]
            model.fee_sell = fee_sell  # type: ignore[assignment]

        await self._session.commit()
        logger.info(
            "exchange_fees_updated",
            exchange=exchange,
            fee_buy=float(fee_buy),
            fee_sell=float(fee_sell),
        )

    async def get_all_fees(self) -> list[dict[str, object]]:
        """Retorna lista con fee_buy y fee_sell de todos los exchanges en DB."""
        result = await self._session.execute(select(ExchangeFee))
        rows = result.scalars().all()
        return [
            {
                "exchange_id": row.exchange,
                "fee_buy": Decimal(str(row.fee_buy)),
                "fee_sell": Decimal(str(row.fee_sell)),
            }
            for row in rows
        ]

    async def initialize_defaults(self, capital: Decimal, threshold: Decimal) -> None:
        """
        Inserta los valores por defecto de system_config solo si no existen.

        Upsert conservador: si ya hay un registro previo (reinicio del contenedor),
        no sobrescribe — se respetan los valores que el operador haya configurado.

        Valores por defecto de primera instalación:
        - MOCK_MODE_ENABLED = true  → arrancar en modo demo para validación visual inmediata
        - ENGINE_PAUSED     = true  → el motor no opera hasta que el operador lo active
        """
        defaults = {
            "INITIAL_CAPITAL_USDT":     str(capital),
            "MIN_PROFIT_THRESHOLD_PCT": str(threshold),
            "MOCK_MODE_ENABLED":        "true",
            "ENGINE_PAUSED":            "true",
        }
        for key, value in defaults.items():
            existing = await self.get(key)
            if existing is None:
                model = SystemConfig(key=key, value=value)
                self._session.add(model)
                logger.info("config_initialized", key=key, value=value)
        await self._session.commit()

    async def get_mock_mode_enabled(self) -> bool:
        """Retorna True si el Modo Demo (mock) está activo. Default: True."""
        value = await self.get("MOCK_MODE_ENABLED")
        return (value if value is not None else "true").lower() == "true"

    async def get_engine_paused(self) -> bool:
        """Retorna True si el motor arranca pausado. Default: True."""
        value = await self.get("ENGINE_PAUSED")
        return (value if value is not None else "true").lower() == "true"
