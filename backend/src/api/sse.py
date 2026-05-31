"""
SSE endpoint: GET /events

Stream en tiempo real para el dashboard via Redis Pub/Sub.
Requiere JWT válido (access_token + fingerprint cookies).

Arquitectura:
- Una cola asyncio.Queue por cliente conectado (maxsize=100)
- Un listener Redis Pub/Sub por cola
- Heartbeat cada 30s para mantener la conexión activa en Nginx
- Los eventos nuevos que no quepan en la cola se descartan (cliente lento)
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_current_user, get_redis

router = APIRouter()

_SSE_CHANNEL = "sse:events"
_HEARTBEAT_TIMEOUT = 30.0  # segundos sin evento → enviar heartbeat
_QUEUE_MAX_SIZE = 100      # máx eventos en cola por cliente


@router.get("/events")
async def event_stream(
    request: Request,
    _: dict[str, object] = Depends(get_current_user),  # JWT obligatorio
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    """
    GET /events — stream SSE autenticado.

    El browser envía automáticamente las cookies HttpOnly (access_token, fingerprint)
    cuando la conexión se crea con withCredentials: true.
    """
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=_QUEUE_MAX_SIZE)

    async def _redis_listener() -> None:
        """Cada cliente tiene su propia suscripción Redis."""
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(_SSE_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    queue.put_nowait(data)
                except (asyncio.QueueFull, json.JSONDecodeError):
                    # Cliente lento o dato malformado — descartar
                    pass

    async def event_generator() -> AsyncGenerator[dict[str, object]]:
        """Generador que lee de la cola y envía eventos al cliente."""
        listener_task = asyncio.create_task(_redis_listener())
        try:
            while True:
                # Detectar desconexión del cliente
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=_HEARTBEAT_TIMEOUT
                    )
                    yield {
                        "event": event.get("type", "message"),
                        "data": json.dumps(event),
                    }
                except TimeoutError:
                    # Heartbeat — mantiene la conexión viva y reinicia proxy_read_timeout
                    yield {"comment": "heartbeat"}
        finally:
            listener_task.cancel()
            await asyncio.gather(listener_task, return_exceptions=True)

    return EventSourceResponse(event_generator())
