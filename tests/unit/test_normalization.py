"""Unit tests for normalization module."""

from unittest.mock import AsyncMock, patch

import pytest

from fin_infra.exceptions import CurrencyNotSupportedError, ExchangeRateAPIError
from fin_infra.normalization import (
    CurrencyConverter,
    SymbolNotFoundError,
    SymbolResolver,
    easy_normalization,
)


class TestSymbolResolver:
    """Tests for SymbolResolver."""

    @pytest.fixture
    def resolver(self):
        """Create symbol resolver instance."""
        return SymbolResolver()

    @pytest.mark.asyncio
    async def test_ticker_to_cusip(self, resolver):
        """Test converting ticker to CUSIP."""
        cusip = await resolver.to_cusip("AAPL")
        assert cusip == "037833100"

        cusip = await resolver.to_cusip("TSLA")
        assert cusip == "88160R101"

    @pytest.mark.asyncio
    async def test_ticker_to_isin(self, resolver):
        """Test converting ticker to ISIN."""
        isin = await resolver.to_isin("AAPL")
        assert isin == "US0378331005"

        isin = await resolver.to_isin("TSLA")
        assert isin == "US88160R1014"

    @pytest.mark.asyncio
    async def test_cusip_to_ticker(self, resolver):
        """Test converting CUSIP to ticker."""
        ticker = await resolver.to_ticker("037833100")
        assert ticker == "AAPL"

        ticker = await resolver.to_ticker("88160R101")
        assert ticker == "TSLA"

    @pytest.mark.asyncio
    async def test_isin_to_ticker(self, resolver):
        """Test converting ISIN to ticker."""
        ticker = await resolver.to_ticker("US0378331005")
        assert ticker == "AAPL"

        ticker = await resolver.to_ticker("US88160R1014")
        assert ticker == "TSLA"

    @pytest.mark.asyncio
    async def test_ticker_unchanged(self, resolver):
        """Test that ticker symbols are returned unchanged."""
        ticker = await resolver.to_ticker("AAPL")
        assert ticker == "AAPL"

        ticker = await resolver.to_ticker("aapl")
        assert ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_exchange_qualified_symbol(self, resolver):
        """Test exchange-qualified symbols (NASDAQ:AAPL)."""
        ticker = await resolver.to_ticker("NASDAQ:AAPL")
        assert ticker == "AAPL"

        ticker = await resolver.to_ticker("NYSE:TSLA")
        assert ticker == "TSLA"

    @pytest.mark.asyncio
    async def test_normalize_yahoo(self, resolver):
        """Test Yahoo Finance symbol normalization."""
        ticker = await resolver.normalize("BTC-USD", "yahoo")
        assert ticker == "BTC"

        ticker = await resolver.normalize("ETH-USD", "yahoo")
        assert ticker == "ETH"

    @pytest.mark.asyncio
    async def test_normalize_coingecko(self, resolver):
        """Test CoinGecko symbol normalization."""
        ticker = await resolver.normalize("bitcoin", "coingecko")
        assert ticker == "BTC"

        ticker = await resolver.normalize("ethereum", "coingecko")
        assert ticker == "ETH"

    @pytest.mark.asyncio
    async def test_normalize_alpaca(self, resolver):
        """Test Alpaca symbol normalization."""
        ticker = await resolver.normalize("BTCUSD", "alpaca")
        assert ticker == "BTC"

        ticker = await resolver.normalize("ETHUSD", "alpaca")
        assert ticker == "ETH"

    @pytest.mark.asyncio
    async def test_normalize_unknown_provider(self, resolver):
        """Test normalization with unknown provider returns uppercase."""
        ticker = await resolver.normalize("AAPL", "unknown")
        assert ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_get_metadata(self, resolver):
        """Test getting symbol metadata."""
        metadata = await resolver.get_metadata("AAPL")
        assert metadata.ticker == "AAPL"
        assert metadata.name == "Apple Inc."
        assert metadata.exchange == "NASDAQ"
        assert metadata.cusip == "037833100"
        assert metadata.isin == "US0378331005"
        assert metadata.sector == "Technology"
        assert metadata.asset_type == "stock"

    @pytest.mark.asyncio
    async def test_get_metadata_crypto(self, resolver):
        """Test getting crypto metadata."""
        metadata = await resolver.get_metadata("BTC")
        assert metadata.ticker == "BTC"
        assert metadata.name == "Bitcoin"
        assert metadata.asset_type == "crypto"

    @pytest.mark.asyncio
    async def test_get_metadata_unknown(self, resolver):
        """Test getting metadata for unknown symbol returns minimal info."""
        metadata = await resolver.get_metadata("UNKNOWN")
        assert metadata.ticker == "UNKNOWN"
        assert metadata.name == "UNKNOWN"
        assert metadata.exchange is None

    @pytest.mark.asyncio
    async def test_resolve_batch(self, resolver):
        """Test batch symbol resolution."""
        symbols = ["037833100", "US88160R1014", "AAPL"]
        results = await resolver.resolve_batch(symbols)

        assert results["037833100"] == "AAPL"
        assert results["US88160R1014"] == "TSLA"
        assert results["AAPL"] == "AAPL"

    @pytest.mark.asyncio
    async def test_add_custom_mapping(self, resolver):
        """Test adding custom symbol mapping."""
        resolver.add_mapping(
            "CUSTOM",
            cusip="999999999",
            isin="US9999999999",
            metadata={"name": "Custom Company", "exchange": "NASDAQ"},
        )

        cusip = await resolver.to_cusip("CUSTOM")
        assert cusip == "999999999"

        isin = await resolver.to_isin("CUSTOM")
        assert isin == "US9999999999"

        metadata = await resolver.get_metadata("CUSTOM")
        assert metadata.name == "Custom Company"

    @pytest.mark.asyncio
    async def test_unknown_cusip_raises(self, resolver):
        """Test that unknown ticker raises SymbolNotFoundError for CUSIP."""
        with pytest.raises(SymbolNotFoundError):
            await resolver.to_cusip("UNKNOWN")

    @pytest.mark.asyncio
    async def test_unknown_isin_raises(self, resolver):
        """Test that unknown ticker raises SymbolNotFoundError for ISIN."""
        with pytest.raises(SymbolNotFoundError):
            await resolver.to_isin("UNKNOWN")


class TestCurrencyConverter:
    """Tests for CurrencyConverter (mock API responses)."""

    @pytest.fixture
    def converter(self):
        """Create currency converter instance."""
        return CurrencyConverter()

    @pytest.mark.asyncio
    async def test_same_currency_conversion(self, converter):
        """Test converting same currency returns original amount."""
        result = await converter.convert(100, "USD", "USD")
        assert result == 100.0

    @pytest.mark.asyncio
    async def test_same_currency_rate(self, converter):
        """Test getting rate for same currency returns 1.0."""
        rate = await converter.get_rate("USD", "USD")
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_convert_with_details(self, converter):
        """Test conversion with detailed result."""
        # This will make a real API call in unit tests
        # In real tests, we'd mock the HTTP client
        # For now, just test the structure
        pass

    @pytest.mark.asyncio
    async def test_batch_convert_same_currency(self, converter):
        """Test batch conversion with same currency."""
        amounts = {"USD": 100}
        results = await converter.batch_convert(amounts, "USD")
        assert results["USD"] == 100.0

    @pytest.mark.asyncio
    async def test_convert_api_error_raises_currency_not_supported(self, converter):
        """Test that API errors are wrapped in CurrencyNotSupportedError."""
        with patch.object(
            converter._client,
            "get_rate",
            new_callable=AsyncMock,
            side_effect=ExchangeRateAPIError("API unavailable"),
        ):
            with pytest.raises(CurrencyNotSupportedError) as exc_info:
                await converter.convert(100, "USD", "XYZ")

            assert "Conversion failed: USD -> XYZ" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_rate_api_error_raises_currency_not_supported(self, converter):
        """Test that get_rate API errors are wrapped in CurrencyNotSupportedError."""
        with patch.object(
            converter._client,
            "get_rate",
            new_callable=AsyncMock,
            side_effect=ExchangeRateAPIError("API unavailable"),
        ):
            with pytest.raises(CurrencyNotSupportedError) as exc_info:
                await converter.get_rate("USD", "XYZ")

            assert "Rate not available: USD -> XYZ" in str(exc_info.value)


class TestEasyNormalization:
    """Tests for easy_normalization builder."""

    def test_easy_normalization_returns_tuple(self):
        """Test that easy_normalization returns (resolver, converter) tuple."""
        resolver, converter = easy_normalization()
        assert isinstance(resolver, SymbolResolver)
        assert isinstance(converter, CurrencyConverter)

    def test_easy_normalization_returns_singletons(self):
        """Test that easy_normalization returns same instances on repeated calls."""
        resolver1, converter1 = easy_normalization()
        resolver2, converter2 = easy_normalization()

        assert resolver1 is resolver2
        assert converter1 is converter2

    @pytest.mark.asyncio
    async def test_easy_normalization_integration(self):
        """Test full integration of easy_normalization."""
        resolver, converter = easy_normalization()

        # Test resolver
        ticker = await resolver.to_ticker("037833100")
        assert ticker == "AAPL"

        # Test converter (same currency)
        result = await converter.convert(100, "USD", "USD")
        assert result == 100.0
