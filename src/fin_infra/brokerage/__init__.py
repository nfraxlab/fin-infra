"""Brokerage module - easy setup for trading operations.

⚠️ **TRADING WARNING**: This module provides real trading capabilities.
Always use paper trading mode for development and testing.
Live trading requires explicit opt-in and involves real financial risk.

Supported providers:
- Alpaca (default): Paper and live trading, US equities

Quick start (PAPER TRADING):
    >>> from fin_infra.brokerage import easy_brokerage
    >>> broker = easy_brokerage(mode="paper")  # Safe default
    >>> account = broker.get_account()
    >>> positions = broker.positions()
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import FastAPI

from ..providers.base import BrokerageProvider
from pydantic import BaseModel, Field
from decimal import Decimal


# Request model for order submission (used by add_brokerage FastAPI routes)
class OrderRequest(BaseModel):
    """Order submission request."""

    symbol: str = Field(description="Trading symbol (e.g., AAPL)")
    qty: Decimal = Field(description="Order quantity")
    side: Literal["buy", "sell"] = Field(description="Order side")
    type: Literal["market", "limit", "stop", "stop_limit"] = Field(description="Order type")
    time_in_force: Literal["day", "gtc", "ioc", "fok"] = Field(default="day")
    limit_price: Decimal | None = Field(None, description="Limit price (for limit orders)")
    stop_price: Decimal | None = Field(None, description="Stop price (for stop orders)")
    client_order_id: str | None = Field(None, description="Client order ID")


def easy_brokerage(
    provider: Literal["alpaca"] | None = None,
    *,
    mode: Literal["paper", "live"] = "paper",
    **config,
) -> BrokerageProvider:
    """Create a brokerage provider with paper/live trading support.

    ⚠️ **SAFETY**: Defaults to paper trading mode. Live trading requires explicit mode="live".

    Auto-detects provider based on environment variables:
    1. If ALPACA_API_KEY and ALPACA_API_SECRET are set → Alpaca
    2. Otherwise → Raises error (credentials required)

    Args:
        provider: Provider name ("alpaca"). If None, defaults to alpaca.
        mode: Trading mode - "paper" (default, safe) or "live" (real money)
        **config: Provider-specific configuration
                 - alpaca: api_key, api_secret, base_url

    Returns:
        Configured BrokerageProvider instance

    Raises:
        ValueError: Invalid provider or missing required configuration
        ImportError: Provider library not installed

    Examples:
        Paper trading (safe default):
            >>> broker = easy_brokerage()  # Paper mode by default
            >>> broker = easy_brokerage(mode="paper")  # Explicit
            >>> account = broker.get_account()

        Live trading (REQUIRES EXPLICIT OPT-IN):
            >>> broker = easy_brokerage(mode="live")  # WARNING: Real money!
            >>> # Only use live mode in production with proper safeguards

        With explicit credentials:
            >>> broker = easy_brokerage(
            ...     api_key="YOUR_KEY",
            ...     api_secret="YOUR_SECRET",
            ...     mode="paper"
            ... )

        Integration with svc-infra:
            >>> from svc_infra.jobs.easy import easy_jobs
            >>> from fin_infra.brokerage import easy_brokerage
            >>>
            >>> broker = easy_brokerage(mode="paper")
            >>> worker, scheduler = easy_jobs(app)
            >>>
            >>> @worker.task
            >>> async def daily_rebalance():
            >>>     positions = broker.positions()
            >>>     # Rebalancing logic here
            >>>     return {"positions": len(positions)}
    """
    # Default to alpaca
    provider_name: str = (provider or "alpaca").lower()

    # Create provider instance
    if provider_name == "alpaca":
        from ..providers.brokerage.alpaca import AlpacaBrokerage

        # Get credentials from config or environment
        api_key = config.get("api_key") or os.getenv("ALPACA_API_KEY")
        api_secret = config.get("api_secret") or os.getenv("ALPACA_API_SECRET")

        if not api_key or not api_secret:
            raise ValueError(
                "Alpaca credentials required. "
                "Provide api_key and api_secret, or set ALPACA_API_KEY and ALPACA_API_SECRET env vars."
            )

        return AlpacaBrokerage(
            api_key=api_key,
            api_secret=api_secret,
            mode=mode,
            base_url=config.get("base_url"),
        )

    else:
        raise ValueError(f"Unknown brokerage provider: {provider_name}. " f"Supported: alpaca")


def add_brokerage(
    app: "FastAPI",
    *,
    provider: str | BrokerageProvider | None = None,
    mode: Literal["paper", "live"] = "paper",
    prefix: str = "/brokerage",
    **config,
) -> BrokerageProvider:
    """Wire brokerage provider to FastAPI app with routes and safety checks.

    ⚠️ **TRADING WARNING**: This mounts trading API endpoints.
    Always use paper trading mode for development.
    Live trading requires explicit mode="live" and proper safeguards.

    This helper mounts brokerage endpoints to your FastAPI application with
    integration with svc-infra for logging and error handling.

    Mounted Routes:
        GET  {prefix}/account
            Get account information (buying power, cash, portfolio value)

        GET  {prefix}/positions
            List all open positions

        GET  {prefix}/positions/{symbol}
            Get position for a specific symbol

        POST {prefix}/orders
            Submit a new order
            Body: {symbol, qty, side, type, time_in_force, limit_price?, stop_price?}

        GET  {prefix}/orders
            List orders (query: status, limit)

        GET  {prefix}/orders/{order_id}
            Get order by ID

        DELETE {prefix}/orders/{order_id}
            Cancel an order

        DELETE {prefix}/positions/{symbol}
            Close a position

        GET  {prefix}/portfolio/history
            Get portfolio history (query: period, timeframe)

    Args:
        app: FastAPI application instance (from svc-infra easy_service_app)
        provider: Provider name or instance. If None, uses easy_brokerage() defaults.
        mode: Trading mode - "paper" (default, safe) or "live" (real money)
        prefix: URL prefix for brokerage routes (default: "/brokerage")
        **config: Additional provider configuration

    Returns:
        Configured BrokerageProvider instance (stored on app.state.brokerage_provider)

    Examples:
        Minimal setup (paper trading):
            >>> from svc_infra.api.fastapi.ease import easy_service_app
            >>> from fin_infra.brokerage import add_brokerage
            >>>
            >>> app = easy_service_app(name="TradingAPI")
            >>> broker = add_brokerage(app, mode="paper")  # Safe paper trading

        Full integration:
            >>> from svc_infra.api.fastapi.ease import easy_service_app
            >>> from svc_infra.logging import setup_logging
            >>> from svc_infra.obs import add_observability
            >>> from fin_infra.brokerage import add_brokerage
            >>>
            >>> setup_logging(level="INFO", fmt="json")
            >>> app = easy_service_app(name="TradingAPI")
            >>> add_observability(app)
            >>> broker = add_brokerage(app, mode="paper")

        Live trading (REQUIRES EXPLICIT OPT-IN):
            >>> # WARNING: Real money at risk!
            >>> broker = add_brokerage(app, mode="live")
            >>> # Only use in production with proper safeguards and risk management
    """
    from svc_infra.api.fastapi.dual.public import public_router
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
    from fastapi import HTTPException, Query

    # Initialize provider if string or None
    if isinstance(provider, str):
        brokerage_provider = easy_brokerage(provider=provider, mode=mode, **config)
    elif provider is None:
        brokerage_provider = easy_brokerage(mode=mode, **config)
    else:
        brokerage_provider = provider

    # Create router - use public_router for API access
    # Note: Production apps should add auth middleware or override dependencies for security
    router = public_router(prefix=prefix, tags=["Brokerage"])

    @router.get("/account")
    async def get_account():
        """Get trading account information.

        Returns account details including buying power, cash, portfolio value, etc.
        """
        try:
            account = brokerage_provider.get_account()
            return account
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching account: {str(e)}")

    @router.get("/positions")
    async def list_positions():
        """List all open positions.

        Returns list of positions with symbol, quantity, P/L, etc.
        """
        try:
            positions = brokerage_provider.positions()
            return {"positions": positions, "count": len(positions)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching positions: {str(e)}")

    @router.get("/positions/{symbol}")
    async def get_position(symbol: str):
        """Get position for a specific symbol.

        Args:
            symbol: Trading symbol (e.g., AAPL)
        """
        try:
            position = brokerage_provider.get_position(symbol)
            return position
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"Position not found for {symbol}: {str(e)}"
            )

    @router.delete("/positions/{symbol}")
    async def close_position(symbol: str):
        """Close a position (market sell/cover).

        Args:
            symbol: Trading symbol to close
        """
        try:
            order = brokerage_provider.close_position(symbol)
            return {"message": f"Closing position for {symbol}", "order": order}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error closing position: {str(e)}")

    @router.post("/orders")
    async def submit_order(order_request: OrderRequest):
        """Submit a new order.

        ⚠️ **TRADING WARNING**: This endpoint executes real trades in live mode.
        """
        try:
            order = brokerage_provider.submit_order(
                symbol=order_request.symbol,
                qty=float(order_request.qty),
                side=order_request.side,
                type_=order_request.type,
                time_in_force=order_request.time_in_force,
                limit_price=float(order_request.limit_price) if order_request.limit_price else None,
                stop_price=float(order_request.stop_price) if order_request.stop_price else None,
                client_order_id=order_request.client_order_id,
            )
            return order
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error submitting order: {str(e)}")

    @router.get("/orders")
    async def list_orders(
        status: str = Query("open", description="Filter by status: open, closed, all"),
        limit: int = Query(50, ge=1, le=500, description="Max orders to return"),
    ):
        """List orders.

        Args:
            status: Filter by status (open, closed, all)
            limit: Max number of orders to return
        """
        try:
            orders = brokerage_provider.list_orders(status=status, limit=limit)
            return {"orders": orders, "count": len(orders)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching orders: {str(e)}")

    @router.get("/orders/{order_id}")
    async def get_order(order_id: str):
        """Get order by ID.

        Args:
            order_id: Order ID
        """
        try:
            order = brokerage_provider.get_order(order_id)
            return order
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Order not found: {str(e)}")

    @router.delete("/orders/{order_id}")
    async def cancel_order(order_id: str):
        """Cancel an order.

        Args:
            order_id: Order ID to cancel
        """
        try:
            brokerage_provider.cancel_order(order_id)
            return {"message": f"Order {order_id} canceled successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error canceling order: {str(e)}")

    @router.get("/portfolio/history")
    async def get_portfolio_history(
        period: str = Query("1M", description="Time period: 1D, 1W, 1M, 3M, 1Y, all"),
        timeframe: str = Query("1D", description="Bar timeframe: 1Min, 5Min, 15Min, 1H, 1D"),
    ):
        """Get portfolio value history.

        Args:
            period: Time period (1D, 1W, 1M, 3M, 1Y, all)
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1H, 1D)
        """
        try:
            history = brokerage_provider.get_portfolio_history(period=period, timeframe=timeframe)
            return history
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching portfolio history: {str(e)}"
            )

    # Watchlist routes
    @router.post("/watchlists")
    async def create_watchlist(
        name: str = Query(..., description="Watchlist name"),
        symbols: list[str] = Query(default=[], description="Initial symbols"),
    ):
        """Create a new watchlist.

        Args:
            name: Watchlist name
            symbols: Optional list of symbols to add initially
        """
        try:
            watchlist = brokerage_provider.create_watchlist(name=name, symbols=symbols)
            return watchlist
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error creating watchlist: {str(e)}")

    @router.get("/watchlists")
    async def list_watchlists():
        """List all watchlists."""
        try:
            watchlists = brokerage_provider.list_watchlists()
            return {"watchlists": watchlists, "count": len(watchlists)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching watchlists: {str(e)}")

    @router.get("/watchlists/{watchlist_id}")
    async def get_watchlist(watchlist_id: str):
        """Get a watchlist by ID.

        Args:
            watchlist_id: Watchlist ID
        """
        try:
            watchlist = brokerage_provider.get_watchlist(watchlist_id)
            return watchlist
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Watchlist not found: {str(e)}")

    @router.delete("/watchlists/{watchlist_id}")
    async def delete_watchlist(watchlist_id: str):
        """Delete a watchlist.

        Args:
            watchlist_id: Watchlist ID
        """
        try:
            brokerage_provider.delete_watchlist(watchlist_id)
            return {"message": f"Watchlist {watchlist_id} deleted successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error deleting watchlist: {str(e)}")

    @router.post("/watchlists/{watchlist_id}/symbols")
    async def add_to_watchlist(
        watchlist_id: str, symbol: str = Query(..., description="Symbol to add")
    ):
        """Add a symbol to a watchlist.

        Args:
            watchlist_id: Watchlist ID
            symbol: Symbol to add
        """
        try:
            watchlist = brokerage_provider.add_to_watchlist(watchlist_id, symbol)
            return watchlist
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error adding symbol: {str(e)}")

    @router.delete("/watchlists/{watchlist_id}/symbols/{symbol}")
    async def remove_from_watchlist(watchlist_id: str, symbol: str):
        """Remove a symbol from a watchlist.

        Args:
            watchlist_id: Watchlist ID
            symbol: Symbol to remove
        """
        try:
            watchlist = brokerage_provider.remove_from_watchlist(watchlist_id, symbol)
            return watchlist
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error removing symbol: {str(e)}")

    # Mount router
    app.include_router(router, include_in_schema=True)

    # Register scoped docs for landing page card
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Brokerage" + (" (Paper Trading)" if mode == "paper" else " ⚠️ LIVE"),
        auto_exclude_from_root=True,
        visible_envs=None,  # Show in all environments
    )

    # Store provider on app state
    app.state.brokerage_provider = brokerage_provider
    app.state.brokerage_mode = mode  # Store mode for safety checks

    return brokerage_provider


__all__ = ["easy_brokerage", "add_brokerage"]
