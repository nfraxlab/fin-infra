"""IRS e-Services provider for tax document retrieval.

Provides access to W-2 and 1099 transcripts via IRS e-Services API.

**IMPORTANT**: Requires IRS e-Services registration (6-8 weeks):
1. Apply for EFIN (Electronic Filing Identification Number)
2. Obtain TCC (Transmitter Control Code)
3. Get PKI certificates (public/private key pair)
4. Complete IP whitelist registration
5. Wait for IRS approval (6-8 weeks)

See: https://www.irs.gov/e-file-providers/e-services

Cost: FREE (one-time setup fee ~$100 for certificates)

Example:
    >>> from fin_infra.providers.tax.irs import IRSProvider
    >>> provider = IRSProvider(efin="...", tcc="...", cert_path="...")
    >>> # NotImplementedError: IRS e-Services requires 6-8 week registration
"""

from decimal import Decimal

from fin_infra.models.tax import (
    TaxDocument,
    CryptoTaxReport,
    TaxLiability,
)
from fin_infra.providers.base import TaxProvider


class IRSProvider(TaxProvider):
    """IRS e-Services provider (v2 - not yet implemented).

    **Registration Required**:
    - EFIN (Electronic Filing Identification Number)
    - TCC (Transmitter Control Code)
    - PKI certificates (cert + key files)
    - IP whitelist approval from IRS
    - 6-8 weeks processing time

    **Environment Variables**:
    - IRS_EFIN: Electronic Filing ID
    - IRS_TCC: Transmitter Control Code
    - IRS_CERT_PATH: Path to public certificate (.pem)
    - IRS_KEY_PATH: Path to private key (.pem)
    - IRS_BASE_URL: API endpoint (default: https://la.www4.irs.gov)

    **Supported Forms**:
    - W-2: Wage and Tax Statement
    - 1099-INT: Interest Income
    - 1099-DIV: Dividends
    - 1099-MISC: Miscellaneous Income
    - 1099-B: Broker Transactions (limited)

    **Not Supported**:
    - Crypto tax calculations (use TaxBit provider)
    - Real-time document retrieval (IRS has delays)

    Example:
        >>> provider = IRSProvider(
        ...     efin=os.getenv("IRS_EFIN"),
        ...     tcc=os.getenv("IRS_TCC"),
        ...     cert_path=os.getenv("IRS_CERT_PATH"),
        ...     key_path=os.getenv("IRS_KEY_PATH")
        ... )
        >>> # Raises NotImplementedError until v2 implementation
    """

    def __init__(
        self,
        efin: str | None = None,
        tcc: str | None = None,
        cert_path: str | None = None,
        key_path: str | None = None,
        base_url: str = "https://la.www4.irs.gov",
        **kwargs,
    ):
        """Initialize IRS provider.

        Args:
            efin: Electronic Filing ID (required)
            tcc: Transmitter Control Code (required)
            cert_path: Path to public certificate .pem file (required)
            key_path: Path to private key .pem file (required)
            base_url: IRS API endpoint (default: production)
            **kwargs: Additional configuration

        Raises:
            NotImplementedError: IRS provider not yet implemented (v2)
        """
        raise NotImplementedError(
            "IRS e-Services provider requires registration (6-8 weeks). "
            "Visit https://www.irs.gov/e-file-providers/e-services to apply. "
            "Use MockTaxProvider for testing or TaxBit for production."
        )

    async def get_tax_forms(self, user_id: str, tax_year: int, **kwargs) -> list[dict]:
        """Not implemented (v2)."""
        raise NotImplementedError("IRS provider not yet implemented")

    async def get_tax_documents(self, user_id: str, tax_year: int, **kwargs) -> list[TaxDocument]:
        """Not implemented (v2)."""
        raise NotImplementedError("IRS provider not yet implemented")

    async def get_tax_document(self, document_id: str, **kwargs) -> TaxDocument:
        """Not implemented (v2)."""
        raise NotImplementedError("IRS provider not yet implemented")

    async def download_document(self, document_id: str, **kwargs) -> bytes:
        """Not implemented (v2)."""
        raise NotImplementedError("IRS provider not yet implemented")

    async def calculate_crypto_gains(
        self, user_id: str, transactions: list[dict], tax_year: int, **kwargs
    ) -> CryptoTaxReport:
        """Not supported by IRS (use TaxBit provider)."""
        raise NotImplementedError(
            "IRS e-Services does not provide crypto tax calculations. "
            "Use TaxBit provider for crypto gains/losses."
        )

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
        raise NotImplementedError("IRS provider not yet implemented")


__all__ = ["IRSProvider"]
