"""Symbol resolver for converting between ticker formats."""

import logging
from typing import Optional

from fin_infra.normalization.models import SymbolMetadata
from fin_infra.normalization.providers import (
    CUSIP_TO_TICKER,
    ISIN_TO_TICKER,
    PROVIDER_SYMBOL_MAP,
    TICKER_METADATA,
    TICKER_TO_CUSIP,
    TICKER_TO_ISIN,
)

logger = logging.getLogger(__name__)


class SymbolNotFoundError(Exception):
    """Symbol could not be resolved."""

    pass


class SymbolResolver:
    """
    Resolve and normalize financial symbols.

    Converts between different symbol formats:
    - Ticker symbols (AAPL, TSLA)
    - CUSIPs (037833100)
    - ISINs (US0378331005)
    - Provider-specific formats (BTC-USD, bitcoin, BTCUSD)
    """

    def __init__(self):
        """Initialize symbol resolver with static mappings."""
        # Use static mappings for common symbols (no API calls needed)
        self._ticker_to_cusip = TICKER_TO_CUSIP
        self._ticker_to_isin = TICKER_TO_ISIN
        self._cusip_to_ticker = CUSIP_TO_TICKER
        self._isin_to_ticker = ISIN_TO_TICKER
        self._provider_maps = PROVIDER_SYMBOL_MAP
        self._metadata_cache = TICKER_METADATA

    async def to_ticker(self, identifier: str) -> str:
        """
        Convert any identifier to ticker symbol.

        Args:
            identifier: CUSIP, ISIN, or ticker symbol

        Returns:
            Standard ticker symbol

        Raises:
            SymbolNotFoundError: If symbol cannot be resolved
        """
        # Already a ticker?
        if identifier.upper() in self._ticker_to_cusip:
            return identifier.upper()

        # CUSIP lookup
        if len(identifier) == 9 and identifier.isalnum():
            ticker = self._cusip_to_ticker.get(identifier)
            if ticker:
                return ticker

        # ISIN lookup
        if len(identifier) == 12 and identifier[:2].isalpha():
            ticker = self._isin_to_ticker.get(identifier)
            if ticker:
                return ticker

        # Exchange-qualified format (e.g., NASDAQ:AAPL)
        if ":" in identifier:
            _exchange, symbol = identifier.split(":", 1)
            return await self.to_ticker(symbol)

        # Provider-specific normalization
        # (but we don't know the provider here, so try common patterns)
        # Remove common separators
        clean = identifier.replace("-", "").replace("_", "").upper()
        if clean in self._ticker_to_cusip:
            return clean

        # Not found in static mappings
        logger.warning(f"Symbol {identifier} not found in resolver, returning as-is")
        return identifier.upper()

    async def to_cusip(self, ticker: str) -> str:
        """
        Convert ticker to CUSIP.

        Args:
            ticker: Ticker symbol

        Returns:
            CUSIP identifier

        Raises:
            SymbolNotFoundError: If CUSIP not found
        """
        cusip = self._ticker_to_cusip.get(ticker.upper())
        if not cusip:
            raise SymbolNotFoundError(f"CUSIP not found for ticker {ticker}")
        return cusip

    async def to_isin(self, ticker: str) -> str:
        """
        Convert ticker to ISIN.

        Args:
            ticker: Ticker symbol

        Returns:
            ISIN identifier

        Raises:
            SymbolNotFoundError: If ISIN not found
        """
        isin = self._ticker_to_isin.get(ticker.upper())
        if not isin:
            raise SymbolNotFoundError(f"ISIN not found for ticker {ticker}")
        return isin

    async def normalize(self, symbol: str, provider: str) -> str:
        """
        Normalize provider-specific symbol to standard ticker.

        Args:
            symbol: Provider-specific symbol (e.g., "BTC-USD", "bitcoin")
            provider: Provider name ("yahoo", "coingecko", "alpaca", etc.)

        Returns:
            Standard ticker symbol

        Examples:
            >>> await resolver.normalize("BTC-USD", "yahoo")
            "BTC"
            >>> await resolver.normalize("bitcoin", "coingecko")
            "BTC"
            >>> await resolver.normalize("BTCUSD", "alpaca")
            "BTC"
        """
        provider_lower = provider.lower()
        provider_map = self._provider_maps.get(provider_lower, {})

        # Direct mapping exists?
        normalized = provider_map.get(symbol)
        if normalized:
            return normalized

        # Try case-insensitive lookup
        normalized = provider_map.get(symbol.upper())
        if normalized:
            return normalized

        normalized = provider_map.get(symbol.lower())
        if normalized:
            return normalized

        # No provider-specific mapping, return as-is
        logger.debug(f"No provider mapping for {symbol} on {provider}, returning as-is")
        return symbol.upper()

    async def get_metadata(self, ticker: str) -> SymbolMetadata:
        """
        Get metadata for a ticker symbol.

        Args:
            ticker: Ticker symbol

        Returns:
            SymbolMetadata with company/asset information

        Raises:
            SymbolNotFoundError: If metadata not found
        """
        ticker_upper = ticker.upper()
        metadata = self._metadata_cache.get(ticker_upper)

        if not metadata:
            # Return minimal metadata
            logger.warning(f"Metadata not found for {ticker}, returning minimal info")
            return SymbolMetadata(
                ticker=ticker_upper,
                name=ticker_upper,
                exchange=None,
                cusip=self._ticker_to_cusip.get(ticker_upper),
                isin=self._ticker_to_isin.get(ticker_upper),
            )

        return SymbolMetadata(
            ticker=ticker_upper,
            name=metadata.get("name", ticker_upper),
            exchange=metadata.get("exchange"),
            cusip=self._ticker_to_cusip.get(ticker_upper),
            isin=self._ticker_to_isin.get(ticker_upper),
            sector=metadata.get("sector"),
            industry=metadata.get("industry"),
            asset_type=metadata.get("asset_type", "stock"),
        )

    async def resolve_batch(self, symbols: list[str]) -> dict[str, str]:
        """
        Batch resolve multiple symbols to tickers.

        Args:
            symbols: List of symbols to resolve

        Returns:
            Dictionary mapping input symbol to ticker

        Example:
            >>> await resolver.resolve_batch(["037833100", "US88160R1014", "AAPL"])
            {"037833100": "AAPL", "US88160R1014": "TSLA", "AAPL": "AAPL"}
        """
        results = {}
        for symbol in symbols:
            try:
                ticker = await self.to_ticker(symbol)
                results[symbol] = ticker
            except SymbolNotFoundError:
                logger.warning(f"Could not resolve {symbol} in batch operation")
                results[symbol] = symbol  # Return original

        return results

    def add_mapping(
        self,
        ticker: str,
        cusip: Optional[str] = None,
        isin: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Add or override a symbol mapping (useful for custom symbols).

        Args:
            ticker: Ticker symbol
            cusip: Optional CUSIP
            isin: Optional ISIN
            metadata: Optional metadata dict

        Example:
            >>> resolver.add_mapping("CUSTOM", cusip="123456789", metadata={
            ...     "name": "Custom Company",
            ...     "exchange": "NASDAQ"
            ... })
        """
        ticker_upper = ticker.upper()

        if cusip:
            self._ticker_to_cusip[ticker_upper] = cusip
            self._cusip_to_ticker[cusip] = ticker_upper

        if isin:
            self._ticker_to_isin[ticker_upper] = isin
            self._isin_to_ticker[isin] = ticker_upper

        if metadata:
            self._metadata_cache[ticker_upper] = metadata

        logger.info(f"Added custom mapping for {ticker_upper}")
