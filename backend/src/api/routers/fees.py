"""
Router: /api/fees — gestión de fees por exchange.

GET /api/fees                    → lista fees de todos los exchanges
PUT /api/fees/{exchange_id}      → actualiza fee_buy y fee_sell de un exchange

Los valores de request se expresan en porcentaje (ej. "0.10" = 0.10%).
El backend convierte a multiplicador antes de guardar en DB (/ 100).
Las respuestas devuelven el multiplicador tal como está en DB (ej. 0.001).
"""

from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.exchanges.registry import EXCHANGE_REGISTRY
from adapters.persistence.config_repo import ConfigRepository
from api.dependencies import get_current_user, get_db
from api.schemas import (
    ExchangeFeeInfo,
    ExchangeFeesListResponse,
    ExchangeFeeUpdateRequest,
    ExchangeFeeUpdateResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/fees", tags=["fees"])

# Multiplicador de conversión: porcentaje → multiplicador
_PCT_TO_MULTIPLIER = Decimal("100")


@router.get("", response_model=ExchangeFeesListResponse)
async def list_fees(
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExchangeFeesListResponse:
    """
    Retorna los fees actuales de todos los exchanges registrados.

    Combina el registry (para display_name) con los fees almacenados en DB.
    Si un exchange no tiene fila en DB, usa el fees_taker del registry
    como valor inicial para fee_buy y fee_sell.
    """
    config_repo = ConfigRepository(session)
    db_fees_list = await config_repo.get_all_fees()

    # Indexar por exchange_id para lookup O(1)
    db_fees: dict[str, dict[str, object]] = {
        str(row["exchange_id"]): row for row in db_fees_list
    }

    fees: list[ExchangeFeeInfo] = []
    for exchange_id, meta in EXCHANGE_REGISTRY.items():
        db_row = db_fees.get(exchange_id)
        if db_row is not None:
            fee_buy = Decimal(str(db_row["fee_buy"]))
            fee_sell = Decimal(str(db_row["fee_sell"]))
        else:
            # Fallback al fees_taker del registry si aún no hay fila en DB
            fee_buy = meta.fees_taker
            fee_sell = meta.fees_taker

        fees.append(
            ExchangeFeeInfo(
                exchange_id=exchange_id,
                display_name=meta.display_name,
                fee_buy=fee_buy,
                fee_sell=fee_sell,
            )
        )

    logger.debug("fees_listed", count=len(fees))
    return ExchangeFeesListResponse(fees=fees)


@router.put("/{exchange_id}", response_model=ExchangeFeeUpdateResponse)
async def update_fees(
    exchange_id: str,
    payload: ExchangeFeeUpdateRequest,
    _: dict[str, object] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExchangeFeeUpdateResponse:
    """
    Actualiza fee_buy y fee_sell de un exchange.

    Recibe porcentajes (ej. "0.10" = 0.10%) y convierte a multiplicador
    antes de guardar en DB (0.10 / 100 = 0.001).
    """
    # Validar que el exchange_id existe en el registry (whitelist)
    meta = EXCHANGE_REGISTRY.get(exchange_id)
    if meta is None:
        raise HTTPException(
            status_code=422,
            detail=f"Exchange '{exchange_id}' no válido.",
        )

    # Convertir porcentaje a multiplicador
    fee_buy_multiplier = payload.fee_buy / _PCT_TO_MULTIPLIER
    fee_sell_multiplier = payload.fee_sell / _PCT_TO_MULTIPLIER

    config_repo = ConfigRepository(session)
    await config_repo.update_fees(
        exchange=exchange_id,
        fee_buy=fee_buy_multiplier,
        fee_sell=fee_sell_multiplier,
    )

    logger.info(
        "fees_updated",
        exchange_id=exchange_id,
        fee_buy_pct=float(payload.fee_buy),
        fee_sell_pct=float(payload.fee_sell),
        fee_buy_multiplier=float(fee_buy_multiplier),
        fee_sell_multiplier=float(fee_sell_multiplier),
    )

    return ExchangeFeeUpdateResponse(
        exchange_id=exchange_id,
        fee_buy=fee_buy_multiplier,
        fee_sell=fee_sell_multiplier,
        message=f"Fees de {meta.display_name} actualizados correctamente.",
    )
