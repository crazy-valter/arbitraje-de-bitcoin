"""
Tests unitarios: ExchangeRegistry.

Verifica que el registro de exchanges tenga los datos correctos
y que las funciones auxiliares funcionen según el contrato.
"""

from decimal import Decimal

import pytest

from adapters.exchanges.registry import (
    EXCHANGE_REGISTRY,
    ExchangeMetadata,
    get,
    is_core,
    list_all,
)


class TestExchangeRegistryStructure:
    """Verifica la estructura y contenido del registry base."""

    def test_tres_exchanges_core_presentes(self) -> None:
        """El registry debe contener exactamente los tres exchanges core."""
        registry = list_all()
        assert "binance" in registry
        assert "bybit" in registry
        assert "kraken" in registry

    def test_binance_es_core(self) -> None:
        """Binance debe marcarse como exchange core."""
        assert is_core("binance") is True

    def test_bybit_es_core(self) -> None:
        """Bybit debe marcarse como exchange core."""
        assert is_core("bybit") is True

    def test_kraken_es_core(self) -> None:
        """Kraken debe marcarse como exchange core."""
        assert is_core("kraken") is True

    def test_binance_currencies(self) -> None:
        """Binance debe tener USDT y BTC como monedas."""
        meta = get("binance")
        assert meta is not None
        assert "USDT" in meta.currencies
        assert "BTC" in meta.currencies

    def test_bybit_currencies(self) -> None:
        """Bybit debe tener USDT y BTC como monedas."""
        meta = get("bybit")
        assert meta is not None
        assert "USDT" in meta.currencies
        assert "BTC" in meta.currencies

    def test_kraken_currencies(self) -> None:
        """Kraken debe tener USDT, BTC y ETH en sus monedas."""
        meta = get("kraken")
        assert meta is not None
        assert "USDT" in meta.currencies
        assert "BTC" in meta.currencies
        assert "ETH" in meta.currencies

    def test_fees_como_decimal(self) -> None:
        """Los fees_taker de todos los exchanges deben ser instancias de Decimal."""
        for exchange_id, meta in EXCHANGE_REGISTRY.items():
            assert isinstance(meta.fees_taker, Decimal), (
                f"{exchange_id}.fees_taker debe ser Decimal, no {type(meta.fees_taker)}"
            )

    def test_binance_fees_taker(self) -> None:
        """Binance: taker fee debe ser 0.001 (0.10%)."""
        meta = get("binance")
        assert meta is not None
        assert meta.fees_taker == Decimal("0.001")

    def test_bybit_fees_taker(self) -> None:
        """Bybit: taker fee debe ser 0.001 (0.10%)."""
        meta = get("bybit")
        assert meta is not None
        assert meta.fees_taker == Decimal("0.001")

    def test_kraken_fees_taker(self) -> None:
        """Kraken: taker fee debe ser 0.0026 (0.26%)."""
        meta = get("kraken")
        assert meta is not None
        assert meta.fees_taker == Decimal("0.0026")

    def test_binance_tiene_eth(self) -> None:
        """Binance debe tener ETH en sus currencies (CHG-007)."""
        meta = get("binance")
        assert meta is not None
        assert "ETH" in meta.currencies

    def test_bybit_tiene_eth(self) -> None:
        """Bybit debe tener ETH en sus currencies (CHG-007)."""
        meta = get("bybit")
        assert meta is not None
        assert "ETH" in meta.currencies

    def test_kraken_tiene_eth(self) -> None:
        """Kraken debe tener ETH en sus currencies (CHG-007)."""
        meta = get("kraken")
        assert meta is not None
        assert "ETH" in meta.currencies

    def test_todos_exchanges_tienen_eth(self) -> None:
        """Los tres exchanges core deben tener ETH como currency (CHG-007)."""
        for exchange_id in ("binance", "bybit", "kraken"):
            meta = get(exchange_id)
            assert meta is not None
            assert "ETH" in meta.currencies, (
                f"{exchange_id} debe tener ETH en currencies"
            )


class TestExchangeRegistryFunctions:
    """Verifica las funciones auxiliares del registry."""

    def test_get_exchange_existente(self) -> None:
        """get() debe retornar el metadata para un exchange registrado."""
        meta = get("binance")
        assert meta is not None
        assert isinstance(meta, ExchangeMetadata)

    def test_get_exchange_inexistente(self) -> None:
        """get() debe retornar None para un exchange no registrado."""
        assert get("exchange_inexistente") is None
        assert get("") is None

    def test_is_core_exchange_inexistente(self) -> None:
        """is_core() debe retornar False para exchanges no registrados."""
        assert is_core("exchange_inexistente") is False

    def test_list_all_retorna_copia(self) -> None:
        """list_all() debe retornar una copia, no la referencia al dict original."""
        copy1 = list_all()
        copy2 = list_all()
        # Modificar la copia no afecta al registry original
        copy1["nuevo_exchange"] = ExchangeMetadata(
            display_name="Test",
            currencies=["USD"],
            fees_taker=Decimal("0.001"),
            core=False,
        )
        assert "nuevo_exchange" not in EXCHANGE_REGISTRY
        assert "nuevo_exchange" not in copy2

    def test_metadata_frozen(self) -> None:
        """ExchangeMetadata debe ser inmutable (frozen dataclass)."""
        meta = get("binance")
        assert meta is not None
        with pytest.raises((AttributeError, TypeError)):
            meta.core = False  # type: ignore[misc]


class TestExchangeRegistryDynamic:
    """Verifica el comportamiento con exchanges no-core (escenario de prueba)."""

    def test_exchange_prueba_en_list_all(self) -> None:
        """
        Un exchange de prueba agregado dinámicamente debe aparecer en list_all().
        Nota: EXCHANGE_REGISTRY es un dict mutable a nivel de módulo,
        aunque ExchangeMetadata es frozen.
        """
        # Agregar temporalmente un exchange de prueba
        test_meta = ExchangeMetadata(
            display_name="TestExchange",
            currencies=["USDT", "BTC"],
            fees_taker=Decimal("0.002"),
            core=False,
        )
        EXCHANGE_REGISTRY["test_exchange"] = test_meta

        try:
            registry = list_all()
            assert "test_exchange" in registry
            assert registry["test_exchange"].display_name == "TestExchange"
        finally:
            # Limpiar — restaurar estado original del registry
            del EXCHANGE_REGISTRY["test_exchange"]

    def test_exchange_prueba_is_core_false(self) -> None:
        """Un exchange de prueba con core=False debe retornar is_core() = False."""
        test_meta = ExchangeMetadata(
            display_name="TestExchange",
            currencies=["USDT", "BTC"],
            fees_taker=Decimal("0.002"),
            core=False,
        )
        EXCHANGE_REGISTRY["test_exchange2"] = test_meta

        try:
            assert is_core("test_exchange2") is False
        finally:
            del EXCHANGE_REGISTRY["test_exchange2"]
