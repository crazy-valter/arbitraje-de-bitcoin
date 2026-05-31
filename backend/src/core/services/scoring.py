"""
Scoring de oportunidades de arbitraje.

El score (0.0-1.0) combina múltiples factores para priorizar
las oportunidades más rentables y confiables:

- net_profit_pct: peso principal (mayor profit → mayor score)
- max_volume_btc: liquidez disponible (más volumen → mejor)
- gross_spread_pct: spread bruto como señal de calidad
- staleness penalty: descuento si los order books están desactualizados
"""

from decimal import Decimal

import structlog

logger = structlog.get_logger(__name__)

# Pesos del scoring
_WEIGHT_PROFIT = 0.5
_WEIGHT_VOLUME = 0.3
_WEIGHT_SPREAD = 0.2

# Referencias de normalización
_MAX_EXPECTED_PROFIT_PCT = Decimal("2.0")   # 2% sería un profit extraordinario
_MAX_EXPECTED_VOLUME_BTC = Decimal("1.0")   # 1 BTC como referencia de liquidez alta
_MAX_EXPECTED_SPREAD_PCT = Decimal("1.0")   # 1% spread bruto como referencia

# Penalización por datos stale
_STALE_PENALTY = 0.3


def calculate_score(
    net_profit_pct: Decimal,
    max_volume_btc: Decimal,
    gross_spread_pct: Decimal,
    has_stale_data: bool = False,
) -> float:
    """
    Calcula el score de prioridad de una oportunidad.

    Retorna un float en [0.0, 1.0]. Scores más altos → mayor prioridad.
    Si hay datos stale (order book vencido), aplica penalización.
    """
    # Normalizar cada factor a [0.0, 1.0]
    profit_norm = float(
        min(net_profit_pct / _MAX_EXPECTED_PROFIT_PCT, Decimal("1.0"))
    )
    volume_norm = float(
        min(max_volume_btc / _MAX_EXPECTED_VOLUME_BTC, Decimal("1.0"))
    )
    spread_norm = float(
        min(gross_spread_pct / _MAX_EXPECTED_SPREAD_PCT, Decimal("1.0"))
    )

    # Evitar scores negativos si algún valor es negativo (oportunidad inválida)
    profit_norm = max(0.0, profit_norm)
    volume_norm = max(0.0, volume_norm)
    spread_norm = max(0.0, spread_norm)

    raw_score = (
        _WEIGHT_PROFIT * profit_norm
        + _WEIGHT_VOLUME * volume_norm
        + _WEIGHT_SPREAD * spread_norm
    )

    # Penalizar si los datos están desactualizados
    if has_stale_data:
        raw_score = raw_score * (1.0 - _STALE_PENALTY)

    score = round(min(max(raw_score, 0.0), 1.0), 4)

    logger.debug(
        "score_calculated",
        net_profit_pct=float(net_profit_pct),
        max_volume_btc=float(max_volume_btc),
        gross_spread_pct=float(gross_spread_pct),
        has_stale_data=has_stale_data,
        score=score,
    )
    return score
