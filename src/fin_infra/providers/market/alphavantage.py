"""Alpha Vantage market data provider.

Free tier: 5 requests/minute, 500 requests/day
Requires API key from https://www.alphavantage.co/support/#api-key
"""

from __future__ import annotations

import os
import time
from typing import Sequence
from decimal import Decimal
from datetime import datetime, timezone

import httpx

from .base import MarketDataProvider
from ...models import Quote, Candle
from ...settings import Settings


_BASE = "https://www.alphavantage.co/query"


class AlphaVantageMarketData(MarketDataProvider):
    """Alpha Vantage market data provider.

    Free tier: 5 requests/minute, 500/day
    Requires API key in ALPHA_VANTAGE_API_KEY or ALPHAVANTAGE_API_KEY env var.

    Features:
    - Real-time quotes (15-min delay on free tier)
    - Historical OHLCV data (daily, up to 20 years)
    - Symbol search
    - Company fundamentals (future)

    Rate limiting:
    - Implements basic client-side throttling (12 seconds between requests = 5/min)
    - Returns cached data on rate limit errors (if caching enabled via svc-infra)
    - Graceful degradation on errors
    """

    def __init__(
        self,
        api_key: str | None = None,
        settings: Settings | None = None,
        throttle: bool = True,
    ) -> None:
        """Initialize Alpha Vantage provider.

        Args:
            api_key: API key (or auto-detect from env)
            settings: Settings object (deprecated, use api_key)
            throttle: Enable basic rate limiting (12s between requests)
        """
        self.settings = settings or Settings()
        self.api_key = (
            api_key
            or os.environ.get("ALPHA_VANTAGE_API_KEY")
            or os.environ.get("ALPHAVANTAGE_API_KEY")
            or getattr(self.settings, "alphavantage_api_key", None)
        )
        self.throttle = throttle
        self._last_request_time = 0.0

        if not self.api_key:
            raise ValueError(
                "Alpha Vantage API key required. Set ALPHA_VANTAGE_API_KEY env var "
                "or pass api_key parameter. Get free key: https://www.alphavantage.co/support/#api-key"
            )

    def _throttle_request(self) -> None:
        """Implement basic rate limiting (5 req/min = 12s between requests)."""
        if not self.throttle:
            return

        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 12.0:  # 5 requests/minute
            sleep_time = 12.0 - elapsed
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

        Returns:
            Quote with price and timestamp

        Raises:
            ValueError: Invalid symbol
            httpx.HTTPStatusError: API errors
            httpx.TimeoutException: Request timeout
        """
        self._throttle_request()

        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.api_key}

        try:
            r = httpx.get(_BASE, params=params, timeout=20.0)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ValueError(
                    "Rate limit exceeded for Alpha Vantage. Free tier: 5 req/min, 500/day. "
                    "Consider caching with svc-infra or upgrading to paid tier."
                ) from e
            raise

        data = r.json()

        # Check for API error responses
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:  # Rate limit message
            raise ValueError(
                f"Alpha Vantage rate limit: {data['Note']}. "
                f"Enable caching with svc-infra to reduce API calls."
            )

        q = data.get("Global Quote", {})
        if not q:
            raise ValueError(f"No data returned for symbol: {symbol}")

        price = Decimal(str(q.get("05. price", "0")))
        ts = q.get("07. latest trading day")
        as_of = (
            datetime.strptime(ts, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if ts
            else datetime.now(timezone.utc)
        )

        return Quote(symbol=symbol.upper(), price=price, as_of=as_of)

    def history(
        self, symbol: str, *, period: str = "1mo", interval: str = "1d"
    ) -> Sequence[Candle]:
        """Get historical OHLCV data.

        Args:
            symbol: Stock ticker symbol
            period: Time period ("1mo", "3mo", "1y", "5y", "max")
            interval: Data interval ("1d" only on free tier)

        Returns:
            List of Candle objects (newest first)

        Raises:
            ValueError: Invalid symbol or period
            httpx.HTTPStatusError: API errors

        Note:
            Free tier supports daily data only.
            Intraday requires premium subscription.
        """
        self._throttle_request()

        # Map period to outputsize
        outputsize = "full" if period in ("1y", "5y", "max") else "compact"

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_key,
        }

        try:
            r = httpx.get(_BASE, params=params, timeout=20.0)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return []  # Graceful degradation on rate limit
            raise

        data = r.json()

        # Check for errors
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            return []  # Rate limit - return empty (cache should serve stale data)

        time_series = data.get("Time Series (Daily)", {})
        if not time_series:
            return []

        # Determine how many candles to return based on period
        limit_map = {
            "1mo": 30,
            "3mo": 90,
            "1y": 365,
            "5y": 1825,
            "max": 10000,
        }
        limit = limit_map.get(period, 30)

        out: list[Candle] = []
        for d, vals in list(time_series.items())[:limit]:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                ts_ms = int(dt.timestamp() * 1000)
                out.append(
                    Candle(
                        ts=ts_ms,
                        open=Decimal(str(vals.get("1. open", "0"))),
                        high=Decimal(str(vals.get("2. high", "0"))),
                        low=Decimal(str(vals.get("3. low", "0"))),
                        close=Decimal(str(vals.get("4. close", "0"))),
                        volume=Decimal(str(vals.get("5. volume", "0"))),
                    )
                )
            except (ValueError, KeyError):
                continue  # Skip malformed data

        return out

    def search(self, keywords: str) -> list[dict]:
        """Search for symbols matching keywords.

        Args:
            keywords: Search query (company name or ticker)

        Returns:
            List of matching symbols with metadata:
            [{
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "type": "Equity",
                "region": "United States",
                "currency": "USD"
            }]

        Raises:
            ValueError: Empty keywords
            httpx.HTTPStatusError: API errors
        """
        if not keywords or not keywords.strip():
            raise ValueError("Search keywords cannot be empty")

        self._throttle_request()

        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
            "apikey": self.api_key,
        }

        try:
            r = httpx.get(_BASE, params=params, timeout=20.0)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return []  # Rate limit - return empty
            raise

        data = r.json()

        # Check for errors
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            return []  # Rate limit

        matches = data.get("bestMatches", [])
        results = []

        for match in matches:
            results.append(
                {
                    "symbol": match.get("1. symbol", ""),
                    "name": match.get("2. name", ""),
                    "type": match.get("3. type", ""),
                    "region": match.get("4. region", ""),
                    "currency": match.get("8. currency", "USD"),
                }
            )

        return results
