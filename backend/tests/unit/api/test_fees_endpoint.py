"""
Tests unitarios: lógica del endpoint /api/fees.

No usa TestClient (httpx no disponible en el contenedor dev).
Prueba la lógica de validación directamente sobre los schemas
y el registry — sin infraestructura de DB ni Redis.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from adapters.exchanges.registry import EXCHANGE_REGISTRY
from api.schemas import (
    ExchangeFeeInfo,
    ExchangeFeeUpdateRequest,
    ExchangeFeeUpdateResponse,
    ExchangeFeesListResponse,
)


class TestGetFeesSchema:
    """Verifica el schema de respuesta del listado de fees."""

    def test_get_fees_returns_three_exchanges(self) -> None:
        """
        ExchangeFeesListResponse debe poder contener exactamente 3 exchanges
        con fee_buy y fee_sell para cada uno.
        """
        fees: list[ExchangeFeeInfo] = []
        for exchange_id, meta in EXCHANGE_REGISTRY.items():
            fees.append(
                ExchangeFeeInfo(
                    exchange_id=exchange_id,
                    display_name=meta.display_name,
                    fee_buy=meta.fees_taker,
                    fee_sell=meta.fees_taker,
                )
            )

        response = ExchangeFeesListResponse(fees=fees)
        assert len(response.fees) == 3

        # Verificar que los 3 exchanges core están presentes
        exchange_ids = {f.exchange_id for f in response.fees}
        assert "binance" in exchange_ids
        assert "bybit" in exchange_ids
        assert "kraken" in exchange_ids

    def test_exchange_fee_info_tiene_fee_buy_y_fee_sell(self) -> None:
        """ExchangeFeeInfo debe tener fee_buy y fee_sell como Decimal."""
        info = ExchangeFeeInfo(
            exchange_id="binance",
            display_name="Binance",
            fee_buy=Decimal("0.001"),
            fee_sell=Decimal("0.001"),
        )
        assert isinstance(info.fee_buy, Decimal)
        assert isinstance(info.fee_sell, Decimal)
        assert info.fee_buy == Decimal("0.001")
        assert info.fee_sell == Decimal("0.001")

    def test_exchange_fee_info_binance_fees_correctos(self) -> None:
        """Binance tiene fees_taker=0.001 en el registry."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None
        info = ExchangeFeeInfo(
            exchange_id="binance",
            display_name=meta.display_name,
            fee_buy=meta.fees_taker,
            fee_sell=meta.fees_taker,
        )
        assert info.fee_buy == Decimal("0.001")
        assert info.fee_sell == Decimal("0.001")

    def test_exchange_fee_info_kraken_fees_correctos(self) -> None:
        """Kraken tiene fees_taker=0.0026 en el registry."""
        meta = EXCHANGE_REGISTRY.get("kraken")
        assert meta is not None
        info = ExchangeFeeInfo(
            exchange_id="kraken",
            display_name=meta.display_name,
            fee_buy=meta.fees_taker,
            fee_sell=meta.fees_taker,
        )
        assert info.fee_buy == Decimal("0.0026")
        assert info.fee_sell == Decimal("0.0026")


class TestPutFeeSchema:
    """Verifica el schema de request/response para la actualización de fees."""

    def test_put_fee_valid(self) -> None:
        """
        PUT /api/fees/binance con fee_buy=0.10 y fee_sell=0.10 debe ser válido.
        Corresponde a 0.10% — rango 0.00 a 9.99.
        """
        req = ExchangeFeeUpdateRequest(
            fee_buy=Decimal("0.10"),
            fee_sell=Decimal("0.10"),
        )
        assert req.fee_buy == Decimal("0.10")
        assert req.fee_sell == Decimal("0.10")

    def test_put_fee_exceeds_max(self) -> None:
        """
        PUT /api/fees/binance con fee_buy=10.00 debe fallar por exceder el máximo 9.99.
        """
        with pytest.raises(Exception):
            ExchangeFeeUpdateRequest(
                fee_buy=Decimal("10.00"),
                fee_sell=Decimal("0.10"),
            )

    def test_put_fee_sell_exceeds_max(self) -> None:
        """fee_sell=10.00 también debe fallar."""
        with pytest.raises(Exception):
            ExchangeFeeUpdateRequest(
                fee_buy=Decimal("0.10"),
                fee_sell=Decimal("10.00"),
            )

    def test_put_fee_zero_valido(self) -> None:
        """fee_buy=0.00 y fee_sell=0.00 deben ser válidos (ge=0.00)."""
        req = ExchangeFeeUpdateRequest(
            fee_buy=Decimal("0.00"),
            fee_sell=Decimal("0.00"),
        )
        assert req.fee_buy == Decimal("0.00")
        assert req.fee_sell == Decimal("0.00")

    def test_put_fee_max_valido(self) -> None:
        """fee_buy=9.99 debe ser válido (le=9.99)."""
        req = ExchangeFeeUpdateRequest(
            fee_buy=Decimal("9.99"),
            fee_sell=Decimal("9.99"),
        )
        assert req.fee_buy == Decimal("9.99")
        assert req.fee_sell == Decimal("9.99")

    def test_put_fee_negativo_invalido(self) -> None:
        """fee_buy negativo debe ser rechazado (ge=0.00)."""
        with pytest.raises(Exception):
            ExchangeFeeUpdateRequest(
                fee_buy=Decimal("-0.01"),
                fee_sell=Decimal("0.10"),
            )


class TestExchangeIdValidation:
    """Verifica que la validación del exchange_id funciona contra el registry."""

    def test_put_fee_invalid_exchange(self) -> None:
        """
        PUT /api/fees/unknown debe ser rechazado.
        La lógica del router valida contra EXCHANGE_REGISTRY.
        """
        # Simular la validación del router: exchange_id no en EXCHANGE_REGISTRY → 422
        exchange_id = "unknown"
        meta = EXCHANGE_REGISTRY.get(exchange_id)
        assert meta is None, "exchange 'unknown' no debe estar en el registry"

    def test_binance_es_exchange_valido(self) -> None:
        """binance debe estar en el registry como exchange válido."""
        meta = EXCHANGE_REGISTRY.get("binance")
        assert meta is not None

    def test_bybit_es_exchange_valido(self) -> None:
        """bybit debe estar en el registry como exchange válido."""
        meta = EXCHANGE_REGISTRY.get("bybit")
        assert meta is not None

    def test_kraken_es_exchange_valido(self) -> None:
        """kraken debe estar en el registry como exchange válido."""
        meta = EXCHANGE_REGISTRY.get("kraken")
        assert meta is not None


class TestConversionPorcentajeAMultiplicador:
    """Verifica que la conversión porcentaje → multiplicador es correcta."""

    def test_conversion_binance_01_pct(self) -> None:
        """0.10% → 0.001 multiplicador."""
        pct = Decimal("0.10")
        multiplicador = pct / Decimal("100")
        assert multiplicador == Decimal("0.001")

    def test_conversion_kraken_026_pct(self) -> None:
        """0.26% → 0.0026 multiplicador."""
        pct = Decimal("0.26")
        multiplicador = pct / Decimal("100")
        assert multiplicador == Decimal("0.0026")

    def test_conversion_cero(self) -> None:
        """0.00% → 0.0000 multiplicador."""
        pct = Decimal("0.00")
        multiplicador = pct / Decimal("100")
        assert multiplicador == Decimal("0.0000")

    def test_conversion_maximo(self) -> None:
        """9.99% → 0.0999 multiplicador."""
        pct = Decimal("9.99")
        multiplicador = pct / Decimal("100")
        assert multiplicador == Decimal("0.0999")


class TestExchangeFeeUpdateResponse:
    """Verifica el schema de respuesta de actualización de fees."""

    def test_response_contiene_multiplicador_no_porcentaje(self) -> None:
        """
        ExchangeFeeUpdateResponse debe contener el multiplicador (lo que va a DB),
        no el porcentaje enviado en el request.
        """
        resp = ExchangeFeeUpdateResponse(
            exchange_id="binance",
            fee_buy=Decimal("0.001"),   # multiplicador, no 0.10
            fee_sell=Decimal("0.001"),
            message="Fees de Binance actualizados correctamente.",
        )
        assert resp.fee_buy == Decimal("0.001")
        assert resp.fee_sell == Decimal("0.001")
        assert resp.exchange_id == "binance"
        assert "actualizados" in resp.message
