"""
Servicio de autenticación del operador.

Seguridad:
- Tiempo constante anti-enumeración: ejecuta el hash aunque el usuario no exista
- Mensaje de error idéntico para usuario inexistente y password incorrecto
- Delega la creación de tokens a jwt_manager (que aplica fingerprint)
"""

import structlog
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException

from adapters.security.hashing import get_password_hasher
from adapters.security.jwt_manager import create_token_pair
from ports.auth_repo_port import IAdminUserRepository

logger = structlog.get_logger(__name__)

# Mensaje genérico — no distingue usuario vs password para anti-enumeración
_AUTH_ERROR_DETAIL = "Credenciales inválidas"


class AuthService:
    """Servicio de autenticación del operador único."""

    def __init__(self, repo: IAdminUserRepository) -> None:
        self._repo = repo

    async def authenticate(self, email: str, password: str) -> dict[str, str]:
        """
        Autentica al operador con email y password.

        Anti-enumeración: si el usuario no existe, ejecuta el hash de todas formas
        para igualar el tiempo de respuesta con un intento fallido real.

        Retorna los datos del token (access_token, refresh_token, fingerprint, expires_at, email).
        Lanza HTTPException 401 si las credenciales son incorrectas.
        """
        ph = get_password_hasher()
        user = await self._repo.find_by_email(email)

        if user is None:
            # Tiempo constante — ejecutar hash aunque el usuario no exista
            ph.hash(password)
            # Mismo event name que password incorrecto — anti-enumeración en logs
            logger.warning("auth_failed", reason="user_not_found")
            raise HTTPException(status_code=401, detail=_AUTH_ERROR_DETAIL)

        try:
            ph.verify(user.password_hash, password)
        except VerifyMismatchError:
            # Mismo event name que usuario no encontrado — anti-enumeración en logs
            logger.warning("auth_failed", reason="wrong_password")
            raise HTTPException(status_code=401, detail=_AUTH_ERROR_DETAIL) from None

        logger.info("auth_success", email=email)
        return create_token_pair(user.email)
