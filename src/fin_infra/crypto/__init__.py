"""Crypto market data module - easy setup for cryptocurrency quotes and OHLCV data.

Supported providers:
- CoinGecko (default): No API key required, 10-30 req/min free tier
- CCXT: Multi-exchange support (future)

Quick start:
    >>> from fin_infra.crypto import easy_crypto
    >>> crypto = easy_crypto()  # CoinGecko, no API key needed
    >>> ticker = crypto.ticker("BTC/USDT")
    >>> candles = crypto.ohlcv("ETH/USDT", timeframe="1h", limit=100)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import FastAPI

from ..providers.base import CryptoDataProvider


def easy_crypto(
    provider: Literal["coingecko"] | None = None,
    **config,
) -> CryptoDataProvider:
    """Create a crypto data provider with zero or minimal configuration.

    Auto-detects provider based on environment variables:
    1. If COINGECKO_API_KEY is set → CoinGecko Pro
    2. Otherwise → CoinGecko Free (no key needed)

    Args:
        provider: Provider name ("coingecko"). If None, defaults to coingecko.
        **config: Provider-specific configuration
                 - coingecko: api_key (optional for free tier)

    Returns:
        Configured CryptoDataProvider instance

    Raises:
        ValueError: Invalid provider or missing required configuration

    Examples:
        Zero config (CoinGecko free tier):
            >>> crypto = easy_crypto()
            >>> ticker = crypto.ticker("BTC/USDT")

        Explicit provider:
            >>> crypto = easy_crypto(provider="coingecko")

        Integration with svc-infra caching:
            >>> from svc_infra.cache import cache_read, resource
            >>> crypto_data = resource("crypto", "symbol")
            >>>
            >>> @crypto_data.cache_read(ttl=60, suffix="ticker")
            >>> def get_ticker(symbol: str):
            >>>     return crypto.ticker(symbol)
    """
    # Default to coingecko
    provider_name: str = (provider or "coingecko").lower()

    # Create provider instance
    if provider_name == "coingecko":
        from ..providers.market.coingecko import CoinGeckoCryptoData

        # CoinGecko free tier doesn't need API key
        return CoinGeckoCryptoData()

    else:
        raise ValueError(f"Unknown crypto data provider: {provider_name}. " f"Supported: coingecko")


def add_crypto_data(
    app: "FastAPI",
    *,
    provider: str | CryptoDataProvider | None = None,
    prefix: str = "/crypto",
    cache_ttl: int = 60,
    **config,
) -> CryptoDataProvider:
    """Wire crypto data provider to FastAPI app with routes, caching, and logging.

    This helper mounts crypto data endpoints to your FastAPI application and configures
    integration with svc-infra for caching and logging. It provides a production-ready
    crypto data API with minimal configuration.

    Mounted Routes:
        GET {prefix}/ticker/{symbol}
            Get current ticker for a crypto pair
            Path: symbol (e.g., "BTC/USDT" or "ETH-USD")
            Response: Quote model (symbol, price, as_of)

        GET {prefix}/ohlcv/{symbol}
            Get OHLCV candles for a crypto pair
            Path: symbol (e.g., "BTC/USDT")
            Query: timeframe (e.g., "1h", "1d"), limit (default: 100)
            Response: List of Candle models

    Args:
        app: FastAPI application instance (from svc-infra easy_service_app)
        provider: Provider name or instance. If None, uses easy_crypto() defaults.
        prefix: URL prefix for crypto routes (default: "/crypto")
        cache_ttl: Cache TTL in seconds (default: 60s)
        **config: Additional provider configuration

    Returns:
        Configured CryptoDataProvider instance (stored on app.state.crypto_provider)

    Examples:
        Minimal setup:
            >>> from svc_infra.api.fastapi.ease import easy_service_app
            >>> from fin_infra.crypto import add_crypto_data
            >>>
            >>> app = easy_service_app(name="CryptoAPI")
            >>> crypto = add_crypto_data(app)  # CoinGecko, no config needed

        With custom prefix:
            >>> crypto = add_crypto_data(app, prefix="/api/v1/crypto")

        Full integration:
            >>> from svc_infra.api.fastapi.ease import easy_service_app
            >>> from svc_infra.cache import init_cache
            >>> from svc_infra.obs import add_observability
            >>> from fin_infra.crypto import add_crypto_data
            >>>
            >>> app = easy_service_app(name="CryptoAPI")
            >>> init_cache(url="redis://localhost")
            >>> add_observability(app)
            >>> crypto = add_crypto_data(app)
    """
    from svc_infra.api.fastapi.dual.public import public_router
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
    from fastapi import HTTPException, Query

    # Initialize provider if string or None
    if isinstance(provider, str):
        # Cast string to Literal type for easy_crypto
        crypto_provider = easy_crypto(provider=provider, **config)  # type: ignore[arg-type]
    elif provider is None:
        crypto_provider = easy_crypto(**config)
    else:
        crypto_provider = provider

    # Create router
    router = public_router(prefix=prefix, tags=["Crypto Data"])

    @router.get("/ticker/{symbol}")
    async def get_ticker(symbol: str):
        """Get current ticker for a crypto pair.

        Args:
            symbol: Crypto pair symbol (e.g., "BTC/USDT", "ETH-USD")

        Returns:
            Quote with symbol, price, and timestamp

        Examples:
            GET /crypto/ticker/BTC/USDT
            GET /crypto/ticker/ETH-USD
        """
        try:
            ticker = crypto_provider.ticker(symbol)
            return {
                "symbol": ticker.symbol,
                "price": float(ticker.price),
                "as_of": ticker.as_of.isoformat()
                if ticker.as_of
                else datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error fetching ticker for {symbol}: {str(e)}"
            )

    @router.get("/ohlcv/{symbol}")
    async def get_ohlcv(
        symbol: str,
        timeframe: str = Query("1d", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)"),
        limit: int = Query(100, ge=1, le=1000, description="Number of candles to fetch"),
    ):
        """Get OHLCV candles for a crypto pair.

        Args:
            symbol: Crypto pair symbol (e.g., "BTC/USDT")
            timeframe: Candle timeframe (default: "1d")
            limit: Number of candles (default: 100, max: 1000)

        Returns:
            List of OHLCV candles

        Examples:
            GET /crypto/ohlcv/BTC/USDT?timeframe=1h&limit=24
            GET /crypto/ohlcv/ETH-USD?timeframe=1d&limit=30
        """
        try:
            candles = crypto_provider.ohlcv(symbol, timeframe=timeframe, limit=limit)
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": len(candles),
                "candles": [
                    {
                        "timestamp": c.ts
                        if isinstance(c.ts, int)
                        else int(c.ts.timestamp() * 1000),
                        "open": float(c.open),
                        "high": float(c.high),
                        "low": float(c.low),
                        "close": float(c.close),
                        "volume": float(c.volume),
                    }
                    for c in candles
                ],
            }
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error fetching OHLCV for {symbol}: {str(e)}"
            )

    # Mount router
    app.include_router(router, include_in_schema=True)

    # Register scoped docs for landing page card
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Crypto Data",
        auto_exclude_from_root=True,
        visible_envs=None,  # Show in all environments
    )

    # Store provider on app state
    app.state.crypto_provider = crypto_provider

    return crypto_provider


__all__ = ["easy_crypto", "add_crypto_data"]
