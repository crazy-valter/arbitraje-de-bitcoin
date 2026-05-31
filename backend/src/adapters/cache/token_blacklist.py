"""
Blacklist de tokens JWT en Redis.

Al hacer logout, los JTIs del access y refresh token se agregan a Redis
con TTL igual al tiempo restante hasta expiración.
Esto garantiza logout real sin necesidad de invalidar los secretos.
"""

from datetime import UTC, datetime

from redis.asyncio import Redis


async def revoke_token(redis: Redis, jti: str, exp: int | float) -> None:
    """
    Revoca un token por su JTI.
    El TTL en Redis es el tiempo restante hasta la expiración del token.
    Si el token ya expiró, no se hace nada (ya es inválido por JWT).
    """
    remaining = int(exp - datetime.now(UTC).timestamp())
    if remaining > 0:
        await redis.setex(f"revoked:{jti}", remaining, "1")


async def is_token_revoked(redis: Redis, jti: str) -> bool:
    """
    Verifica si un token fue revocado (está en la blacklist).
    Retorna True si el JTI existe en Redis → token inválido.
    """
    return await redis.exists(f"revoked:{jti}") == 1  # type: ignore[no-any-return]
