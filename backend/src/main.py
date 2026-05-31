"""
FastAPI app factory — punto de entrada del backend.

Lifespan:
1. Conecta Redis y lo almacena en app.state.redis
2. Hace seed del admin desde .env
3. Inicializa wallets por defecto
4. Lanza el ArbitrageEngine como tarea asyncio
5. Al shutdown: detiene el engine y cierra Redis
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from adapters.cache.event_publisher import RedisEventPublisher
from adapters.cache.order_book_store import RedisOrderBookStore
from adapters.exchanges.binance_adapter import BinanceAdapter
from adapters.exchanges.bybit_adapter import BybitAdapter
from adapters.exchanges.kraken_adapter import KrakenAdapter
from adapters.exchanges.registry import EXCHANGE_REGISTRY
from adapters.persistence.config_repo import ConfigRepository
from adapters.persistence.opportunity_repo import OpportunityRepository
from adapters.persistence.trade_repo import TradeRepository
from adapters.persistence.wallet_repo import WalletRepository
from adapters.security.admin_seeder import seed_admin_user
from api.routers.auth import router as auth_router
from api.routers.config import router as config_router
from api.routers.engine import router as engine_router
from api.routers.exchanges import router as exchanges_router
from api.routers.fees import router as fees_router
from api.routers.health import router as health_router
from api.routers.metrics import router as metrics_router
from api.routers.opportunities import router as opportunities_router
from api.routers.ping import router as ping_router
from api.routers.public_prices import router as public_prices_router
from api.routers.trades import router as trades_router
from api.routers.wallets import router as wallets_router
from api.sse import router as sse_router
from config.settings import get_settings
from core.services.arbitrage_engine import ArbitrageEngine
from core.services.fee_calculator import FeeCalculator
from core.services.trade_simulator import TradeSimulator
from core.strategies.cross_exchange import CrossExchangeStrategy
from core.strategies.registry import StrategyRegistry
from db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)
settings = get_settings()

# Rate limiter — clave: IP del cliente
limiter = Limiter(key_func=get_remote_address)

# Timestamp de arranque — expuesto para que metrics.py calcule uptime_seconds
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Gestiona el ciclo de vida completo de la aplicación."""
    global _start_time
    # ── Startup ───────────────────────────────────────────────────────────────
    _start_time = time.monotonic()
    app.state.start_time = _start_time
    logger.info("startup", environment=settings.environment)

    # 1. Conectar Redis
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis
    logger.info("redis_connected", url=settings.redis_url)

    # 2. Seed del admin, configuración inicial de wallets e inicialización de system_config
    async with AsyncSessionLocal() as session:
        await seed_admin_user(session)

        # Lista de exchange_ids desde el registry — elimina hardcodeo
        exchange_ids = list(EXCHANGE_REGISTRY.keys())

        wallet_repo = WalletRepository(session)
        capital = settings.initial_capital_usdt
        await wallet_repo.initialize_defaults(
            exchanges=exchange_ids,
            initial_usdt=capital,
        )

        # Upsert de system_config solo si no existe — no sobrescribir en reinicios
        config_repo_init = ConfigRepository(session)
        await config_repo_init.initialize_defaults(
            capital=settings.initial_capital_usdt,
            threshold=settings.min_profit_threshold_pct,
        )
        mock_mode     = await config_repo_init.get_mock_mode_enabled()
        engine_paused = await config_repo_init.get_engine_paused()

    # 3. Construir el grafo de dependencias del motor de arbitraje
    order_book_store = RedisOrderBookStore(redis)
    event_publisher = RedisEventPublisher(redis)

    # Elegir adaptadores según mock_mode_enabled persistido en DB
    _exchange_adapter_map = {
        "binance": BinanceAdapter,
        "bybit": BybitAdapter,
        "kraken": KrakenAdapter,
    }
    if mock_mode:
        from adapters.exchanges.mock_exchange import MockExchangeAdapter
        from adapters.exchanges.mock_scenarios import SPREAD_HIGH

        logger.warning(
            "mock_mode_at_startup",
            msg="MODO MOCK ACTIVO — no conectado a exchanges reales",
        )
        exchanges = [
            MockExchangeAdapter(eid, SPREAD_HIGH)
            for eid in EXCHANGE_REGISTRY
        ]
    else:
        exchanges = [
            _exchange_adapter_map[eid]()
            for eid in EXCHANGE_REGISTRY
            if eid in _exchange_adapter_map
        ]

    # El engine mantiene su propia sesión DB de larga duración
    engine_session = AsyncSessionLocal()
    config_repo = ConfigRepository(engine_session)
    opportunity_repo = OpportunityRepository(engine_session)
    trade_repo = TradeRepository(engine_session)
    wallet_repo_engine = WalletRepository(engine_session)
    fee_calculator = FeeCalculator(config_repo)

    trade_simulator = TradeSimulator(
        opportunity_repo=opportunity_repo,
        trade_repo=trade_repo,
        wallet_repo=wallet_repo_engine,
        event_publisher=event_publisher,
        fee_calculator=fee_calculator,
    )

    strategy_registry = StrategyRegistry()
    strategy_registry.register(
        CrossExchangeStrategy(
            fee_calculator=fee_calculator,
            config_repo=config_repo,
        )
    )

    engine = ArbitrageEngine(
        exchanges=exchanges,
        order_book_store=order_book_store,
        opportunity_repo=opportunity_repo,
        strategy_registry=strategy_registry,
        trade_simulator=trade_simulator,
        event_publisher=event_publisher,
        config_repo=config_repo,
    )
    app.state.engine = engine

    # 4. Lanzar el motor de arbitraje en background
    # Aplicar estado de pausa persistido antes de arrancar
    if engine_paused:
        engine.pause()
        logger.info("arbitrage_engine_starts_paused")

    engine_task = asyncio.create_task(engine.run(), name="arbitrage_engine")
    logger.info("arbitrage_engine_launched", paused=engine_paused)

    yield  # ── Servidor corriendo ────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("shutdown")
    engine_task.cancel()
    await asyncio.gather(engine_task, return_exceptions=True)
    await engine.stop()
    await engine_session.close()
    await redis.aclose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Bitcoin Arbitrage Bot",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS — allow_credentials=True es obligatorio para cookies HttpOnly
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

# Registrar todos los routers
app.include_router(health_router)
app.include_router(sse_router)
app.include_router(auth_router)
app.include_router(opportunities_router)
app.include_router(trades_router)
app.include_router(wallets_router)
app.include_router(exchanges_router)
app.include_router(fees_router)
app.include_router(config_router)
app.include_router(engine_router)
app.include_router(metrics_router)
# Endpoint público intencional: GET /ping — sin autenticación, para health checks externos
app.include_router(ping_router)
# Endpoint público intencional: GET /api/public/prices — sin auth, solo lectura de precios
app.include_router(public_prices_router)
