"""Brokerage data models for orders, positions, and portfolio."""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Order(BaseModel):
    """Order model for trade execution."""

    id: str = Field(description="Unique order ID from broker")
    client_order_id: str | None = Field(None, description="Client-provided order ID")
    symbol: str = Field(description="Trading symbol (e.g., AAPL)")
    qty: Decimal = Field(description="Order quantity (number of shares/units)")
    side: Literal["buy", "sell"] = Field(description="Order side: buy or sell")
    type: Literal["market", "limit", "stop", "stop_limit"] = Field(description="Order type")
    time_in_force: Literal["day", "gtc", "ioc", "fok"] = Field(
        description="Time in force: day, good-till-canceled, immediate-or-cancel, fill-or-kill"
    )
    limit_price: Decimal | None = Field(None, description="Limit price (for limit orders)")
    stop_price: Decimal | None = Field(None, description="Stop price (for stop orders)")
    filled_qty: Decimal = Field(default=Decimal("0"), description="Quantity filled")
    filled_avg_price: Decimal | None = Field(None, description="Average fill price")
    status: Literal[
        "new",
        "partially_filled",
        "filled",
        "done_for_day",
        "canceled",
        "expired",
        "replaced",
        "pending_cancel",
        "pending_replace",
        "accepted",
        "pending_new",
        "accepted_for_bidding",
        "stopped",
        "rejected",
        "suspended",
        "calculated",
    ] = Field(description="Order status")
    created_at: datetime = Field(description="Order creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    filled_at: datetime | None = Field(None, description="Fill completion timestamp")
    canceled_at: datetime | None = Field(None, description="Cancellation timestamp")
    expired_at: datetime | None = Field(None, description="Expiration timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "ord_123456",
                "client_order_id": "my_order_001",
                "symbol": "AAPL",
                "qty": "100",
                "side": "buy",
                "type": "limit",
                "time_in_force": "day",
                "limit_price": "150.00",
                "filled_qty": "100",
                "filled_avg_price": "149.50",
                "status": "filled",
                "created_at": "2025-01-15T10:00:00Z",
                "filled_at": "2025-01-15T10:01:23Z",
            }
        }
    }


class Position(BaseModel):
    """Position model for current holdings."""

    symbol: str = Field(description="Trading symbol")
    qty: Decimal = Field(description="Total quantity held")
    side: Literal["long", "short"] = Field(description="Position side: long or short")
    avg_entry_price: Decimal = Field(description="Average entry price")
    current_price: Decimal = Field(description="Current market price")
    market_value: Decimal = Field(description="Current market value (qty * current_price)")
    cost_basis: Decimal = Field(description="Total cost basis")
    unrealized_pl: Decimal = Field(description="Unrealized profit/loss")
    unrealized_plpc: Decimal = Field(description="Unrealized P/L percentage")
    exchange: str | None = Field(None, description="Exchange")
    asset_class: str | None = Field(None, description="Asset class (e.g., us_equity, crypto)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "symbol": "AAPL",
                "qty": "100",
                "side": "long",
                "avg_entry_price": "149.50",
                "current_price": "155.00",
                "market_value": "15500.00",
                "cost_basis": "14950.00",
                "unrealized_pl": "550.00",
                "unrealized_plpc": "0.0368",
                "asset_class": "us_equity",
            }
        }
    }


class Account(BaseModel):
    """Trading account information."""

    id: str = Field(description="Account ID")
    account_number: str = Field(description="Account number")
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"] = Field(description="Account status")
    currency: str = Field(default="USD", description="Base currency")
    buying_power: Decimal = Field(description="Current buying power")
    cash: Decimal = Field(description="Cash balance")
    portfolio_value: Decimal = Field(description="Total portfolio value")
    equity: Decimal = Field(description="Total equity")
    last_equity: Decimal = Field(description="Previous day equity")
    long_market_value: Decimal = Field(
        default=Decimal("0"), description="Long positions market value"
    )
    short_market_value: Decimal = Field(
        default=Decimal("0"), description="Short positions market value"
    )
    initial_margin: Decimal = Field(default=Decimal("0"), description="Initial margin requirement")
    maintenance_margin: Decimal = Field(
        default=Decimal("0"), description="Maintenance margin requirement"
    )
    sma: Decimal | None = Field(None, description="Special Memorandum Account")
    daytrade_count: int | None = Field(None, description="Day trade count")
    pattern_day_trader: bool = Field(default=False, description="Pattern day trader flag")
    trading_blocked: bool = Field(default=False, description="Trading blocked flag")
    account_blocked: bool = Field(default=False, description="Account blocked flag")
    created_at: datetime = Field(description="Account creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "acc_123456",
                "account_number": "123456789",
                "status": "ACTIVE",
                "currency": "USD",
                "buying_power": "50000.00",
                "cash": "25000.00",
                "portfolio_value": "100000.00",
                "equity": "100000.00",
                "last_equity": "98500.00",
                "long_market_value": "75000.00",
                "pattern_day_trader": False,
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    }


class PortfolioHistory(BaseModel):
    """Portfolio value history for a time period."""

    timestamp: list[int] = Field(description="Unix timestamps in milliseconds")
    equity: list[Decimal] = Field(description="Equity values")
    profit_loss: list[Decimal] = Field(description="Profit/loss values")
    profit_loss_pct: list[Decimal] = Field(description="Profit/loss percentages")
    base_value: Decimal = Field(description="Base portfolio value at start of period")
    timeframe: Literal["1D", "1W", "1M", "3M", "1Y", "ALL"] = Field(description="Timeframe")

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": [1704067200000, 1704153600000],
                "equity": ["100000.00", "101500.00"],
                "profit_loss": ["0.00", "1500.00"],
                "profit_loss_pct": ["0.00", "0.015"],
                "base_value": "100000.00",
                "timeframe": "1W",
            }
        }
    }


class Watchlist(BaseModel):
    """Watchlist for tracking symbols."""

    id: str = Field(description="Unique watchlist ID")
    name: str = Field(description="Watchlist name")
    account_id: str = Field(description="Account ID this watchlist belongs to")
    symbols: list[str] = Field(default_factory=list, description="List of symbols in watchlist")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "wl_123456",
                "name": "Tech Stocks",
                "account_id": "acc_123456",
                "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN"],
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T12:30:00Z",
            }
        }
    }


__all__ = ["Order", "Position", "Account", "PortfolioHistory", "Watchlist"]
