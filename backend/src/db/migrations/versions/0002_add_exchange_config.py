"""add_exchange_config

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30 00:00:00.000000

Crea la tabla exchange_config para almacenar el estado activo/inactivo
de cada exchange. Los exchanges se registran con is_active=TRUE por defecto.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # --- exchange_config ---
    op.create_table(
        "exchange_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exchange_id", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange_id", name="uq_exchange_config_exchange_id"),
    )

    # Insertar los tres exchanges core activos por defecto
    op.execute(
        """
        INSERT INTO exchange_config (exchange_id, is_active) VALUES
            ('binance', true),
            ('bybit',   true),
            ('kraken',  true)
        ON CONFLICT (exchange_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("exchange_config")
