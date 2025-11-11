"""HTTP client for Experian API with retry logic and error handling.

Integrates:
- svc-infra.http for timeouts and client creation
- ExperianAuthManager for OAuth tokens
- Automatic retry on transient failures (429, 500, 503)
- FCRA compliance headers

Example:
    >>> client = ExperianClient(
    ...     base_url="https://sandbox.experian.com",
    ...     auth_manager=auth,
    ... )
    >>> data = await client.get_credit_score("user123")
"""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from fin_infra.credit.experian.auth import ExperianAuthManager


class ExperianAPIError(Exception):
    """Base exception for Experian API errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ExperianRateLimitError(ExperianAPIError):
    """Raised when rate limit is exceeded (429)."""

    pass


class ExperianAuthError(ExperianAPIError):
    """Raised when authentication fails (401)."""

    pass


class ExperianNotFoundError(ExperianAPIError):
    """Raised when user not found in bureau (404)."""

    pass


class ExperianClient:
    """HTTP client for Experian Consumer Services API.

    Handles:
    - OAuth token injection
    - Automatic retries (rate limit, server errors)
    - Error response parsing
    - FCRA compliance headers

    Args:
        base_url: Experian API base URL (sandbox or production)
        auth_manager: ExperianAuthManager instance
        timeout: Request timeout in seconds (default: 10.0)

    Example:
        >>> auth = ExperianAuthManager(client_id="...", client_secret="...", base_url="...")
        >>> client = ExperianClient(base_url="...", auth_manager=auth)
        >>> score_data = await client.get_credit_score("user123")
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth_manager: ExperianAuthManager,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = auth_manager
        self.timeout = timeout

        # Create httpx client (from svc-infra pattern)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )

    async def close(self) -> None:
        """Close HTTP client connection pool."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ExperianRateLimitError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        permissible_purpose: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make authenticated HTTP request to Experian API.

        Automatically:
        - Injects OAuth token
        - Adds FCRA compliance headers (if permissible_purpose provided)
        - Retries on rate limit (429) or server error (500, 503)
        - Parses error responses

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path (e.g., "/credit/v2/scores/user123")
            headers: Additional headers
            permissible_purpose: FCRA permissible purpose (required for credit reports)
            **kwargs: Additional httpx request kwargs

        Returns:
            Parsed JSON response

        Raises:
            ExperianAuthError: Authentication failed (401)
            ExperianRateLimitError: Rate limit exceeded (429)
            ExperianNotFoundError: User not found (404)
            ExperianAPIError: Other API errors
        """
        # Get OAuth token
        token = await self.auth.get_token()

        # Build headers
        request_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Add FCRA compliance header if permissible purpose provided
        if permissible_purpose:
            request_headers["X-Permissible-Purpose"] = permissible_purpose

        # Merge additional headers
        if headers:
            request_headers.update(headers)

        # Make request
        try:
            response = await self._client.request(
                method,
                path,
                headers=request_headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            # Parse error response
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass

            status = e.response.status_code
            message = error_data.get("error", {}).get("message", str(e))

            # Handle specific error types
            if status == 401:
                # Auth error - invalidate token and raise
                await self.auth.invalidate()
                raise ExperianAuthError(message, status_code=status, response=error_data)
            elif status == 404:
                raise ExperianNotFoundError(message, status_code=status, response=error_data)
            elif status == 429:
                raise ExperianRateLimitError(message, status_code=status, response=error_data)
            else:
                raise ExperianAPIError(message, status_code=status, response=error_data)

    async def get_credit_score(
        self,
        user_id: str,
        *,
        permissible_purpose: str = "account_review",
    ) -> dict[str, Any]:
        """Fetch credit score from Experian API.

        Args:
            user_id: User identifier (SSN hash or internal ID)
            permissible_purpose: FCRA permissible purpose (default: account_review)

        Returns:
            Experian API response with credit score data

        Example:
            >>> data = await client.get_credit_score("user123")
            >>> print(data["creditProfile"]["score"])  # 735
        """
        return await self._request(
            "GET",
            f"/consumerservices/credit/v2/scores/{user_id}",
            permissible_purpose=permissible_purpose,
        )

    async def get_credit_report(
        self,
        user_id: str,
        *,
        permissible_purpose: str = "account_review",
    ) -> dict[str, Any]:
        """Fetch full credit report from Experian API.

        FCRA Compliance: Permissible purpose header is REQUIRED.

        Args:
            user_id: User identifier (SSN hash or internal ID)
            permissible_purpose: FCRA permissible purpose (account_review, credit_application, etc.)

        Returns:
            Experian API response with full credit report

        Example:
            >>> data = await client.get_credit_report("user123", permissible_purpose="credit_application")
            >>> print(data["creditProfile"]["tradelines"])  # Credit accounts
        """
        return await self._request(
            "GET",
            f"/consumerservices/credit/v2/reports/{user_id}",
            permissible_purpose=permissible_purpose,
        )

    async def subscribe_to_changes(
        self,
        user_id: str,
        callback_url: str,
        *,
        events: list[str] | None = None,
        signature_key: str | None = None,
    ) -> dict[str, Any]:
        """Subscribe to credit change webhooks.

        Args:
            user_id: User identifier
            callback_url: Webhook URL to receive notifications
            events: Event types to subscribe to (default: score_change, new_inquiry, new_account)
            signature_key: Webhook signature key for verification

        Returns:
            Subscription response with subscription_id

        Example:
            >>> data = await client.subscribe_to_changes(
            ...     "user123",
            ...     "https://api.example.com/webhooks/credit",
            ...     signature_key="secret_key_123"
            ... )
            >>> print(data["subscriptionId"])  # "sub_abc123"
        """
        if events is None:
            events = ["score_change", "new_inquiry", "new_account"]

        payload = {
            "userId": user_id,
            "callbackUrl": callback_url,
            "events": events,
        }

        if signature_key:
            payload["signatureKey"] = signature_key

        return await self._request(
            "POST",
            "/consumerservices/credit/v2/webhooks",
            json=payload,
        )
