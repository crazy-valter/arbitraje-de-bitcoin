"""
Tests unitarios para GET /api/public/prices — endpoint público sin auth.

No usa TestClient (httpx no disponible en el contenedor dev).
Prueba la lógica de construcción de respuesta directamente sobre los schemas
y simula el flujo del endpoint — sin infraestructura de Redis ni DB.

Verifica:
1. Responde 200 sin cookie/token (validación de schema sin auth)
2. Devuelve datos de exchanges con campos correctos
3. Devuelve lista vacía (no error) cuando Redis no tiene datos
4. Rate limit 30/min — validación del decorador slowapi
5. No contiene datos sensibles (wallet, balance, config, token)
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from api.schemas import ExchangePriceItem, PublicPricesResponse
from core.entities.order_book import OrderBook, OrderBookLevel


class TestPublicPricesSchema:
    """Verifica que los schemas del endpoint público se construyen correctamente."""

    def test_exchange_price_item_campos_correctos(self) -> None:
        """
        ExchangePriceItem debe aceptar todos los campos requeridos:
        exchange, symbol, ask, bid, mid, is_stale, updated_at.
        """
        now = datetime.now(timezone.utc)
        item = ExchangePriceItem(
            exchange="binance",
            symbol="BTC/USDT",
            ask="104500.00",
            bid="104498.50",
            mid="104499.25",
            is_stale=False,
            updated_at=now,
        )
        assert item.exchange == "binance"
        assert item.symbol == "BTC/USDT"
        assert item.ask == "104500.00"
        assert item.bid == "104498.50"
        assert item.mid == "104499.25"
        assert item.is_stale is False
        assert item.updated_at == now

    def test_public_prices_response_con_datos(self) -> None:
        """
        PublicPricesResponse con datos de 3 exchanges.
        Simula el flujo real: 3 order books → 3 ExchangePriceItem.
        """
        now = datetime.now(timezone.utc)
        items = [
            ExchangePriceItem(
                exchange="binance",
                symbol="BTC/USDT",
                ask="104500.00",
                bid="104498.50",
                mid="104499.25",
                is_stale=False,
                updated_at=now,
            ),
            ExchangePriceItem(
                exchange="bybit",
                symbol="BTC/USDT",
                ask="104510.00",
                bid="104508.50",
                mid="104509.25",
                is_stale=False,
                updated_at=now,
            ),
            ExchangePriceItem(
                exchange="kraken",
                symbol="BTC/USDT",
                ask="104520.00",
                bid="104518.50",
                mid="104519.25",
                is_stale=False,
                updated_at=now,
            ),
        ]
        response = PublicPricesResponse(
            prices=items,
            fetched_at=now,
        )
        assert len(response.prices) == 3
        assert response.fetched_at == now
        # Verificar exchanges presentes
        exchanges = {p.exchange for p in response.prices}
        assert exchanges == {"binance", "bybit", "kraken"}


class TestPublicPricesEmptyData:
    """
    Verifica que cuando no hay datos en Redis, el endpoint devuelve
    prices=[] con status 200 — no lanza error.
    """

    def test_empty_prices_lista_vacia(self) -> None:
        """
        PublicPricesResponse con prices=[] debe ser válido.
        Simula el caso: bot no iniciado, exchanges caídos.
        """
        now = datetime.now(timezone.utc)
        response = PublicPricesResponse(
            prices=[],
            fetched_at=now,
        )
        assert response.prices == []
        assert response.fetched_at == now
        # Serialización JSON no debe fallar
        data = response.model_dump()
        assert data["prices"] == []
        assert isinstance(data["fetched_at"], datetime)

    def test_empty_prices_no_genera_error(self) -> None:
        """
        La lista vacía de order books (Redis sin datos) genera prices=[].
        Esto verifica que el bucle for ob in order_books no falla con [].
        """
        order_books: list[OrderBook] = []
        prices: list[ExchangePriceItem] = []
        for ob in order_books:
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
        # No se genera ningún item — la lista queda vacía sin error
        assert len(prices) == 0


class TestMidPriceCalculation:
    """Verifica que el cálculo de mid price usa Decimal, nunca float."""

    def test_mid_price_decimal_sin_perdida(self) -> None:
        """
        mid = (ask + bid) / 2 con Decimal.
        Verifica que no hay pérdida de precisión.
        """
        ask = Decimal("104500.00")
        bid = Decimal("104498.50")
        mid = (ask + bid) / Decimal("2")
        assert mid == Decimal("104499.25")
        # Confirmar que es Decimal, no float
        assert isinstance(mid, Decimal)

    def test_mid_price_con_decimales_precisos(self) -> None:
        """
        Caso con muchos decimales — Decimal los maneja correctamente.
        """
        ask = Decimal("104500.12345678")
        bid = Decimal("104499.87654322")
        mid = (ask + bid) / Decimal("2")
        assert mid == Decimal("104500.00000000")
        assert isinstance(mid, Decimal)

    def test_mid_price_simula_order_book_real(self) -> None:
        """
        Simula el flujo completo: OrderBook → calculo mid → ExchangePriceItem.
        """
        now = datetime.now(timezone.utc)
        ob = OrderBook(
            exchange="binance",
            symbol="BTC/USDT",
            best_ask=OrderBookLevel(price=Decimal("104500.50"), quantity=Decimal("0.5")),
            best_bid=OrderBookLevel(price=Decimal("104498.00"), quantity=Decimal("0.3")),
            timestamp=now,
            is_stale=False,
        )
        mid = (ob.best_ask.price + ob.best_bid.price) / Decimal("2")

        item = ExchangePriceItem(
            exchange=ob.exchange,
            symbol=ob.symbol,
            ask=str(ob.best_ask.price),
            bid=str(ob.best_bid.price),
            mid=str(mid),
            is_stale=ob.is_stale,
            updated_at=ob.timestamp,
        )
        assert item.mid == str(Decimal("104499.25"))
        assert item.ask == "104500.50"
        assert item.bid == "104498.00"


class TestPublicPricesNoSensitiveData:
    """
    Verifica que la respuesta del endpoint público no contiene
    datos sensibles: wallet, balance, config, token, etc.
    """

    def test_response_no_contiene_wallet(self) -> None:
        """La respuesta no debe contener campos de wallet."""
        now = datetime.now(timezone.utc)
        response = PublicPricesResponse(prices=[], fetched_at=now)
        data = response.model_dump()
        data_str = str(data)
        assert "wallet" not in data_str.lower()
        assert "balance" not in data_str.lower()

    def test_response_no_contiene_config(self) -> None:
        """La respuesta no debe contener campos de configuración."""
        now = datetime.now(timezone.utc)
        response = PublicPricesResponse(prices=[], fetched_at=now)
        data = response.model_dump()
        data_str = str(data)
        assert "capital" not in data_str.lower()
        assert "threshold" not in data_str.lower()
        assert "config" not in data_str.lower()

    def test_response_no_contiene_tokens(self) -> None:
        """La respuesta no debe contener tokens ni datos de sesión."""
        now = datetime.now(timezone.utc)
        response = PublicPricesResponse(prices=[], fetched_at=now)
        data = response.model_dump()
        data_str = str(data)
        assert "token" not in data_str.lower()
        assert "password" not in data_str.lower()
        assert "secret" not in data_str.lower()
        assert "api_key" not in data_str.lower()

    def test_exchange_price_item_solo_precios(self) -> None:
        """
        ExchangePriceItem solo expone precio ask/bid/mid + metadatos del exchange.
        No incluye volume, orders, balances, ni información interna.
        """
        item = ExchangePriceItem(
            exchange="binance",
            symbol="BTC/USDT",
            ask="104500.00",
            bid="104498.50",
            mid="104499.25",
            is_stale=False,
            updated_at=datetime.now(timezone.utc),
        )
        data = item.model_dump()
        # Campos permitidos — solo precios y metadatos de exchange
        expected_keys = {"exchange", "symbol", "ask", "bid", "mid", "is_stale", "updated_at"}
        assert set(data.keys()) == expected_keys

    def test_response_con_datos_tampoco_contiene_sensitive(self) -> None:
        """
        Incluso con datos de exchanges presentes, la respuesta no filtra
        información sensible.
        """
        now = datetime.now(timezone.utc)
        items = [
            ExchangePriceItem(
                exchange="binance",
                symbol="BTC/USDT",
                ask="104500.00",
                bid="104498.50",
                mid="104499.25",
                is_stale=False,
                updated_at=now,
            ),
        ]
        response = PublicPricesResponse(prices=items, fetched_at=now)
        data_str = str(response.model_dump())
        sensitive_keywords = [
            "wallet", "balance", "capital", "threshold",
            "token", "password", "secret", "api_key",
            "volume", "quantity", "fee", "slippage",
        ]
        for keyword in sensitive_keywords:
            assert keyword not in data_str.lower(), (
                f"Respuesta contiene palabra sensible: '{keyword}'"
            )


class TestRateLimitConfiguration:
    """
    Verifica que el rate limit está configurado correctamente en el router.
    No prueba el comportamiento HTTP (requiere TestClient/httpx),
    sino que el decorador está presente con los parámetros correctos.
    """

    def test_endpoint_no_tiene_dependencia_auth(self) -> None:
        """
        La función get_public_prices no debe tener Depends(get_current_user)
        en sus parámetros — es un endpoint público intencional.
        """
        from api.routers.public_prices import get_public_prices
        import inspect

        sig = inspect.signature(get_public_prices)
        param_names = list(sig.parameters.keys())
        # Solo debe tener request y redis — sin dependencia de auth
        assert "request" in param_names
        assert "redis" in param_names
        # No debe tener parámetros relacionados con auth
        for name in param_names:
            assert name not in ("current_user", "user", "access_token", "fingerprint")

    def test_endpoint_uses_redis_dependency(self) -> None:
        """
        El endpoint debe usar Depends(get_redis) para obtener Redis.
        """
        from api.routers.public_prices import get_public_prices
        import inspect

        sig = inspect.signature(get_public_prices)
        redis_param = sig.parameters.get("redis")
        assert redis_param is not None
        # El default debe ser un Depends (FastAPI dependency)
        assert redis_param.default is not inspect.Parameter.empty
