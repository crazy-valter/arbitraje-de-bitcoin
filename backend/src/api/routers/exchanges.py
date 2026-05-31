"""
Router: /api/exchanges — listado y toggle de exchanges.

GET  /api/exchanges                       → lista todos los exchanges del registry
PUT  /api/exchanges/{exchange_id}/toggle  → activa/desactiva un exchange no-core
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.exchanges.registry import EXCHANGE_REGISTRY, is_core
from adapters.persistence.models import ExchangeConfig
from api.dependencies import get_current_user, get_db
from api.schemas import ExchangeInfo, ExchangesListResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])


@router.get("", response_model=ExchangesListResponse)
async def list_exchanges(
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExchangesListResponse:
    """
    Lista todos los exchanges del registry con su estado is_active desde DB.
    Si un exchange del registry no tiene fila en exchange_config, se asume activo.
    """
    # Leer estados desde DB en una sola query
    result = await session.execute(select(ExchangeConfig))
    db_states: dict[str, bool] = {
        row.exchange_id: row.is_active for row in result.scalars().all()
    }

    items: list[ExchangeInfo] = []
    for exchange_id, meta in EXCHANGE_REGISTRY.items():
        # Si no hay fila en DB, el exchange se considera activo (valor por defecto)
        is_active = db_states.get(exchange_id, True)
        items.append(
            ExchangeInfo(
                exchange_id=exchange_id,
                display_name=meta.display_name,
                currencies=meta.currencies,
                fees_taker=str(meta.fees_taker),
                core=meta.core,
                is_active=is_active,
            )
        )

    logger.debug("exchanges_listed", count=len(items))
    return ExchangesListResponse(items=items)


@router.put("/{exchange_id}/toggle", response_model=ExchangeInfo)
async def toggle_exchange(
    exchange_id: str,
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExchangeInfo:
    """
    Activa o desactiva un exchange no-core.
    Los exchanges core (binance, bybit, kraken) siempre responden 403.
    Validación: exchange_id debe existir en EXCHANGE_REGISTRY (whitelist).
    """
    # Validación whitelist — rechaza cualquier exchange_id no registrado
    meta = EXCHANGE_REGISTRY.get(exchange_id)
    if meta is None:
        raise HTTPException(
            status_code=422,
            detail=f"Exchange '{exchange_id}' no registrado.",
        )

    # Protección para exchanges core — independiente del estado en DB
    if is_core(exchange_id):
        raise HTTPException(
            status_code=403,
            detail=f"El exchange '{exchange_id}' es core y no puede ser desactivado.",
        )

    # Buscar o crear fila en exchange_config
    result = await session.execute(
        select(ExchangeConfig).where(ExchangeConfig.exchange_id == exchange_id)
    )
    config = result.scalar_one_or_none()

    if config is None:
        # Primera vez que se toca este exchange — insertar con toggle (activo → inactivo)
        config = ExchangeConfig(exchange_id=exchange_id, is_active=False)
        session.add(config)
    else:
        config.is_active = not config.is_active  # type: ignore[assignment]

    await session.commit()
    await session.refresh(config)

    logger.info(
        "exchange_toggled",
        exchange_id=exchange_id,
        is_active=config.is_active,
    )

    return ExchangeInfo(
        exchange_id=exchange_id,
        display_name=meta.display_name,
        currencies=meta.currencies,
        fees_taker=str(meta.fees_taker),
        core=meta.core,
        is_active=config.is_active,
    )
