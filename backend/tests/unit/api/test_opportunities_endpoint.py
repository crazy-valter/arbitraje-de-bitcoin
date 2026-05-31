"""
Tests unitarios: validacion de parametros del endpoint GET /api/opportunities.

No usa TestClient (httpx no disponible en el contenedor dev).
Verifica el schema OpportunitiesListResponse, OpportunityResponse,
la logica de validacion de status/exchange y la serializacion de campos CHG-009.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from api.schemas import OpportunitiesListResponse, OpportunityResponse
from core.entities.opportunity import OpportunityStatus


def _make_opportunity(**kwargs: object) -> OpportunityResponse:
    """Fabrica un OpportunityResponse con valores por defecto."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": uuid4(),
        "buy_exchange": "binance",
        "sell_exchange": "kraken",
        "buy_price": "95000.00000000",
        "sell_price": "95500.00000000",
        "gross_spread_pct": "0.526316",
        "total_fees_usdt": "150.00000000",
        "slippage_usdt": "10.00000000",
        "net_profit_usdt": "340.00000000",
        "net_profit_pct": "0.357895",
        "max_volume_btc": "0.10000000",
        "strategy": "cross_exchange",
        "score": 0.8542,
        "status": "EXECUTED",
        "detected_at": now,
        "executed_at": now,
        "trading_fee_buy_usdt": "95.00000000",
        "trading_fee_sell_usdt": "95.50000000",
        "withdrawal_fee_usdt": "0.00000000",
        "network_latency_ms": "0.00",
    }
    defaults.update(kwargs)
    return OpportunityResponse(**defaults)  # type: ignore[arg-type]


class TestOpportunityResponseSchema:
    """Verifica que OpportunityResponse incluye los campos de CHG-009."""

    def test_incluye_trading_fee_buy_usdt(self) -> None:
        op = _make_opportunity(trading_fee_buy_usdt="95.00000000")
        assert op.trading_fee_buy_usdt == "95.00000000"

    def test_incluye_trading_fee_sell_usdt(self) -> None:
        op = _make_opportunity(trading_fee_sell_usdt="95.50000000")
        assert op.trading_fee_sell_usdt == "95.50000000"

    def test_incluye_withdrawal_fee_usdt(self) -> None:
        op = _make_opportunity(withdrawal_fee_usdt="5.00000000")
        assert op.withdrawal_fee_usdt == "5.00000000"

    def test_incluye_network_latency_ms(self) -> None:
        op = _make_opportunity(network_latency_ms="12.50")
        assert op.network_latency_ms == "12.50"

    def test_defaults_son_cero(self) -> None:
        """Campos de desglose deben defaultear a '0' si no se proveen."""
        now = datetime.now(timezone.utc)
        op = OpportunityResponse(
            id=uuid4(),
            buy_exchange="binance",
            sell_exchange="bybit",
            buy_price="95000",
            sell_price="95300",
            gross_spread_pct="0.315",
            total_fees_usdt="100",
            slippage_usdt="5",
            net_profit_usdt="195",
            net_profit_pct="0.205",
            max_volume_btc="0.05",
            strategy="cross_exchange",
            score=0.75,
            status="REJECTED",
            detected_at=now,
        )
        assert op.trading_fee_buy_usdt == "0"
        assert op.trading_fee_sell_usdt == "0"
        assert op.withdrawal_fee_usdt == "0"
        assert op.network_latency_ms == "0"

    def test_incluye_campo_status(self) -> None:
        op = _make_opportunity(status="REJECTED")
        assert op.status == "REJECTED"


class TestOpportunitiesListResponseSchema:
    """Verifica la estructura de la respuesta paginada."""

    def test_items_y_total(self) -> None:
        """La respuesta paginada debe tener items y total."""
        op1 = _make_opportunity()
        op2 = _make_opportunity(status="REJECTED")
        response = OpportunitiesListResponse(items=[op1, op2], total=2)
        assert len(response.items) == 2
        assert response.total == 2

    def test_limit_dos_devuelve_exactamente_dos(self) -> None:
        """Simula que offset=0&limit=2 devuelve exactamente 2 items."""
        items = [_make_opportunity() for _ in range(2)]
        response = OpportunitiesListResponse(items=items, total=10)
        assert len(response.items) == 2
        assert response.total == 10  # total refleja COUNT real, no len(items)

    def test_respuesta_vacia(self) -> None:
        response = OpportunitiesListResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestOpportunityStatusValidation:
    """Verifica la logica de validacion del enum OpportunityStatus."""

    def test_status_ejecutado_valido(self) -> None:
        assert OpportunityStatus("EXECUTED") == OpportunityStatus.EXECUTED

    def test_status_rechazado_valido(self) -> None:
        assert OpportunityStatus("REJECTED") == OpportunityStatus.REJECTED

    def test_status_fallido_valido(self) -> None:
        assert OpportunityStatus("FAILED") == OpportunityStatus.FAILED

    def test_status_detectado_valido(self) -> None:
        assert OpportunityStatus("DETECTED") == OpportunityStatus.DETECTED

    def test_status_invalido_lanza_error(self) -> None:
        with pytest.raises(ValueError):
            OpportunityStatus("INVALID_STATUS")

    def test_todos_los_estados_validos(self) -> None:
        valid = {"DETECTED", "EXECUTING", "EXECUTED", "REJECTED", "FAILED"}
        assert {s.value for s in OpportunityStatus} == valid


class TestExchangeWhitelistValidation:
    """Verifica la validacion de exchanges contra EXCHANGE_REGISTRY."""

    def test_exchanges_validos_en_registry(self) -> None:
        from adapters.exchanges.registry import EXCHANGE_REGISTRY
        assert "binance" in EXCHANGE_REGISTRY
        assert "bybit" in EXCHANGE_REGISTRY
        assert "kraken" in EXCHANGE_REGISTRY

    def test_exchange_invalido_no_en_registry(self) -> None:
        from adapters.exchanges.registry import EXCHANGE_REGISTRY
        assert "fake_exchange" not in EXCHANGE_REGISTRY
        assert "bitmex" not in EXCHANGE_REGISTRY
