"""Easy builder for investment providers.

Simplifies provider configuration with auto-detection from environment variables
and sensible defaults. Most apps should use BOTH Plaid (traditional accounts)
and SnapTrade (retail brokerages) for maximum coverage.
"""

from __future__ import annotations

import os
from typing import Any, Literal, Optional

from .providers.base import InvestmentProvider


def easy_investments(
    provider: Optional[Literal["plaid", "snaptrade"]] = None,
    **config: Any,
) -> InvestmentProvider:
    """Create investment provider with auto-configuration.

    Auto-detects provider from environment variables if not specified.
    Returns configured InvestmentProvider ready to use.

    Provider Selection Guide:
        **Most apps should use BOTH providers for complete coverage:**

        - **Plaid**: Traditional investment accounts (401k, IRA, bank brokerage)
          - Coverage: 15,000+ institutions
          - Best for: Employer retirement accounts, bank-connected investments
          - Data freshness: Daily updates (usually overnight)
          - Authentication: access_token from Plaid Link

        - **SnapTrade**: Retail brokerage accounts (E*TRADE, Wealthsimple, Robinhood)
          - Coverage: 125M+ accounts, 70+ brokerages
          - Best for: User's EXISTING retail brokerage accounts
          - Data freshness: Real-time or near real-time
          - Authentication: user_id + user_secret from SnapTrade portal
          - **CRITICAL**: Works with accounts users already have (vs Alpaca which requires new accounts)
          - BONUS: Can execute trades for most brokerages (except Robinhood)

        **Why both matter**: Most users have retirement accounts (Plaid) AND retail
        brokerage accounts (SnapTrade). Using both provides complete portfolio view.

    Environment Variables (auto-detection):
        Plaid:
            - PLAID_CLIENT_ID: Plaid client ID
            - PLAID_SECRET: Plaid secret key
            - PLAID_ENVIRONMENT: Environment (sandbox/development/production), default: sandbox

        SnapTrade:
            - SNAPTRADE_CLIENT_ID: SnapTrade client ID
            - SNAPTRADE_CONSUMER_KEY: SnapTrade consumer key (secret)
            - SNAPTRADE_BASE_URL: API base URL, default: https://api.snaptrade.com/api/v1

    Args:
        provider: Provider to use ("plaid" or "snaptrade"). If None, auto-detects
            from environment variables with priority: Plaid > SnapTrade.
        **config: Provider-specific configuration overrides.
            Plaid: client_id, secret, environment
            SnapTrade: client_id, consumer_key, base_url

    Returns:
        Configured InvestmentProvider instance

    Raises:
        ValueError: If no provider specified and none can be auto-detected,
            or if required credentials are missing.

    Examples:
        Zero-config usage (auto-detect from env vars):
            >>> # Set PLAID_CLIENT_ID, PLAID_SECRET in environment
            >>> investments = easy_investments()
            >>> holdings = await investments.get_holdings(access_token)

        Explicit provider selection:
            >>> investments = easy_investments(
            ...     provider="plaid",
            ...     client_id="your_client_id",
            ...     secret="your_secret",
            ...     environment="sandbox"
            ... )

        SnapTrade for retail brokerages:
            >>> # User connects via SnapTrade portal, you get user_id + user_secret
            >>> investments = easy_investments(provider="snaptrade")
            >>> holdings = await investments.get_holdings("user_123:secret_abc")

        Use BOTH providers for complete coverage:
            >>> # Plaid for traditional accounts (401k, IRA)
            >>> plaid = easy_investments(provider="plaid")
            >>> plaid_holdings = await plaid.get_holdings(plaid_token)
            >>>
            >>> # SnapTrade for retail brokerages (E*TRADE, Robinhood)
            >>> snaptrade = easy_investments(provider="snaptrade")
            >>> snaptrade_holdings = await snaptrade.get_holdings("user:secret")
            >>>
            >>> # Combine for unified portfolio view
            >>> all_holdings = plaid_holdings + snaptrade_holdings
            >>> total_value = sum(h.institution_value for h in all_holdings)

        Integration with banking (shared Plaid credentials):
            >>> from fin_infra.banking import easy_banking
            >>> # Use same Plaid credentials for banking and investments
            >>> banking = easy_banking(provider="plaid")
            >>> investments = easy_investments(provider="plaid")

    Notes:
        - Plaid: Uses access_token authentication (from Plaid Link flow)
        - SnapTrade: Uses user_id + user_secret authentication (from SnapTrade portal)
        - Robinhood via SnapTrade is READ-ONLY (no trading support)
        - Most other SnapTrade brokerages support trading operations
    """
    # Auto-detect provider from environment if not specified
    detected_provider: str | None = provider
    if detected_provider is None:
        detected_provider = _detect_provider()

    # Validate provider
    if detected_provider not in ("plaid", "snaptrade"):
        raise ValueError(f"Invalid provider: {detected_provider}. Must be 'plaid' or 'snaptrade'.")

    # Instantiate provider
    if detected_provider == "plaid":
        return _create_plaid_provider(**config)
    elif detected_provider == "snaptrade":
        return _create_snaptrade_provider(**config)

    # Should never reach here
    raise ValueError(f"Unsupported provider: {provider}")


def _detect_provider() -> str:
    """Auto-detect provider from environment variables.

    Priority: Plaid > SnapTrade

    Returns:
        Provider name ("plaid" or "snaptrade")

    Raises:
        ValueError: If no provider credentials found in environment
    """
    # Check Plaid credentials (highest priority)
    if os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET"):
        return "plaid"

    # Check SnapTrade credentials
    if os.getenv("SNAPTRADE_CLIENT_ID") and os.getenv("SNAPTRADE_CONSUMER_KEY"):
        return "snaptrade"

    # No credentials found
    raise ValueError(
        "No investment provider credentials found in environment. "
        "Please set one of:\n"
        "  - Plaid: PLAID_CLIENT_ID and PLAID_SECRET\n"
        "  - SnapTrade: SNAPTRADE_CLIENT_ID and SNAPTRADE_CONSUMER_KEY\n"
        "Or explicitly specify provider: easy_investments(provider='plaid', ...)"
    )


def _create_plaid_provider(**config: Any) -> InvestmentProvider:
    """Create Plaid investment provider.

    Args:
        **config: Configuration overrides (client_id, secret, environment)

    Returns:
        Configured PlaidInvestmentProvider

    Raises:
        ValueError: If required credentials missing
    """
    from .providers.plaid import PlaidInvestmentProvider

    # Get credentials from config or environment
    client_id = config.get("client_id") or os.getenv("PLAID_CLIENT_ID")
    secret = config.get("secret") or os.getenv("PLAID_SECRET")
    environment = config.get("environment") or os.getenv("PLAID_ENVIRONMENT", "sandbox")

    # Validate required credentials
    if not client_id or not secret:
        raise ValueError(
            "Plaid credentials missing. Please provide:\n"
            "  - client_id (or set PLAID_CLIENT_ID)\n"
            "  - secret (or set PLAID_SECRET)\n"
            "Example: easy_investments(provider='plaid', client_id='...', secret='...')"
        )

    # Validate environment
    valid_envs = ("sandbox", "development", "production")
    if environment not in valid_envs:
        raise ValueError(
            f"Invalid Plaid environment: {environment}. Must be one of: {', '.join(valid_envs)}"
        )

    return PlaidInvestmentProvider(
        client_id=client_id,
        secret=secret,
        environment=environment,
    )


def _create_snaptrade_provider(**config: Any) -> InvestmentProvider:
    """Create SnapTrade investment provider.

    Args:
        **config: Configuration overrides (client_id, consumer_key, base_url)

    Returns:
        Configured SnapTradeInvestmentProvider

    Raises:
        ValueError: If required credentials missing
    """
    from .providers.snaptrade import SnapTradeInvestmentProvider

    # Get credentials from config or environment
    client_id = config.get("client_id") or os.getenv("SNAPTRADE_CLIENT_ID")
    consumer_key = config.get("consumer_key") or os.getenv("SNAPTRADE_CONSUMER_KEY")
    base_url = config.get("base_url") or os.getenv(
        "SNAPTRADE_BASE_URL", "https://api.snaptrade.com/api/v1"
    )

    # Validate required credentials
    if not client_id or not consumer_key:
        raise ValueError(
            "SnapTrade credentials missing. Please provide:\n"
            "  - client_id (or set SNAPTRADE_CLIENT_ID)\n"
            "  - consumer_key (or set SNAPTRADE_CONSUMER_KEY)\n"
            "Example: easy_investments(provider='snaptrade', client_id='...', consumer_key='...')"
        )

    # Ensure base_url is a string (default is set in SnapTradeInvestmentProvider)
    resolved_base_url: str = (
        base_url if isinstance(base_url, str) else "https://api.snaptrade.com/api/v1"
    )

    return SnapTradeInvestmentProvider(
        client_id=client_id,
        consumer_key=consumer_key,
        base_url=resolved_base_url,
    )


__all__ = ["easy_investments"]
