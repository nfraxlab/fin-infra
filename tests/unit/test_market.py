"""Unit tests for market data providers."""
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import httpx

from fin_infra.markets import easy_market
from fin_infra.providers.market.alphavantage import AlphaVantageMarketData
from fin_infra.providers.market.yahoo import YahooFinanceMarketData
from fin_infra.models import Quote, Candle


class TestEasyMarket:
    """Test the easy_market() builder function."""
    
    def test_easy_market_auto_detects_alphavantage_with_key(self, monkeypatch):
        """Should auto-detect Alpha Vantage when API key is in env."""
        monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test_key")
        market = easy_market()
        assert isinstance(market, AlphaVantageMarketData)
        assert market.api_key == "test_key"
    
    def test_easy_market_auto_detects_yahoo_without_key(self, monkeypatch):
        """Should auto-detect Yahoo Finance when no API key."""
        monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        market = easy_market()
        assert isinstance(market, YahooFinanceMarketData)
    
    def test_easy_market_explicit_provider(self):
        """Should use explicit provider when specified."""
        market = easy_market(provider="yahoo")
        assert isinstance(market, YahooFinanceMarketData)
    
    def test_easy_market_with_config(self):
        """Should pass config to provider."""
        market = easy_market(provider="alphavantage", api_key="custom_key", throttle=False)
        assert isinstance(market, AlphaVantageMarketData)
        assert market.api_key == "custom_key"
        assert market.throttle is False
    
    def test_easy_market_invalid_provider(self):
        """Should raise error for invalid provider."""
        with pytest.raises(ValueError, match="Unknown market data provider"):
            easy_market(provider="invalid")


class TestAlphaVantageMarketData:
    """Test Alpha Vantage provider."""
    
    @patch("fin_infra.providers.market.alphavantage.Settings")
    def test_init_requires_api_key(self, mock_settings_class, monkeypatch):
        """Should raise error if no API key provided."""
        monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        
        # Mock Settings to return None for API key
        mock_settings = Mock()
        mock_settings.alphavantage_api_key = None
        mock_settings_class.return_value = mock_settings
        
        with pytest.raises(ValueError, match="API key required"):
            AlphaVantageMarketData()
    
    def test_init_with_api_key_param(self):
        """Should accept API key as parameter."""
        provider = AlphaVantageMarketData(api_key="test_key")
        assert provider.api_key == "test_key"
    
    def test_init_from_env(self, monkeypatch):
        """Should load API key from environment."""
        monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "env_key")
        provider = AlphaVantageMarketData()
        assert provider.api_key == "env_key"
    
    @patch("httpx.get")
    def test_quote_success(self, mock_get):
        """Should return Quote on successful API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.25",
                "07. latest trading day": "2025-01-15",
            }
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        quote = provider.quote("AAPL")
        
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.25")
        assert isinstance(quote.as_of, datetime)
    
    @patch("httpx.get")
    def test_quote_handles_rate_limit(self, mock_get):
        """Should raise ValueError on rate limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        
        with pytest.raises(ValueError, match="rate limit"):
            provider.quote("AAPL")
    
    @patch("httpx.get")
    def test_quote_handles_error_message(self, mock_get):
        """Should raise ValueError on API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Error Message": "Invalid API call"
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        
        with pytest.raises(ValueError, match="Alpha Vantage error"):
            provider.quote("AAPL")
    
    @patch("httpx.get")
    def test_quote_handles_429_status(self, mock_get):
        """Should raise ValueError on 429 status code."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            provider.quote("AAPL")
    
    @patch("httpx.get")
    def test_history_success(self, mock_get):
        """Should return list of Candles on successful API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Time Series (Daily)": {
                "2025-01-15": {
                    "1. open": "150.00",
                    "2. high": "152.50",
                    "3. low": "149.00",
                    "4. close": "151.25",
                    "5. volume": "50000000",
                },
                "2025-01-14": {
                    "1. open": "148.00",
                    "2. high": "150.00",
                    "3. low": "147.50",
                    "4. close": "149.75",
                    "5. volume": "45000000",
                },
            }
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        candles = provider.history("AAPL", period="1mo")
        
        assert isinstance(candles, list)
        assert len(candles) == 2
        assert all(isinstance(c, Candle) for c in candles)
        assert candles[0].close == Decimal("151.25")
    
    @patch("httpx.get")
    def test_history_returns_empty_on_rate_limit(self, mock_get):
        """Should return empty list on rate limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Note": "Rate limit exceeded"
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        candles = provider.history("AAPL")
        
        assert candles == []
    
    @patch("httpx.get")
    def test_search_success(self, mock_get):
        """Should return list of symbol matches."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bestMatches": [
                {
                    "1. symbol": "AAPL",
                    "2. name": "Apple Inc.",
                    "3. type": "Equity",
                    "4. region": "United States",
                    "8. currency": "USD",
                },
                {
                    "1. symbol": "APLE",
                    "2. name": "Apple Hospitality REIT Inc.",
                    "3. type": "Equity",
                    "4. region": "United States",
                    "8. currency": "USD",
                },
            ]
        }
        mock_get.return_value = mock_response
        
        provider = AlphaVantageMarketData(api_key="test_key", throttle=False)
        results = provider.search("apple")
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["name"] == "Apple Inc."
    
    def test_search_empty_keywords(self):
        """Should raise ValueError for empty keywords."""
        provider = AlphaVantageMarketData(api_key="test_key")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.search("")


class TestYahooFinanceMarketData:
    """Test Yahoo Finance provider."""
    
    def test_init_no_config_needed(self):
        """Should initialize without any configuration."""
        provider = YahooFinanceMarketData()
        assert provider is not None
    
    @patch("fin_infra.providers.market.yahoo.Ticker")
    def test_quote_success(self, mock_ticker_class):
        """Should return Quote on successful API call."""
        mock_ticker = Mock()
        mock_ticker.quotes = {
            "AAPL": {
                "regularMarketPrice": 150.25,
                "regularMarketTime": 1705334400,  # Unix timestamp
                "currency": "USD",
            }
        }
        mock_ticker_class.return_value = mock_ticker
        
        provider = YahooFinanceMarketData()
        quote = provider.quote("AAPL")
        
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.25")
        assert quote.currency == "USD"
    
    @patch("fin_infra.providers.market.yahoo.Ticker")
    def test_quote_handles_error(self, mock_ticker_class):
        """Should raise ValueError on API error."""
        mock_ticker = Mock()
        mock_ticker.quotes = {"error": "Invalid symbol"}
        mock_ticker_class.return_value = mock_ticker
        
        provider = YahooFinanceMarketData()
        
        with pytest.raises(ValueError, match="Yahoo Finance error"):
            provider.quote("INVALID")
    
    @patch("fin_infra.providers.market.yahoo.Ticker")
    def test_history_success(self, mock_ticker_class):
        """Should return list of Candles."""
        import pandas as pd
        
        mock_ticker = Mock()
        # Yahoo returns oldest first, so 2025-01-14 should come before 2025-01-15
        mock_df = pd.DataFrame({
            "date": [datetime(2025, 1, 14), datetime(2025, 1, 15)],
            "open": [148.00, 150.00],
            "high": [150.00, 152.50],
            "low": [147.50, 149.00],
            "close": [149.75, 151.25],
            "volume": [45000000, 50000000],
        })
        mock_ticker.history.return_value = mock_df
        mock_ticker_class.return_value = mock_ticker
        
        provider = YahooFinanceMarketData()
        candles = provider.history("AAPL", period="1mo")
        
        assert isinstance(candles, list)
        assert len(candles) == 2
        assert all(isinstance(c, Candle) for c in candles)
        # After reversing, newest (2025-01-15) should be first
        assert candles[0].close == Decimal("151.25")
        assert candles[1].close == Decimal("149.75")
    
    @patch("fin_infra.providers.market.yahoo.Ticker")
    def test_history_empty_dataframe(self, mock_ticker_class):
        """Should return empty list for empty dataframe."""
        import pandas as pd
        
        mock_ticker = Mock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_class.return_value = mock_ticker
        
        provider = YahooFinanceMarketData()
        candles = provider.history("INVALID")
        
        assert candles == []
