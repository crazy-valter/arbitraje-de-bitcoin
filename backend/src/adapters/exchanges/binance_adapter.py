"""
BinanceAdapter — adaptador ccxt.pro para Binance.

Monitorea BTC/USDT via WebSocket con feeds públicos.
API keys opcionales para funcionalidad extendida (via .env).
"""

import os

from adapters.exchanges.base_exchange import BaseExchangeAdapter


class BinanceAdapter(BaseExchangeAdapter):
    """Adaptador Binance — BTC/USDT via ccxt.pro WebSocket."""

    def __init__(self) -> None:
        super().__init__(
            exchange_id="binance",
            symbol="BTC/USDT",
            api_key=os.getenv("BINANCE_API_KEY", ""),
            secret=os.getenv("BINANCE_SECRET", ""),
        )
