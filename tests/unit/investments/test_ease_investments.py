"""Unit tests for easy_investments() builder."""

import os
from unittest.mock import Mock, patch

import pytest

from fin_infra.investments.ease import easy_investments
from fin_infra.investments.providers.base import InvestmentProvider
from fin_infra.investments.providers.plaid import PlaidInvestmentProvider
from fin_infra.investments.providers.snaptrade import SnapTradeInvestmentProvider


# Test auto-detection


def test_auto_detect_plaid():
    """Test auto-detection of Plaid from environment."""
    with patch.dict(
        os.environ,
        {
            "PLAID_CLIENT_ID": "test_client_id",
            "PLAID_SECRET": "test_secret",
        },
        clear=True,
    ):
        provider = easy_investments()
        assert isinstance(provider, PlaidInvestmentProvider)
        assert provider.client_id == "test_client_id"
        assert provider.secret == "test_secret"


def test_auto_detect_snaptrade():
    """Test auto-detection of SnapTrade from environment."""
    with patch.dict(
        os.environ,
        {
            "SNAPTRADE_CLIENT_ID": "test_client_id",
            "SNAPTRADE_CONSUMER_KEY": "test_consumer_key",
        },
        clear=True,
    ):
        provider = easy_investments()
        assert isinstance(provider, SnapTradeInvestmentProvider)
        assert provider.client_id == "test_client_id"
        assert provider.consumer_key == "test_consumer_key"


def test_auto_detect_priority_plaid_over_snaptrade():
    """Test Plaid has priority when both are set."""
    with patch.dict(
        os.environ,
        {
            "PLAID_CLIENT_ID": "plaid_id",
            "PLAID_SECRET": "plaid_secret",
            "SNAPTRADE_CLIENT_ID": "snap_id",
            "SNAPTRADE_CONSUMER_KEY": "snap_key",
        },
        clear=True,
    ):
        provider = easy_investments()
        # Should choose Plaid (higher priority)
        assert isinstance(provider, PlaidInvestmentProvider)


def test_auto_detect_no_credentials():
    """Test error when no credentials in environment."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="No investment provider credentials found"):
            easy_investments()


# Test explicit provider selection


def test_explicit_plaid_with_config():
    """Test explicit Plaid provider with config parameters."""
    provider = easy_investments(
        provider="plaid",
        client_id="explicit_id",
        secret="explicit_secret",
        environment="production",
    )
    assert isinstance(provider, PlaidInvestmentProvider)
    assert provider.client_id == "explicit_id"
    assert provider.secret == "explicit_secret"


def test_explicit_plaid_with_env():
    """Test explicit Plaid provider using environment variables."""
    with patch.dict(
        os.environ,
        {
            "PLAID_CLIENT_ID": "env_id",
            "PLAID_SECRET": "env_secret",
        },
        clear=True,
    ):
        provider = easy_investments(provider="plaid")
        assert isinstance(provider, PlaidInvestmentProvider)
        assert provider.client_id == "env_id"
        assert provider.secret == "env_secret"


def test_explicit_snaptrade_with_config():
    """Test explicit SnapTrade provider with config parameters."""
    provider = easy_investments(
        provider="snaptrade",
        client_id="explicit_id",
        consumer_key="explicit_key",
        base_url="https://test.snaptrade.com/api/v1",
    )
    assert isinstance(provider, SnapTradeInvestmentProvider)
    assert provider.client_id == "explicit_id"
    assert provider.consumer_key == "explicit_key"
    assert provider.base_url == "https://test.snaptrade.com/api/v1"


def test_explicit_snaptrade_with_env():
    """Test explicit SnapTrade provider using environment variables."""
    with patch.dict(
        os.environ,
        {
            "SNAPTRADE_CLIENT_ID": "env_id",
            "SNAPTRADE_CONSUMER_KEY": "env_key",
        },
        clear=True,
    ):
        provider = easy_investments(provider="snaptrade")
        assert isinstance(provider, SnapTradeInvestmentProvider)
        assert provider.client_id == "env_id"
        assert provider.consumer_key == "env_key"


# Test environment configuration


def test_plaid_default_environment():
    """Test Plaid defaults to sandbox environment."""
    provider = easy_investments(
        provider="plaid",
        client_id="test_id",
        secret="test_secret",
    )
    # PlaidInvestmentProvider should use sandbox by default
    assert isinstance(provider, PlaidInvestmentProvider)


def test_plaid_custom_environment():
    """Test Plaid with custom environment."""
    provider = easy_investments(
        provider="plaid",
        client_id="test_id",
        secret="test_secret",
        environment="production",
    )
    assert isinstance(provider, PlaidInvestmentProvider)


def test_plaid_environment_from_env_var():
    """Test Plaid environment from PLAID_ENVIRONMENT variable."""
    with patch.dict(
        os.environ,
        {
            "PLAID_CLIENT_ID": "test_id",
            "PLAID_SECRET": "test_secret",
            "PLAID_ENVIRONMENT": "production",
        },
        clear=True,
    ):
        provider = easy_investments(provider="plaid")
        assert isinstance(provider, PlaidInvestmentProvider)


def test_snaptrade_default_base_url():
    """Test SnapTrade defaults to production base URL."""
    provider = easy_investments(
        provider="snaptrade",
        client_id="test_id",
        consumer_key="test_key",
    )
    assert isinstance(provider, SnapTradeInvestmentProvider)
    assert provider.base_url == "https://api.snaptrade.com/api/v1"


def test_snaptrade_custom_base_url():
    """Test SnapTrade with custom base URL."""
    provider = easy_investments(
        provider="snaptrade",
        client_id="test_id",
        consumer_key="test_key",
        base_url="https://sandbox.snaptrade.com/api/v1",
    )
    assert isinstance(provider, SnapTradeInvestmentProvider)
    assert provider.base_url == "https://sandbox.snaptrade.com/api/v1"


# Test error handling


def test_invalid_provider():
    """Test error for invalid provider name."""
    with pytest.raises(ValueError, match="Invalid provider"):
        easy_investments(provider="invalid")


def test_plaid_missing_client_id():
    """Test error when Plaid client_id is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Plaid credentials missing"):
            easy_investments(provider="plaid", secret="test_secret")


def test_plaid_missing_secret():
    """Test error when Plaid secret is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Plaid credentials missing"):
            easy_investments(provider="plaid", client_id="test_id")


def test_plaid_invalid_environment():
    """Test error for invalid Plaid environment."""
    with pytest.raises(ValueError, match="Invalid Plaid environment"):
        easy_investments(
            provider="plaid",
            client_id="test_id",
            secret="test_secret",
            environment="invalid",
        )


def test_snaptrade_missing_client_id():
    """Test error when SnapTrade client_id is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="SnapTrade credentials missing"):
            easy_investments(provider="snaptrade", consumer_key="test_key")


def test_snaptrade_missing_consumer_key():
    """Test error when SnapTrade consumer_key is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="SnapTrade credentials missing"):
            easy_investments(provider="snaptrade", client_id="test_id")


# Test config override precedence


def test_config_overrides_env_plaid():
    """Test config parameters override environment variables for Plaid."""
    with patch.dict(
        os.environ,
        {
            "PLAID_CLIENT_ID": "env_id",
            "PLAID_SECRET": "env_secret",
            "PLAID_ENVIRONMENT": "sandbox",
        },
        clear=True,
    ):
        provider = easy_investments(
            provider="plaid",
            client_id="config_id",
            secret="config_secret",
            environment="production",
        )
        assert provider.client_id == "config_id"
        assert provider.secret == "config_secret"


def test_config_overrides_env_snaptrade():
    """Test config parameters override environment variables for SnapTrade."""
    with patch.dict(
        os.environ,
        {
            "SNAPTRADE_CLIENT_ID": "env_id",
            "SNAPTRADE_CONSUMER_KEY": "env_key",
            "SNAPTRADE_BASE_URL": "https://env.snaptrade.com",
        },
        clear=True,
    ):
        provider = easy_investments(
            provider="snaptrade",
            client_id="config_id",
            consumer_key="config_key",
            base_url="https://config.snaptrade.com",
        )
        assert provider.client_id == "config_id"
        assert provider.consumer_key == "config_key"
        assert provider.base_url == "https://config.snaptrade.com"


# Test multi-provider scenarios


def test_multiple_providers_can_coexist():
    """Test creating multiple provider instances."""
    # Create Plaid provider
    plaid = easy_investments(
        provider="plaid",
        client_id="plaid_id",
        secret="plaid_secret",
    )
    assert isinstance(plaid, PlaidInvestmentProvider)

    # Create SnapTrade provider
    snaptrade = easy_investments(
        provider="snaptrade",
        client_id="snap_id",
        consumer_key="snap_key",
    )
    assert isinstance(snaptrade, SnapTradeInvestmentProvider)

    # Both should be independent instances
    assert plaid is not snaptrade
    assert plaid.client_id == "plaid_id"
    assert snaptrade.client_id == "snap_id"


def test_returns_investment_provider_interface():
    """Test that all providers return InvestmentProvider interface."""
    plaid = easy_investments(
        provider="plaid",
        client_id="test_id",
        secret="test_secret",
    )
    assert isinstance(plaid, InvestmentProvider)

    snaptrade = easy_investments(
        provider="snaptrade",
        client_id="test_id",
        consumer_key="test_key",
    )
    assert isinstance(snaptrade, InvestmentProvider)
