import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Lee la configuración del archivo alembic.ini
config = context.config

# Configura logging usando la sección [loggers] de alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importar Base con todos los modelos para que Alembic detecte cambios
from adapters.persistence.models import Base  # noqa: E402

target_metadata = Base.metadata


def get_url() -> str:
    # La URL de conexión se obtiene de settings para centralizar la configuración
    from config.settings import get_settings

    return get_settings().database_url


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline' (sin conexión real a la DB)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online' con driver async."""
    connectable = create_async_engine(get_url())
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
