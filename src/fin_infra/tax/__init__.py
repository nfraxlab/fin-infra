"""Tax data integration (W-2, 1099-*, crypto tax calculations).

Providers for tax documents and cryptocurrency tax reporting:
- MockTaxProvider: Hardcoded sample data for testing (v1)
- IRSProvider: IRS e-Services for W-2/1099 transcripts (v2 - requires registration)
- TaxBitProvider: Crypto tax calculations (v2 - requires subscription)
- easy_tax(): One-liner to create configured tax provider
- add_tax_data(): FastAPI helper to wire tax routes

IRS Compliance:
- Retain tax documents for 7 years (use svc-infra RetentionPolicy)
- Provide accurate Form 8949 for crypto reporting
- Support GDPR/CCPA erasure after retention period

Cost Considerations:
- IRS e-Services: FREE (one-time setup ~$100, 6-8 weeks registration)
- TaxBit: $50-$200/month + $1-$5/user (~$10k-$50k/month for 10k users)
- Recommended: IRS for traditional forms, TaxBit for crypto (if budget allows)

Example:
    >>> from fin_infra.tax import easy_tax
    >>>
    >>> # Auto-detect: uses MockTaxProvider by default
    >>> tax = easy_tax()
    >>> documents = await tax.get_tax_documents("user123", 2024)
    >>>
    >>> # Explicit provider
    >>> tax = easy_tax(provider="mock")
    >>> w2 = [d for d in documents if d.form_type == "W2"][0]
    >>> print(w2.wages)  # 75000.00
"""

import os

from fin_infra.providers.base import TaxProvider
from fin_infra.providers.tax import MockTaxProvider, IRSProvider, TaxBitProvider
from fin_infra.tax.add import add_tax_data
from fin_infra.tax.tlh import (
    TLHOpportunity,
    TLHScenario,
    find_tlh_opportunities,
    simulate_tlh_scenario,
)


def easy_tax(provider: str | TaxProvider = "mock", **config) -> TaxProvider:
    """Create configured tax provider with environment variable auto-detection.

    Zero-config builder for tax document retrieval and crypto tax calculations.
    Automatically:
    - Uses MockTaxProvider by default (no API keys required)
    - Falls back to mock if IRS/TaxBit credentials not configured
    - Reads configuration from environment variables

    Args:
        provider: Tax provider name or TaxProvider instance
            - "mock" (default): Mock provider with hardcoded sample data
            - "irs": IRS e-Services (requires EFIN, TCC, certificates)
            - "taxbit": TaxBit crypto tax API (requires client credentials)
            - TaxProvider instance: Use directly
        **config: Optional configuration overrides
            - For IRS: efin, tcc, cert_path, key_path, base_url
            - For TaxBit: client_id, client_secret, base_url

    Returns:
        Configured TaxProvider instance

    Environment Variables:
        IRS_EFIN: Electronic Filing ID for IRS e-Services
        IRS_TCC: Transmitter Control Code for IRS
        IRS_CERT_PATH: Path to public certificate (.pem)
        IRS_KEY_PATH: Path to private key (.pem)
        IRS_BASE_URL: IRS API endpoint (default: production)

        TAXBIT_CLIENT_ID: OAuth client ID for TaxBit
        TAXBIT_CLIENT_SECRET: OAuth client secret for TaxBit
        TAXBIT_BASE_URL: TaxBit API endpoint (default: production)

    Examples:
        >>> # Auto-detect (uses MockTaxProvider by default)
        >>> tax = easy_tax()
        >>> docs = await tax.get_tax_documents("user123", 2024)

        >>> # Explicit mock provider
        >>> tax = easy_tax(provider="mock")
        >>>
        >>> # IRS provider (requires registration)
        >>> tax = easy_tax(
        ...     provider="irs",
        ...     efin=os.getenv("IRS_EFIN"),
        ...     tcc=os.getenv("IRS_TCC"),
        ...     cert_path="./irs_cert.pem",
        ...     key_path="./irs_key.pem"
        ... )
        >>> # Raises NotImplementedError (v2 not yet implemented)

        >>> # TaxBit provider (requires subscription)
        >>> tax = easy_tax(
        ...     provider="taxbit",
        ...     client_id=os.getenv("TAXBIT_CLIENT_ID"),
        ...     client_secret=os.getenv("TAXBIT_CLIENT_SECRET")
        ... )
        >>> # Raises NotImplementedError (v2 not yet implemented)

        >>> # Custom provider instance
        >>> from fin_infra.providers.tax import MockTaxProvider
        >>> custom_provider = MockTaxProvider()
        >>> tax = easy_tax(provider=custom_provider)
    """
    # If provider is already a TaxProvider instance, return it
    if isinstance(provider, TaxProvider):
        return provider

    # Provider factory
    provider_name = provider.lower() if isinstance(provider, str) else "mock"

    if provider_name == "mock":
        # Mock provider (v1 - default)
        return MockTaxProvider(**config)

    elif provider_name == "irs":
        # IRS e-Services provider (v2 - not yet implemented)
        # Extract credentials from config or env
        efin = config.pop("efin", os.getenv("IRS_EFIN"))
        tcc = config.pop("tcc", os.getenv("IRS_TCC"))
        cert_path = config.pop("cert_path", os.getenv("IRS_CERT_PATH"))
        key_path = config.pop("key_path", os.getenv("IRS_KEY_PATH"))
        base_url = config.pop("base_url", os.getenv("IRS_BASE_URL", "https://la.www4.irs.gov"))

        return IRSProvider(
            efin=efin, tcc=tcc, cert_path=cert_path, key_path=key_path, base_url=base_url, **config
        )

    elif provider_name == "taxbit":
        # TaxBit provider (v2 - not yet implemented)
        # Extract credentials from config or env
        client_id = config.pop("client_id", os.getenv("TAXBIT_CLIENT_ID"))
        client_secret = config.pop("client_secret", os.getenv("TAXBIT_CLIENT_SECRET"))
        base_url = config.pop("base_url", os.getenv("TAXBIT_BASE_URL", "https://api.taxbit.com"))

        return TaxBitProvider(
            client_id=client_id, client_secret=client_secret, base_url=base_url, **config
        )

    else:
        raise ValueError(
            f"Unknown tax provider: {provider}. " f"Supported providers: 'mock', 'irs', 'taxbit'"
        )


__all__ = [
    "easy_tax",
    "add_tax_data",
    "MockTaxProvider",
    "IRSProvider",
    "TaxBitProvider",
    # TLH exports
    "TLHOpportunity",
    "TLHScenario",
    "find_tlh_opportunities",
    "simulate_tlh_scenario",
]
