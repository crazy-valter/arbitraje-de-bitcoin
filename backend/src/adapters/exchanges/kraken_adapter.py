"""
KrakenAdapter — adaptador ccxt.pro para Kraken.

Monitorea BTC/USDT via WebSocket con feeds públicos.
Nota: Kraken usa "XBT/USDT" internamente en algunos endpoints;
ccxt.pro normaliza a "BTC/USDT" automáticamente.
API keys opcionales para funcionalidad extendida (via .env).
"""

import os

from adapters.exchanges.base_exchange import BaseExchangeAdapter


class KrakenAdapter(BaseExchangeAdapter):
    """Adaptador Kraken — BTC/USDT via ccxt.pro WebSocket."""

    def __init__(self) -> None:
        super().__init__(
            exchange_id="kraken",
            symbol="BTC/USDT",
            api_key=os.getenv("KRAKEN_API_KEY", ""),
            secret=os.getenv("KRAKEN_SECRET", ""),
        )
