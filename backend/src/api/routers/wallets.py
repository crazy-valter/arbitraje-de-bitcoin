"""
Router: /api/wallets — balances simulados por exchange y moneda.

GET /api/wallets                              → lista todos los balances
PUT /api/wallets/{exchange}/{currency}        → establece un nuevo balance
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.cache.event_publisher import RedisEventPublisher
from adapters.exchanges.registry import EXCHANGE_REGISTRY
from adapters.persistence.wallet_repo import WalletRepository
from api.dependencies import get_current_user, get_db, get_redis
from api.schemas import (
    WalletBalanceResponse,
    WalletSetBalanceRequest,
    WalletSetBalanceResponse,
    WalletsListResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/wallets", tags=["wallets"])


@router.get("", response_model=WalletsListResponse)
async def list_wallets(
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletsListResponse:
    """Lista todos los balances simulados por exchange y moneda."""
    repo = WalletRepository(session)
    all_balances = await repo.list_all()
    return WalletsListResponse(
        items=[
            WalletBalanceResponse(
                exchange=str(b["exchange"]),
                currency=str(b["currency"]),
                balance=str(b["balance"]),
                updated_at=b.get("updated_at"),  # type: ignore[arg-type]
            )
            for b in all_balances
        ]
    )


@router.put("/{exchange}/{currency}", response_model=WalletSetBalanceResponse)
async def set_wallet_balance(
    exchange: str,
    currency: str,
    body: WalletSetBalanceRequest,
    request: Request,
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WalletSetBalanceResponse:
    """
    Establece el balance de una wallet (exchange + currency).

    Seguridad:
    - exchange y currency se validan contra EXCHANGE_REGISTRY (whitelist)
    - balance debe ser > 0 (validado en schema Pydantic)
    - Emite evento SSE wallet_update tras la actualización exitosa
    """
    # Validación whitelist de exchange
    meta = EXCHANGE_REGISTRY.get(exchange)
    if meta is None:
        raise HTTPException(
            status_code=422,
            detail=f"Exchange '{exchange}' no registrado.",
        )

    # Validación whitelist de currency para este exchange
    if currency not in meta.currencies:
        raise HTTPException(
            status_code=422,
            detail=f"Moneda '{currency}' no válida para exchange '{exchange}'. "
                   f"Monedas aceptadas: {meta.currencies}",
        )

    repo = WalletRepository(session)
    await repo.set_balance(exchange, currency, body.balance)

    # Publicar evento SSE wallet_update
    redis = get_redis(request)
    publisher = RedisEventPublisher(redis)
    await publisher.publish_wallet_update(exchange, currency, body.balance)

    logger.info(
        "wallet_balance_set",
        exchange=exchange,
        currency=currency,
        balance=str(body.balance),
    )

    return WalletSetBalanceResponse(
        exchange=exchange,
        currency=currency,
        balance=str(body.balance),
        updated=True,
    )
