"""
Gestión de tokens JWT con secrets separados y fail-fast.

Seguridad:
- Access token (1h) y refresh token (8h) con secretos distintos
- Fingerprint sha256 en el payload (anti-XSS)
- JTI único por token para blacklist en Redis
- _require_secret(): sys.exit(1) si falta ACCESS_TOKEN_SECRET o REFRESH_TOKEN_SECRET
"""

import hashlib
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from jose import JWTError, jwt

# Falla al importar el módulo si los secretos no están definidos
# Esto asegura que el servidor no arranque sin configuración de seguridad


def _require_secret(key: str) -> str:
    """Obtiene un secret del entorno o aborta con sys.exit(1) si no existe."""
    value = os.getenv(key)
    if not value:
        print(
            f"[FATAL] Variable '{key}' no definida. El servidor no arranca.",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


ACCESS_TOKEN_SECRET: str = _require_secret("ACCESS_TOKEN_SECRET")
REFRESH_TOKEN_SECRET: str = _require_secret("REFRESH_TOKEN_SECRET")

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_HOURS = 1
_REFRESH_TOKEN_EXPIRE_HOURS = 8


def create_token_pair(email: str) -> dict[str, str]:
    """
    Genera un par de tokens JWT (access + refresh) con fingerprint compartido.

    El fingerprint viaja:
    - Como sha256(fp) dentro del payload del JWT (no legible sin el secreto)
    - Como valor crudo en cookie HttpOnly (nunca accesible por JavaScript)

    Retorna los tokens, el fingerprint crudo y el timestamp de expiración del access token.
    Los tokens NO se incluyen en el body de respuesta — se setean como cookies.
    """
    fingerprint = secrets.token_hex(20)  # 40 bytes aleatorios
    fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
    now = datetime.now(UTC)

    access_payload: dict[str, object] = {
        "sub": email,
        "fingerprint": fp_hash,
        "jti": str(uuid4()),
        "exp": now + timedelta(hours=_ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": now,
    }
    refresh_payload: dict[str, object] = {
        "sub": email,
        "fingerprint": fp_hash,  # mismo fingerprint en ambos tokens
        "jti": str(uuid4()),
        "exp": now + timedelta(hours=_REFRESH_TOKEN_EXPIRE_HOURS),
        "iat": now,
        "type": "refresh",
    }

    access_token = jwt.encode(access_payload, ACCESS_TOKEN_SECRET, algorithm=_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, REFRESH_TOKEN_SECRET, algorithm=_ALGORITHM)
    expires_at = (now + timedelta(hours=_ACCESS_TOKEN_EXPIRE_HOURS)).isoformat()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "fingerprint": fingerprint,
        "expires_at": expires_at,
        "email": email,
    }


def validate_access_token(token: str, fingerprint: str) -> dict[str, object]:
    """
    Valida el access token y verifica el fingerprint.

    Lanza HTTPException 401 en caso de:
    - Token inválido o expirado
    - Fingerprint no coincide (posible token robado)
    - Token revocado (verificado vía is_token_revoked antes de llamar aquí)
    """
    try:
        data: dict[str, object] = jwt.decode(
            token, ACCESS_TOKEN_SECRET, algorithms=[_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado") from None

    expected_fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
    if expected_fp_hash != data.get("fingerprint"):
        raise HTTPException(status_code=401, detail="Sesión inválida")

    return data


def validate_refresh_token(token: str, fingerprint: str) -> dict[str, object]:
    """
    Valida el refresh token y verifica el fingerprint.
    Confirma que el token tiene type="refresh".
    """
    try:
        data: dict[str, object] = jwt.decode(
            token, REFRESH_TOKEN_SECRET, algorithms=[_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado") from None

    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Tipo de token inválido")

    expected_fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
    if expected_fp_hash != data.get("fingerprint"):
        raise HTTPException(status_code=401, detail="Sesión inválida")

    return data
