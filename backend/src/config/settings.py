"""
Settings del backend via pydantic-settings.

Los secrets (ACCESS_TOKEN_SECRET, REFRESH_TOKEN_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD)
se validan en sus módulos respectivos con _require_secret() → sys.exit(1) si faltan.
Aquí solo se definen campos con defaults seguros para desarrollo.
"""

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql+asyncpg://arbitrage_user:devpassword@db:5432/arbitrage_db"

    # Redis
    redis_url: str = "redis://cache:6379/0"

    # Entorno
    environment: str = "development"
    log_level: str = "INFO"

    # CORS — pydantic-settings v2 no parsea List[str] desde env vars sin JSON.
    # Se declara como str y se divide por coma en la property.
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:80"

    # Exchanges (opcionales — feeds públicos por defecto)
    binance_api_key: str = ""
    binance_secret: str = ""
    kraken_api_key: str = ""
    kraken_secret: str = ""
    bybit_api_key: str = ""
    bybit_secret: str = ""

    # Configuración operacional (fallback si no está en DB)
    initial_capital_usdt: Decimal = Decimal("10000")
    min_profit_threshold_pct: Decimal = Decimal("0.15")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
