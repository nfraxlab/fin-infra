"""Investment holdings and portfolio data integration.

This module provides READ-ONLY access to investment holdings, securities,
and portfolio data from aggregation providers (Plaid, SnapTrade).

Enables real P/L calculations, asset allocation analysis, and portfolio tracking.
Serves personal finance apps, robo-advisors, wealth management platforms.

Supported Providers:
- Plaid Investment API: 15,000+ institutions (401k, IRA, traditional accounts)
- SnapTrade: 125M+ retail accounts, 70+ brokerages (real-time, hybrid read+write)

Example usage:
    from fin_infra.investments import easy_investments

    # Zero config (uses env vars)
    investments = easy_investments()

    # Explicit provider
    investments = easy_investments(provider="plaid")
    holdings = await investments.get_holdings(access_token)

    # Calculate metrics
    allocation = investments.calculate_allocation(holdings)
    metrics = investments.calculate_portfolio_metrics(holdings)

    # With FastAPI
    from svc_infra.api.fastapi.ease import easy_service_app
    from fin_infra.investments import add_investments

    app = easy_service_app(name="FinanceAPI")
    investments = add_investments(app, provider="plaid")

Environment Variables:
    Plaid:
        PLAID_CLIENT_ID: Client ID from Plaid dashboard
        PLAID_SECRET: Secret key from Plaid dashboard
        PLAID_ENVIRONMENT: "sandbox", "development", or "production" (default: sandbox)

    SnapTrade:
        SNAPTRADE_CLIENT_ID: Client ID from SnapTrade dashboard
        SNAPTRADE_CONSUMER_KEY: Consumer key from SnapTrade dashboard
        SNAPTRADE_ENVIRONMENT: "sandbox" or "production" (default: sandbox)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import FastAPI

# Use the local InvestmentProvider base class (same as providers use)
from .providers.base import InvestmentProvider

# Lazy imports to avoid loading provider SDKs unless needed
_provider_cache: dict[str, InvestmentProvider] = {}


def easy_investments(
    provider: Literal["plaid", "snaptrade"] | None = None,
    **config,
) -> InvestmentProvider:
    """Create an investment provider for holdings and portfolio data.

    Automatically detects provider from environment variables if not specified.

    Args:
        provider: Provider name ("plaid", "snaptrade"). Auto-detected if None.
        **config: Provider-specific configuration overrides.

    Returns:
        InvestmentProvider instance for fetching holdings, transactions, securities.

    Environment detection order:
        1. If PLAID_CLIENT_ID set → Plaid
        2. If SNAPTRADE_CLIENT_ID set → SnapTrade
        3. Default: Plaid (most common)

    Examples:
        # Auto-detect from env vars
        >>> investments = easy_investments()
        >>> holdings = await investments.get_holdings(access_token)

        # Explicit provider
        >>> plaid_inv = easy_investments(provider="plaid")
        >>> st_inv = easy_investments(provider="snaptrade")

        # With config overrides
        >>> investments = easy_investments(
        ...     provider="plaid",
        ...     client_id="custom_id",
        ...     secret="custom_secret",
        ...     environment="production"
        ... )

        # Calculate metrics
        >>> allocation = investments.calculate_allocation(holdings)
        >>> metrics = investments.calculate_portfolio_metrics(holdings)
        >>> # Returns: {total_value, total_cost_basis, total_unrealized_gain_loss, ...}
    """
    # Auto-detect provider from env vars
    if provider is None:
        if os.getenv("PLAID_CLIENT_ID"):
            provider = "plaid"
        elif os.getenv("SNAPTRADE_CLIENT_ID"):
            provider = "snaptrade"
        else:
            provider = "plaid"  # Default to Plaid

    # Check cache
    cache_key = f"{provider}:{sorted(config.items())!s}"
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]

    # Lazy import and initialize provider
    instance: InvestmentProvider
    if provider == "plaid":
        from .providers.plaid import PlaidInvestmentProvider

        instance = PlaidInvestmentProvider(**config)
    elif provider == "snaptrade":
        from .providers.snaptrade import SnapTradeInvestmentProvider

        instance = SnapTradeInvestmentProvider(**config)
    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: 'plaid', 'snaptrade'")

    _provider_cache[cache_key] = instance
    return instance


def add_investments(
    app: FastAPI,
    *,
    provider: Literal["plaid", "snaptrade"] | None = None,
    prefix: str = "/investments",
    tags: list[str] | None = None,
    **provider_config,
) -> InvestmentProvider:
    """Add investment endpoints to a FastAPI app.

    Registers routes for holdings, transactions, securities, and accounts.

    Args:
        app: FastAPI application instance
        provider: Provider name ("plaid", "snaptrade"). Auto-detected if None.
        prefix: URL prefix for investment routes (default: "/investments")
        tags: OpenAPI tags for investment endpoints (default: ["Investments"])
        **provider_config: Provider-specific configuration

    Returns:
        InvestmentProvider instance used by the routes

    Routes added:
        GET /investments/holdings - Get all holdings
        GET /investments/holdings/{account_id} - Get holdings for specific account
        GET /investments/transactions - Get investment transactions
        GET /investments/securities - Get security details
        GET /investments/accounts - Get investment accounts with aggregated data

    Examples:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.investments import add_investments
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> investments = add_investments(app, provider="plaid")
        >>>
        >>> # Routes available at:
        >>> # GET /investments/holdings
        >>> # GET /investments/transactions
        >>> # etc.
    """
    from .add import add_investments as add_investments_impl
    from .providers.base import InvestmentProvider as InvestmentProviderBase

    # Resolve provider from string Literal to actual InvestmentProvider instance
    resolved_provider: InvestmentProviderBase | None = None
    if provider is not None:
        resolved_provider = easy_investments(provider=provider, **provider_config)

    return add_investments_impl(
        app,
        provider=resolved_provider,
        prefix=prefix,
        tags=tags or ["Investments"],
    )


__all__ = [
    "easy_investments",
    "add_investments",
    "InvestmentProvider",
]
