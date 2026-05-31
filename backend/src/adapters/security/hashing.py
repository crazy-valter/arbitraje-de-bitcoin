"""
Hashing de contraseñas con Argon2id.

Parámetros OWASP (ganador del Password Hashing Competition 2015):
- memory_cost=19*1024 (19 MB) — resistente a ataques GPU/ASIC
- hash_len=32 (256 bits)
- parallelism=1
- salt_len=16
"""

from argon2 import PasswordHasher
from argon2.low_level import Type


def get_password_hasher() -> PasswordHasher:
    """Retorna el hasher configurado con parámetros OWASP para Argon2id."""
    return PasswordHasher(
        time_cost=2,
        memory_cost=19 * 1024,  # 19 MB — resistente a ataques GPU
        parallelism=1,
        hash_len=32,            # 256 bits
        salt_len=16,
        type=Type.ID,           # Argon2id: recomendado para passwords
    )
