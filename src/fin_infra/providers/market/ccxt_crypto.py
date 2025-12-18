from __future__ import annotations

from typing import Any, cast

try:
    import ccxt

    HAS_CCXT = True
except ImportError:  # pragma: no cover
    HAS_CCXT = False
    ccxt = None

from ..base import CryptoDataProvider


def _require_ccxt() -> None:
    """Raise ImportError if ccxt is not installed."""
    if not HAS_CCXT:
        raise ImportError(
            "Crypto exchange support requires the 'ccxt' package. "
            "Install with: pip install fin-infra[crypto] or pip install fin-infra[markets]"
        )


class CCXTCryptoData(CryptoDataProvider):
    """Exchange-agnostic crypto market data using CCXT."""

    def __init__(self, exchange: str = "binance") -> None:
        _require_ccxt()
        if not hasattr(ccxt, exchange):
            raise ValueError(f"Unknown exchange '{exchange}' in ccxt")
        self.exchange = getattr(ccxt, exchange)()
        # Defer load_markets to first call to avoid network on construction
        self._markets_loaded = False

    def ticker(self, symbol_pair: str) -> dict[Any, Any]:
        if not self._markets_loaded:
            self.exchange.load_markets()
            self._markets_loaded = True
        return cast("dict[Any, Any]", self.exchange.fetch_ticker(symbol_pair))

    def ohlcv(self, symbol_pair: str, timeframe: str = "1d", limit: int = 100) -> list[list[float]]:
        if not self._markets_loaded:
            self.exchange.load_markets()
            self._markets_loaded = True
        return cast(
            "list[list[float]]",
            self.exchange.fetch_ohlcv(symbol_pair, timeframe=timeframe, limit=limit),
        )
