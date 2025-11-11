"""Teller banking provider implementation.

Teller provides bank account aggregation with a free tier (100 connections/month).
Uses certificate-based authentication (mTLS) for enhanced security.

API Documentation: https://teller.io/docs

Environment Variables:
    TELLER_CERTIFICATE_PATH: Path to certificate.pem file
    TELLER_PRIVATE_KEY_PATH: Path to private_key.pem file
    TELLER_ENVIRONMENT: "sandbox" or "production" (default: sandbox)

Example:
    >>> from fin_infra.providers.banking.teller_client import TellerClient
    >>> teller = TellerClient(
    ...     cert_path="./teller_certificate.pem",
    ...     key_path="./teller_private_key.pem",
    ...     environment="sandbox"
    ... )
    >>> accounts = teller.accounts(access_token="test_token")
"""

from __future__ import annotations

import ssl
import httpx
from typing import Any

from ..base import BankingProvider


class TellerClient(BankingProvider):
    """Teller banking provider for account aggregation.

    Features:
    - Free tier: 100 connections/month, 100 requests/minute
    - Direct access token flow (no Link UI)
    - US-only coverage (5000+ institutions)
    - Full sandbox environment

    Rate Limits:
    - 100 requests/minute (free tier)
    - 1000 requests/minute (paid tiers)

    API Base URLs:
    - Sandbox: https://api.sandbox.teller.io
    - Production: https://api.teller.io
    """

    def __init__(
        self,
        cert_path: str | None = None,
        key_path: str | None = None,
        environment: str = "sandbox",
        timeout: float = 30.0,
    ) -> None:
        """Initialize TellerClient banking provider.

        Args:
            cert_path: Path to certificate.pem file (required for real usage)
            key_path: Path to private_key.pem file (required for real usage)
            environment: "sandbox" or "production" (default: sandbox)
            timeout: HTTP request timeout in seconds (default: 30.0)

        Raises:
            ValueError: If cert/key paths are missing in production environment
        """
        if environment == "production" and (not cert_path or not key_path):
            raise ValueError("cert_path and key_path are required for production environment")

        self.cert_path = cert_path
        self.key_path = key_path
        self.environment = environment
        self.timeout = timeout

        # Set base URL based on environment
        if environment == "sandbox":
            self.base_url = "https://api.sandbox.teller.io"
        else:
            self.base_url = "https://api.teller.io"

        # Create HTTP client with mTLS certificate authentication
        client_kwargs = {
            "base_url": self.base_url,
            "timeout": timeout,
            "headers": {"User-Agent": "fin-infra/1.0"},
        }

        # Add certificate using SSL context (recommended approach, not deprecated)
        if cert_path and key_path:
            # Create SSL context with client certificate
            ssl_context = ssl.create_default_context()
            ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            client_kwargs["verify"] = ssl_context

        self.client = httpx.Client(**client_kwargs)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make HTTP request to Teller API with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON data (dict or list)

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            httpx.RequestError: On network errors
        """
        response = self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def create_link_token(self, user_id: str) -> str:
        """Create link token for user authentication.

        Note: Teller uses a simpler auth flow than Plaid. In production,
        users authenticate directly and receive an access token via Teller Connect.
        For sandbox testing, you can use predefined test tokens.

        Args:
            user_id: Your application's user identifier

        Returns:
            Link token or enrollment ID for user to authenticate

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        # Teller's enrollment endpoint for creating application links
        response = self._request(
            "POST",
            "/enrollments",
            json={
                "user_id": user_id,
                "products": ["accounts", "transactions", "balances", "identity"],
            },
        )
        return response.get("enrollment_id", "")

    def exchange_public_token(self, public_token: str) -> dict:
        """Exchange public token for access token.

        Note: Teller's auth flow is simpler than Plaid's. This method is included
        for interface compatibility but Teller typically returns access tokens directly.

        Args:
            public_token: Public token from Teller Connect

        Returns:
            Dictionary with access_token and optional item_id
        """
        # In Teller's flow, the access token is often provided directly
        # This method provides Plaid-compatible interface
        return {
            "access_token": public_token,
            "item_id": None,
        }

    def accounts(self, access_token: str) -> list[dict]:
        """Fetch accounts for an access token.

        Args:
            access_token: Access token from successful authentication

        Returns:
            List of account dictionaries with fields:
            - id: Account ID
            - name: Account name
            - type: Account type (checking, savings, credit, etc.)
            - mask: Last 4 digits of account number
            - currency: Currency code (USD, etc.)
            - institution: Institution name
            - balance_available: Available balance
            - balance_current: Current balance

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        # Override auth for this request with access token
        response = self.client.get(
            "/accounts",
            auth=(access_token, ""),
        )
        response.raise_for_status()
        return response.json()

    def transactions(
        self,
        access_token: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Fetch transactions for an access token.

        Args:
            access_token: Access token from successful authentication
            start_date: Start date for transactions (ISO 8601: YYYY-MM-DD)
            end_date: End date for transactions (ISO 8601: YYYY-MM-DD)

        Returns:
            List of transaction dictionaries with fields:
            - id: Transaction ID
            - account_id: Account ID
            - amount: Transaction amount (negative for debits)
            - currency: Currency code
            - date: Transaction date
            - description: Transaction description
            - category: Transaction category
            - pending: Whether transaction is pending
            - merchant_name: Merchant name (if available)

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        params = {}
        if start_date:
            params["from_date"] = start_date
        if end_date:
            params["to_date"] = end_date

        response = self.client.get(
            "/transactions",
            auth=(access_token, ""),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def balances(self, access_token: str, account_id: str | None = None) -> dict:
        """Fetch current balances.

        Args:
            access_token: Access token from successful authentication
            account_id: Optional specific account ID to fetch balance for

        Returns:
            Dictionary with balance information:
            - accounts: List of account balances if account_id not specified
            - balance_available: Available balance if account_id specified
            - balance_current: Current balance if account_id specified

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        if account_id:
            # Fetch specific account balance
            response = self.client.get(
                f"/accounts/{account_id}/balances",
                auth=(access_token, ""),
            )
        else:
            # Fetch all account balances
            response = self.client.get(
                "/accounts/balances",
                auth=(access_token, ""),
            )

        response.raise_for_status()
        return response.json()

    def identity(self, access_token: str) -> dict:
        """Fetch identity/account holder information.

        Args:
            access_token: Access token from successful authentication

        Returns:
            Dictionary with identity information:
            - name: Account holder name
            - email: Email address
            - phone: Phone number
            - address: Physical address
            - ssn_last4: Last 4 digits of SSN (if available)

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        response = self.client.get(
            "/identity",
            auth=(access_token, ""),
        )
        response.raise_for_status()
        return response.json()

    def __del__(self) -> None:
        """Close HTTP client on cleanup."""
        try:
            self.client.close()
        except Exception:
            pass  # Best effort cleanup
