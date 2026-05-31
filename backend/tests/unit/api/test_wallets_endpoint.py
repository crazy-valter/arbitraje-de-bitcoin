"""
Tests unitarios: lógica del endpoint PUT /api/wallets/{exchange}/{currency}.

No usa TestClient (httpx no disponible en el contenedor dev).
Prueba la validación de balance, whitelist de exchanges y currencies,
usando los schemas Pydantic y el registry directamente.
"""

from decimal import Decimal

import pytest

from adapters.exchanges.registry import EXCHANGE_REGISTRY
from api.schemas import WalletSetBalanceRequest, WalletSetBalanceResponse


class TestWalletBalanceValidation:
    """Verifica validación del balance en WalletSetBalanceRequest."""

    def test_balance_valido_retorna_objeto(self) -> None:
        """Balance positivo debe crear WalletSetBalanceRequest sin error."""
        req = WalletSetBalanceRequest(balance=Decimal("15000.00"))
        assert req.balance == Decimal("15000.00")

    def test_balance_negativo_lanza_error(self) -> None:
        """Balance negativo debe levantar ValidationError (gt=0)."""
        with pytest.raises(Exception):
            WalletSetBalanceRequest(balance=Decimal("-100.00"))

    def test_balance_cero_valido(self) -> None:
        """Balance igual a cero debe ser aceptado (ge=0) — permite resetear a cero."""
        req = WalletSetBalanceRequest(balance=Decimal("0"))
        assert req.balance == Decimal("0")

    def test_balance_btc_pequeño_valido(self) -> None:
        """Balance BTC con 8 decimales debe ser aceptado."""
        req = WalletSetBalanceRequest(balance=Decimal("0.00000001"))
        assert req.balance == Decimal("0.00000001")

    def test_balance_grande_valido(self) -> None:
        """Balance grande en USDT debe ser aceptado."""
        req = WalletSetBalanceRequest(balance=Decimal("9999999.99"))
        assert req.balance == Decimal("9999999.99")


class TestWalletExchangeWhitelist:
    """Verifica que solo exchanges del registry sean aceptados."""

    def test_binance_en_registry(self) -> None:
        """Binance debe estar en el registry."""
        assert "binance" in EXCHANGE_REGISTRY

    def test_bybit_en_registry(self) -> None:
        """Bybit debe estar en el registry."""
        assert "bybit" in EXCHANGE_REGISTRY

    def test_kraken_en_registry(self) -> None:
        """Kraken debe estar en el registry."""
        assert "kraken" in EXCHANGE_REGISTRY

    def test_exchange_fantasma_no_en_registry(self) -> None:
        """Exchange no registrado no debe pasar la whitelist."""
        assert "exchange_fantasma" not in EXCHANGE_REGISTRY
        assert EXCHANGE_REGISTRY.get("exchange_fantasma") is None

    def test_inyeccion_no_pasa_whitelist(self) -> None:
        """Intento de inyección de path no debe estar en el registry."""
        assert "../admin" not in EXCHANGE_REGISTRY
        assert "binance; DROP TABLE wallets" not in EXCHANGE_REGISTRY


class TestWalletCurrencyWhitelist:
    """Verifica que solo currencies válidas para cada exchange sean aceptadas."""

    def test_binance_usdt_valido(self) -> None:
        """USDT es currency válida para Binance."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        assert "USDT" in meta.currencies

    def test_binance_btc_valido(self) -> None:
        """BTC es currency válida para Binance."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        assert "BTC" in meta.currencies

    def test_binance_eur_invalido(self) -> None:
        """EUR no es currency válida para Binance."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        assert "EUR" not in meta.currencies

    def test_kraken_usdt_valido(self) -> None:
        """USDT es currency válida para Kraken (CHG-007)."""
        meta = EXCHANGE_REGISTRY.get("kraken")
        assert meta is not None
        assert "USDT" in meta.currencies

    def test_kraken_eth_valido(self) -> None:
        """ETH es currency válida para Kraken (CHG-007)."""
        meta = EXCHANGE_REGISTRY.get("kraken")
        assert meta is not None
        assert "ETH" in meta.currencies

    def test_kraken_btc_valido(self) -> None:
        """BTC es currency válida para Kraken."""
        meta = EXCHANGE_REGISTRY.get("kraken")
        assert meta is not None
        assert "BTC" in meta.currencies


class TestWalletSetBalanceResponse:
    """Verifica el schema de respuesta del endpoint PUT /api/wallets."""

    def test_response_binance_usdt(self) -> None:
        """Respuesta para Binance USDT debe ser correcta."""
        resp = WalletSetBalanceResponse(
            exchange="binance",
            currency="USDT",
            balance="15000.00",
            updated=True,
        )
        assert resp.exchange == "binance"
        assert resp.currency == "USDT"
        assert resp.balance == "15000.00"
        assert resp.updated is True

    def test_balance_es_string_en_respuesta(self) -> None:
        """El balance en la respuesta debe ser string (Decimal serializado)."""
        resp = WalletSetBalanceResponse(
            exchange="kraken",
            currency="USD",
            balance="5000.00",
            updated=True,
        )
        assert isinstance(resp.balance, str)
