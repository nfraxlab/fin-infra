"""Unit tests for brokerage module - easy_brokerage and add_brokerage."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

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
        
        broker = easy_brokerage(
            api_key="explicit_key",
            api_secret="explicit_secret",
            mode="paper"
        )
        
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
                "portfolio_value": "100000.00"
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
            "status": "new"
        }
        
        order_data = {
            "symbol": "AAPL",
            "qty": "10",
            "side": "buy",
            "type": "market",
            "time_in_force": "day"
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
