"""
Adaptador: AdminUserRepository → PostgreSQL.

Implementa IAdminUserRepository para búsqueda y creación del operador único.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.models import AdminUser
from ports.auth_repo_port import AdminUserRecord, IAdminUserRepository

logger = structlog.get_logger(__name__)


class AdminUserRepository(IAdminUserRepository):
    """Repositorio del usuario administrador sobre PostgreSQL async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> AdminUserRecord | None:
        """Busca el operador por email. Retorna None si no existe."""
        result = await self._session.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return AdminUserRecord(email=user.email, password_hash=user.password_hash)

    async def create(self, email: str, password_hash: str) -> None:
        """
        Crea el usuario administrador si no existe.
        No lanza error si ya existe — idempotente para el seeder.
        """
        existing = await self.find_by_email(email)
        if existing is not None:
            logger.info("admin_user_already_exists", email=email)
            return

        user = AdminUser(email=email, password_hash=password_hash)
        self._session.add(user)
        await self._session.commit()
        logger.info("admin_user_created", email=email)
