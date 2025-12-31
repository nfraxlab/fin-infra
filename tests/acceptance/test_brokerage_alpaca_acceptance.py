"""Acceptance tests for Alpaca brokerage provider.

[!] TRADING WARNING: These tests use paper trading mode only.
Never run with live trading credentials.

These tests make real API calls when credentials are available:
- ALPACA_PAPER_API_KEY: Alpaca paper trading API key
- ALPACA_PAPER_SECRET_KEY: Alpaca paper trading secret key

Get paper trading credentials from: https://app.alpaca.markets/paper/dashboard/overview

When credentials are not available, tests use mocked responses to validate code paths.
"""

import os
from unittest.mock import Mock

import pytest

from fin_infra.providers.brokerage.alpaca import AlpacaBrokerage

pytestmark = [pytest.mark.acceptance]


# Check if real credentials are available
HAS_REAL_CREDENTIALS = bool(
    os.getenv("ALPACA_PAPER_API_KEY") and os.getenv("ALPACA_PAPER_SECRET_KEY")
)


class TestAlpacaBrokerageAcceptance:
    """Acceptance tests for Alpaca brokerage provider (paper trading only)."""

    @pytest.fixture(autouse=True)
    def _setup_mocks(self, monkeypatch):
        """Setup mocks if no real credentials available."""
        if not HAS_REAL_CREDENTIALS:
            # Enable Alpaca even if library not installed
            monkeypatch.setattr("fin_infra.providers.brokerage.alpaca.ALPACA_AVAILABLE", True)
            # Mock the REST client class
            self.mock_rest_class = Mock()
            self.mock_client = Mock()
            self.mock_rest_class.return_value = self.mock_client
            monkeypatch.setattr("fin_infra.providers.brokerage.alpaca.REST", self.mock_rest_class)

    @pytest.fixture
    def broker(self):
        """Create Alpaca broker in paper mode (mocked if no credentials)."""
        if HAS_REAL_CREDENTIALS:
            # Use real credentials
            return AlpacaBrokerage(
                api_key=os.getenv("ALPACA_PAPER_API_KEY"),
                api_secret=os.getenv("ALPACA_PAPER_SECRET_KEY"),
                mode="paper",
            )
        else:
            # Use mocked broker when no credentials available
            broker = AlpacaBrokerage(api_key="test_key", api_secret="test_secret", mode="paper")
            # Store mock reference for test assertions
            broker._mock_client = self.mock_client
            return broker

    def test_get_account(self, broker):
        """Test getting account information."""
        if not HAS_REAL_CREDENTIALS:
            # Mock the response
            mock_account = Mock()
            mock_account._raw = {
                "id": "test-account-id",
                "status": "ACTIVE",
                "buying_power": "100000.00",
                "cash": "100000.00",
                "portfolio_value": "100000.00",
            }
            broker._mock_client.get_account.return_value = mock_account

        account = broker.get_account()

        assert isinstance(account, dict)
        assert "id" in account
        assert "status" in account
        assert "buying_power" in account
        assert "cash" in account
        assert "portfolio_value" in account

        # Verify paper trading account
        assert account["status"] in ("ACTIVE", "INACTIVE")
        print(
            f"[OK] Alpaca account: Status={account['status']}, "
            f"Buying Power=${account['buying_power']}, "
            f"Portfolio Value=${account['portfolio_value']}"
        )

    def test_list_positions(self, broker):
        """Test listing positions."""
        if not HAS_REAL_CREDENTIALS:
            # Mock empty positions list
            broker._mock_client.list_positions.return_value = []

        positions = broker.positions()

        assert isinstance(positions, list)
        # May be empty if no positions
        print(f"[OK] Alpaca positions: {len(positions)} open positions")

        if positions:
            pos = positions[0]
            assert "symbol" in pos
            assert "qty" in pos
            assert "side" in pos
            assert "market_value" in pos
            print(
                f"  Example: {pos['symbol']} - {pos['qty']} shares @ ${pos.get('current_price', 'N/A')}"
            )

    def test_list_orders(self, broker):
        """Test listing orders."""
        if not HAS_REAL_CREDENTIALS:
            # Mock empty orders list
            broker._mock_client.list_orders.return_value = []

        # List all orders (including closed)
        orders = broker.list_orders(status="all", limit=10)

        assert isinstance(orders, list)
        print(f"[OK] Alpaca orders: {len(orders)} orders in history")

        if orders:
            order = orders[0]
            assert "id" in order
            assert "symbol" in order
            assert "qty" in order
            assert "side" in order
            assert "type" in order
            assert "status" in order
            print(
                f"  Latest: {order['symbol']} - {order['side'].upper()} {order['qty']} @ {order['type']}, Status={order['status']}"
            )

    def test_submit_and_cancel_order(self, broker):
        """Test submitting and canceling an order.

        Uses a limit order that's unlikely to fill immediately,
        so we can test order management without executing trades.
        """
        if not HAS_REAL_CREDENTIALS:
            # Mock order submission
            mock_order = Mock()
            mock_order._raw = {
                "id": "test-order-123",
                "symbol": "AAPL",
                "qty": "1",
                "side": "buy",
                "type": "limit",
                "status": "accepted",
                "limit_price": "1.00",
            }
            broker._mock_client.submit_order.return_value = mock_order
            broker._mock_client.get_order.return_value = mock_order

            # Mock canceled order for final check
            canceled_mock = Mock()
            canceled_mock._raw = {**mock_order._raw, "status": "canceled"}
            broker._mock_client.get_order.side_effect = [mock_order, canceled_mock]
            broker._mock_client.cancel_order.return_value = None

        # Submit a limit order at very low price (unlikely to fill)
        order = broker.submit_order(
            symbol="AAPL",
            qty=1,
            side="buy",
            type_="limit",
            time_in_force="day",
            limit_price=1.00,  # Very low price, won't fill
        )

        assert isinstance(order, dict)
        assert "id" in order
        assert order["symbol"] == "AAPL"
        assert order["side"] == "buy"
        assert order["type"] == "limit"
        assert order["status"] in ("new", "accepted", "pending_new")
        print(
            f"[OK] Order submitted: ID={order['id']}, Symbol={order['symbol']}, Status={order['status']}"
        )

        order_id = order["id"]

        # Get order details
        fetched_order = broker.get_order(order_id)
        assert fetched_order["id"] == order_id
        assert fetched_order["symbol"] == "AAPL"
        print(f"[OK] Order fetched: ID={order_id}, Status={fetched_order['status']}")

        # Cancel the order
        broker.cancel_order(order_id)
        print(f"[OK] Order canceled: ID={order_id}")

        # Verify cancellation
        canceled_order = broker.get_order(order_id)
        # Status may be "canceled" or "pending_cancel" depending on timing
        assert canceled_order["status"] in ("canceled", "pending_cancel")
        print(f"[OK] Order status after cancel: {canceled_order['status']}")

    def test_get_portfolio_history(self, broker):
        """Test getting portfolio history."""
        if not HAS_REAL_CREDENTIALS:
            # Mock portfolio history
            mock_history = Mock()
            mock_history._raw = {
                "timestamp": [1609459200, 1609545600, 1609632000],
                "equity": [100000.0, 100500.0, 101000.0],
                "profit_loss": [0, 500, 1000],
                "profit_loss_pct": [0, 0.005, 0.01],
            }
            broker._mock_client.get_portfolio_history.return_value = mock_history

        history = broker.get_portfolio_history(period="1W", timeframe="1D")

        assert isinstance(history, dict)
        assert "timestamp" in history
        assert "equity" in history

        # May have data depending on account history
        timestamps = history.get("timestamp", [])
        print(f"[OK] Portfolio history: {len(timestamps)} data points over 1 week")

        if timestamps:
            equity_values = history.get("equity", [])
            print(f"  Latest equity: ${equity_values[-1] if equity_values else 'N/A'}")
