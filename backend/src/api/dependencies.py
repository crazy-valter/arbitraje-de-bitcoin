"""
FastAPI Dependency Injection — dependencias compartidas entre routers.

get_current_user: lee access_token y fingerprint desde cookies HttpOnly.
get_redis: retorna el cliente Redis async del estado de la app.
get_db: retorna una AsyncSession para uso en routers.
"""

from collections.abc import AsyncGenerator

import structlog
from fastapi import Cookie, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.cache.token_blacklist import is_token_revoked
from adapters.security.jwt_manager import validate_access_token
from db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provee una AsyncSession con cierre automático al finalizar el request."""
    async with AsyncSessionLocal() as session:
        yield session


def get_redis(request: Request) -> Redis:
    """Retorna el cliente Redis almacenado en el estado de la app."""
    redis: Redis = request.app.state.redis
    return redis


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None),
    fingerprint: str | None = Cookie(default=None),
) -> dict[str, object]:
    """
    Dependencia de autenticación para endpoints protegidos.

    Lee access_token y fingerprint desde cookies HttpOnly.
    Valida el JWT, el fingerprint (anti-XSS) y la blacklist de Redis.
    Lanza HTTPException 401 si cualquier validación falla.
    """
    if not access_token or not fingerprint:
        raise HTTPException(status_code=401, detail="No autenticado")

    # Validar JWT + fingerprint
    token_data = validate_access_token(access_token, fingerprint)

    # Verificar blacklist en Redis (logout real)
    redis = get_redis(request)
    jti = str(token_data.get("jti", ""))
    if jti and await is_token_revoked(redis, jti):
        raise HTTPException(status_code=401, detail="Sesión revocada")

    return token_data
