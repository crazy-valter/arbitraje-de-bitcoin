"""
ArbitrageEngine — loop async principal del bot de arbitraje.

Orquesta:
1. Recibe order books desde los adaptadores de exchanges
2. Los persiste en Redis (IOrderBookStore)
3. Publica throttled updates de order book al canal SSE
4. Ejecuta las estrategias activas para detectar oportunidades
5. Filtra, persiste y simula los trades de las mejores oportunidades
6. Publica métricas al canal SSE cada 5 segundos

El hot path es: WS → Redis → Estrategia → SSE
PostgreSQL solo se toca en el cold path (persistir oportunidad, trade, wallet).
"""

import asyncio
import contextlib
import time
from datetime import UTC, datetime

import structlog

from core.entities.order_book import OrderBook
from core.services.trade_simulator import TradeSimulator
from core.strategies.registry import StrategyRegistry
from ports.config_port import IConfigRepository
from ports.event_publisher_port import IEventPublisher
from ports.exchange_port import IExchangePort
from ports.opportunity_repo_port import IOpportunityRepository
from ports.order_book_store_port import IOrderBookStore

logger = structlog.get_logger(__name__)

_SYMBOL = "BTC/USDT"
_METRICS_INTERVAL_SECONDS = 5.0


class ArbitrageEngine:
    """Orquestador principal del bot de arbitraje."""

    def __init__(
        self,
        exchanges: list[IExchangePort],
        order_book_store: IOrderBookStore,
        opportunity_repo: IOpportunityRepository,
        strategy_registry: StrategyRegistry,
        trade_simulator: TradeSimulator,
        event_publisher: IEventPublisher,
        config_repo: IConfigRepository,
    ) -> None:
        self._exchanges = exchanges
        self._order_book_store = order_book_store
        self._opportunity_repo = opportunity_repo
        self._strategy_registry = strategy_registry
        self._trade_simulator = trade_simulator
        self._event_publisher = event_publisher
        self._config = config_repo
        self._running = False
        self._paused = False
        self._opportunities_count = 0
        self._executed_count = 0
        self._start_time: float = time.monotonic()
        self._exchange_tasks: list[asyncio.Task[None]] = []
        # Serializa los writes a DB — evita colisiones entre las tasks de exchange concurrentes
        self._process_lock = asyncio.Lock()

    @property
    def opportunities_detected(self) -> int:
        """Contador de oportunidades detectadas desde el inicio del engine."""
        return self._opportunities_count

    @property
    def trades_simulated(self) -> int:
        """Contador de trades simulados exitosamente desde el inicio del engine."""
        return self._executed_count

    @property
    def is_paused(self) -> bool:
        """True cuando el motor está pausado — feeds activos pero sin procesar oportunidades."""
        return self._paused

    def pause(self) -> None:
        """Pausa el procesamiento de oportunidades sin desconectar los feeds."""
        self._paused = True
        logger.info("arbitrage_engine_paused")

    def resume(self) -> None:
        """Reanuda el procesamiento de oportunidades."""
        self._paused = False
        logger.info("arbitrage_engine_resumed")

    async def run(self) -> None:
        """
        Inicia el loop del motor de arbitraje.

        Las exchange tasks se lanzan como tareas independientes para permitir
        hot-swap via reload_exchanges(). El loop de métricas bloquea este
        coroutine hasta que se cancele.
        """
        self._running = True
        self._start_exchange_tasks()
        logger.info(
            "arbitrage_engine_started",
            exchanges=[e.exchange_id for e in self._exchanges],
        )

        try:
            await self._metrics_loop()  # bloquea hasta CancelledError
        except asyncio.CancelledError:
            logger.info("arbitrage_engine_cancelled")
            for task in self._exchange_tasks:
                task.cancel()
            await asyncio.gather(*self._exchange_tasks, return_exceptions=True)

    def _start_exchange_tasks(self) -> None:
        """Crea y registra las tasks de streaming por exchange (sin await)."""
        self._exchange_tasks = [
            asyncio.create_task(
                self._stream_exchange(exchange),
                name=f"stream_{exchange.exchange_id}",
            )
            for exchange in self._exchanges
        ]

    async def reload_exchanges(self, new_exchanges: list[IExchangePort]) -> None:
        """
        Hot-swap: cancela tasks actuales, reemplaza adaptadores y relanza.

        Permite cambiar entre adaptadores reales y mock sin reiniciar el servidor.
        """
        # Cancelar y esperar que terminen las tasks actuales
        for task in self._exchange_tasks:
            task.cancel()
        if self._exchange_tasks:
            await asyncio.gather(*self._exchange_tasks, return_exceptions=True)

        # Desconectar los adaptadores anteriores
        for exc in self._exchanges:
            with contextlib.suppress(Exception):
                await exc.disconnect()

        # Reemplazar y relanzar
        self._exchanges = new_exchanges
        self._start_exchange_tasks()
        logger.info(
            "exchanges_reloaded",
            exchanges=[e.exchange_id for e in self._exchanges],
        )

    async def _stream_exchange(self, exchange: IExchangePort) -> None:
        """
        Stream continuo de un exchange.
        Llama a _on_order_book_update con cada nueva actualización.
        """
        await exchange.stream_forever(
            symbol=_SYMBOL,
            on_update=self._on_order_book_update,
        )

    async def _on_order_book_update(self, order_book: OrderBook) -> None:
        """
        Callback invocado con cada actualización de order book.

        1. Guarda en Redis con TTL
        2. Publica evento SSE throttled
        3. Carga todos los books disponibles
        4. Ejecuta estrategias activas
        5. Procesa oportunidades detectadas
        """
        # Guardar en Redis
        await self._order_book_store.save(order_book)

        # Publicar al SSE (throttled: max 1 por 500ms por exchange)
        await self._event_publisher.publish_orderbook(
            exchange=order_book.exchange,
            ask=order_book.best_ask.price,
            bid=order_book.best_bid.price,
        )

        # Cargar todos los order books disponibles
        order_books = await self._order_book_store.get_all_exchanges(_SYMBOL)
        if len(order_books) < 2:
            return  # necesitamos al menos 2 exchanges para arbitraje cross-exchange

        if self._paused:
            return  # feeds activos pero sin procesar oportunidades

        # El lock serializa el acceso a la sesión DB — strategy.detect() lee fees,
        # _process_opportunity escribe oportunidades y trades, ambos en la misma sesión.
        async with self._process_lock:
            active_strategy_ids = await self._get_active_strategy_ids()
            active_strategies = self._strategy_registry.get_active(active_strategy_ids)

            for strategy in active_strategies:
                try:
                    opportunities = await strategy.detect(order_books)
                    for opportunity in opportunities:
                        await self._process_opportunity(opportunity)
                except Exception as exc:
                    logger.error(
                        "strategy_error",
                        strategy=strategy.strategy_id,
                        error=str(exc),
                    )

    async def _process_opportunity(
        self,
        opportunity_entity,  # ArbitrageOpportunity
    ) -> None:
        """
        Persiste la oportunidad, la publica al SSE y simula el trade.

        El lock serializa los writes a DB para evitar conflictos de sesión cuando
        múltiples exchange tasks detectan oportunidades en el mismo ciclo asyncio.
        """
        self._opportunities_count += 1

        # Persistir en DB (llamado ya dentro del _process_lock del caller)
        saved = await self._opportunity_repo.save(opportunity_entity)

        # Publicar al SSE
        await self._event_publisher.publish_opportunity(saved)

        # Simular trade
        result = await self._trade_simulator.simulate(saved)
        if result is not None:
            self._executed_count += 1

    async def _get_active_strategy_ids(self) -> list[str]:
        """Lee los feature flags de estrategias desde la configuración."""
        active = []
        for strategy_id, config_key in [
            ("cross_exchange", "STRATEGY_CROSS_EXCHANGE"),
            ("triangular", "STRATEGY_TRIANGULAR"),
            ("statistical", "STRATEGY_STATISTICAL"),
        ]:
            value = await self._config.get(config_key)
            if value and value.lower() == "true":
                active.append(strategy_id)
        return active

    async def _metrics_loop(self) -> None:
        """Publica métricas cada 5 segundos al canal SSE."""
        while self._running:
            await asyncio.sleep(_METRICS_INTERVAL_SECONDS)
            try:
                total_pnl = await self._opportunity_repo.get_total_pnl()
                win_rate = (
                    self._executed_count / self._opportunities_count * 100
                    if self._opportunities_count > 0
                    else 0.0
                )
                connected_exchanges = sum(
                    1 for e in self._exchanges if e.is_connected
                )

                exchange_latencies = {
                    e.exchange_id: e.feed_staleness_ms
                    for e in self._exchanges
                }

                await self._event_publisher.publish_metrics({
                    "opportunities_detected": self._opportunities_count,
                    "trades_simulated": self._executed_count,
                    "win_rate_pct": round(win_rate, 2),
                    "total_pnl_usdt": total_pnl,
                    "connected_exchanges": connected_exchanges,
                    "exchange_latencies": exchange_latencies,
                    "uptime_seconds": int(time.monotonic() - self._start_time),
                    "timestamp": datetime.now(UTC).isoformat(),
                })
            except Exception as exc:
                logger.error("metrics_loop_error", error=str(exc))

    async def stop(self) -> None:
        """Detiene el motor y desconecta los exchanges."""
        self._running = False
        for exchange in self._exchanges:
            with contextlib.suppress(Exception):
                await exchange.disconnect()
        logger.info("arbitrage_engine_stopped")
