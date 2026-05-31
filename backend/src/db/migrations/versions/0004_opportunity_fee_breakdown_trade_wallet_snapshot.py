"""opportunity_fee_breakdown_trade_wallet_snapshot

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-30 00:00:00.000000

Agrega columnas de desglose de fees en opportunities y snapshots de
wallet en trades para soportar la vista de transacciones simuladas (CHG-009).

Todas las columnas son nullable con server_default="0" para no romper
registros historicos existentes.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # --- Nuevas columnas en opportunities: desglose de fees ---
    op.add_column(
        "opportunities",
        sa.Column(
            "trading_fee_buy_usdt",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "trading_fee_sell_usdt",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "withdrawal_fee_usdt",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "network_latency_ms",
            sa.Numeric(10, 2),
            nullable=True,
            server_default="0",
        ),
    )

    # --- Nuevas columnas en trades: snapshot de wallet antes/despues ---
    op.add_column(
        "trades",
        sa.Column(
            "wallet_usdt_before",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "wallet_usdt_after",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "wallet_btc_before",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "wallet_btc_after",
            sa.Numeric(20, 8),
            nullable=True,
            server_default="0",
        ),
    )


def downgrade() -> None:
    # --- Eliminar columnas de trades ---
    op.drop_column("trades", "wallet_btc_after")
    op.drop_column("trades", "wallet_btc_before")
    op.drop_column("trades", "wallet_usdt_after")
    op.drop_column("trades", "wallet_usdt_before")

    # --- Eliminar columnas de opportunities ---
    op.drop_column("opportunities", "network_latency_ms")
    op.drop_column("opportunities", "withdrawal_fee_usdt")
    op.drop_column("opportunities", "trading_fee_sell_usdt")
    op.drop_column("opportunities", "trading_fee_buy_usdt")
