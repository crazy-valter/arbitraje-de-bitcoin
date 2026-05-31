"""fees_buy_sell_eth_wallets

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-30 00:00:00.000000

Dos cambios coordinados:
1. Renombra las columnas de exchange_fees:
   - maker_fee → fee_buy
   - taker_fee → fee_sell
   Se preservan todos los valores existentes (rename puro, sin pérdida de datos).

2. Seed de wallets ETH para los tres exchanges core:
   - (binance, ETH, 0.00000000)
   - (bybit,   ETH, 0.00000000)
   - (kraken,  ETH, 0.00000000)
   Usa ON CONFLICT DO NOTHING para garantizar idempotencia.
"""

from alembic import op

# revision identifiers, used by Alembic
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # --- Parte 1: renombrar columnas en exchange_fees ---
    op.alter_column(
        "exchange_fees",
        "maker_fee",
        new_column_name="fee_buy",
    )
    op.alter_column(
        "exchange_fees",
        "taker_fee",
        new_column_name="fee_sell",
    )

    # --- Parte 2: seed wallets ETH para los tres exchanges core ---
    op.execute(
        """
        INSERT INTO wallets (exchange, currency, balance) VALUES
            ('binance', 'ETH', '0.00000000'),
            ('bybit',   'ETH', '0.00000000'),
            ('kraken',  'ETH', '0.00000000')
        ON CONFLICT (exchange, currency) DO NOTHING
        """
    )


def downgrade() -> None:
    # Eliminar las wallets ETH insertadas en upgrade
    op.execute(
        """
        DELETE FROM wallets
        WHERE currency = 'ETH'
          AND exchange IN ('binance', 'bybit', 'kraken')
        """
    )

    # Restaurar nombres originales de columnas en exchange_fees
    op.alter_column(
        "exchange_fees",
        "fee_sell",
        new_column_name="taker_fee",
    )
    op.alter_column(
        "exchange_fees",
        "fee_buy",
        new_column_name="maker_fee",
    )
