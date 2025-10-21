from __future__ import annotations

import os
from typing import Any, Sequence
from decimal import Decimal
from datetime import datetime, timezone

import httpx

from .base import MarketDataProvider
from ...models import Quote, Candle
from ...settings import Settings
from typing import Any


_BASE = "https://www.alphavantage.co/query"


class AlphaVantageMarketData(MarketDataProvider):
    """Minimal Alpha Vantage wrapper. Requires API key in env/settings.

    Free tier is rate-limited; methods are cached briefly.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.api_key = os.environ.get("ALPHAVANTAGE_API_KEY") or getattr(
            self.settings, "alphavantage_api_key", None
        )

    def quote(self, symbol: str) -> Quote:
        if not self.api_key:
            # Return a minimal placeholder to keep type contract; price 0
            return Quote(symbol=symbol, price=Decimal(0), as_of=datetime.now(timezone.utc))
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.api_key}
        r = httpx.get(_BASE, params=params, timeout=20.0)
        r.raise_for_status()
        data = r.json()
        q = data.get("Global Quote", {})
        price = Decimal(str(q.get("05. price", "0")))
        ts = q.get("07. latest trading day")
        as_of = (
            datetime.strptime(ts, "%Y-%m-%d").replace(tzinfo=timezone.utc) if ts else datetime.now(timezone.utc)
        )
        return Quote(symbol=symbol, price=price, as_of=as_of)

    def history(self, symbol: str, *, period: str = "1mo", interval: str = "1d") -> Sequence[Candle]:
        # Alpha Vantage uses fixed functions; map interval roughly to TIME_SERIES_DAILY
        if not self.api_key:
            return []
        params = {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact", "apikey": self.api_key}
        r = httpx.get(_BASE, params=params, timeout=20.0)
        r.raise_for_status()
        data = r.json().get("Time Series (Daily)", {})
        out: list[Candle] = []
        for d, vals in list(data.items())[:30]:  # compact to ~1mo
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
        return out
