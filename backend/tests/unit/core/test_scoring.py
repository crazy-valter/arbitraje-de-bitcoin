"""
Tests unitarios: calculate_score.

Verifica que el scoring combine correctamente los factores
y que la penalización por datos stale funcione.
"""

from decimal import Decimal

import pytest

from core.services.scoring import calculate_score


class TestCalculateScore:
    def test_score_within_bounds(self) -> None:
        """El score siempre debe estar en [0.0, 1.0]."""
        score = calculate_score(
            net_profit_pct=Decimal("0.5"),
            max_volume_btc=Decimal("0.3"),
            gross_spread_pct=Decimal("0.8"),
        )
        assert 0.0 <= score <= 1.0

    def test_high_profit_gives_higher_score(self) -> None:
        """Mayor profit_pct → mayor score (peso principal)."""
        score_low = calculate_score(
            net_profit_pct=Decimal("0.1"),
            max_volume_btc=Decimal("0.5"),
            gross_spread_pct=Decimal("0.5"),
        )
        score_high = calculate_score(
            net_profit_pct=Decimal("1.5"),
            max_volume_btc=Decimal("0.5"),
            gross_spread_pct=Decimal("0.5"),
        )
        assert score_high > score_low

    def test_stale_data_penalizes_score(self) -> None:
        """Datos stale deben resultar en score más bajo."""
        score_fresh = calculate_score(
            net_profit_pct=Decimal("0.5"),
            max_volume_btc=Decimal("0.5"),
            gross_spread_pct=Decimal("0.5"),
            has_stale_data=False,
        )
        score_stale = calculate_score(
            net_profit_pct=Decimal("0.5"),
            max_volume_btc=Decimal("0.5"),
            gross_spread_pct=Decimal("0.5"),
            has_stale_data=True,
        )
        assert score_stale < score_fresh

    def test_negative_profit_gives_zero_score(self) -> None:
        """Profit negativo no debe dar score negativo."""
        score = calculate_score(
            net_profit_pct=Decimal("-1.0"),
            max_volume_btc=Decimal("0.5"),
            gross_spread_pct=Decimal("0.0"),
        )
        assert score >= 0.0

    def test_perfect_conditions_near_one(self) -> None:
        """Condiciones ideales deben dar score cercano a 1.0."""
        score = calculate_score(
            net_profit_pct=Decimal("2.0"),   # máximo esperado
            max_volume_btc=Decimal("1.0"),   # máximo esperado
            gross_spread_pct=Decimal("1.0"), # máximo esperado
        )
        assert score >= 0.95

    def test_zero_conditions_gives_zero(self) -> None:
        """Sin profit ni volumen → score cero."""
        score = calculate_score(
            net_profit_pct=Decimal("0"),
            max_volume_btc=Decimal("0"),
            gross_spread_pct=Decimal("0"),
        )
        assert score == 0.0

    def test_score_is_rounded_to_4_decimals(self) -> None:
        """El score debe tener máximo 4 decimales."""
        score = calculate_score(
            net_profit_pct=Decimal("0.333"),
            max_volume_btc=Decimal("0.333"),
            gross_spread_pct=Decimal("0.333"),
        )
        assert round(score, 4) == score

    def test_volume_contributes_to_score(self) -> None:
        """Mayor volumen → mayor score (mismo profit)."""
        score_low_vol = calculate_score(
            net_profit_pct=Decimal("0.5"),
            max_volume_btc=Decimal("0.1"),
            gross_spread_pct=Decimal("0.5"),
        )
        score_high_vol = calculate_score(
            net_profit_pct=Decimal("0.5"),
            max_volume_btc=Decimal("0.9"),
            gross_spread_pct=Decimal("0.5"),
        )
        assert score_high_vol > score_low_vol
