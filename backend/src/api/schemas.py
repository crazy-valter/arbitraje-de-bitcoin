"""
Pydantic schemas para requests y responses de la API REST.

Todos los valores monetarios se representan como str (Decimal serializado)
para evitar pérdida de precisión en JSON.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email del operador")
    password: str = Field(..., min_length=1, description="Password del operador")


class LoginResponse(BaseModel):
    ok: bool
    user: dict[str, str]
    expires_at: str


# ── Opportunities ─────────────────────────────────────────────────────────────

class OpportunityResponse(BaseModel):
    id: UUID
    buy_exchange: str
    sell_exchange: str
    buy_price: str           # Decimal como string para precisión
    sell_price: str
    gross_spread_pct: str
    total_fees_usdt: str
    slippage_usdt: str
    net_profit_usdt: str
    net_profit_pct: str
    max_volume_btc: str
    strategy: str
    score: float
    status: str
    detected_at: datetime
    executed_at: datetime | None = None
    # Desglose de fees por componente (CHG-009)
    trading_fee_buy_usdt: str = "0"
    trading_fee_sell_usdt: str = "0"
    withdrawal_fee_usdt: str = "0"
    network_latency_ms: str = "0"

    model_config = {"from_attributes": True}


class OpportunitiesListResponse(BaseModel):
    items: list[OpportunityResponse]
    total: int


# ── Trades ────────────────────────────────────────────────────────────────────

class TradeResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    side: str
    exchange: str
    price: str
    volume_btc: str
    fee_usdt: str
    slippage_usdt: str
    executed_at: datetime
    is_partial: bool
    # Campos extendidos (CHG-009)
    status: str = "PENDING"
    wallet_usdt_before: str = "0"
    wallet_usdt_after: str = "0"
    wallet_btc_before: str = "0"
    wallet_btc_after: str = "0"

    model_config = {"from_attributes": True}


class TradesListResponse(BaseModel):
    items: list[TradeResponse]
    total: int


# ── Wallets ───────────────────────────────────────────────────────────────────

class WalletBalanceResponse(BaseModel):
    exchange: str
    currency: str
    balance: str
    updated_at: datetime | None = None


class WalletsListResponse(BaseModel):
    items: list[WalletBalanceResponse]


# ── Config ────────────────────────────────────────────────────────────────────

class ConfigResponse(BaseModel):
    initial_capital_usdt: str
    min_profit_threshold_pct: str
    strategy_cross_exchange: bool
    strategy_triangular: bool
    strategy_statistical: bool
    mock_mode_enabled: bool = False  # True cuando el Modo Demo está activo


class ConfigUpdateRequest(BaseModel):
    initial_capital_usdt: Decimal | None = Field(
        default=None, gt=Decimal("0"), description="Capital inicial en USDT"
    )
    min_profit_threshold_pct: Decimal | None = Field(
        default=None, ge=Decimal("0"), description="Threshold mínimo de profit (%)"
    )
    strategy_cross_exchange: bool | None = None
    strategy_triangular: bool | None = None
    strategy_statistical: bool | None = None
    mock_mode_enabled: bool | None = None  # Activa/desactiva el Modo Demo con hot-swap


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricsResponse(BaseModel):
    opportunities_detected: int
    trades_simulated: int
    uptime_seconds: int
    win_rate_pct: float
    total_pnl_usdt: float
    connected_exchanges: int
    exchange_latencies: dict[str, int] = Field(default_factory=dict)
    timestamp: str


# ── Exchanges ─────────────────────────────────────────────────────────────────

class ExchangeInfo(BaseModel):
    """Metadatos + estado de un exchange del registry."""

    exchange_id: str
    display_name: str
    currencies: list[str]
    fees_taker: str          # Decimal serializado como string
    core: bool
    is_active: bool


class ExchangesListResponse(BaseModel):
    items: list[ExchangeInfo]


# ── Wallets (set balance) ─────────────────────────────────────────────────────

class WalletSetBalanceRequest(BaseModel):
    """Petición para establecer el balance de una wallet."""

    balance: Decimal = Field(
        ...,
        ge=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="Nuevo balance. Debe ser mayor o igual a 0, máximo 20 dígitos con 8 decimales.",
    )


class WalletSetBalanceResponse(BaseModel):
    """Respuesta tras actualizar el balance de una wallet."""

    exchange: str
    currency: str
    balance: str             # Decimal serializado como string
    updated: bool


# ── Fees ──────────────────────────────────────────────────────────────────────

class ExchangeFeeInfo(BaseModel):
    """Información de fees de un exchange individual."""

    exchange_id: str
    display_name: str
    fee_buy: Decimal
    fee_sell: Decimal

    model_config = ConfigDict(json_encoders={Decimal: str})


class ExchangeFeesListResponse(BaseModel):
    """Respuesta del listado de fees de todos los exchanges."""

    fees: list[ExchangeFeeInfo]


class ExchangeFeeUpdateRequest(BaseModel):
    """
    Petición para actualizar fees de un exchange.
    Los valores se expresan en porcentaje (ej. "0.10" = 0.10%).
    Rango válido: 0.00% a 9.99%.
    """

    fee_buy: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("9.99"),
        decimal_places=2,
        description="Fee de compra en porcentaje (ej. 0.10 = 0.10%)",
    )
    fee_sell: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("9.99"),
        decimal_places=2,
        description="Fee de venta en porcentaje (ej. 0.10 = 0.10%)",
    )


class ExchangeFeeUpdateResponse(BaseModel):
    """Respuesta tras actualizar los fees de un exchange."""

    exchange_id: str
    fee_buy: Decimal     # multiplicador guardado en DB (ej. 0.001)
    fee_sell: Decimal    # multiplicador guardado en DB (ej. 0.001)
    message: str

    model_config = ConfigDict(json_encoders={Decimal: str})


# ── Public Prices ──────────────────────────────────────────────────────────────

class ExchangePriceItem(BaseModel):
    """Precio BTC/USDT de un exchange individual para el endpoint público."""

    exchange: str
    symbol: str
    ask: str               # Decimal serializado: precio más bajo de venta
    bid: str               # Decimal serializado: precio más alto de compra
    mid: str               # Decimal serializado: (ask + bid) / 2
    is_stale: bool         # True si los datos tienen > 8s de antigüedad en Redis
    updated_at: datetime   # Timestamp del último order book recibido


class PublicPricesResponse(BaseModel):
    """Respuesta del endpoint público de precios."""

    prices: list[ExchangePriceItem]
    fetched_at: datetime   # Timestamp del servidor al responder
