"""Unit tests for brokerage module - easy_brokerage and add_brokerage."""

import pytest
from unittest.mock import Mock, patch

# Note: These tests use mocking and don't require actual alpaca-trade-api package


class TestEasyBrokerage:
    """Test easy_brokerage() builder function."""

    @patch("fin_infra.providers.brokerage.alpaca.AlpacaBrokerage")
    @patch.dict("os.environ", {"ALPACA_API_KEY": "test_key", "ALPACA_API_SECRET": "test_secret"})
    def test_default_provider_paper_mode(self, mock_alpaca):
        """Should default to Alpaca provider in paper mode."""
        from fin_infra.brokerage import easy_brokerage

        broker = easy_brokerage()

        mock_alpaca.assert_called_once()
        call_kwargs = mock_alpaca.call_args[1]
        assert call_kwargs["mode"] == "paper"

    @patch("fin_infra.providers.brokerage.alpaca.AlpacaBrokerage")
    @patch.dict("os.environ", {"ALPACA_API_KEY": "test_key", "ALPACA_API_SECRET": "test_secret"})
    def test_explicit_paper_mode(self, mock_alpaca):
        """Should create broker in paper mode when explicitly specified."""
        from fin_infra.brokerage import easy_brokerage

        broker = easy_brokerage(mode="paper")

        call_kwargs = mock_alpaca.call_args[1]
        assert call_kwargs["mode"] == "paper"

    @patch("fin_infra.providers.brokerage.alpaca.AlpacaBrokerage")
    @patch.dict("os.environ", {"ALPACA_API_KEY": "test_key", "ALPACA_API_SECRET": "test_secret"})
    def test_explicit_live_mode(self, mock_alpaca):
        """Should create broker in live mode when explicitly specified."""
        from fin_infra.brokerage import easy_brokerage

        broker = easy_brokerage(mode="live")

        call_kwargs = mock_alpaca.call_args[1]
        assert call_kwargs["mode"] == "live"

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_credentials_raises_error(self):
        """Should raise ValueError when credentials are missing."""
        from fin_infra.brokerage import easy_brokerage

        with pytest.raises(ValueError, match="Alpaca credentials required"):
            easy_brokerage()

    @patch("fin_infra.providers.brokerage.alpaca.AlpacaBrokerage")
    def test_explicit_credentials(self, mock_alpaca):
        """Should accept explicit credentials."""
        from fin_infra.brokerage import easy_brokerage

        broker = easy_brokerage(api_key="explicit_key", api_secret="explicit_secret", mode="paper")

        call_kwargs = mock_alpaca.call_args[1]
        assert call_kwargs["api_key"] == "explicit_key"
        assert call_kwargs["api_secret"] == "explicit_secret"

    def test_invalid_provider_raises_error(self):
        """Should raise ValueError for unsupported provider."""
        from fin_infra.brokerage import easy_brokerage

        with pytest.raises(ValueError, match="Unknown brokerage provider: invalid"):
            easy_brokerage(provider="invalid", api_key="key", api_secret="secret")


class TestAddBrokerage:
    """Test add_brokerage() FastAPI integration helper."""

    @patch("fin_infra.brokerage.easy_brokerage")
    def test_add_brokerage_mounts_routes(self, mock_easy_brokerage):
        """Should mount brokerage routes to FastAPI app."""
        from fastapi import FastAPI
        from fin_infra.brokerage import add_brokerage

        # Mock the provider
        mock_provider = Mock()
        mock_easy_brokerage.return_value = mock_provider

        app = FastAPI()
        broker = add_brokerage(app, prefix="/brokerage")

        # Check provider stored on app state
        assert hasattr(app.state, "brokerage_provider")
        assert hasattr(app.state, "brokerage_mode")
        assert app.state.brokerage_provider is mock_provider
        assert app.state.brokerage_mode == "paper"  # Default mode

        # Check routes are mounted
        route_paths = [route.path for route in app.routes]
        assert "/brokerage/account" in route_paths
        assert "/brokerage/positions" in route_paths
        assert "/brokerage/orders" in route_paths

    @patch("fin_infra.brokerage.easy_brokerage")
    def test_add_brokerage_paper_mode_default(self, mock_easy_brokerage):
        """Should default to paper mode for safety."""
        from fastapi import FastAPI
        from fin_infra.brokerage import add_brokerage

        mock_provider = Mock()
        mock_easy_brokerage.return_value = mock_provider

        app = FastAPI()
        add_brokerage(app)

        assert app.state.brokerage_mode == "paper"
        mock_easy_brokerage.assert_called_once()
        call_kwargs = mock_easy_brokerage.call_args[1]
        assert call_kwargs["mode"] == "paper"

    @patch("fin_infra.brokerage.easy_brokerage")
    def test_add_brokerage_live_mode_explicit(self, mock_easy_brokerage):
        """Should accept live mode when explicitly specified."""
        from fastapi import FastAPI
        from fin_infra.brokerage import add_brokerage

        mock_provider = Mock()
        mock_easy_brokerage.return_value = mock_provider

        app = FastAPI()
        add_brokerage(app, mode="live")

        assert app.state.brokerage_mode == "live"
        call_kwargs = mock_easy_brokerage.call_args[1]
        assert call_kwargs["mode"] == "live"

    @patch("fin_infra.brokerage.easy_brokerage")
    def test_add_brokerage_custom_prefix(self, mock_easy_brokerage):
        """Should mount routes with custom prefix."""
        from fastapi import FastAPI
        from fin_infra.brokerage import add_brokerage

        mock_provider = Mock()
        mock_easy_brokerage.return_value = mock_provider

        app = FastAPI()
        add_brokerage(app, prefix="/api/v1/trading")

        route_paths = [route.path for route in app.routes]
        assert "/api/v1/trading/account" in route_paths
        assert "/api/v1/trading/positions" in route_paths


class TestBrokerageRoutes:
    """Test brokerage API routes."""

    @pytest.fixture
    def app_with_brokerage(self):
        """Create FastAPI app with brokerage routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        with patch("fin_infra.brokerage.easy_brokerage") as mock_easy_brokerage:
            # Mock provider
            mock_provider = Mock()
            mock_provider.get_account.return_value = {
                "id": "acc_123",
                "buying_power": "50000.00",
                "cash": "25000.00",
                "portfolio_value": "100000.00",
            }
            mock_provider.positions.return_value = [
                {"symbol": "AAPL", "qty": "100", "market_value": "15000.00"}
            ]
            mock_provider.list_orders.return_value = [
                {"id": "ord_123", "symbol": "AAPL", "status": "filled"}
            ]
            mock_easy_brokerage.return_value = mock_provider

            app = FastAPI()
            from fin_infra.brokerage import add_brokerage

            add_brokerage(app, prefix="/brokerage")

            yield TestClient(app), mock_provider

    def test_get_account_endpoint(self, app_with_brokerage):
        """Should fetch account information."""
        client, mock_provider = app_with_brokerage

        response = client.get("/brokerage/account")

        assert response.status_code == 200
        data = response.json()
        assert "buying_power" in data
        assert "cash" in data
        assert "portfolio_value" in data
        mock_provider.get_account.assert_called_once()

    def test_list_positions_endpoint(self, app_with_brokerage):
        """Should list all positions."""
        client, mock_provider = app_with_brokerage

        response = client.get("/brokerage/positions")

        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert "count" in data
        assert len(data["positions"]) == 1
        mock_provider.positions.assert_called_once()

    def test_list_orders_endpoint(self, app_with_brokerage):
        """Should list orders."""
        client, mock_provider = app_with_brokerage

        response = client.get("/brokerage/orders?status=open&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert "count" in data
        mock_provider.list_orders.assert_called_once_with(status="open", limit=10)

    def test_submit_order_endpoint(self, app_with_brokerage):
        """Should submit an order."""
        client, mock_provider = app_with_brokerage

        mock_provider.submit_order.return_value = {
            "id": "ord_123",
            "symbol": "AAPL",
            "qty": "10",
            "side": "buy",
            "status": "new",
        }

        order_data = {
            "symbol": "AAPL",
            "qty": "10",
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }

        response = client.post("/brokerage/orders", json=order_data)

        # Debug validation errors
        if response.status_code != 200:
            print(f"Response: {response.status_code}, Body: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["status"] == "new"
        mock_provider.submit_order.assert_called_once()


class TestWatchlistRoutes:
    """Test watchlist-related FastAPI routes."""

    @pytest.fixture
    def app_with_brokerage(self):
        """Create FastAPI app with mocked brokerage provider."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from fin_infra.brokerage import add_brokerage
        from unittest.mock import Mock

        app = FastAPI()

        # Mock the provider
        mock_provider = Mock()
        mock_provider.create_watchlist.return_value = {
            "id": "wl_123",
            "name": "Tech Stocks",
            "symbols": ["AAPL", "GOOGL"],
        }
        mock_provider.list_watchlists.return_value = [
            {"id": "wl_123", "name": "Tech Stocks", "symbols": ["AAPL"]},
            {"id": "wl_456", "name": "Finance", "symbols": ["JPM"]},
        ]
        mock_provider.get_watchlist.return_value = {
            "id": "wl_123",
            "name": "Tech Stocks",
            "symbols": ["AAPL", "GOOGL"],
        }
        mock_provider.delete_watchlist.return_value = None
        mock_provider.add_to_watchlist.return_value = {
            "id": "wl_123",
            "name": "Tech Stocks",
            "symbols": ["AAPL", "GOOGL", "MSFT"],
        }
        mock_provider.remove_from_watchlist.return_value = {
            "id": "wl_123",
            "name": "Tech Stocks",
            "symbols": ["AAPL"],
        }

        # Add brokerage with mocked provider
        with patch("fin_infra.brokerage.easy_brokerage", return_value=mock_provider):
            add_brokerage(app, mode="paper")

        client = TestClient(app)
        return client, mock_provider

    def test_create_watchlist_endpoint(self, app_with_brokerage):
        """Should create a new watchlist."""
        client, mock_provider = app_with_brokerage

        response = client.post("/brokerage/watchlists?name=Tech Stocks&symbols=AAPL&symbols=GOOGL")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wl_123"
        assert data["name"] == "Tech Stocks"
        assert len(data["symbols"]) == 2
        mock_provider.create_watchlist.assert_called_once()

    def test_list_watchlists_endpoint(self, app_with_brokerage):
        """Should list all watchlists."""
        client, mock_provider = app_with_brokerage

        response = client.get("/brokerage/watchlists")

        assert response.status_code == 200
        data = response.json()
        assert "watchlists" in data
        assert "count" in data
        assert len(data["watchlists"]) == 2
        mock_provider.list_watchlists.assert_called_once()

    def test_get_watchlist_endpoint(self, app_with_brokerage):
        """Should get a watchlist by ID."""
        client, mock_provider = app_with_brokerage

        response = client.get("/brokerage/watchlists/wl_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wl_123"
        assert data["name"] == "Tech Stocks"
        mock_provider.get_watchlist.assert_called_once_with("wl_123")

    def test_delete_watchlist_endpoint(self, app_with_brokerage):
        """Should delete a watchlist."""
        client, mock_provider = app_with_brokerage

        response = client.delete("/brokerage/watchlists/wl_123")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()
        mock_provider.delete_watchlist.assert_called_once_with("wl_123")

    def test_add_to_watchlist_endpoint(self, app_with_brokerage):
        """Should add a symbol to a watchlist."""
        client, mock_provider = app_with_brokerage

        response = client.post("/brokerage/watchlists/wl_123/symbols?symbol=MSFT")

        assert response.status_code == 200
        data = response.json()
        assert len(data["symbols"]) == 3
        mock_provider.add_to_watchlist.assert_called_once_with("wl_123", "MSFT")

    def test_remove_from_watchlist_endpoint(self, app_with_brokerage):
        """Should remove a symbol from a watchlist."""
        client, mock_provider = app_with_brokerage

        response = client.delete("/brokerage/watchlists/wl_123/symbols/GOOGL")

        assert response.status_code == 200
        data = response.json()
        assert len(data["symbols"]) == 1
        mock_provider.remove_from_watchlist.assert_called_once_with("wl_123", "GOOGL")
