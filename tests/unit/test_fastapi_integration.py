"""Tests for FastAPI integration helpers (add_banking, add_market_data)."""

from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAddBanking:
    """Tests for add_banking() FastAPI helper."""

    @patch("fin_infra.banking.resolve")
    def test_add_banking_mounts_routes(self, mock_resolve):
        """Test that add_banking mounts all banking routes."""
        app = FastAPI()

        mock_provider = Mock()
        mock_provider.create_link_token.return_value = "link_token_123"
        mock_provider.exchange_public_token.return_value = {
            "access_token": "access_456",
            "item_id": "item_789",
        }
        mock_provider.accounts.return_value = [{"id": "acc1", "name": "Checking"}]
        mock_provider.transactions.return_value = [{"id": "tx1", "amount": 100}]
        mock_provider.balances.return_value = {"available": 1000}
        mock_provider.identity.return_value = {"name": "John Doe"}
        mock_resolve.return_value = mock_provider

        from fin_infra.banking import add_banking

        banking = add_banking(app, provider="teller")

        # Verify provider was created (with any config)
        assert banking == mock_provider
        assert mock_resolve.called
        assert mock_resolve.call_args[0][:2] == ("banking", "teller")

        # Test routes with TestClient
        client = TestClient(app)

        # Test create link token
        response = client.post("/banking/link", json={"user_id": "user123"})
        assert response.status_code == 200
        assert response.json() == {"link_token": "link_token_123"}

        # Test exchange token
        response = client.post("/banking/exchange", json={"public_token": "pub_123"})
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "access_456"
        assert data["item_id"] == "item_789"

        # Test get accounts
        response = client.get("/banking/accounts", headers={"Authorization": "Bearer token123"})
        assert response.status_code == 200
        assert response.json() == {"accounts": [{"id": "acc1", "name": "Checking"}]}

        # Test get transactions
        response = client.get("/banking/transactions", headers={"Authorization": "Bearer token123"})
        assert response.status_code == 200
        # Updated to match new pagination envelope format (Task 31)
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert data["data"] == [{"id": "tx1", "amount": 100}]
        assert data["meta"]["total"] == 1

        # Test get balances
        response = client.get("/banking/balances", headers={"Authorization": "Bearer token123"})
        assert response.status_code == 200
        assert response.json() == {"balances": {"available": 1000}}

        # Test get identity
        response = client.get("/banking/identity", headers={"Authorization": "Bearer token123"})
        assert response.status_code == 200
        assert response.json() == {"identity": {"name": "John Doe"}}

    @patch("fin_infra.banking.resolve")
    def test_add_banking_custom_prefix(self, mock_resolve):
        """Test that add_banking respects custom prefix."""
        app = FastAPI()

        mock_provider = Mock()
        mock_provider.create_link_token.return_value = "link_token_123"
        mock_resolve.return_value = mock_provider

        from fin_infra.banking import add_banking

        # Test custom prefix (user can still use versioned paths if they want)
        add_banking(app, provider="teller", prefix="/api/banking")

        client = TestClient(app)
        response = client.post("/api/banking/link", json={"user_id": "user123"})
        assert response.status_code == 200

    @patch("fin_infra.banking.resolve")
    def test_add_banking_missing_authorization_header(self, mock_resolve):
        """Test that protected routes require Authorization header."""
        app = FastAPI()

        mock_provider = Mock()
        mock_resolve.return_value = mock_provider

        from fin_infra.banking import add_banking

        add_banking(app, provider="teller")

        client = TestClient(app)
        response = client.get("/banking/accounts")
        assert response.status_code == 422  # Missing required header

    @patch("fin_infra.banking.resolve")
    def test_add_banking_invalid_authorization_format(self, mock_resolve):
        """Test that invalid Authorization format is rejected."""
        app = FastAPI()

        mock_provider = Mock()
        mock_resolve.return_value = mock_provider

        from fin_infra.banking import add_banking

        add_banking(app, provider="teller")

        client = TestClient(app)
        response = client.get(
            "/banking/accounts", headers={"Authorization": "InvalidFormat token123"}
        )
        assert response.status_code == 401
        assert "Invalid authorization header" in response.json()["detail"]

    def test_add_banking_with_provider_instance(self):
        """Test that add_banking accepts a provider instance directly."""
        from fin_infra.providers.base import BankingProvider

        app = FastAPI()

        # Create mock provider instance that implements BankingProvider
        mock_provider = Mock(spec=BankingProvider)
        mock_provider.create_link_token.return_value = "link_token_instance"

        from fin_infra.banking import add_banking

        banking = add_banking(app, provider=mock_provider)

        # Should use the provided instance directly
        assert banking is mock_provider

        # Test that routes work with instance
        client = TestClient(app)
        response = client.post("/banking/link", json={"user_id": "user123"})
        assert response.status_code == 200
        assert response.json() == {"link_token": "link_token_instance"}


class TestAddMarketData:
    """Tests for add_market_data() FastAPI helper."""

    def test_add_market_data_mounts_routes(self):
        """Test that add_market_data mounts all market routes."""
        app = FastAPI()

        with patch("fin_infra.markets.easy_market") as mock_easy:
            mock_provider = Mock()

            # Create a mock that behaves like a dict
            mock_quote = Mock()
            mock_quote.model_dump.return_value = {
                "symbol": "AAPL",
                "price": 150.0,
                "as_of": "2024-01-01",
                "currency": "USD",
            }
            mock_provider.quote.return_value = mock_quote

            mock_candle = Mock()
            mock_candle.model_dump.return_value = {
                "ts": "2024-01-01",
                "open": 150,
                "high": 155,
                "low": 148,
                "close": 152,
                "volume": 1000,
            }
            mock_provider.history.return_value = [mock_candle]
            mock_provider.search.return_value = [{"symbol": "AAPL", "name": "Apple Inc."}]
            mock_easy.return_value = mock_provider

            from fin_infra.markets import add_market_data

            market = add_market_data(app, provider="alphavantage")

            # Verify provider was created
            assert market == mock_provider
            mock_easy.assert_called_once_with(provider="alphavantage")

            # Test routes with TestClient
            client = TestClient(app)

            # Test get quote
            response = client.get("/market/quote/AAPL")
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["price"] == 150.0

            # Test get history
            response = client.get("/market/history/AAPL?period=1mo&interval=1d")
            assert response.status_code == 200
            data = response.json()
            assert "candles" in data
            assert len(data["candles"]) == 1
            assert data["candles"][0]["ts"] == "2024-01-01"

            # Test search
            response = client.get("/market/search?keywords=Apple")
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1

    def test_add_market_data_custom_prefix(self):
        """Test that add_market_data respects custom prefix."""
        app = FastAPI()

        with patch("fin_infra.markets.easy_market") as mock_easy:
            mock_provider = Mock()
            mock_quote = Mock()
            mock_quote.model_dump.return_value = {"symbol": "AAPL", "price": 150.0}
            mock_provider.quote.return_value = mock_quote
            mock_easy.return_value = mock_provider

            from fin_infra.markets import add_market_data

            # Test custom prefix (user can still use versioned paths if they want)
            add_market_data(app, provider="yahoo", prefix="/api/market")

            client = TestClient(app)
            response = client.get("/api/market/quote/AAPL")
            assert response.status_code == 200

    def test_add_market_data_search_not_supported(self):
        """Test that search returns 501 if provider doesn't support it."""
        app = FastAPI()

        with patch("fin_infra.markets.easy_market") as mock_easy:
            # Yahoo doesn't have search method
            mock_provider = Mock(spec=["quote", "history"])  # No search
            mock_easy.return_value = mock_provider

            from fin_infra.markets import add_market_data

            add_market_data(app, provider="yahoo")

            client = TestClient(app)
            response = client.get("/market/search?keywords=Apple")
            assert response.status_code == 501
            assert "not supported" in response.json()["detail"]

    def test_add_market_data_error_handling(self):
        """Test that provider errors are converted to HTTP errors."""
        app = FastAPI()

        with patch("fin_infra.markets.easy_market") as mock_easy:
            mock_provider = Mock()
            mock_provider.quote.side_effect = Exception("Invalid symbol")
            mock_easy.return_value = mock_provider

            from fin_infra.markets import add_market_data

            add_market_data(app, provider="yahoo")

            client = TestClient(app)
            response = client.get("/market/quote/INVALID")
            assert response.status_code == 400
            assert "Invalid symbol" in response.json()["detail"]

    def test_add_market_data_with_provider_instance(self):
        """Test that add_market_data accepts a provider instance directly."""
        from fin_infra.providers.base import MarketDataProvider
        from fin_infra.models import Quote
        from datetime import datetime

        app = FastAPI()

        # Create mock provider instance that implements MarketDataProvider
        mock_provider = Mock(spec=MarketDataProvider)
        # Return a proper Quote model (not Mock)
        mock_quote = Quote(symbol="TSLA", price=250.0, as_of=datetime.now(), currency="USD")
        mock_provider.quote.return_value = mock_quote

        from fin_infra.markets import add_market_data

        market = add_market_data(app, provider=mock_provider)

        # Should use the provided instance directly
        assert market is mock_provider

        # Test that routes work with instance
        client = TestClient(app)
        response = client.get("/market/quote/TSLA")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "TSLA"
        assert data["price"] == 250.0

    def test_add_market_data_auto_detect_provider(self):
        """Test that add_market_data auto-detects provider from env."""
        app = FastAPI()

        with patch("fin_infra.markets.easy_market") as mock_easy:
            mock_provider = Mock()
            mock_quote = Mock(symbol="AAPL", price=150.0)
            mock_provider.quote.return_value = mock_quote
            mock_easy.return_value = mock_provider

            from fin_infra.markets import add_market_data

            add_market_data(app)  # No provider specified

            # Should call easy_market with provider=None (auto-detect)
            mock_easy.assert_called_once_with(provider=None)


class TestFastAPIIntegration:
    """Integration tests for combining multiple FastAPI helpers."""

    @patch("fin_infra.markets.easy_market")
    @patch("fin_infra.banking.resolve")
    def test_add_banking_and_market_together(self, mock_banking_resolve, mock_market_easy):
        """Test that both helpers can be added to the same app."""
        app = FastAPI()

        mock_banking_provider = Mock()
        mock_banking_provider.create_link_token.return_value = "link_123"
        mock_banking_resolve.return_value = mock_banking_provider

        mock_market_provider = Mock()
        mock_quote = Mock()
        mock_quote.model_dump.return_value = {"symbol": "AAPL", "price": 150.0}
        mock_market_provider.quote.return_value = mock_quote
        mock_market_easy.return_value = mock_market_provider

        from fin_infra.banking import add_banking
        from fin_infra.markets import add_market_data

        add_banking(app, provider="teller")
        add_market_data(app, provider="yahoo")

        # Verify both providers are stored
        assert app.state.banking_provider == mock_banking_provider
        assert app.state.market_provider == mock_market_provider

        # Test both routes work
        client = TestClient(app)

        response = client.post("/banking/link", json={"user_id": "user123"})
        assert response.status_code == 200

        response = client.get("/market/quote/AAPL")
        assert response.status_code == 200
