"""Yahoo Finance market data provider (unofficial API).

FREE - No API key required!
Uses yahooquery library which scrapes Yahoo Finance.
Great for development and testing.

Note: This is an unofficial API and may break without notice.
For production, consider Alpha Vantage or other official providers.
"""

from __future__ import annotations

from typing import Sequence
from decimal import Decimal
from datetime import datetime, timezone

from yahooquery import Ticker

from .base import MarketDataProvider
from ...models import Quote, Candle


class YahooFinanceMarketData(MarketDataProvider):
    """Yahoo Finance provider (zero config, no API key needed).

    Features:
    - FREE - No API key required
    - Real-time quotes (15-min delay)
    - Historical OHLCV data
    - No rate limits (but be respectful)

    Limitations:
    - Unofficial API (may break)
    - No symbol search
    - Less reliable than official APIs

    Best for:
    - Development and testing
    - MVPs with no budget
    - Fallback when other providers are rate-limited
    """

    def __init__(self) -> None:
        """Initialize Yahoo Finance provider (no configuration needed)."""
        pass

    def quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

        Returns:
            Quote with price and timestamp

        Raises:
            ValueError: Invalid symbol or no data
            Exception: Network or API errors
        """
        tk = Ticker(symbol, asynchronous=False)
        quotes = tk.quotes

        if isinstance(quotes, dict) and "error" in quotes:
            raise ValueError(f"Yahoo Finance error: {quotes['error']}")

        data = quotes.get(symbol)
        if not data:
            raise ValueError(f"No data returned for symbol: {symbol}")

        # Yahoo returns regularMarketPrice for current price
        price_raw = data.get("regularMarketPrice") or data.get("price")
        if price_raw is None:
            raise ValueError(f"No price data for symbol: {symbol}")

        price = Decimal(str(price_raw))

        # Get timestamp (use regularMarketTime or current time)
        ts_raw = data.get("regularMarketTime")
        if ts_raw:
            # Convert Unix timestamp to datetime
            as_of = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        else:
            as_of = datetime.now(timezone.utc)

        return Quote(
            symbol=symbol.upper(),
            price=price,
            as_of=as_of,
            currency=data.get("currency", "USD"),
        )

    def history(
        self, symbol: str, *, period: str = "1mo", interval: str = "1d"
    ) -> Sequence[Candle]:
        """Get historical OHLCV data.

        Args:
            symbol: Stock ticker symbol
            period: Time period ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            interval: Data interval ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")

        Returns:
            List of Candle objects (newest first)

        Raises:
            ValueError: Invalid symbol or period
            Exception: Network or API errors

        Note:
            Intraday data (1m, 5m, etc.) limited to last 7 days.
        """
        tk = Ticker(symbol, asynchronous=False)
        df = tk.history(period=period, interval=interval)

        if df is None or df.empty:
            return []

        # Reset index to access date column
        df = df.reset_index()

        candles: list[Candle] = []
        for _, row in df.iterrows():
            try:
                # Get timestamp
                date_val = row.get("date") or row.get("Date") or row.get("index")
                if date_val is None:
                    continue

                # Convert to datetime if needed
                if not isinstance(date_val, datetime):
                    # Try parsing as string
                    dt = datetime.fromisoformat(str(date_val))
                else:
                    dt = date_val

                # Ensure timezone aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                ts_ms = int(dt.timestamp() * 1000)

                candles.append(
                    Candle(
                        ts=ts_ms,
                        open=Decimal(str(row.get("open", 0))),
                        high=Decimal(str(row.get("high", 0))),
                        low=Decimal(str(row.get("low", 0))),
                        close=Decimal(str(row.get("close", 0))),
                        volume=Decimal(str(row.get("volume", 0))),
                    )
                )
            except (ValueError, KeyError, TypeError):
                continue  # Skip malformed rows

        # Reverse to get newest first (Yahoo returns oldest first)
        return list(reversed(candles))
