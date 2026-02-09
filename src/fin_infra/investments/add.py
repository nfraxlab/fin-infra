"""FastAPI integration for investments module.

Provides add_investments() helper to mount investment endpoints for holdings,
transactions, accounts, allocation, and securities data.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .ease import easy_investments
from .models import (
    AssetAllocation,
    Holding,
    InvestmentAccount,
    InvestmentTransaction,
    Security,
)
from .providers.base import InvestmentProvider

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI

# Import Identity for dependency injection
try:
    from svc_infra.api.fastapi.auth.security import Identity
except ImportError:
    # Fallback type for type checking if svc-infra not installed
    Identity = None  # type: ignore


# Request models for API
class HoldingsRequest(BaseModel):
    """Request model for holdings endpoint."""

    access_token: str | None = Field(None, description="Plaid access token (Plaid only)")
    user_id: str | None = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: str | None = Field(None, description="SnapTrade user secret (SnapTrade only)")
    account_ids: list[str] | None = Field(None, description="Filter by specific account IDs")


class TransactionsRequest(BaseModel):
    """Request model for transactions endpoint."""

    access_token: str | None = Field(None, description="Plaid access token (Plaid only)")
    user_id: str | None = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: str | None = Field(None, description="SnapTrade user secret (SnapTrade only)")
    start_date: date = Field(..., description="Start date for transactions (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date for transactions (YYYY-MM-DD)")
    account_ids: list[str] | None = Field(None, description="Filter by specific account IDs")


class AccountsRequest(BaseModel):
    """Request model for investment accounts endpoint."""

    access_token: str | None = Field(None, description="Plaid access token (Plaid only)")
    user_id: str | None = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: str | None = Field(None, description="SnapTrade user secret (SnapTrade only)")


class AllocationRequest(BaseModel):
    """Request model for asset allocation endpoint."""

    access_token: str | None = Field(None, description="Plaid access token (Plaid only)")
    user_id: str | None = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: str | None = Field(None, description="SnapTrade user secret (SnapTrade only)")
    account_ids: list[str] | None = Field(None, description="Filter by specific account IDs")


class SecuritiesRequest(BaseModel):
    """Request model for securities endpoint."""

    access_token: str | None = Field(None, description="Plaid access token (Plaid only)")
    user_id: str | None = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: str | None = Field(None, description="SnapTrade user secret (SnapTrade only)")
    security_ids: list[str] = Field(..., description="List of security IDs to retrieve")


def add_investments(
    app: FastAPI,
    prefix: str = "/investments",
    provider: InvestmentProvider | None = None,
    include_in_schema: bool = True,
    tags: list[str] | None = None,
) -> InvestmentProvider:
    """Add investment endpoints to FastAPI application.

    Mounts investment endpoints for holdings, transactions, accounts, allocation,
    and securities data. Supports both Plaid (access_token) and SnapTrade
    (user_id + user_secret) authentication patterns.

    Args:
        app: FastAPI application instance
        prefix: URL prefix for investment endpoints (default: "/investments")
        provider: Optional pre-configured InvestmentProvider instance
        include_in_schema: Include in OpenAPI schema (default: True)
        tags: OpenAPI tags for the router (default: ["Investments"])

    Returns:
        InvestmentProvider instance (either provided or newly created)

    Raises:
        ValueError: If invalid configuration provided
        HTTPException: 401 for invalid credentials, 400 for validation errors

    Example:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.investments import add_investments
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> investments = add_investments(app)
        >>>
        >>> # Access at /investments/holdings, /investments/transactions, etc.
        >>> # Visit /docs to see "Investment Holdings" card on landing page

    Endpoints mounted:
        - POST /investments/holdings - List investment holdings
        - POST /investments/transactions - List investment transactions
        - POST /investments/accounts - List investment accounts
        - POST /investments/allocation - Get asset allocation
        - POST /investments/securities - Get security details

    Authentication patterns:
        Plaid:   POST /investments/holdings with {"access_token": "...", "account_ids": [...]}
        SnapTrade: POST /investments/holdings with {"user_id": "...", "user_secret": "...", "account_ids": [...]}

    API Compliance:
        - Uses svc-infra user_router (requires user authentication)
        - Stores provider on app.state.investment_provider
        - Returns provider for programmatic access
        - All endpoints appear in main /docs (no scoped docs)

    Authentication Layers:
        1. App Authentication (user_router): Handled by svc-infra
           - Validates user's JWT/session cookie
           - Ensures user is logged into YOUR application
           - Provides identity.user with authenticated user

        2. Provider Access (endpoint logic): Handled by these endpoints
           - Gets Plaid/SnapTrade access token for the provider
           - Auto-resolves from identity.user.banking_providers
           - Can be overridden with explicit token in request body
           - Used to call external provider APIs (Plaid, SnapTrade)

        POST requests are used (not GET) because:
        1. Provider credentials should not be in URL query parameters
        2. Request bodies are more suitable for sensitive data
        3. Consistent with industry standards for financial APIs
    """
    # 1. Create or use provided investment provider
    if provider is None:
        provider = easy_investments()

    # 2. Store on app state
    app.state.investment_provider = provider

    # 3. Capture provider in local variable for closure
    investment_provider = provider

    # 4. Import user_router from svc-infra (requires authentication)
    from svc_infra.api.fastapi.dual.protected import user_router

    router = user_router(prefix=prefix, tags=tags or ["Investments"])

    def _resolve_plaid_access_token(identity: Identity) -> str:
        """Resolve primary Plaid access token, supporting multi-item format."""
        banking_providers = getattr(identity.user, "banking_providers", {})
        if not banking_providers or "plaid" not in banking_providers:
            raise HTTPException(
                status_code=400,
                detail="No Plaid connection found. Please connect your accounts first.",
            )

        plaid_data = banking_providers["plaid"]

        # Multi-item format: {"items": {"item_id": {"access_token": "..."}}}
        if isinstance(plaid_data, dict) and "items" in plaid_data:
            for item_data in plaid_data["items"].values():
                if isinstance(item_data, dict) and item_data.get("is_healthy", True):
                    token = item_data.get("access_token")
                    if token:
                        return str(token)
            # Fallback to any token if none marked healthy
            for item_data in plaid_data["items"].values():
                if isinstance(item_data, dict):
                    token = item_data.get("access_token")
                    if token:
                        return str(token)

        # Legacy format: {"access_token": "..."}
        access_token = plaid_data.get("access_token") if isinstance(plaid_data, dict) else None
        if not access_token:
            raise HTTPException(
                status_code=400, detail="No access token found. Please reconnect your accounts."
            )
        return str(access_token)

    def _resolve_all_plaid_access_tokens(identity: Identity) -> list[str]:
        """Resolve ALL Plaid access tokens for multi-item support.

        Returns a list of access tokens from all connected Plaid items.
        Falls back to _resolve_plaid_access_token for legacy single-token format.
        """
        banking_providers = getattr(identity.user, "banking_providers", {})
        if not banking_providers or "plaid" not in banking_providers:
            raise HTTPException(
                status_code=400,
                detail="No Plaid connection found. Please connect your accounts first.",
            )

        plaid_data = banking_providers["plaid"]
        tokens: list[str] = []

        # Multi-item format: {"items": {"item_id": {"access_token": "..."}}}
        if isinstance(plaid_data, dict) and "items" in plaid_data:
            for item_data in plaid_data["items"].values():
                if isinstance(item_data, dict):
                    token = item_data.get("access_token")
                    if token:
                        tokens.append(str(token))

        # Legacy single-token format
        if not tokens:
            access_token = plaid_data.get("access_token") if isinstance(plaid_data, dict) else None
            if access_token:
                tokens.append(str(access_token))

        if not tokens:
            raise HTTPException(
                status_code=400, detail="No access token found. Please reconnect your accounts."
            )
        return tokens

    # 4. Define endpoint handlers

    @router.post(
        "/holdings",
        response_model=list[Holding],
        summary="List Holdings",
        description="Fetch investment holdings with securities, quantities, and values",
    )
    async def get_holdings(request: HoldingsRequest, identity: Identity) -> list[Holding]:
        """
        Retrieve investment holdings for authenticated user's accounts.

        App authentication: Handled by user_router (identity.user guaranteed)
        Provider access: Auto-resolved from user's stored Plaid token or explicit override
        """
        # Get access token - prefer explicit, fallback to user's stored token
        if request.access_token:
            access_tokens = [request.access_token]
        elif request.user_id and request.user_secret:
            access_tokens = [f"{request.user_id}:{request.user_secret}"]
        else:
            # Auto-resolve ALL tokens from authenticated user for multi-item support
            access_tokens = _resolve_all_plaid_access_tokens(identity)

        # Fetch holdings from ALL items and merge results
        all_holdings: list[Holding] = []
        for access_token in access_tokens:
            try:
                holdings = await investment_provider.get_holdings(
                    access_token=access_token,
                    account_ids=request.account_ids,
                )
                if holdings:
                    all_holdings.extend(holdings)
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except Exception as e:
                if len(access_tokens) == 1:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch holdings: {e}")
                logger.warning("Failed to fetch holdings for an item: %s", e)
        return all_holdings

    @router.post(
        "/transactions",
        response_model=list[InvestmentTransaction],
        summary="List Transactions",
        description="Fetch investment transactions (buy, sell, dividend, etc.) within date range",
    )
    async def get_transactions(
        request: TransactionsRequest, identity: Identity
    ) -> list[InvestmentTransaction]:
        """
        Retrieve investment transactions for authenticated user's accounts.

        App authentication: Handled by user_router (identity.user guaranteed)
        Provider access: Auto-resolved from user's stored Plaid token or explicit override
        """
        # Validate date range
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before end_date",
            )

        # Get access token
        if request.access_token:
            access_tokens = [request.access_token]
        elif request.user_id and request.user_secret:
            access_tokens = [f"{request.user_id}:{request.user_secret}"]
        else:
            access_tokens = _resolve_all_plaid_access_tokens(identity)

        # Fetch transactions from ALL items and merge results
        all_transactions: list[InvestmentTransaction] = []
        for access_token in access_tokens:
            try:
                transactions = await investment_provider.get_transactions(
                    access_token=access_token,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    account_ids=request.account_ids,
                )
                if transactions:
                    all_transactions.extend(transactions)
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except Exception as e:
                if len(access_tokens) == 1:
                    raise HTTPException(
                        status_code=500, detail=f"Failed to fetch transactions: {e}"
                    )
                logger.warning("Failed to fetch transactions for an item: %s", e)
        return all_transactions

    @router.post(
        "/accounts",
        response_model=list[InvestmentAccount],
        summary="List Investment Accounts",
        description="Fetch investment accounts with aggregated holdings and performance",
    )
    async def get_accounts(request: AccountsRequest, identity: Identity) -> list[InvestmentAccount]:
        """
        Retrieve investment accounts for authenticated user.

        App authentication: Handled by user_router (identity.user guaranteed)
        Provider access: Auto-resolved from user's stored Plaid token or explicit override
        """
        if request.access_token:
            access_tokens = [request.access_token]
        elif request.user_id and request.user_secret:
            access_tokens = [f"{request.user_id}:{request.user_secret}"]
        else:
            access_tokens = _resolve_all_plaid_access_tokens(identity)

        # Fetch accounts from ALL items and merge results
        all_accounts: list[InvestmentAccount] = []
        for access_token in access_tokens:
            try:
                accounts = await investment_provider.get_investment_accounts(
                    access_token=access_token,
                )
                if accounts:
                    all_accounts.extend(accounts)
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except Exception as e:
                if len(access_tokens) == 1:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {e}")
                logger.warning("Failed to fetch accounts for an item: %s", e)
        return all_accounts

    @router.post(
        "/allocation",
        response_model=AssetAllocation,
        summary="Asset Allocation",
        description="Calculate portfolio asset allocation by security type and sector",
    )
    async def get_allocation(request: AllocationRequest, identity: Identity) -> AssetAllocation:
        """
        Calculate asset allocation for authenticated user's holdings.

        App authentication: Handled by user_router (identity.user guaranteed)
        Provider access: Auto-resolved from user's stored Plaid token or explicit override
        """
        if request.access_token:
            access_tokens = [request.access_token]
        elif request.user_id and request.user_secret:
            access_tokens = [f"{request.user_id}:{request.user_secret}"]
        else:
            access_tokens = _resolve_all_plaid_access_tokens(identity)

        # Fetch holdings from ALL items for allocation calculation
        all_holdings: list[Holding] = []
        for access_token in access_tokens:
            try:
                holdings = await investment_provider.get_holdings(
                    access_token=access_token,
                    account_ids=request.account_ids,
                )
                if holdings:
                    all_holdings.extend(holdings)
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except Exception as e:
                if len(access_tokens) == 1:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch allocation: {e}")
                logger.warning("Failed to fetch holdings for allocation: %s", e)
        holdings = all_holdings

        # Calculate allocation using base provider helper
        allocation = investment_provider.calculate_allocation(holdings)
        return allocation

    @router.post(
        "/securities",
        response_model=list[Security],
        summary="Security Details",
        description="Fetch security information (ticker, name, type, price)",
    )
    async def get_securities(request: SecuritiesRequest, identity: Identity) -> list[Security]:
        """
        Retrieve security details for authenticated user.

        App authentication: Handled by user_router (identity.user guaranteed)
        Provider access: Auto-resolved from user's stored Plaid token or explicit override
        """
        if request.access_token:
            access_tokens = [request.access_token]
        elif request.user_id and request.user_secret:
            access_tokens = [f"{request.user_id}:{request.user_secret}"]
        else:
            access_tokens = _resolve_all_plaid_access_tokens(identity)

        # Fetch securities from ALL items and merge (deduplicate by security_id)
        seen_ids: set[str] = set()
        all_securities: list[Security] = []
        for access_token in access_tokens:
            try:
                securities = await investment_provider.get_securities(
                    access_token=access_token,
                    security_ids=request.security_ids,
                )
                for sec in securities or []:
                    if sec.security_id not in seen_ids:
                        seen_ids.add(sec.security_id)
                        all_securities.append(sec)
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            except Exception as e:
                if len(access_tokens) == 1:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch securities: {e}")
                logger.warning("Failed to fetch securities for an item: %s", e)
        return all_securities

    # 5. Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    # 6. Scoped docs removed (per architectural decision)
    # All investment endpoints appear in main /docs

    # 7. Return provider instance for programmatic access
    return provider


# Alias for backward compatibility
add_investments_impl = add_investments

__all__ = ["add_investments", "add_investments_impl"]
