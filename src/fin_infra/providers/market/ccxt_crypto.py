from __future__ import annotations

import ccxt

from ..base import CryptoDataProvider


class CCXTCryptoData(CryptoDataProvider):
    """Exchange-agnostic crypto market data using CCXT."""

    def __init__(self, exchange: str = "binance") -> None:
        if not hasattr(ccxt, exchange):
            raise ValueError(f"Unknown exchange '{exchange}' in ccxt")
        self.exchange = getattr(ccxt, exchange)()
        # Defer load_markets to first call to avoid network on construction
        self._markets_loaded = False

    def ticker(self, symbol_pair: str) -> dict:
        if not self._markets_loaded:
            self.exchange.load_markets()
            self._markets_loaded = True
        return self.exchange.fetch_ticker(symbol_pair)

    def ohlcv(self, symbol_pair: str, timeframe: str = "1d", limit: int = 100) -> list[list[float]]:
        if not self._markets_loaded:
            self.exchange.load_markets()
            self._markets_loaded = True
        return self.exchange.fetch_ohlcv(symbol_pair, timeframe=timeframe, limit=limit)
