"""
Seed del operador único desde variables de entorno.

Se ejecuta durante el lifespan de FastAPI al arrancar.
Si el usuario ya existe, no sobreescribe.
Requiere ADMIN_EMAIL y ADMIN_PASSWORD en el entorno.
"""

import os
import sys

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.admin_user_repo import AdminUserRepository
from adapters.security.hashing import get_password_hasher

logger = structlog.get_logger(__name__)


def _require_admin_env(key: str) -> str:
    """Obtiene variable de entorno requerida para el admin o aborta."""
    value = os.getenv(key)
    if not value:
        print(
            f"[FATAL] Variable '{key}' no definida. El servidor no arranca.",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


async def seed_admin_user(session: AsyncSession) -> None:
    """
    Crea el operador único desde ADMIN_EMAIL y ADMIN_PASSWORD.
    Idempotente: si ya existe, no hace nada.
    """
    admin_email = _require_admin_env("ADMIN_EMAIL")
    admin_password = _require_admin_env("ADMIN_PASSWORD")

    repo = AdminUserRepository(session)
    existing = await repo.find_by_email(admin_email)

    if existing is not None:
        # Usuario ya existe — no sobreescribir en cada reinicio
        logger.info("admin_seeder_skip", email=admin_email, reason="already_exists")
        return

    hasher = get_password_hasher()
    password_hash = hasher.hash(admin_password)
    await repo.create(email=admin_email, password_hash=password_hash)
    logger.info("admin_seeder_ok", email=admin_email)
