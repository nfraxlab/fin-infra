"""Credit score monitoring providers.

Providers for credit bureaus (Experian, Equifax, TransUnion):
- ExperianProvider: Experian credit reports and scores (v2: real API)
- MockExperianProvider: Mock provider for development (v1)
- easy_credit(): One-liner to create configured credit provider
- add_credit_monitoring(): FastAPI helper to wire credit routes

FCRA Compliance:
- All credit pulls must have permissible purpose
- Log all credit report accesses (see fin_infra.compliance)
- Provide adverse action notices if applicable

Cost Optimization:
- Use svc-infra.cache with 24h TTL to minimize bureau API costs
- Bureau pulls cost ~$0.50-$2.00 each; caching saves 95% of costs

Versions:
- v1 (Mock): Uses MockExperianProvider with hardcoded data
- v2 (Real): Uses ExperianProvider with real Experian API calls

Example:
    >>> from fin_infra.credit import easy_credit
    >>>
    >>> # Auto-detect: uses real API if credentials present, mock otherwise
    >>> credit = easy_credit()
    >>> score = await credit.get_credit_score("user123")
    >>>
    >>> # Force mock (for development)
    >>> credit = easy_credit(provider="experian", use_mock=True)
    >>>
    >>> # Force real API
    >>> credit = easy_credit(
    ...     provider="experian",
    ...     client_id="...",
    ...     client_secret="...",
    ...     environment="sandbox"
    ... )
"""

import os

from fin_infra.credit.add import add_credit
from fin_infra.credit.experian import ExperianProvider
from fin_infra.credit.mock import MockExperianProvider
from fin_infra.providers.base import CreditProvider
from fin_infra.settings import Settings


def easy_credit(
    provider: str | CreditProvider = "experian", *, use_mock: bool | None = None, **config
) -> CreditProvider:
    """Create configured credit provider with environment variable auto-detection.

    Zero-config builder for credit monitoring. Automatically:
    - Uses real Experian API if credentials are present
    - Falls back to mock provider for development
    - Reads configuration from environment variables

    Args:
        provider: Bureau name or CreditProvider instance
            - "experian" (default): Experian provider
            - "equifax": Equifax provider (future)
            - "transunion": TransUnion provider (future)
            - CreditProvider instance: Use directly
        use_mock: Force mock provider (True) or real provider (False)
            - None (default): Auto-detect based on credentials
        **config: Optional configuration overrides
            - client_id: Experian client ID (overrides env)
            - client_secret: Experian client secret (overrides env)
            - api_key: API key (overrides env)
            - environment: "sandbox" or "production" (overrides env)

    Returns:
        Configured CreditProvider instance (real or mock)

    Environment Variables:
        EXPERIAN_CLIENT_ID: Client ID for Experian API
        EXPERIAN_CLIENT_SECRET: Client secret for Experian API
        EXPERIAN_API_KEY: API key (if required)
        EXPERIAN_ENVIRONMENT: "sandbox" or "production" (default: sandbox)
        USE_MOCK_CREDIT: "true" to force mock provider

    Examples:
        >>> # Auto-detect (real if credentials present, mock otherwise)
        >>> credit = easy_credit()
        >>> score = await credit.get_credit_score("user123")

        >>> # Force mock for development
        >>> credit = easy_credit(use_mock=True)
        >>> score = credit.get_credit_score("user123")  # Sync mock call

        >>> # Force real API with explicit credentials
        >>> credit = easy_credit(
        ...     provider="experian",
        ...     client_id="your_client_id",
        ...     client_secret="your_client_secret",
        ...     environment="sandbox"
        ... )
        >>> score = await credit.get_credit_score("user123")  # Async real API call

        >>> # Custom provider instance
        >>> from fin_infra.credit.experian import ExperianProvider
        >>> custom_provider = ExperianProvider(client_id="...", client_secret="...")
        >>> credit = easy_credit(provider=custom_provider)
    """
    # If provider is already a CreditProvider instance, return it
    if isinstance(provider, CreditProvider):
        return provider

    # Load settings from environment
    settings = Settings()

    # Provider factory
    if provider == "experian":
        # Check if mock should be used
        use_mock_env = os.getenv("USE_MOCK_CREDIT", "").lower() == "true"

        # Auto-detect if use_mock not specified
        if use_mock is None:
            # Check if credentials are available
            client_id = config.get("client_id") or getattr(settings, "experian_client_id", None)
            client_secret = config.get("client_secret") or getattr(
                settings, "experian_client_secret", None
            )

            # Use mock if credentials missing OR explicitly requested
            use_mock = not (client_id and client_secret) or use_mock_env

        if use_mock:
            # Use mock provider (v1)
            from fin_infra.credit.mock import MockExperianProvider

            api_key = config.pop("api_key", getattr(settings, "experian_api_key", None))
            environment = config.pop(
                "environment", getattr(settings, "experian_environment", "sandbox")
            )
            return MockExperianProvider(api_key=api_key, environment=environment, **config)
        else:
            # Use real provider (v2)
            from fin_infra.credit.experian import ExperianProvider

            # Extract credentials from config or env
            client_id = config.pop("client_id", getattr(settings, "experian_client_id", None))
            client_secret = config.pop(
                "client_secret", getattr(settings, "experian_client_secret", None)
            )
            api_key = config.pop("api_key", getattr(settings, "experian_api_key", None))
            environment = config.pop(
                "environment", getattr(settings, "experian_environment", "sandbox")
            )

            return ExperianProvider(
                client_id=client_id,
                client_secret=client_secret,
                api_key=api_key,
                environment=environment,
                **config,
            )

    elif provider == "equifax":
        raise NotImplementedError("Equifax provider not implemented yet (v2)")
    elif provider == "transunion":
        raise NotImplementedError("TransUnion provider not implemented yet (v2)")
    else:
        raise ValueError(f"Unknown credit provider: {provider}")


__all__ = [
    "ExperianProvider",
    "MockExperianProvider",
    "easy_credit",
    "add_credit",
]
