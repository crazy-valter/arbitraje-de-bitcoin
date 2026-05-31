"""
Router de autenticación: login, refresh, logout.

Seguridad:
- Tokens SOLO en cookies HttpOnly, nunca en el body
- Rate limiting: 5/min en /login, 30/min en /refresh (slowapi)
- Fingerprint sha256 en payload del JWT
- Logout revoca ambos tokens en Redis
- Rotación de refresh token: el token usado se revoca inmediatamente
"""

import structlog
from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from redis.asyncio import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.cache.token_blacklist import revoke_token
from adapters.persistence.admin_user_repo import AdminUserRepository
from adapters.security.jwt_manager import (
    REFRESH_TOKEN_SECRET,
    create_token_pair,
    validate_refresh_token,
)
from api.dependencies import get_current_user, get_db, get_redis
from api.schemas import LoginRequest
from config.settings import get_settings
from core.services.auth_service import AuthService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


def _cookie_opts(is_prod: bool) -> dict[str, object]:
    """Opciones comunes para las cookies de sesión."""
    return {
        "httponly": True,
        "samesite": "strict",
        "secure": is_prod,
    }


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    POST /api/auth/login — autentica al operador.

    Rate limiting aplicado en main.py: 5 req/min por IP.
    Retorna perfil del usuario en el body; tokens solo en cookies HttpOnly.
    """
    repo = AdminUserRepository(session)
    service = AuthService(repo)
    token_data = await service.authenticate(credentials.email, credentials.password)

    is_prod = settings.environment == "production"
    opts = _cookie_opts(is_prod)

    response = JSONResponse(
        content={
            "ok": True,
            "user": {"email": token_data["email"]},
            "expires_at": token_data["expires_at"],
        }
    )
    response.set_cookie("access_token", token_data["access_token"], **opts)   # type: ignore[arg-type]
    response.set_cookie("refresh_token", token_data["refresh_token"], **opts) # type: ignore[arg-type]
    response.set_cookie("fingerprint", token_data["fingerprint"], **opts)     # type: ignore[arg-type]
    return response


@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    refresh_token: str | None = Cookie(default=None),
    fingerprint: str | None = Cookie(default=None),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """
    POST /api/auth/refresh — rota el par de tokens.

    Rate limiting aplicado en main.py: 30 req/min por IP.
    Revoca el refresh token usado e ige nuevo par.
    """
    if not refresh_token or not fingerprint:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="No autenticado")

    # Validar el refresh token actual
    token_data = validate_refresh_token(refresh_token, fingerprint)

    # Revocar el refresh token usado (rotación — limita la ventana de robo)
    jti = str(token_data.get("jti", ""))
    exp = float(token_data.get("exp", 0))  # type: ignore[arg-type]
    if jti:
        await revoke_token(redis, jti, exp)

    # Emitir nuevo par de tokens
    sub = str(token_data["sub"])
    new_tokens = create_token_pair(sub)

    is_prod = settings.environment == "production"
    opts = _cookie_opts(is_prod)

    response = JSONResponse(
        content={"ok": True, "expires_at": new_tokens["expires_at"]}
    )
    response.set_cookie("access_token", new_tokens["access_token"], **opts)   # type: ignore[arg-type]
    response.set_cookie("refresh_token", new_tokens["refresh_token"], **opts) # type: ignore[arg-type]
    response.set_cookie("fingerprint", new_tokens["fingerprint"], **opts)     # type: ignore[arg-type]
    return response


@router.post("/logout")
@limiter.limit("20/minute")
async def logout(
    request: Request,
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None),
    fingerprint: str | None = Cookie(default=None),
    redis: Redis = Depends(get_redis),
    _: dict[str, object] = Depends(get_current_user),
) -> JSONResponse:
    """
    POST /api/auth/logout — revoca ambos tokens en Redis y limpia las cookies.
    """
    # Revocar access token
    if access_token:
        try:
            from adapters.security.jwt_manager import ACCESS_TOKEN_SECRET
            data = jwt.decode(access_token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
            jti = str(data.get("jti", ""))
            exp = float(data.get("exp", 0))
            if jti:
                await revoke_token(redis, jti, exp)
        except JWTError:
            pass  # ya expirado — no importa

    # Revocar refresh token
    if refresh_token:
        try:
            data = jwt.decode(refresh_token, REFRESH_TOKEN_SECRET, algorithms=["HS256"])
            jti = str(data.get("jti", ""))
            exp = float(data.get("exp", 0))
            if jti:
                await revoke_token(redis, jti, exp)
        except JWTError:
            pass

    response = JSONResponse(content={"ok": True})
    response.delete_cookie("access_token", path="/", httponly=True, samesite="strict")
    response.delete_cookie("refresh_token", path="/", httponly=True, samesite="strict")
    response.delete_cookie("fingerprint", path="/", httponly=True, samesite="strict")
    logger.info("logout_ok")
    return response
