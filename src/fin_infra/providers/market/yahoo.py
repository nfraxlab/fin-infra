from __future__ import annotations

from typing import Any

from yahooquery import Ticker

from .base import MarketDataProvider
from ...settings import Settings


class YahooMarketData(MarketDataProvider):
    """Thin wrapper around yahooquery for consistent interface."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def quote(self, symbol: str) -> dict:
        tk = Ticker(symbol, asynchronous=False)
        q = tk.quotes
        return q.get(symbol) or {}

    def history(self, symbol: str, *, period: str = "1mo", interval: str = "1d") -> Any:
        tk = Ticker(symbol, asynchronous=False)
        df = tk.history(period=period, interval=interval)
        return df.reset_index()
