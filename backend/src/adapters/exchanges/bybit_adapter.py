"""
BybitAdapter — adaptador ccxt.pro para Bybit.

Monitorea BTC/USDT via WebSocket con feeds públicos.
API keys opcionales para funcionalidad extendida (via .env).
"""

import os

from adapters.exchanges.base_exchange import BaseExchangeAdapter


class BybitAdapter(BaseExchangeAdapter):
    """Adaptador Bybit — BTC/USDT via ccxt.pro WebSocket."""

    def __init__(self) -> None:
        super().__init__(
            exchange_id="bybit",
            symbol="BTC/USDT",
            api_key=os.getenv("BYBIT_API_KEY", ""),
            secret=os.getenv("BYBIT_SECRET", ""),
        )
