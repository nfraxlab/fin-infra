"""TaxBit provider for cryptocurrency tax calculations.

Provides Form 8949, 1099-B, and crypto capital gains reports.

**IMPORTANT**: Requires paid TaxBit subscription:
- Pricing: $50-$200/month base + $1-$5/user
- 10,000 users: ~$10,000-$50,000/month
- OAuth 2.0 authentication
- Rate limit: 100 requests/minute

See: https://taxbit.com/products/api

Alternative: Use IRS provider for traditional forms (free)

Example:
    >>> from fin_infra.providers.tax.taxbit import TaxBitProvider
    >>> provider = TaxBitProvider(client_id="...", client_secret="...")
    >>> # NotImplementedError: TaxBit requires paid subscription
"""

from decimal import Decimal

from fin_infra.models.tax import (
    TaxDocument,
    CryptoTaxReport,
    TaxLiability,
)
from fin_infra.providers.base import TaxProvider


class TaxBitProvider(TaxProvider):
    """TaxBit provider for crypto tax calculations (v2 - not yet implemented).

    **Subscription Required**:
    - Base fee: $50-$200/month
    - Per-user fee: $1-$5/user
    - Total cost: $10k-$50k/month for 10,000 users

    **Authentication**:
    - OAuth 2.0 with client credentials
    - Access token refresh every 24 hours
    - Rate limit: 100 requests/minute

    **Environment Variables**:
    - TAXBIT_CLIENT_ID: OAuth client ID
    - TAXBIT_CLIENT_SECRET: OAuth client secret
    - TAXBIT_BASE_URL: API endpoint (default: https://api.taxbit.com)

    **Supported Features**:
    - Form 8949: Sales and Other Dispositions of Capital Assets
    - 1099-B: Proceeds from Broker Transactions (crypto)
    - 1099-MISC: Staking rewards, airdrops
    - Capital gains/losses calculation (FIFO, LIFO, HIFO)
    - Cost basis tracking

    **Not Supported**:
    - Traditional tax forms (W-2, 1099-INT/DIV) - use IRS provider

    Example:
        >>> provider = TaxBitProvider(
        ...     client_id=os.getenv("TAXBIT_CLIENT_ID"),
        ...     client_secret=os.getenv("TAXBIT_CLIENT_SECRET")
        ... )
        >>> # Raises NotImplementedError until v2 implementation
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = "https://api.taxbit.com",
        **kwargs,
    ):
        """Initialize TaxBit provider.

        Args:
            client_id: OAuth client ID (required)
            client_secret: OAuth client secret (required)
            base_url: TaxBit API endpoint (default: production)
            **kwargs: Additional configuration

        Raises:
            NotImplementedError: TaxBit provider not yet implemented (v2)
        """
        raise NotImplementedError(
            "TaxBit provider requires paid subscription ($50-$200/month + $1-$5/user). "
            "Visit https://taxbit.com/products/api for pricing. "
            "Use MockTaxProvider for testing or IRS for traditional forms (free)."
        )

    async def get_tax_forms(self, user_id: str, tax_year: int, **kwargs) -> list[dict]:
        """Not implemented (v2)."""
        raise NotImplementedError("TaxBit provider not yet implemented")

    async def get_tax_documents(self, user_id: str, tax_year: int, **kwargs) -> list[TaxDocument]:
        """Not implemented (v2)."""
        raise NotImplementedError("TaxBit provider not yet implemented")

    async def get_tax_document(self, document_id: str, **kwargs) -> TaxDocument:
        """Not implemented (v2)."""
        raise NotImplementedError("TaxBit provider not yet implemented")

    async def download_document(self, document_id: str, **kwargs) -> bytes:
        """Not implemented (v2)."""
        raise NotImplementedError("TaxBit provider not yet implemented")

    async def calculate_crypto_gains(
        self, user_id: str, transactions: list[dict], tax_year: int, **kwargs
    ) -> CryptoTaxReport:
        """Not implemented (v2)."""
        raise NotImplementedError("TaxBit provider not yet implemented")

    async def calculate_tax_liability(
        self,
        user_id: str,
        income: Decimal,
        deductions: Decimal,
        filing_status: str,
        tax_year: int,
        **kwargs,
    ) -> TaxLiability:
        """Not implemented (v2)."""
        raise NotImplementedError("TaxBit provider not yet implemented")


__all__ = ["TaxBitProvider"]
