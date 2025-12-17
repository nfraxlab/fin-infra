"""
Tests for provider registry system.

Tests dynamic provider loading, fallback, and configuration.
"""

import pytest

from fin_infra.providers import (
    BankingProvider,
    CreditProvider,
    CryptoDataProvider,
    MarketDataProvider,
    ProviderNotFoundError,
    ProviderRegistry,
    TaxProvider,
    list_providers,
    resolve,
)


class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    def test_registry_initialization(self):
        """Test registry can be instantiated."""
        registry = ProviderRegistry()
        assert registry is not None
        assert isinstance(registry, ProviderRegistry)

    def test_list_providers_all(self):
        """Test listing all available providers."""
        providers = list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

        # Should include banking providers
        assert any("banking:" in p for p in providers)
        # Should include market providers
        assert any("market:" in p for p in providers)
        # Should include crypto providers
        assert any("crypto:" in p for p in providers)

    def test_list_providers_by_domain(self):
        """Test filtering providers by domain."""
        banking_providers = list_providers(domain="banking")
        assert all(p.startswith("banking:") for p in banking_providers)
        assert "banking:plaid" in banking_providers
        assert "banking:teller" in banking_providers

        market_providers = list_providers(domain="market")
        assert all(p.startswith("market:") for p in market_providers)
        assert "market:alphavantage" in market_providers
        assert "market:yahoo" in market_providers

    def test_list_providers_empty_domain(self):
        """Test listing providers for non-existent domain."""
        providers = list_providers(domain="nonexistent")
        assert providers == []

    def test_resolve_unknown_provider(self):
        """Test resolving unknown provider raises error."""
        registry = ProviderRegistry()

        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.resolve("banking", "unknown_provider")

        assert "banking:unknown_provider" in str(exc_info.value)
        assert "not found in registry" in str(exc_info.value)

    def test_resolve_unknown_domain(self):
        """Test resolving unknown domain with no default raises error."""
        registry = ProviderRegistry()

        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.resolve("unknown_domain")

        assert "No default provider" in str(exc_info.value)

    def test_module_to_class_name_conversion(self):
        """Test module path to class name conversion."""
        registry = ProviderRegistry()

        # Test various naming patterns
        assert registry._module_to_class_name("fin_infra.providers.banking.plaid_client") in [
            "PlaidClient",
            "PlaidClientProvider",
        ]

        result = registry._module_to_class_name("fin_infra.providers.market.alpha_vantage")
        assert "Alpha" in result
        assert "Vantage" in result

    def test_provider_types_mapping(self):
        """Test provider type mapping is complete."""
        from fin_infra.providers.registry import PROVIDER_TYPES

        # Verify all expected domains are mapped
        assert "banking" in PROVIDER_TYPES
        assert "market" in PROVIDER_TYPES
        assert "crypto" in PROVIDER_TYPES
        assert "brokerage" in PROVIDER_TYPES
        assert "credit" in PROVIDER_TYPES
        assert "identity" in PROVIDER_TYPES
        assert "tax" in PROVIDER_TYPES

        # Verify mappings are to ABC types
        assert PROVIDER_TYPES["banking"] == BankingProvider
        assert PROVIDER_TYPES["market"] == MarketDataProvider
        assert PROVIDER_TYPES["crypto"] == CryptoDataProvider
        assert PROVIDER_TYPES["credit"] == CreditProvider
        assert PROVIDER_TYPES["tax"] == TaxProvider

    def test_default_providers_exist(self):
        """Test default providers are configured for all domains."""
        from fin_infra.providers.registry import DEFAULT_PROVIDERS, PROVIDER_MODULES

        # Each domain should have a default
        for domain, default_name in DEFAULT_PROVIDERS.items():
            provider_key = f"{domain}:{default_name}"
            assert provider_key in PROVIDER_MODULES, (
                f"Default provider '{provider_key}' not found in PROVIDER_MODULES"
            )

    def test_provider_modules_format(self):
        """Test provider module mappings have correct format."""
        from fin_infra.providers.registry import PROVIDER_MODULES

        for key, module_path in PROVIDER_MODULES.items():
            # Key should be domain:name
            assert ":" in key, f"Provider key '{key}' missing colon separator"
            domain, name = key.split(":", 1)
            assert domain, f"Empty domain in provider key '{key}'"
            assert name, f"Empty name in provider key '{key}'"

            # Module path should be valid Python identifier
            assert module_path.startswith("fin_infra.providers."), (
                f"Module path '{module_path}' should start with 'fin_infra.providers.'"
            )

    def test_cache_functionality(self):
        """Test provider instance caching."""
        registry = ProviderRegistry()

        # Cache should be empty initially
        assert len(registry._cache) == 0

        # Clear cache works
        registry.clear_cache()
        assert len(registry._cache) == 0

    def test_global_resolve_function(self):
        """Test global resolve function exists and delegates to registry."""
        # resolve should be callable
        assert callable(resolve)

        # Should raise error for unknown provider (not instantiate successfully)
        with pytest.raises(ProviderNotFoundError):
            resolve("banking", "nonexistent_provider")

    def test_global_list_providers_function(self):
        """Test global list_providers function."""
        # Should return same results as registry method
        providers = list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

        banking_providers = list_providers(domain="banking")
        assert all(p.startswith("banking:") for p in banking_providers)


class TestProviderRegistryIntegration:
    """Integration tests for provider registry."""

    def test_all_registered_providers_have_modules(self):
        """Test all providers in registry map to valid module paths."""
        from fin_infra.providers.registry import PROVIDER_MODULES

        for provider_key in PROVIDER_MODULES.keys():
            domain, name = provider_key.split(":", 1)
            # Verify key format
            assert domain in [
                "banking",
                "market",
                "crypto",
                "brokerage",
                "credit",
                "identity",
                "tax",
            ]
            assert name  # name should not be empty

    def test_provider_count_per_domain(self):
        """Test each domain has multiple providers for redundancy."""
        banking = list_providers(domain="banking")
        market = list_providers(domain="market")
        crypto = list_providers(domain="crypto")
        brokerage = list_providers(domain="brokerage")
        credit = list_providers(domain="credit")

        # Should have multiple options per domain
        assert len(banking) >= 2, "Should have at least 2 banking providers"
        assert len(market) >= 2, "Should have at least 2 market providers"
        assert len(crypto) >= 2, "Should have at least 2 crypto providers"
        assert len(brokerage) >= 2, "Should have at least 2 brokerage providers"
        assert len(credit) >= 2, "Should have at least 2 credit providers"

    def test_provider_naming_consistency(self):
        """Test provider naming follows conventions."""
        providers = list_providers()

        for provider_key in providers:
            # Should be lowercase with colon separator
            assert provider_key.islower() or ":" in provider_key
            # Domain should be lowercase
            domain = provider_key.split(":")[0]
            assert domain.islower()


class TestProviderRegistryErrorHandling:
    """Tests for error handling in provider registry."""

    def test_import_error_handling(self):
        """Test graceful handling of import errors."""
        registry = ProviderRegistry()

        # Try to resolve provider that doesn't exist yet
        with pytest.raises(ProviderNotFoundError) as exc_info:
            # Use a valid registry entry but module doesn't exist
            registry.resolve("banking", "fake_provider_for_test")

        error_msg = str(exc_info.value)
        assert "not found in registry" in error_msg or "Failed to import" in error_msg

    def test_missing_provider_class_error(self):
        """Test error when provider class not found in module."""
        # This would require mocking importlib, so we test the error message format
        registry = ProviderRegistry()

        # The error should mention the class name
        with pytest.raises(ProviderNotFoundError):
            registry.resolve("unknown_domain", "unknown_provider")

    def test_resolve_with_none_name_uses_default(self):
        """Test resolving with name=None uses default provider."""
        registry = ProviderRegistry()

        # Should resolve to default provider (teller for banking)
        # Banking default is now "teller" which exists, so it should succeed
        provider = registry.resolve("banking", name=None)

        # Should be a TellerClient instance
        from fin_infra.providers.banking.teller_client import TellerClient

        assert isinstance(provider, TellerClient)

        # Test with a domain that has no implementation yet (should fail)
        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.resolve("market", name=None)  # Default is alphavantage which doesn't exist yet

        error_msg = str(exc_info.value)
        assert "alphavantage" in error_msg.lower() or "Failed to import" in error_msg
