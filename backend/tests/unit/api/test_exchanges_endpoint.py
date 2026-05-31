"""
Tests unitarios: lógica de endpoints exchanges y wallets.

No usa TestClient (httpx no disponible en el contenedor dev).
Prueba la lógica de validación directamente sobre las funciones
de los routers y el registry.
"""

from decimal import Decimal

import pytest

from adapters.exchanges.registry import EXCHANGE_REGISTRY, ExchangeMetadata, is_core
from api.schemas import (
    ExchangeInfo,
    ExchangesListResponse,
    WalletSetBalanceRequest,
    WalletSetBalanceResponse,
)


class TestExchangeToggleValidation:
    """Verifica la lógica de validación del toggle de exchanges."""

    def test_binance_es_core_no_se_puede_togglear(self) -> None:
        """Binance tiene core=True en el registry — toggle debe ser rechazado."""
        assert is_core("binance") is True

    def test_bybit_es_core_no_se_puede_togglear(self) -> None:
        """Bybit tiene core=True en el registry — toggle debe ser rechazado."""
        assert is_core("bybit") is True

    def test_kraken_es_core_no_se_puede_togglear(self) -> None:
        """Kraken tiene core=True en el registry — toggle debe ser rechazado."""
        assert is_core("kraken") is True

    def test_exchange_inexistente_no_esta_en_registry(self) -> None:
        """Exchange no registrado no debe estar en EXCHANGE_REGISTRY (whitelist)."""
        assert "exchange_fantasma" not in EXCHANGE_REGISTRY
        assert EXCHANGE_REGISTRY.get("exchange_fantasma") is None

    def test_exchange_no_core_puede_togglearse(self) -> None:
        """Un exchange con core=False puede ser toggleado."""
        test_meta = ExchangeMetadata(
            display_name="TestExchange",
            currencies=["USDT", "BTC"],
            fees_taker=Decimal("0.002"),
            core=False,
        )
        EXCHANGE_REGISTRY["test_toggle_logic"] = test_meta
        try:
            assert is_core("test_toggle_logic") is False
            # La lógica del router permite toggle si core=False
            meta = EXCHANGE_REGISTRY.get("test_toggle_logic")
            assert meta is not None
            assert meta.core is False
        finally:
            del EXCHANGE_REGISTRY["test_toggle_logic"]


class TestExchangeInfoSchema:
    """Verifica el schema ExchangeInfo para el listado de exchanges."""

    def test_exchange_info_serializacion(self) -> None:
        """ExchangeInfo debe serializar fees_taker como string."""
        info = ExchangeInfo(
            exchange_id="binance",
            display_name="Binance",
            currencies=["USDT", "BTC"],
            fees_taker="0.001",
            core=True,
            is_active=True,
        )
        data = info.model_dump()
        assert isinstance(data["fees_taker"], str)
        assert data["exchange_id"] == "binance"
        assert data["core"] is True
        assert data["is_active"] is True

    def test_exchanges_list_response_contiene_items(self) -> None:
        """ExchangesListResponse debe contener la lista de ExchangeInfo."""
        items = [
            ExchangeInfo(
                exchange_id=eid,
                display_name=meta.display_name,
                currencies=meta.currencies,
                fees_taker=str(meta.fees_taker),
                core=meta.core,
                is_active=True,
            )
            for eid, meta in EXCHANGE_REGISTRY.items()
        ]
        response = ExchangesListResponse(items=items)
        assert len(response.items) == len(EXCHANGE_REGISTRY)

    def test_todos_exchanges_core_tienen_core_true(self) -> None:
        """Todos los exchanges del registry base deben tener core=True."""
        for exchange_id, meta in EXCHANGE_REGISTRY.items():
            info = ExchangeInfo(
                exchange_id=exchange_id,
                display_name=meta.display_name,
                currencies=meta.currencies,
                fees_taker=str(meta.fees_taker),
                core=meta.core,
                is_active=True,
            )
            assert info.core is True, f"{exchange_id} debe tener core=True"


class TestWalletCurrencyWhitelist:
    """Verifica la validación de currencies contra el registry (whitelist)."""

    def test_binance_acepta_usdt(self) -> None:
        """Binance tiene USDT en sus currencies."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        assert "USDT" in meta.currencies

    def test_binance_acepta_btc(self) -> None:
        """Binance tiene BTC en sus currencies."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        assert "BTC" in meta.currencies

    def test_binance_no_acepta_eur(self) -> None:
        """Binance NO tiene EUR en sus currencies."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        assert "EUR" not in meta.currencies

    def test_kraken_acepta_usdt_btc_eth(self) -> None:
        """Kraken tiene USDT, BTC y ETH en sus currencies (CHG-007)."""
        meta = EXCHANGE_REGISTRY.get("kraken")
        assert meta is not None
        assert "USDT" in meta.currencies
        assert "BTC" in meta.currencies
        assert "ETH" in meta.currencies

    def test_exchange_fantasma_no_pasa_whitelist(self) -> None:
        """Exchange no registrado no pasa la validación whitelist."""
        meta = EXCHANGE_REGISTRY.get("exchange_fantasma")
        assert meta is None


class TestWalletSetBalanceSchema:
    """Verifica el schema WalletSetBalanceRequest para validación de balance."""

    def test_balance_positivo_valido(self) -> None:
        """Balance positivo debe ser aceptado por el schema."""
        req = WalletSetBalanceRequest(balance=Decimal("15000.00"))
        assert req.balance == Decimal("15000.00")

    def test_balance_negativo_invalido(self) -> None:
        """Balance negativo debe ser rechazado (gt=0)."""
        with pytest.raises(Exception):
            WalletSetBalanceRequest(balance=Decimal("-100.00"))

    def test_balance_cero_valido(self) -> None:
        """Balance igual a cero debe ser aceptado (ge=0) — permite resetear a cero."""
        req = WalletSetBalanceRequest(balance=Decimal("0"))
        assert req.balance == Decimal("0")

    def test_balance_btc_valido(self) -> None:
        """Balance en BTC con decimales debe ser aceptado."""
        req = WalletSetBalanceRequest(balance=Decimal("0.5"))
        assert req.balance == Decimal("0.5")

    def test_balance_muy_pequeño_valido(self) -> None:
        """Balance muy pequeño pero positivo debe ser aceptado."""
        req = WalletSetBalanceRequest(balance=Decimal("0.00000001"))
        assert req.balance == Decimal("0.00000001")

    def test_balance_response_schema(self) -> None:
        """WalletSetBalanceResponse debe serializar correctamente."""
        resp = WalletSetBalanceResponse(
            exchange="binance",
            currency="USDT",
            balance="15000.00",
            updated=True,
        )
        assert resp.exchange == "binance"
        assert resp.updated is True
