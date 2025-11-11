"""
Provider registry for dynamic provider loading and configuration.

Supports:
- Dynamic import of providers by domain:name (e.g., "banking:plaid")
- Configuration via YAML or environment variables
- Fallback chains for provider selection
- Feature flags for provider switching
"""

from __future__ import annotations

import importlib
from typing import Any, TypeVar

from .base import (
    BankingProvider,
    BrokerageProvider,
    CreditProvider,
    CryptoDataProvider,
    IdentityProvider,
    MarketDataProvider,
    TaxProvider,
)

T = TypeVar("T")

# Provider domain to ABC mapping
PROVIDER_TYPES = {
    "banking": BankingProvider,
    "brokerage": BrokerageProvider,
    "credit": CreditProvider,
    "crypto": CryptoDataProvider,
    "identity": IdentityProvider,
    "market": MarketDataProvider,
    "tax": TaxProvider,
}

# Provider name to module path mapping
PROVIDER_MODULES = {
    # Banking providers
    "banking:plaid": "fin_infra.providers.banking.plaid_client",
    "banking:teller": "fin_infra.providers.banking.teller_client",
    "banking:mx": "fin_infra.providers.banking.mx_client",
    # Market data providers
    "market:alphavantage": "fin_infra.providers.market.alpha_vantage",
    "market:yahoo": "fin_infra.providers.market.yahoo",
    "market:polygon": "fin_infra.providers.market.polygon",
    # Crypto providers
    "crypto:coingecko": "fin_infra.providers.market.coingecko",
    "crypto:ccxt": "fin_infra.providers.market.ccxt_crypto",
    "crypto:cryptocompare": "fin_infra.providers.market.cryptocompare",
    # Brokerage providers
    "brokerage:alpaca": "fin_infra.providers.brokerage.alpaca",
    "brokerage:ib": "fin_infra.providers.brokerage.interactive_brokers",
    "brokerage:tdameritrade": "fin_infra.providers.brokerage.td_ameritrade",
    # Credit providers
    "credit:experian": "fin_infra.providers.credit.experian",
    "credit:equifax": "fin_infra.providers.credit.equifax",
    "credit:transunion": "fin_infra.providers.credit.transunion",
    # Identity providers
    "identity:stripe": "fin_infra.providers.identity.stripe_identity",
    # Tax providers
    "tax:taxbit": "fin_infra.providers.tax.taxbit",
    "tax:irs": "fin_infra.providers.tax.irs",
}

# Default providers for each domain
DEFAULT_PROVIDERS = {
    "banking": "teller",  # Changed to Teller (free tier, simpler auth)
    "market": "alphavantage",
    "crypto": "coingecko",
    "brokerage": "alpaca",
    "credit": "experian",
    "identity": "stripe",
    "tax": "taxbit",
}


class ProviderNotFoundError(Exception):
    """Raised when a provider cannot be found or loaded."""

    pass


class ProviderRegistry:
    """
    Registry for financial data providers.

    Provides dynamic loading and configuration of providers.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def resolve(self, domain: str, name: str | None = None, **config) -> Any:
        """
        Resolve and instantiate a provider.

        Args:
            domain: Provider domain (e.g., 'banking', 'market', 'crypto')
            name: Provider name (e.g., 'plaid', 'alphavantage'). If None, uses default.
            **config: Configuration passed to provider constructor

        Returns:
            Configured provider instance

        Raises:
            ProviderNotFoundError: If provider cannot be loaded

        Examples:
            >>> registry = ProviderRegistry()
            >>> banking = registry.resolve("banking", "plaid", client_id="...", secret="...")
            >>> market = registry.resolve("market", "yahoo")  # uses free tier
            >>> crypto = registry.resolve("crypto")  # uses default (coingecko)
        """
        # Use default provider if name not specified
        if name is None:
            name = DEFAULT_PROVIDERS.get(domain)
            if name is None:
                raise ProviderNotFoundError(f"No default provider configured for domain '{domain}'")

        # Check cache
        cache_key = f"{domain}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get provider module path
        module_path = PROVIDER_MODULES.get(cache_key)
        if module_path is None:
            raise ProviderNotFoundError(
                f"Provider '{cache_key}' not found in registry. "
                f"Available: {list(PROVIDER_MODULES.keys())}"
            )

        # Dynamically import provider
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ProviderNotFoundError(
                f"Failed to import provider '{cache_key}' from '{module_path}': {e}"
            ) from e

        # Get provider class (convention: TitleCaseProvider)
        # e.g., plaid_client -> PlaidClient, alpha_vantage -> AlphaVantageProvider
        class_name = self._module_to_class_name(module_path)
        provider_class = getattr(module, class_name, None)

        if provider_class is None:
            raise ProviderNotFoundError(
                f"Provider class '{class_name}' not found in module '{module_path}'"
            )

        # Validate provider implements correct interface
        expected_type = PROVIDER_TYPES.get(domain)
        if expected_type and not issubclass(provider_class, expected_type):
            raise ProviderNotFoundError(
                f"Provider '{cache_key}' does not implement {expected_type.__name__}"
            )

        # Instantiate provider with config
        try:
            instance = provider_class(**config)
        except Exception as e:
            raise ProviderNotFoundError(f"Failed to instantiate provider '{cache_key}': {e}") from e

        # Cache instance
        self._cache[cache_key] = instance
        return instance

    def _module_to_class_name(self, module_path: str) -> str:
        """
        Convert module path to expected class name.

        Examples:
            fin_infra.providers.banking.plaid_client -> PlaidClient
            fin_infra.providers.market.alpha_vantage -> AlphaVantageProvider
        """
        # Get last part of module path
        module_name = module_path.split(".")[-1]

        # Convert snake_case to TitleCase
        parts = module_name.split("_")
        class_name = "".join(part.capitalize() for part in parts)

        # Add Provider suffix if not already present
        if not class_name.endswith("Provider") and not class_name.endswith("Client"):
            # Try common patterns
            if class_name.endswith("Client"):
                return class_name
            # Default to Provider suffix
            return f"{class_name}Provider"

        return class_name

    def list_providers(self, domain: str | None = None) -> list[str]:
        """
        List available providers.

        Args:
            domain: Optional domain filter (e.g., 'banking', 'market')

        Returns:
            List of provider keys (e.g., ['banking:plaid', 'banking:teller'])
        """
        if domain:
            return [k for k in PROVIDER_MODULES.keys() if k.startswith(f"{domain}:")]
        return list(PROVIDER_MODULES.keys())

    def clear_cache(self):
        """Clear provider instance cache."""
        self._cache.clear()


# Global registry instance
_registry = ProviderRegistry()


def resolve(domain: str, name: str | None = None, **config) -> Any:
    """
    Resolve and instantiate a provider using the global registry.

    Convenience function for the global registry.

    Args:
        domain: Provider domain (e.g., 'banking', 'market')
        name: Provider name (e.g., 'plaid', 'alphavantage'). If None, uses default.
        **config: Configuration passed to provider constructor

    Returns:
        Configured provider instance

    Examples:
        >>> from fin_infra.providers import resolve
        >>> banking = resolve("banking", "plaid", client_id="...", secret="...")
        >>> market = resolve("market")  # uses default (alphavantage)
    """
    return _registry.resolve(domain, name, **config)


def list_providers(domain: str | None = None) -> list[str]:
    """
    List available providers.

    Args:
        domain: Optional domain filter

    Returns:
        List of provider keys
    """
    return _registry.list_providers(domain)
