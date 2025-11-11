"""Currency converter using exchange rate APIs."""

import logging
from datetime import date as DateType
from typing import Optional

from fin_infra.normalization.models import CurrencyConversionResult
from fin_infra.normalization.providers.exchangerate import (
    ExchangeRateAPIError,
    ExchangeRateClient,
)

logger = logging.getLogger(__name__)


class CurrencyNotSupportedError(Exception):
    """Currency code not supported."""

    pass


class CurrencyConverter:
    """
    Convert amounts between currencies using live exchange rates.

    Uses exchangerate-api.io for rate data (1,500 requests/month free tier).
    Supports 160+ currencies including crypto (BTC, ETH).
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize currency converter.

        Args:
            api_key: Optional API key for exchangerate-api.io (paid tier)
        """
        self._client = ExchangeRateClient(api_key=api_key)

    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        date: Optional[DateType] = None,
    ) -> float:
        """
        Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "EUR")
            date: Optional date for historical rate (paid tier only)

        Returns:
            Converted amount

        Raises:
            CurrencyNotSupportedError: If currency not supported
            ExchangeRateAPIError: If API request fails

        Example:
            >>> await converter.convert(100, "USD", "EUR")
            92.0
        """
        # Same currency?
        if from_currency.upper() == to_currency.upper():
            return amount

        try:
            rate_data = await self._client.get_rate(from_currency, to_currency, date)
            return amount * rate_data.rate

        except ExchangeRateAPIError as e:
            logger.error(f"Failed to convert {from_currency} to {to_currency}: {e}")
            raise CurrencyNotSupportedError(
                f"Conversion failed: {from_currency} → {to_currency}"
            ) from e

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        date: Optional[DateType] = None,
    ) -> float:
        """
        Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            date: Optional date for historical rate (paid tier only)

        Returns:
            Exchange rate (1 from_currency = rate to_currency)

        Raises:
            CurrencyNotSupportedError: If currency not supported
            ExchangeRateAPIError: If API request fails

        Example:
            >>> await converter.get_rate("USD", "EUR")
            0.92
        """
        # Same currency?
        if from_currency.upper() == to_currency.upper():
            return 1.0

        try:
            rate_data = await self._client.get_rate(from_currency, to_currency, date)
            return rate_data.rate

        except ExchangeRateAPIError as e:
            logger.error(f"Failed to get rate {from_currency} → {to_currency}: {e}")
            raise CurrencyNotSupportedError(
                f"Rate not available: {from_currency} → {to_currency}"
            ) from e

    async def get_rates(self, base_currency: str = "USD") -> dict[str, float]:
        """
        Get all exchange rates for a base currency.

        Args:
            base_currency: Base currency code (default: USD)

        Returns:
            Dictionary of currency codes to exchange rates

        Raises:
            ExchangeRateAPIError: If API request fails

        Example:
            >>> await converter.get_rates("USD")
            {"EUR": 0.92, "GBP": 0.79, "JPY": 149.50, ...}
        """
        try:
            return await self._client.get_rates(base_currency)
        except ExchangeRateAPIError as e:
            logger.error(f"Failed to get rates for {base_currency}: {e}")
            raise

    async def convert_with_details(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        date: Optional[DateType] = None,
    ) -> CurrencyConversionResult:
        """
        Convert amount with detailed result information.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            date: Optional date for historical rate

        Returns:
            CurrencyConversionResult with amount, rate, and metadata

        Example:
            >>> result = await converter.convert_with_details(100, "USD", "EUR")
            >>> result.converted
            92.0
            >>> result.rate
            0.92
        """
        rate = await self.get_rate(from_currency, to_currency, date)
        converted = amount * rate

        return CurrencyConversionResult(
            amount=amount,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            converted=converted,
            rate=rate,
            date=date,
        )

    async def supported_currencies(self) -> list[str]:
        """
        Get list of supported currency codes.

        Returns:
            List of ISO 4217 currency codes

        Raises:
            ExchangeRateAPIError: If API request fails

        Example:
            >>> await converter.supported_currencies()
            ["USD", "EUR", "GBP", "JPY", "CAD", ...]
        """
        try:
            return await self._client.supported_currencies()
        except ExchangeRateAPIError as e:
            logger.error(f"Failed to get supported currencies: {e}")
            raise

    async def batch_convert(
        self,
        amounts: dict[str, float],
        to_currency: str,
    ) -> dict[str, float]:
        """
        Convert multiple amounts to a single target currency.

        Args:
            amounts: Dictionary of currency code to amount
            to_currency: Target currency code

        Returns:
            Dictionary of currency code to converted amount

        Example:
            >>> amounts = {"USD": 100, "EUR": 90, "GBP": 80}
            >>> await converter.batch_convert(amounts, "USD")
            {"USD": 100.0, "EUR": 97.8, "GBP": 101.3}
        """
        results = {}
        for from_currency, amount in amounts.items():
            try:
                converted = await self.convert(amount, from_currency, to_currency)
                results[from_currency] = converted
            except (CurrencyNotSupportedError, ExchangeRateAPIError) as e:
                logger.warning(f"Failed to convert {from_currency} to {to_currency}: {e}")
                results[from_currency] = amount  # Return original on error

        return results
