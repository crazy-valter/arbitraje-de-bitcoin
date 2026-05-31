"""create_tables

Revision ID: 0001
Revises:
Create Date: 2026-05-29 00:00:00.000000

Crea las 6 tablas del sistema:
- opportunities: oportunidades de arbitraje detectadas
- trades: trades simulados (compra/venta) vinculados a oportunidades
- wallets: balances simulados por exchange y moneda
- system_config: configuración clave-valor del bot
- exchange_fees: fees de cada exchange (actualizables sin reiniciar)
- admin_users: operador único del sistema
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # --- admin_users ---
    op.create_table(
        "admin_users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # --- opportunities ---
    op.create_table(
        "opportunities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("buy_exchange", sa.String(length=20), nullable=False),
        sa.Column("sell_exchange", sa.String(length=20), nullable=False),
        sa.Column("buy_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("sell_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("gross_spread_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("total_fees_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column("slippage_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column("net_profit_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column("net_profit_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("max_volume_btc", sa.Numeric(20, 8), nullable=False),
        sa.Column("strategy", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Índice principal: consultas por tiempo descendente
    op.create_index(
        "idx_opportunities_detected_at",
        "opportunities",
        [sa.text("detected_at DESC")],
    )
    # Índice por estado para filtros frecuentes
    op.create_index("idx_opportunities_status", "opportunities", ["status"])
    # Índice parcial para P&L acumulado (solo ejecutadas)
    op.create_index(
        "idx_opportunities_status_executed",
        "opportunities",
        ["status"],
        postgresql_where=sa.text("status = 'EXECUTED'"),
    )

    # --- trades ---
    op.create_table(
        "trades",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume_btc", sa.Numeric(20, 8), nullable=False),
        sa.Column("fee_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column("slippage_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_partial", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_trades_opportunity_id", "trades", ["opportunity_id"])

    # --- wallets ---
    op.create_table(
        "wallets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("balance", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange", "currency", name="uq_wallets_exchange_currency"),
    )

    # --- system_config ---
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # --- exchange_fees ---
    op.create_table(
        "exchange_fees",
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("maker_fee", sa.Numeric(6, 4), nullable=False),
        sa.Column("taker_fee", sa.Numeric(6, 4), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("exchange"),
    )

    # Insertar fees iniciales por defecto
    op.execute(
        """
        INSERT INTO exchange_fees (exchange, maker_fee, taker_fee) VALUES
            ('binance', 0.0010, 0.0010),
            ('bybit',   0.0010, 0.0010),
            ('kraken',  0.0026, 0.0026)
        ON CONFLICT (exchange) DO NOTHING
        """
    )

    # Insertar configuración inicial del bot
    op.execute(
        """
        INSERT INTO system_config (key, value) VALUES
            ('INITIAL_CAPITAL_USDT',     '10000.00'),
            ('MIN_PROFIT_THRESHOLD_PCT', '0.15'),
            ('STRATEGY_CROSS_EXCHANGE',  'true'),
            ('STRATEGY_TRIANGULAR',      'false'),
            ('STRATEGY_STATISTICAL',     'false')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("exchange_fees")
    op.drop_table("system_config")
    op.drop_table("wallets")
    op.drop_index("idx_trades_opportunity_id", table_name="trades")
    op.drop_table("trades")
    op.drop_index("idx_opportunities_status_executed", table_name="opportunities")
    op.drop_index("idx_opportunities_status", table_name="opportunities")
    op.drop_index("idx_opportunities_detected_at", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_table("admin_users")
