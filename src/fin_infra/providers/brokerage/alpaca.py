"""Alpaca brokerage provider for paper and live trading.

⚠️ IMPORTANT: This module provides real trading capabilities. Always use paper trading
mode for development and testing. Live trading requires explicit opt-in.
"""

from __future__ import annotations

import os
from typing import Literal

try:
    from alpaca_trade_api import REST

    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    REST = None  # type: ignore

from ..base import BrokerageProvider


class AlpacaBrokerage(BrokerageProvider):
    """Alpaca brokerage provider with paper and live trading support.

    Defaults to paper trading for safety. Live trading requires explicit mode="live".

    Args:
        api_key: Alpaca API key (or set ALPACA_API_KEY env var)
        api_secret: Alpaca API secret (or set ALPACA_API_SECRET env var)
        mode: Trading mode - "paper" (default) or "live"
        base_url: Optional custom base URL (auto-detected from mode if not provided)

    Raises:
        ImportError: If alpaca-trade-api is not installed
        ValueError: If credentials are missing or mode is invalid

    Examples:
        Paper trading (safe default):
            >>> broker = AlpacaBrokerage(api_key="...", api_secret="...", mode="paper")
            >>> account = broker.get_account()

        Live trading (requires explicit opt-in):
            >>> broker = AlpacaBrokerage(api_key="...", api_secret="...", mode="live")
            >>> # WARNING: Real money at risk!
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        mode: Literal["paper", "live"] = "paper",
        base_url: str | None = None,
    ) -> None:
        if not ALPACA_AVAILABLE:
            raise ImportError(
                "alpaca-trade-api is not installed. "
                "Install it with: pip install alpaca-trade-api"
            )

        # Get credentials from args or environment
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials required. "
                "Provide api_key and api_secret, or set ALPACA_API_KEY and ALPACA_API_SECRET env vars."
            )

        # Validate mode
        if mode not in ("paper", "live"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'paper' or 'live'.")

        self.mode = mode

        # Auto-detect base URL from mode if not provided
        if base_url is None:
            if mode == "paper":
                base_url = "https://paper-api.alpaca.markets"
            else:
                base_url = "https://api.alpaca.markets"

        self.base_url = base_url

        # Initialize Alpaca REST client
        self.client = REST(
            key_id=self.api_key,
            secret_key=self.api_secret,
            base_url=self.base_url,
            api_version="v2",
        )

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        type_: str,
        time_in_force: str = "day",
        limit_price: float | None = None,
        stop_price: float | None = None,
        client_order_id: str | None = None,
    ) -> dict:
        """Submit an order to Alpaca.

        Args:
            symbol: Trading symbol (e.g., "AAPL")
            qty: Order quantity
            side: "buy" or "sell"
            type_: "market", "limit", "stop", or "stop_limit"
            time_in_force: "day", "gtc", "ioc", or "fok" (default: "day")
            limit_price: Limit price (required for limit/stop_limit orders)
            stop_price: Stop price (required for stop/stop_limit orders)
            client_order_id: Optional client order ID

        Returns:
            Order dict with id, status, filled_qty, etc.

        Raises:
            Exception: If order submission fails
        """
        order = self.client.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type=type_,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            client_order_id=client_order_id,
        )
        # Extract raw dict from Alpaca entity
        return self._extract_raw(order)

    def get_order(self, order_id: str) -> dict:
        """Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order dict
        """
        order = self.client.get_order(order_id)
        return self._extract_raw(order)

    def cancel_order(self, order_id: str) -> None:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel
        """
        self.client.cancel_order(order_id)

    def list_orders(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List orders.

        Args:
            status: Filter by status ("open", "closed", "all"). Default: "open"
            limit: Max number of orders to return (default: 50)

        Returns:
            List of order dicts
        """
        orders = self.client.list_orders(status=status, limit=limit)
        return [self._extract_raw(o) for o in orders]

    def positions(self) -> list[dict]:
        """Get all positions.

        Returns:
            List of position dicts
        """
        positions = self.client.list_positions()
        return [self._extract_raw(p) for p in positions]

    def get_position(self, symbol: str) -> dict:
        """Get position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position dict
        """
        position = self.client.get_position(symbol)
        return self._extract_raw(position)

    def close_position(self, symbol: str) -> dict:
        """Close a position.

        Args:
            symbol: Trading symbol to close

        Returns:
            Order dict for the closing order
        """
        order = self.client.close_position(symbol)
        return self._extract_raw(order)

    def get_account(self) -> dict:
        """Get account information.

        Returns:
            Account dict with buying_power, cash, portfolio_value, etc.
        """
        account = self.client.get_account()
        return self._extract_raw(account)

    def get_portfolio_history(
        self,
        period: str = "1M",
        timeframe: str = "1D",
    ) -> dict:
        """Get portfolio history.

        Args:
            period: Time period ("1D", "1W", "1M", "3M", "1Y", "all")
            timeframe: Bar timeframe ("1Min", "5Min", "15Min", "1H", "1D")

        Returns:
            Portfolio history dict with timestamp, equity, profit_loss arrays
        """
        history = self.client.get_portfolio_history(period=period, timeframe=timeframe)
        return self._extract_raw(history)

    def create_watchlist(self, name: str, symbols: list[str] | None = None) -> dict:
        """Create a new watchlist.

        Args:
            name: Watchlist name
            symbols: Optional list of symbols to add initially

        Returns:
            Watchlist dict with id, name, symbols
        """
        watchlist = self.client.create_watchlist(name=name, symbols=symbols or [])
        return self._extract_raw(watchlist)

    def get_watchlist(self, watchlist_id: str) -> dict:
        """Get a watchlist by ID.

        Args:
            watchlist_id: Watchlist ID

        Returns:
            Watchlist dict with id, name, symbols
        """
        watchlist = self.client.get_watchlist(watchlist_id)
        return self._extract_raw(watchlist)

    def list_watchlists(self) -> list[dict]:
        """List all watchlists for the account.

        Returns:
            List of watchlist dicts
        """
        watchlists = self.client.get_watchlists()
        return [self._extract_raw(w) for w in watchlists]

    def delete_watchlist(self, watchlist_id: str) -> None:
        """Delete a watchlist.

        Args:
            watchlist_id: Watchlist ID
        """
        self.client.delete_watchlist(watchlist_id)

    def add_to_watchlist(self, watchlist_id: str, symbol: str) -> dict:
        """Add a symbol to a watchlist.

        Args:
            watchlist_id: Watchlist ID
            symbol: Symbol to add

        Returns:
            Updated watchlist dict
        """
        watchlist = self.client.add_to_watchlist(watchlist_id, symbol)
        return self._extract_raw(watchlist)

    def remove_from_watchlist(self, watchlist_id: str, symbol: str) -> dict:
        """Remove a symbol from a watchlist.

        Args:
            watchlist_id: Watchlist ID
            symbol: Symbol to remove

        Returns:
            Updated watchlist dict
        """
        watchlist = self.client.delete_from_watchlist(watchlist_id, symbol)
        return self._extract_raw(watchlist)

    @staticmethod
    def _extract_raw(obj) -> dict:
        """Extract raw dict from Alpaca entity object.

        Alpaca entities have a _raw attribute with the API response data.
        """
        if hasattr(obj, "_raw"):
            return obj._raw
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return obj
