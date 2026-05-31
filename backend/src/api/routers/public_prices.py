"""
Router público — GET /api/public/prices

Endpoint sin autenticación que devuelve precios BTC/USDT en tiempo real
para los tres exchanges monitoreados. Solo lectura de order books (datos de mercado públicos).
"""

from datetime import UTC, datetime
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address

from adapters.cache.order_book_store import RedisOrderBookStore
from api.dependencies import get_redis
from api.schemas import ExchangePriceItem, PublicPricesResponse

logger = structlog.get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/api/public/prices",
    response_model=PublicPricesResponse,
)
@limiter.limit("30/minute")
async def get_public_prices(
    request: Request,  # requerido por slowapi
    response: Response,
    redis: Redis = Depends(get_redis),
) -> PublicPricesResponse:
    """
    Devuelve los precios BTC/USDT actuales para los exchanges monitoreados.
    Endpoint público — no requiere autenticación.
    Lee de RedisOrderBookStore (misma fuente que el motor de arbitraje).

    Si no hay datos en Redis (bot no iniciado o exchanges caídos),
    devuelve prices=[] con status 200 para no interrumpir la vista de login.
    """
    response.headers["Cache-Control"] = "no-store"
    store = RedisOrderBookStore(redis)
    order_books = await store.get_all_exchanges("BTC/USDT")

    prices: list[ExchangePriceItem] = []
    for ob in order_books:
        # mid price con Decimal — nunca float
        mid = (ob.best_ask.price + ob.best_bid.price) / Decimal("2")
        prices.append(
            ExchangePriceItem(
                exchange=ob.exchange,
                symbol=ob.symbol,
                ask=str(ob.best_ask.price),
                bid=str(ob.best_bid.price),
                mid=str(mid),
                is_stale=ob.is_stale,
                updated_at=ob.timestamp,
            )
        )

    return PublicPricesResponse(
        prices=prices,
        fetched_at=datetime.now(UTC),
    )
