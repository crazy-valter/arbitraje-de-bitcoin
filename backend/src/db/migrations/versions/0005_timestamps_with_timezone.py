"""timestamps_with_timezone

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-30 00:00:00.000000

Convierte todas las columnas TIMESTAMP WITHOUT TIME ZONE a
TIMESTAMP WITH TIME ZONE. Los valores existentes se interpretan
como UTC (que es la zona que siempre usó el sistema).

Motivación: asyncpg >= 0.24 rechaza datetime timezone-aware al
insertar en columnas TIMESTAMP WITHOUT TIME ZONE, causando que
todos los registros fallen silenciosamente en modo demo.
"""

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE opportunities "
        "ALTER COLUMN detected_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING detected_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE opportunities "
        "ALTER COLUMN executed_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING executed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE trades "
        "ALTER COLUMN executed_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING executed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE wallets "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE system_config "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE exchange_fees "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE admin_users "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE exchange_config "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE exchange_config "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE opportunities "
        "ALTER COLUMN detected_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING detected_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE opportunities "
        "ALTER COLUMN executed_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING executed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE trades "
        "ALTER COLUMN executed_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING executed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE wallets "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE system_config "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE exchange_fees "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE admin_users "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE exchange_config "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE exchange_config "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
