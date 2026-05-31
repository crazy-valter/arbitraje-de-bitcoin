"""
Tests unitarios: MetricsResponse schema.

Verifica que el schema incluye los campos renombrados/agregados en CHG-004:
- opportunities_detected (renombrado desde opportunities_total)
- trades_simulated (renombrado desde executed_total)
- uptime_seconds (campo nuevo, int >= 0)

No requiere base de datos ni Redis — es un test de schema puro.
"""

from api.schemas import MetricsResponse


class TestMetricsResponseFields:
    def test_has_opportunities_detected_field(self) -> None:
        """El schema debe tener el campo opportunities_detected (no opportunities_total)."""
        fields = MetricsResponse.model_fields
        assert "opportunities_detected" in fields
        assert "opportunities_total" not in fields

    def test_has_trades_simulated_field(self) -> None:
        """El schema debe tener el campo trades_simulated (no executed_total)."""
        fields = MetricsResponse.model_fields
        assert "trades_simulated" in fields
        assert "executed_total" not in fields

    def test_has_uptime_seconds_field(self) -> None:
        """El schema debe tener el campo uptime_seconds de tipo int."""
        fields = MetricsResponse.model_fields
        assert "uptime_seconds" in fields
        annotation = fields["uptime_seconds"].annotation
        assert annotation is int

    def test_instantiation_with_all_fields(self) -> None:
        """El schema debe instanciarse correctamente con los campos esperados."""
        metrics = MetricsResponse(
            opportunities_detected=42,
            trades_simulated=10,
            uptime_seconds=3600,
            win_rate_pct=75.0,
            total_pnl_usdt=1234.56,
            connected_exchanges=3,
            timestamp="2026-05-29T00:00:00+00:00",
        )
        assert metrics.opportunities_detected == 42
        assert metrics.trades_simulated == 10
        assert metrics.uptime_seconds == 3600

    def test_uptime_seconds_accepts_zero(self) -> None:
        """uptime_seconds >= 0 — debe aceptar el valor 0 (primer segundo de vida)."""
        metrics = MetricsResponse(
            opportunities_detected=0,
            trades_simulated=0,
            uptime_seconds=0,
            win_rate_pct=0.0,
            total_pnl_usdt=0.0,
            connected_exchanges=0,
            timestamp="2026-05-29T00:00:00+00:00",
        )
        assert metrics.uptime_seconds == 0
