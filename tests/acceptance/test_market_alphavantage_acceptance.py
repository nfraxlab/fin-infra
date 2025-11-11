"""Acceptance tests for market data providers (Alpha Vantage, Yahoo Finance).

These tests make real API calls and require:
- Alpha Vantage: ALPHA_VANTAGE_API_KEY or ALPHAVANTAGE_API_KEY env var
- Yahoo Finance: No API key needed (zero config)
"""

import os
from decimal import Decimal

import pytest

from fin_infra.markets import easy_market
from fin_infra.providers.market.alphavantage import AlphaVantageMarketData
from fin_infra.providers.market.yahoo import YahooFinanceMarketData
from fin_infra.models import Quote, Candle


pytestmark = [pytest.mark.acceptance]


@pytest.mark.skipif(
    not (os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHAVANTAGE_API_KEY")),
    reason="No Alpha Vantage API key in environment",
)
class TestAlphaVantageAcceptance:
    """Acceptance tests for Alpha Vantage provider."""

    def test_quote(self):
        """Test real quote fetch from Alpha Vantage.

        NOTE: May fail due to Alpha Vantage rate limits (5 req/min free tier).
        """
        provider = AlphaVantageMarketData()
        try:
            quote = provider.quote("AAPL")
        except ValueError as e:
            if "No data returned" in str(e) or "rate limit" in str(e).lower():
                pytest.skip(f"Alpha Vantage API issue (likely rate limited): {e}")
            raise

        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.price > Decimal(0)
        assert quote.currency == "USD"
        print(f"✓ Alpha Vantage quote: AAPL @ ${quote.price}")

    def test_history(self):
        """Test real historical data fetch from Alpha Vantage.

        NOTE: May fail due to Alpha Vantage rate limits (5 req/min free tier).
        """
        provider = AlphaVantageMarketData()
        candles = provider.history("AAPL", period="1mo")

        assert isinstance(candles, list)
        # Alpha Vantage may return empty results when rate limited
        if len(candles) == 0:
            pytest.skip("Alpha Vantage returned empty results (likely rate limited)")

        assert all(isinstance(c, Candle) for c in candles)

        # Verify data structure
        first_candle = candles[0]
        assert first_candle.ts > 0
        assert first_candle.close > Decimal(0)
        assert first_candle.volume >= Decimal(0)
        print(f"✓ Alpha Vantage history: {len(candles)} candles for AAPL")

    def test_search(self):
        """Test real symbol search from Alpha Vantage.

        NOTE: May fail due to Alpha Vantage rate limits (5 req/min free tier).
        """
        provider = AlphaVantageMarketData()
        results = provider.search("Apple")

        assert isinstance(results, list)
        # Alpha Vantage may return empty results when rate limited
        if len(results) == 0:
            pytest.skip("Alpha Vantage returned empty results (likely rate limited)")

        # AAPL should be in results
        symbols = [r["symbol"] for r in results]
        assert "AAPL" in symbols

        # Check result structure
        first_result = results[0]
        assert "symbol" in first_result
        assert "name" in first_result
        assert "type" in first_result
        print(f"✓ Alpha Vantage search: Found {len(results)} results for 'Apple'")


class TestYahooFinanceAcceptance:
    """Acceptance tests for Yahoo Finance provider (zero config)."""

    def test_quote(self):
        """Test real quote fetch from Yahoo Finance."""
        provider = YahooFinanceMarketData()
        quote = provider.quote("AAPL")

        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.price > Decimal(0)
        print(f"✓ Yahoo Finance quote: AAPL @ ${quote.price}")

    def test_history(self):
        """Test real historical data fetch from Yahoo Finance."""
        provider = YahooFinanceMarketData()
        candles = provider.history("AAPL", period="1mo")

        assert isinstance(candles, list)
        assert len(candles) > 0
        assert all(isinstance(c, Candle) for c in candles)

        # Verify data structure
        first_candle = candles[0]
        assert first_candle.ts > 0
        assert first_candle.close > Decimal(0)
        print(f"✓ Yahoo Finance history: {len(candles)} candles for AAPL")


class TestEasyMarketAcceptance:
    """Acceptance tests for easy_market() builder."""

    def test_easy_market_yahoo_zero_config(self, monkeypatch):
        """Test that easy_market() defaults to Yahoo when no API key."""
        # Remove Alpha Vantage keys to force Yahoo
        monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)

        market = easy_market()
        assert isinstance(market, YahooFinanceMarketData)

        # Verify it works
        quote = market.quote("AAPL")
        assert isinstance(quote, Quote)
        assert quote.price > Decimal(0)
        print(f"✓ easy_market() zero-config: AAPL @ ${quote.price}")

    @pytest.mark.skipif(
        not (os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHAVANTAGE_API_KEY")),
        reason="No Alpha Vantage API key in environment",
    )
    def test_easy_market_auto_detects_alphavantage(self):
        """Test that easy_market() auto-detects Alpha Vantage when key present.

        NOTE: May fail due to Alpha Vantage rate limits (5 req/min free tier).
        """
        market = easy_market()
        assert isinstance(market, AlphaVantageMarketData)

        # Verify it works (with rate limit handling)
        try:
            quote = market.quote("MSFT")
            assert isinstance(quote, Quote)
            assert quote.price > Decimal(0)
            print(f"✓ easy_market() auto-detect: MSFT @ ${quote.price}")
        except ValueError as e:
            if "No data returned" in str(e) or "rate limit" in str(e).lower():
                pytest.skip(f"Alpha Vantage API issue (likely rate limited): {e}")
            raise
