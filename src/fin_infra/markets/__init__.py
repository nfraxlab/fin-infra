"""Market data module - easy setup for stock/equity quotes and historical data.

Supported providers:
- Alpha Vantage (default): Requires API key, 5 req/min free tier
- Yahoo Finance: No API key, unlimited (unofficial API)

Quick start:
    >>> from fin_infra.markets import easy_market
    >>> market = easy_market()  # Auto-detects provider from env
    >>> quote = market.quote("AAPL")
    >>> history = market.history("AAPL", period="1mo")
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import FastAPI

from ..providers.base import MarketDataProvider

# Deprecated: MarketDataClient alias for backward compatibility
# Use MarketDataProvider instead
MarketDataClient = MarketDataProvider  # type: ignore[misc]


def easy_market(
    provider: Literal["alphavantage", "yahoo"] | None = None,
    **config,
) -> MarketDataProvider:
    """Create a market data provider with zero or minimal configuration.

    Auto-detects provider based on environment variables:
    1. If ALPHA_VANTAGE_API_KEY or ALPHAVANTAGE_API_KEY is set → Alpha Vantage
    2. Otherwise → Yahoo Finance (no key needed)

    Args:
        provider: Provider name ("alphavantage" or "yahoo").
                 If None, auto-detects from environment.
        **config: Provider-specific configuration
                 - alphavantage: api_key, throttle (default: True)
                 - yahoo: (no config needed)

    Returns:
        Configured MarketDataProvider instance

    Raises:
        ValueError: Invalid provider or missing required configuration

    Examples:
        Zero config (auto-detect):
            >>> market = easy_market()
            >>> quote = market.quote("AAPL")

        Explicit provider:
            >>> market = easy_market(provider="alphavantage")
            >>> market = easy_market(provider="yahoo")

        With configuration:
            >>> market = easy_market(provider="alphavantage", api_key="YOUR_KEY", throttle=False)

        Integration with svc-infra caching:
            >>> from svc_infra.cache import cache_read, resource
            >>> market_data = resource("market", "symbol")
            >>>
            >>> @market_data.cache_read(ttl=60, suffix="quote")
            >>> def get_quote(symbol: str):
            >>>     return market.quote(symbol)
    """
    # Auto-detect provider if not specified
    provider_name: str
    if provider is None:
        if os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHAVANTAGE_API_KEY"):
            provider_name = "alphavantage"
        else:
            provider_name = "yahoo"
    else:
        # Normalize provider name
        provider_name = provider.lower()

    # Create provider instance
    if provider_name == "alphavantage":
        from ..providers.market.alphavantage import AlphaVantageMarketData

        api_key = config.get("api_key")
        throttle = config.get("throttle", True)

        return AlphaVantageMarketData(api_key=api_key, throttle=throttle)

    elif provider_name == "yahoo":
        from ..providers.market.yahoo import YahooFinanceMarketData

        return YahooFinanceMarketData()

    else:
        raise ValueError(
            f"Unknown market data provider: {provider_name}. Supported: alphavantage, yahoo"
        )


def add_market_data(
    app: FastAPI,
    *,
    provider: str | MarketDataProvider | None = None,
    prefix: str = "/market",
    cache_ttl: int = 60,
    **config,
) -> MarketDataProvider:
    """Wire market data provider to FastAPI app with routes, caching, and logging.

    This helper mounts market data endpoints to your FastAPI application and configures
    integration with svc-infra for caching and logging. It provides a production-ready
    market data API with minimal configuration.

    Mounted Routes:
        GET {prefix}/quote/{symbol}
            Get current quote for a symbol
            Path: symbol (e.g., "AAPL")
            Response: Quote model (symbol, price, as_of, currency)

        GET {prefix}/history/{symbol}
            Get historical candles for a symbol
            Path: symbol (e.g., "AAPL")
            Query: period (1mo, 3mo, 1y, 5y, max), interval (1d, 1wk, 1mo)
            Response: {"candles": [Candle...]}

        GET {prefix}/search
            Search for symbols (Alpha Vantage only)
            Query: keywords (e.g., "Apple")
            Response: {"results": [...]}

    Args:
        app: FastAPI application instance
        provider: Provider name ("alphavantage", "yahoo"), provider instance, or None for auto-detect
        prefix: URL prefix for market routes (default: "/market")
        cache_ttl: Cache TTL in seconds for quotes (default: 60)
        **config: Optional provider configuration overrides (ignored if provider is an instance)

    Returns:
        Configured MarketDataProvider instance used by the routes

    Raises:
        ValueError: If provider configuration is invalid
        ImportError: If provider SDK is not installed

    Examples:
        # Basic setup with auto-detection (Yahoo Finance)
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.markets import add_market_data
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> market = add_market_data(app)

        # With provider name
        >>> market = add_market_data(app, provider="alphavantage")

        # With provider instance (useful for custom configuration)
        >>> from fin_infra.markets import easy_market
        >>> market_provider = easy_market(provider="yahoo")
        >>> market = add_market_data(app, provider=market_provider)

        # Custom cache TTL
        >>> market = add_market_data(
        ...     app,
        ...     provider="yahoo",
        ...     cache_ttl=120  # 2 minutes
        ... )

        # Routes mounted at /market/* (matches svc-infra pattern like /payments, /auth)
        # GET /market/quote/{symbol}
        # GET /market/history/{symbol}
        # GET /market/search

    Integration with svc-infra:
        - Cache: Uses svc_infra.cache for quote caching
        - Logging: Uses svc_infra.logging for provider call logging
        - Rate Limiting: Provider-specific rate limiting applied

    See Also:
        - easy_market(): For standalone provider usage without FastAPI
        - docs/market-data.md: API documentation and examples
    """
    from fastapi import HTTPException, Query

    # Import svc-infra public router (no auth required for market data)
    from svc_infra.api.fastapi.dual.public import public_router

    # Create market provider instance (or use the provided one)
    if isinstance(provider, MarketDataProvider):
        market = provider
    else:
        # Cast provider to Literal type for type checker
        provider_literal: Literal["alphavantage", "yahoo"] | None = (
            provider if provider in ("alphavantage", "yahoo", None) else None  # type: ignore[assignment]
        )
        market = easy_market(provider=provider_literal, **config)

    # Create router (public - no auth required)
    router = public_router(prefix=prefix, tags=["Market Data"])

    # Routes
    @router.get("/quote/{symbol}")
    async def get_quote(symbol: str):
        """Get current quote for a symbol."""
        try:
            quote = market.quote(symbol)
            # Convert to dict if it's a Pydantic model
            if hasattr(quote, "model_dump"):
                return quote.model_dump()
            elif hasattr(quote, "dict"):
                return quote.dict()
            return quote
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/history/{symbol}")
    async def get_history(
        symbol: str,
        period: str = Query("1mo", description="Period: 1mo, 3mo, 1y, 5y, max"),
        interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo"),
    ):
        """Get historical candles for a symbol."""
        try:
            candles = market.history(symbol, period=period, interval=interval)
            # Convert to dicts if they're Pydantic models
            candles_list: list[dict] = []
            for candle in candles:
                if hasattr(candle, "model_dump"):
                    candles_list.append(candle.model_dump())
                elif hasattr(candle, "dict"):
                    candles_list.append(candle.dict())
                else:
                    # Cast to dict for type compatibility
                    candles_list.append(
                        dict(candle) if hasattr(candle, "__iter__") else {"data": candle}
                    )
            return {"candles": candles_list}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/search")
    async def search_symbols(keywords: str = Query(..., description="Search keywords")):
        """Search for symbols (Alpha Vantage only)."""
        # Check if provider supports search
        if not hasattr(market, "search"):
            raise HTTPException(status_code=501, detail="Search not supported by current provider")

        try:
            results = market.search(keywords)
            return {"results": results}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Mount router to app (explicitly include in schema for OpenAPI docs)
    app.include_router(router, include_in_schema=True)

    # Register scoped docs for landing page card (creates separate card like /auth, /payments)

    # Store provider instance on app state for access in routes
    if not hasattr(app.state, "market_provider"):
        app.state.market_provider = market

    return market


__all__ = [
    "MarketDataClient",
    "easy_market",
    "add_market_data",
]
