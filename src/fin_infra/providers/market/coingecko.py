from __future__ import annotations

import httpx
from decimal import Decimal
from datetime import datetime, timezone

from ..base import CryptoDataProvider
from ...models import Quote, Candle


_BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoCryptoData(CryptoDataProvider):
    def __init__(self) -> None:
        # No auth required for public endpoints
        pass

    def ticker(self, symbol_pair: str) -> Quote:
        # Translate 'BTC/USDT' -> ids=bitcoin vs vs_currencies=usdt using simple mapping
        base, quote = symbol_pair.replace("-", "/").split("/")
        params: dict[str, str] = {"ids": _to_cg_id(base), "vs_currencies": quote.lower()}
        try:
            r = httpx.get(f"{_BASE}/simple/price", params=params, timeout=20.0)
            r.raise_for_status()
            data = r.json()
            price = data.get(_to_cg_id(base), {}).get(quote.lower(), 0)
        except Exception:
            price = 0
        return Quote(
            symbol=f"{base}/{quote}", price=Decimal(str(price)), as_of=datetime.now(timezone.utc)
        )

    def ohlcv(self, symbol_pair: str, timeframe: str = "1d", limit: int = 100) -> list[Candle]:
        # CoinGecko provides market_chart with daily data; map timeframe crudely
        base, quote = symbol_pair.replace("-", "/").split("/")
        days = _tf_to_days(timeframe, limit)
        params: dict[str, str | int] = {"vs_currency": quote.lower(), "days": days}
        try:
            r = httpx.get(
                f"{_BASE}/coins/{_to_cg_id(base)}/market_chart", params=params, timeout=20.0
            )
            r.raise_for_status()
            prices = r.json().get("prices", [])
        except Exception:
            prices = []
        out: list[Candle] = []
        for p in prices[:limit]:
            ts_ms = int(p[0])
            price = Decimal(str(p[1]))
            out.append(
                Candle(ts=ts_ms, open=price, high=price, low=price, close=price, volume=Decimal(0))
            )
        return out


def _to_cg_id(sym: str) -> str:
    m = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }
    return m.get(sym.upper(), sym.lower())


def _tf_to_days(tf: str, limit: int) -> int:
    tf = tf.lower()
    if tf.endswith("h"):
        hours = int(tf[:-1]) * max(limit, 1)
        return max(1, hours // 24)
    if tf.endswith("d"):
        days = int(tf[:-1]) * max(limit, 1)
        return max(1, days)
    return 30
