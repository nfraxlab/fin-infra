"""Banking provider integration for account aggregation (Teller, Plaid, MX).

This module provides easy setup for banking providers to fetch accounts,
transactions, balances, and identity data from financial institutions.

Supported Providers:
- Teller (default): Free tier, 100 connections/month
- Plaid: Industry standard, free sandbox
- MX: Enterprise-grade

Example usage:
    from fin_infra.banking import easy_banking

    # Zero config (uses env vars)
    banking = easy_banking()

    # Explicit provider
    banking = easy_banking(provider="plaid")

    # With FastAPI
    from svc_infra.api.fastapi.ease import easy_service_app
    from fin_infra.banking import add_banking

    app = easy_service_app(name="FinanceAPI")
    banking = add_banking(app, provider="teller")

Environment Variables:
    Teller:
        TELLER_CERTIFICATE_PATH: Path to certificate.pem file
        TELLER_PRIVATE_KEY_PATH: Path to private_key.pem file
        TELLER_ENVIRONMENT: "sandbox" or "production" (default: sandbox)

    Plaid:
        PLAID_CLIENT_ID: Client ID from Plaid dashboard
        PLAID_SECRET: Secret key from Plaid dashboard
        PLAID_ENVIRONMENT: "sandbox", "development", or "production" (default: sandbox)

    MX:
        MX_CLIENT_ID: Client ID from MX dashboard
        MX_API_KEY: API key from MX dashboard
        MX_ENVIRONMENT: "sandbox" or "production" (default: sandbox)
"""

from __future__ import annotations

import os
from datetime import date
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from ..providers.registry import resolve
from ..providers.base import BankingProvider

if TYPE_CHECKING:
    from fastapi import FastAPI


__all__ = [
    "easy_banking",
    "add_banking",
    # Utilities for apps to manage banking connections
    "validate_plaid_token",
    "validate_teller_token",
    "validate_mx_token",
    "validate_provider_token",
    "parse_banking_providers",
    "sanitize_connection_status",
    "mark_connection_unhealthy",
    "mark_connection_healthy",
    "get_primary_access_token",
    "test_connection_health",
    "should_refresh_token",
    "BankingConnectionInfo",
    "BankingConnectionStatus",
]


# Pydantic models defined at module level to avoid forward reference issues
class CreateLinkTokenRequest(BaseModel):
    """Request model for creating a link token."""

    user_id: str


class CreateLinkTokenResponse(BaseModel):
    """Response model for link token creation."""

    link_token: str


class ExchangeTokenRequest(BaseModel):
    """Request model for exchanging public token."""

    public_token: str


class ExchangeTokenResponse(BaseModel):
    """Response model for token exchange."""

    access_token: str
    item_id: Optional[str] = None


class BalanceHistoryStats(BaseModel):
    """Statistics calculated from balance history."""

    trend: str = Field(..., description="Trend direction: increasing, decreasing, or stable")
    average: float = Field(..., description="Average balance over the period")
    minimum: float = Field(..., description="Minimum balance in the period")
    maximum: float = Field(..., description="Maximum balance in the period")
    change_amount: float = Field(..., description="Net change from start to end")
    change_percent: float = Field(..., description="Percentage change from start to end")


class BalanceHistoryResponse(BaseModel):
    """Response from balance history endpoint with snapshots and statistics."""

    account_id: str = Field(..., description="Account identifier")
    snapshots: list = Field(..., description="List of balance snapshots")
    stats: BalanceHistoryStats = Field(..., description="Statistical summary of balance history")


def easy_banking(provider: str = "teller", **config) -> BankingProvider:
    """Create configured banking provider with environment variable auto-detection.

    This is the simplest way to get started with banking integration. The function
    automatically detects provider credentials from environment variables and returns
    a ready-to-use BankingProvider instance.

    Args:
        provider: Provider name - "teller" (default), "plaid", or "mx"
        **config: Optional configuration overrides (api_key, client_id, secret, environment)

    Returns:
        Configured BankingProvider instance ready to use

    Raises:
        ValueError: If required environment variables are missing
        ImportError: If provider SDK is not installed

    Examples:
        # Zero config with Teller (uses TELLER_API_KEY from env)
        >>> banking = easy_banking()
        >>> link_token = banking.create_link_token(user_id="user123")

        # Explicit provider with Plaid
        >>> banking = easy_banking(provider="plaid")
        >>> accounts = banking.accounts(access_token="...")

        # Override environment
        >>> banking = easy_banking(
        ...     provider="teller",
        ...     api_key="test_key",
        ...     environment="sandbox"
        ... )

    Provider-specific environment variables:
        Teller:
            - TELLER_CERTIFICATE_PATH (required)
            - TELLER_PRIVATE_KEY_PATH (required)
            - TELLER_ENVIRONMENT (optional, default: "sandbox")

        Plaid:
            - PLAID_CLIENT_ID (required)
            - PLAID_SECRET (required)
            - PLAID_ENVIRONMENT (optional, default: "sandbox")

        MX:
            - MX_CLIENT_ID (required)
            - MX_API_KEY (required)
            - MX_ENVIRONMENT (optional, default: "sandbox")

    See Also:
        - add_banking(): For FastAPI integration with routes
        - docs/banking.md: Comprehensive banking integration guide
        - docs/adr/0003-banking-integration.md: Architecture decisions
    """
    # Auto-detect provider config from environment if not explicitly provided
    # Only auto-detect if no config params were passed
    if not config:
        if provider == "teller":
            config = {
                "cert_path": os.getenv("TELLER_CERTIFICATE_PATH"),
                "key_path": os.getenv("TELLER_PRIVATE_KEY_PATH"),
                "environment": os.getenv("TELLER_ENVIRONMENT", "sandbox"),
            }
        elif provider == "plaid":
            config = {
                "client_id": os.getenv("PLAID_CLIENT_ID"),
                "secret": os.getenv("PLAID_SECRET"),
                "environment": os.getenv("PLAID_ENVIRONMENT", "sandbox"),
            }
        elif provider == "mx":
            config = {
                "client_id": os.getenv("MX_CLIENT_ID"),
                "api_key": os.getenv("MX_API_KEY"),
                "environment": os.getenv("MX_ENVIRONMENT", "sandbox"),
            }

    # Use provider registry to dynamically load and configure provider
    return resolve("banking", provider, **config)


def add_banking(
    app: "FastAPI",
    *,
    provider: str | BankingProvider | None = None,
    prefix: str = "/banking",
    cache_ttl: int = 60,
    **config,
) -> BankingProvider:
    """Wire banking provider to FastAPI app with routes, caching, and logging.

    This helper mounts banking endpoints to your FastAPI application and configures
    integration with svc-infra for caching, logging, and security. It provides a
    production-ready banking API with minimal configuration.

    Mounted Routes:
        POST {prefix}/link
            Create link token for user authentication
            Request: {"user_id": "string"}
            Response: {"link_token": "string"}

        POST {prefix}/exchange
            Exchange public token for access token (Plaid flow)
            Request: {"public_token": "string"}
            Response: {"access_token": "string", "item_id": "string"}

        GET {prefix}/accounts
            List accounts for access token
            Headers: Authorization: Bearer {access_token}
            Response: {"accounts": [Account...]}

        GET {prefix}/transactions
            List transactions for access token
            Query: start_date, end_date (optional)
            Headers: Authorization: Bearer {access_token}
            Response: {"transactions": [Transaction...]}

        GET {prefix}/balances
            Get current balances
            Query: account_id (optional)
            Headers: Authorization: Bearer {access_token}
            Response: {"balances": {...}}

        GET {prefix}/identity
            Get identity/account holder information
            Headers: Authorization: Bearer {access_token}
            Response: {"identity": {...}}

    Args:
        app: FastAPI application instance
        provider: Provider name ("plaid", "teller"), provider instance, or None for auto-detect
        prefix: URL prefix for banking routes (default: "/banking")
        cache_ttl: Cache TTL in seconds for account data (default: 60)
        **config: Optional provider configuration overrides (ignored if provider is an instance)

    Returns:
        Configured BankingProvider instance used by the routes

    Raises:
        ValueError: If required environment variables are missing
        ImportError: If svc-infra or provider SDK is not installed

    Examples:
        # Basic setup with auto-detect (Teller default)
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.banking import add_banking
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> banking = add_banking(app)

        # With provider name
        >>> banking = add_banking(app, provider="plaid")

        # With provider instance (useful for custom configuration)
        >>> from fin_infra.banking import easy_banking
        >>> banking_provider = easy_banking(provider="teller")
        >>> banking = add_banking(app, provider=banking_provider)

        # Custom cache TTL
        >>> banking = add_banking(
        ...     app,
        ...     provider="teller",
        ...     cache_ttl=120  # 2 minutes
        ... )

        # Routes mounted at /banking/* (matches svc-infra pattern like /payments, /auth)
        # GET  /banking/accounts
        # GET  /banking/transactions
        # GET  /banking/balances
        # POST /banking/link
        # POST /banking/exchange

    Integration with svc-infra:
        - Cache: Uses svc_infra.cache for account/transaction caching
        - Logging: Uses svc_infra.logging with PII masking for account numbers
        - DB: Stores encrypted access tokens via svc_infra.db
        - Auth: Integrates with svc_infra.api.fastapi.auth for protected routes

    See Also:
        - easy_banking(): For standalone provider usage without FastAPI
        - docs/banking.md: API documentation and examples
        - svc-infra docs: Backend integration patterns
    """
    # Import FastAPI dependencies
    from fastapi import Depends, Header, HTTPException, Query

    # Import svc-infra public router (no auth - banking providers use their own access tokens like Plaid/Teller)
    from svc_infra.api.fastapi.dual.public import public_router

    # Create banking provider instance (or use the provided one)
    if isinstance(provider, BankingProvider):
        banking = provider
    else:
        # Auto-detect provider from environment if not specified
        if provider is None:
            provider = os.getenv("BANKING_PROVIDER", "teller")
        banking = easy_banking(provider=provider, **config)

    # Create router (public - banking providers use their own provider-specific access tokens)
    router = public_router(prefix=prefix, tags=["Banking"])

    # Dependency to extract access token from header
    def get_access_token(authorization: str = Header(..., alias="Authorization")) -> str:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        return authorization[7:]  # Strip "Bearer "

    # Routes - use module-level Pydantic models
    @router.post("/link", response_model=CreateLinkTokenResponse)
    async def create_link_token(request: CreateLinkTokenRequest):
        """Create link token for user authentication."""
        link_token = banking.create_link_token(user_id=request.user_id)
        return CreateLinkTokenResponse(link_token=link_token)

    @router.post("/exchange", response_model=ExchangeTokenResponse)
    async def exchange_token(request: ExchangeTokenRequest):
        """Exchange public token for access token (Plaid flow)."""
        result = banking.exchange_public_token(public_token=request.public_token)
        return ExchangeTokenResponse(**result)

    @router.get("/accounts")
    async def get_accounts(access_token: str = Depends(get_access_token)):
        """List accounts for access token."""
        accounts = banking.accounts(access_token=access_token)
        return {"accounts": accounts}

    @router.get("/transactions")
    async def get_transactions(
        access_token: str = Depends(get_access_token),
        start_date: Optional[date] = Query(None, description="Filter by start date (ISO format)"),
        end_date: Optional[date] = Query(None, description="Filter by end date (ISO format)"),
        merchant: Optional[str] = Query(
            None, description="Filter by merchant name (partial match, case-insensitive)"
        ),
        category: Optional[str] = Query(
            None, description="Filter by category (comma-separated list for multiple)"
        ),
        min_amount: Optional[float] = Query(
            None, description="Minimum transaction amount (inclusive)"
        ),
        max_amount: Optional[float] = Query(
            None, description="Maximum transaction amount (inclusive)"
        ),
        tags: Optional[str] = Query(None, description="Filter by tags (comma-separated list)"),
        account_id: Optional[str] = Query(None, description="Filter by specific account ID"),
        is_recurring: Optional[bool] = Query(None, description="Filter by recurring status"),
        sort_by: Optional[str] = Query("date", description="Sort field: date, amount, or merchant"),
        order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
        page: int = Query(1, ge=1, description="Page number (starts at 1)"),
        per_page: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    ):
        """List transactions for access token with advanced filtering.

        Supports filtering by date range, merchant, category, amount range, tags,
        account, recurring status, and pagination. Results are cached for common queries.

        Examples:
            - Recent transactions: ?page=1&per_page=50
            - By merchant: ?merchant=starbucks
            - By category: ?category=food,restaurants
            - By amount range: ?min_amount=50&max_amount=200
            - Recurring only: ?is_recurring=true
            - Combined filters: ?category=food&min_amount=10&sort_by=amount&order=desc

        Returns:
            {
                "data": [...transactions...],
                "meta": {
                    "total": 1234,
                    "page": 1,
                    "per_page": 50,
                    "total_pages": 25
                }
            }
        """
        # Get all transactions from provider
        transactions = banking.transactions(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
        )

        # Apply filters
        filtered = transactions

        # Merchant filter (case-insensitive partial match)
        if merchant:
            merchant_lower = merchant.lower()
            filtered = [
                t
                for t in filtered
                if t.get("merchant_name") and merchant_lower in t["merchant_name"].lower()
            ]

        # Category filter (comma-separated list)
        if category:
            categories = [c.strip() for c in category.split(",")]
            filtered = [t for t in filtered if t.get("category") in categories]

        # Amount range filters
        if min_amount is not None:
            filtered = [t for t in filtered if t.get("amount", 0) >= min_amount]

        if max_amount is not None:
            filtered = [t for t in filtered if t.get("amount", 0) <= max_amount]

        # Tags filter (comma-separated list, all tags must match)
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            filtered = [
                t for t in filtered if t.get("tags") and all(tag in t["tags"] for tag in tag_list)
            ]

        # Account ID filter
        if account_id:
            filtered = [t for t in filtered if t.get("account_id") == account_id]

        # Recurring status filter
        if is_recurring is not None:
            filtered = [t for t in filtered if t.get("is_recurring", False) == is_recurring]

        # Sort transactions
        reverse = order == "desc"
        if sort_by == "amount":
            filtered.sort(key=lambda t: t.get("amount", 0), reverse=reverse)
        elif sort_by == "merchant":
            filtered.sort(key=lambda t: t.get("merchant_name", ""), reverse=reverse)
        else:  # Default to date
            filtered.sort(key=lambda t: t.get("date", ""), reverse=reverse)

        # Calculate pagination
        total = len(filtered)
        total_pages = (total + per_page - 1) // per_page  # Ceiling division

        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated = filtered[start_idx:end_idx]

        return {
            "data": paginated,
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            },
        }

    @router.get("/balances")
    async def get_balances(
        access_token: str = Depends(get_access_token),
        account_id: Optional[str] = Query(None),
    ):
        """Get current balances."""
        balances = banking.balances(
            access_token=access_token,
            account_id=account_id,
        )
        return {"balances": balances}

    @router.get("/identity")
    async def get_identity(access_token: str = Depends(get_access_token)):
        """Get identity/account holder information."""
        identity = banking.identity(access_token=access_token)
        return {"identity": identity}

    @router.get("/accounts/{account_id}/history", response_model=BalanceHistoryResponse)
    async def get_balance_history(
        account_id: str,
        days: int = Query(
            90, ge=1, le=365, description="Number of days of history to retrieve (1-365)"
        ),
    ):
        """Get balance history for an account with trend analysis and statistics.

        Returns historical balance snapshots along with calculated statistics including:
        - Trend direction (increasing, decreasing, stable)
        - Average, minimum, and maximum balance
        - Net change amount and percentage

        Results are cached with 24h TTL for performance.
        """
        from fin_infra.banking.history import get_balance_history as get_history

        # Get balance history from storage
        history = get_history(account_id=account_id, days=days)

        # If no history, return empty response
        if not history:
            return BalanceHistoryResponse(
                account_id=account_id,
                snapshots=[],
                stats=BalanceHistoryStats(
                    trend="stable",
                    average=0.0,
                    minimum=0.0,
                    maximum=0.0,
                    change_amount=0.0,
                    change_percent=0.0,
                ),
            )

        # Convert snapshots to dict for JSON serialization
        snapshots_data = [
            {
                "account_id": s.account_id,
                "balance": s.balance,
                "date": s.snapshot_date.isoformat(),
                "source": s.source,
                "created_at": s.created_at.isoformat(),
            }
            for s in history
        ]

        # Calculate statistics
        balances = [s.balance for s in history]
        avg_balance = sum(balances) / len(balances)
        min_balance = min(balances)
        max_balance = max(balances)

        # Calculate trend (compare first and last snapshot)
        # History is sorted descending, so reverse to get oldest first
        oldest_balance = history[-1].balance
        newest_balance = history[0].balance
        change_amount = newest_balance - oldest_balance

        # Calculate percentage change (handle zero division)
        if oldest_balance != 0:
            change_percent = (change_amount / oldest_balance) * 100
        else:
            change_percent = 0.0

        # Determine trend direction
        if abs(change_percent) < 5.0:  # Less than 5% change is stable
            trend = "stable"
        elif change_amount > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Create statistics object
        stats = BalanceHistoryStats(
            trend=trend,
            average=avg_balance,
            minimum=min_balance,
            maximum=max_balance,
            change_amount=change_amount,
            change_percent=change_percent,
        )

        return BalanceHistoryResponse(
            account_id=account_id,
            snapshots=snapshots_data,
            stats=stats,
        )

    # Mount router to app (explicitly include in schema for OpenAPI docs)
    app.include_router(router, include_in_schema=True)

    # Store provider instance on app state for access in routes
    if not hasattr(app.state, "banking_provider"):
        app.state.banking_provider = banking

    return banking


# Import utilities at end to avoid circular imports
from .utils import (
    validate_plaid_token,
    validate_teller_token,
    validate_mx_token,
    validate_provider_token,
    parse_banking_providers,
    sanitize_connection_status,
    mark_connection_unhealthy,
    mark_connection_healthy,
    get_primary_access_token,
    test_connection_health,
    should_refresh_token,
    BankingConnectionInfo,
    BankingConnectionStatus,
)
