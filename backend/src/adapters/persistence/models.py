"""
SQLAlchemy 2 — Modelos ORM del sistema de arbitraje.

Tablas:
- opportunities: oportunidades detectadas (ejecutadas y descartadas)
- trades: trades simulados vinculados a oportunidades
- wallets: balances por exchange y moneda
- system_config: configuración del bot en tiempo de ejecución
- exchange_fees: fees actualizables por exchange
- admin_users: operador único del sistema
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Opportunity(Base):
    """Oportunidad de arbitraje detectada por el motor."""

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    buy_exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    sell_exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    sell_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    gross_spread_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    total_fees_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    slippage_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    net_profit_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    net_profit_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    max_volume_btc: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    strategy: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'cross_exchange' | 'triangular' | 'statistical'
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'DETECTED' | 'EXECUTING' | 'EXECUTED' | 'REJECTED' | 'FAILED'
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Desglose de fees por componente (CHG-009)
    trading_fee_buy_usdt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )
    trading_fee_sell_usdt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )
    withdrawal_fee_usdt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )
    network_latency_ms: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True, server_default=text("0")
    )

    __table_args__ = (
        # Queries frecuentes: listar por tiempo descendente
        Index("idx_opportunities_detected_at", "detected_at"),
        # Filtro por estado
        Index("idx_opportunities_status", "status"),
        # P&L acumulado: filtrar solo ejecutadas
        Index(
            "idx_opportunities_status_executed",
            "status",
            postgresql_where="status = 'EXECUTED'",
        ),
    )


class Trade(Base):
    """Trade simulado (compra o venta) vinculado a una oportunidad."""

    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # 'BUY' | 'SELL'
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume_btc: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fee_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    slippage_usdt: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Snapshot de wallet antes/despues de la ejecucion (CHG-009)
    wallet_usdt_before: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )
    wallet_usdt_after: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )
    wallet_btc_before: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )
    wallet_btc_after: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True, server_default=text("0")
    )

    __table_args__ = (
        # Historial de trades por oportunidad
        Index("idx_trades_opportunity_id", "opportunity_id"),
    )


class Wallet(Base):
    """Balance simulado de wallet por exchange y moneda."""

    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)  # 'USDT' | 'BTC'
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # Un solo registro por (exchange, moneda)
        UniqueConstraint("exchange", "currency", name="uq_wallets_exchange_currency"),
    )


class SystemConfig(Base):
    """Configuración del bot en tiempo de ejecución (clave-valor)."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExchangeFee(Base):
    """Fees por exchange — actualizables sin reiniciar el bot."""

    __tablename__ = "exchange_fees"

    exchange: Mapped[str] = mapped_column(String(20), primary_key=True)
    fee_buy: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    fee_sell: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AdminUser(Base):
    """Operador único del sistema — seed desde .env al arrancar."""

    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExchangeConfig(Base):
    """Estado activo/inactivo de cada exchange — gestionado desde la UI."""

    __tablename__ = "exchange_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
