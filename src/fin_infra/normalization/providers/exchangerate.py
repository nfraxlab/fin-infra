"""Exchange rate API client for exchangerate-api.io."""

import os
from datetime import date as DateType
from typing import Optional

import httpx

from fin_infra.normalization.models import ExchangeRate


class ExchangeRateAPIError(Exception):
    """Exchange rate API error."""

    pass


class ExchangeRateClient:
    """Client for exchangerate-api.io API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize exchange rate client.

        Args:
            api_key: API key (optional, uses env var EXCHANGE_RATE_API_KEY if not provided)
        """
        self.api_key = api_key or os.getenv("EXCHANGE_RATE_API_KEY")

        # Free tier: 1,500 requests/month without API key
        # Paid tier: Higher limits with API key
        if self.api_key:
            self.base_url = f"https://v6.exchangerate-api.com/v6/{self.api_key}"
        else:
            # Free tier URL
            self.base_url = "https://api.exchangerate-api.com/v4/latest"

    async def get_rates(self, base_currency: str = "USD") -> dict[str, float]:
        """
        Get all exchange rates for a base currency.

        Args:
            base_currency: Base currency code (e.g., "USD")

        Returns:
            Dictionary of currency codes to exchange rates

        Raises:
            ExchangeRateAPIError: If API request fails
        """
        try:
            if self.api_key:
                url = f"{self.base_url}/latest/{base_currency}"
            else:
                url = f"{self.base_url}/{base_currency}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if self.api_key:
                    # Paid tier response format
                    if data.get("result") != "success":
                        raise ExchangeRateAPIError(
                            f"API returned error: {data.get('error-type', 'unknown')}"
                        )
                    return data["conversion_rates"]
                else:
                    # Free tier response format
                    return data["rates"]

        except httpx.HTTPError as e:
            raise ExchangeRateAPIError(f"HTTP error fetching rates: {e}")
        except (KeyError, ValueError) as e:
            raise ExchangeRateAPIError(f"Invalid API response: {e}")

    async def get_rate(
        self, from_currency: str, to_currency: str, date: Optional[DateType] = None
    ) -> ExchangeRate:
        """
        Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            date: Optional date for historical rate (paid tier only)

        Returns:
            ExchangeRate object

        Raises:
            ExchangeRateAPIError: If API request fails
        """
        if date and not self.api_key:
            raise ExchangeRateAPIError("Historical rates require API key (paid tier)")

        try:
            if date and self.api_key:
                # Historical rate (paid tier only)
                date_str = date.strftime("%Y-%m-%d")
                url = f"{self.base_url}/history/{from_currency}/{date_str}"

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("result") != "success":
                        raise ExchangeRateAPIError(
                            f"API returned error: {data.get('error-type', 'unknown')}"
                        )

                    rate = data["conversion_rates"].get(to_currency)
                    if rate is None:
                        raise ExchangeRateAPIError(f"Currency {to_currency} not found in response")

                    return ExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                        date=date,
                    )
            else:
                # Current rate
                rates = await self.get_rates(from_currency)
                rate = rates.get(to_currency)

                if rate is None:
                    raise ExchangeRateAPIError(f"Currency {to_currency} not supported")

                return ExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    date=None,
                )

        except httpx.HTTPError as e:
            raise ExchangeRateAPIError(f"HTTP error fetching rate: {e}")
        except (KeyError, ValueError) as e:
            raise ExchangeRateAPIError(f"Invalid API response: {e}")

    async def supported_currencies(self) -> list[str]:
        """
        Get list of supported currency codes.

        Returns:
            List of ISO 4217 currency codes

        Raises:
            ExchangeRateAPIError: If API request fails
        """
        try:
            if self.api_key:
                url = f"{self.base_url}/codes"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("result") != "success":
                        raise ExchangeRateAPIError(
                            f"API returned error: {data.get('error-type', 'unknown')}"
                        )

                    # Returns list of [code, name] pairs
                    return [code for code, _name in data["supported_codes"]]
            else:
                # Free tier: get currencies from rates endpoint
                rates = await self.get_rates("USD")
                return list(rates.keys())

        except httpx.HTTPError as e:
            raise ExchangeRateAPIError(f"HTTP error fetching currencies: {e}")
        except (KeyError, ValueError) as e:
            raise ExchangeRateAPIError(f"Invalid API response: {e}")
