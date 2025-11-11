"""Experian credit provider with real API integration.

This is the v2 implementation that replaces mock data with real Experian API calls.

Features:
- Real OAuth 2.0 authentication
- HTTP client with retry logic
- Response parsing to Pydantic models
- FCRA compliance headers
- Error handling

Example:
    >>> from fin_infra.credit.experian import ExperianProvider
    >>>
    >>> provider = ExperianProvider(
    ...     api_key="your_api_key",
    ...     client_id="your_client_id",
    ...     client_secret="your_client_secret",
    ...     environment="sandbox"
    ... )
    >>>
    >>> # Get credit score
    >>> score = await provider.get_credit_score("user123")
    >>> print(score.score)  # Real FICO score from Experian
    >>>
    >>> # Get full report
    >>> report = await provider.get_credit_report("user123")
    >>> print(len(report.accounts))  # Real credit accounts
"""

from typing import Literal

from fin_infra.credit.experian.auth import ExperianAuthManager
from fin_infra.credit.experian.client import ExperianClient
from fin_infra.credit.experian.parser import parse_credit_report, parse_credit_score
from fin_infra.models.credit import CreditReport, CreditScore
from fin_infra.providers.base import CreditProvider
from fin_infra.settings import Settings


class ExperianProvider(CreditProvider):
    """Experian credit bureau provider with real API integration.

    v2 Implementation:
    - Real Experian API calls (sandbox or production)
    - OAuth 2.0 authentication
    - Automatic retries and error handling
    - FCRA compliance headers

    Args:
        client_id: Experian API client ID (required)
        client_secret: Experian API client secret (required)
        api_key: Experian API key (optional, for additional auth)
        environment: "sandbox" or "production" (default: sandbox)
        base_url: Override base URL (optional, auto-detected from environment)
        **config: Additional configuration

    Environment Variables:
        EXPERIAN_CLIENT_ID: Client ID for Experian API
        EXPERIAN_CLIENT_SECRET: Client secret for Experian API
        EXPERIAN_API_KEY: API key (if required)
        EXPERIAN_ENVIRONMENT: "sandbox" or "production" (default: sandbox)
        EXPERIAN_BASE_URL: Override base URL

    Example:
        >>> # From environment variables
        >>> provider = ExperianProvider()
        >>>
        >>> # Explicit credentials
        >>> provider = ExperianProvider(
        ...     client_id="your_client_id",
        ...     client_secret="your_client_secret",
        ...     environment="sandbox"
        ... )
        >>>
        >>> # Get credit score
        >>> score = await provider.get_credit_score("user123")
    """

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_key: str | None = None,
        environment: Literal["sandbox", "production"] = "sandbox",
        base_url: str | None = None,
        **config,
    ):
        # Load from environment if not provided
        settings = Settings()

        self.client_id = client_id or getattr(settings, "experian_client_id", None)
        self.client_secret = client_secret or getattr(settings, "experian_client_secret", None)
        self.api_key = api_key or getattr(settings, "experian_api_key", None)
        self.environment = environment
        self.config = config

        # Validate required credentials
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Experian client_id and client_secret are required. "
                "Set EXPERIAN_CLIENT_ID and EXPERIAN_CLIENT_SECRET environment variables "
                "or pass them explicitly."
            )

        # Determine base URL
        if base_url:
            self.base_url = base_url
        elif hasattr(settings, "experian_base_url") and settings.experian_base_url:
            self.base_url = settings.experian_base_url
        else:
            # Auto-detect from environment
            if environment == "production":
                self.base_url = "https://api.experian.com"
            else:
                self.base_url = "https://sandbox.experian.com"

        # Initialize auth manager
        self._auth = ExperianAuthManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
        )

        # Initialize HTTP client
        self._client = ExperianClient(
            base_url=self.base_url,
            auth_manager=self._auth,
        )

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_credit_score(self, user_id: str, **kwargs) -> CreditScore:
        """Retrieve current credit score for a user from Experian API.

        Makes real API call to Experian. Uses FCRA-compliant permissible purpose.

        Args:
            user_id: User identifier (SSN hash or internal ID)
            **kwargs: Additional parameters
                - permissible_purpose: FCRA purpose (default: "account_review")

        Returns:
            CreditScore with real FICO score from Experian

        Raises:
            ExperianAPIError: If API call fails
            ExperianNotFoundError: If user not found in bureau

        Example:
            >>> provider = ExperianProvider()
            >>> score = await provider.get_credit_score("user123")
            >>> print(score.score)  # Real FICO score (300-850)
        """
        permissible_purpose = kwargs.get("permissible_purpose", "account_review")

        # Fetch from Experian API
        data = await self._client.get_credit_score(
            user_id,
            permissible_purpose=permissible_purpose,
        )

        # Parse response to CreditScore model
        return parse_credit_score(data, user_id=user_id)

    async def get_credit_report(self, user_id: str, **kwargs) -> CreditReport:
        """Retrieve full credit report for a user from Experian API.

        Makes real API call to Experian. Includes FCRA-required permissible purpose header.

        Args:
            user_id: User identifier (SSN hash or internal ID)
            **kwargs: Additional parameters
                - permissible_purpose: FCRA purpose (default: "account_review")

        Returns:
            CreditReport with real credit data from Experian

        Raises:
            ExperianAPIError: If API call fails
            ExperianNotFoundError: If user not found in bureau

        Example:
            >>> provider = ExperianProvider()
            >>> report = await provider.get_credit_report("user123")
            >>> print(len(report.accounts))  # Real credit accounts
            >>> print(report.score.score)  # Real FICO score
        """
        permissible_purpose = kwargs.get("permissible_purpose", "account_review")

        # Fetch from Experian API
        data = await self._client.get_credit_report(
            user_id,
            permissible_purpose=permissible_purpose,
        )

        # Parse response to CreditReport model
        return parse_credit_report(data, user_id=user_id)

    async def subscribe_to_changes(self, user_id: str, webhook_url: str, **kwargs) -> str:
        """Subscribe to credit score change notifications from Experian.

        Creates webhook subscription in Experian system. Experian will POST to webhook_url
        when credit changes occur.

        Args:
            user_id: User identifier
            webhook_url: URL to receive webhook notifications
            **kwargs: Additional parameters
                - events: List of event types (default: score_change, new_inquiry, new_account)
                - signature_key: Webhook signature key for verification

        Returns:
            Subscription ID from Experian

        Example:
            >>> provider = ExperianProvider()
            >>> sub_id = await provider.subscribe_to_changes(
            ...     "user123",
            ...     "https://api.example.com/webhooks/credit",
            ...     signature_key="secret_key_123"
            ... )
            >>> print(sub_id)  # "sub_abc123"
        """
        events = kwargs.get("events")
        signature_key = kwargs.get("signature_key")

        # Subscribe via Experian API
        data = await self._client.subscribe_to_changes(
            user_id,
            webhook_url,
            events=events,
            signature_key=signature_key,
        )

        return data.get("subscriptionId", "unknown")
