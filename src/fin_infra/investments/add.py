"""FastAPI integration for investments module.

Provides add_investments() helper to mount investment endpoints for holdings,
transactions, accounts, allocation, and securities data.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional, Literal

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fastapi import FastAPI

from .ease import easy_investments
from .models import (
    Holding,
    InvestmentTransaction,
    InvestmentAccount,
    AssetAllocation,
    Security,
)
from .providers.base import InvestmentProvider


# Request models for API
class HoldingsRequest(BaseModel):
    """Request model for holdings endpoint."""

    access_token: Optional[str] = Field(None, description="Plaid access token (Plaid only)")
    user_id: Optional[str] = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: Optional[str] = Field(
        None, description="SnapTrade user secret (SnapTrade only)"
    )
    account_ids: Optional[list[str]] = Field(
        None, description="Filter by specific account IDs"
    )


class TransactionsRequest(BaseModel):
    """Request model for transactions endpoint."""

    access_token: Optional[str] = Field(None, description="Plaid access token (Plaid only)")
    user_id: Optional[str] = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: Optional[str] = Field(
        None, description="SnapTrade user secret (SnapTrade only)"
    )
    start_date: date = Field(..., description="Start date for transactions (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date for transactions (YYYY-MM-DD)")
    account_ids: Optional[list[str]] = Field(
        None, description="Filter by specific account IDs"
    )


class AccountsRequest(BaseModel):
    """Request model for investment accounts endpoint."""

    access_token: Optional[str] = Field(None, description="Plaid access token (Plaid only)")
    user_id: Optional[str] = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: Optional[str] = Field(
        None, description="SnapTrade user secret (SnapTrade only)"
    )


class AllocationRequest(BaseModel):
    """Request model for asset allocation endpoint."""

    access_token: Optional[str] = Field(None, description="Plaid access token (Plaid only)")
    user_id: Optional[str] = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: Optional[str] = Field(
        None, description="SnapTrade user secret (SnapTrade only)"
    )
    account_ids: Optional[list[str]] = Field(
        None, description="Filter by specific account IDs"
    )


class SecuritiesRequest(BaseModel):
    """Request model for securities endpoint."""

    access_token: Optional[str] = Field(None, description="Plaid access token (Plaid only)")
    user_id: Optional[str] = Field(None, description="SnapTrade user ID (SnapTrade only)")
    user_secret: Optional[str] = Field(
        None, description="SnapTrade user secret (SnapTrade only)"
    )
    security_ids: list[str] = Field(..., description="List of security IDs to retrieve")


def add_investments(
    app: FastAPI,
    prefix: str = "/investments",
    provider: Optional[InvestmentProvider] = None,
    include_in_schema: bool = True,
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
        - Uses svc-infra public_router (no database dependency)
        - Stores provider on app.state.investment_provider
        - Returns provider for programmatic access
        - All endpoints appear in main /docs (no scoped docs)

    Note:
        Investments endpoints use POST requests (not GET) because:
        1. Credentials should not be in URL query parameters (security)
        2. Request bodies are more suitable for sensitive data (tokens, secrets)
        3. Consistent with industry standards for financial APIs
    """
    # 1. Create or use provided investment provider
    if provider is None:
        provider = easy_investments()

    # 2. Store on app state
    app.state.investment_provider = provider

    # 3. Import public_router from svc-infra
    from svc_infra.api.fastapi.dual.public import public_router

    router = public_router(prefix=prefix, tags=["Investments"])

    # 4. Define endpoint handlers

    @router.post(
        "/holdings",
        response_model=list[Holding],
        summary="List Holdings",
        description="Fetch investment holdings with securities, quantities, and values",
    )
    async def get_holdings(request: HoldingsRequest) -> list[Holding]:
        """
        Retrieve investment holdings for a user's accounts.

        Supports both Plaid (access_token) and SnapTrade (user_id + user_secret).
        Returns holdings with security details, quantity, cost basis, current value.

        Raises:
            HTTPException: 401 if credentials invalid, 400 if validation fails
        """
        try:
            # Determine auth method and call provider
            if request.access_token:
                # Plaid authentication
                holdings = await provider.get_holdings(
                    access_token=request.access_token,
                    account_ids=request.account_ids,
                )
            elif request.user_id and request.user_secret:
                # SnapTrade authentication
                holdings = await provider.get_holdings(
                    access_token=f"{request.user_id}:{request.user_secret}",
                    account_ids=request.account_ids,
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either access_token (Plaid) or user_id + user_secret (SnapTrade)",
                )

            return holdings

        except HTTPException:
            # Re-raise HTTPException (400, 401, etc.) without modification
            raise
        except ValueError as e:
            # Invalid credentials or access token
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            # Generic errors
            raise HTTPException(status_code=500, detail=f"Failed to fetch holdings: {str(e)}")

    @router.post(
        "/transactions",
        response_model=list[InvestmentTransaction],
        summary="List Transactions",
        description="Fetch investment transactions (buy, sell, dividend, etc.) within date range",
    )
    async def get_transactions(request: TransactionsRequest) -> list[InvestmentTransaction]:
        """
        Retrieve investment transactions for a user's accounts.

        Returns buy/sell/dividend transactions within the specified date range.

        Raises:
            HTTPException: 401 if credentials invalid, 400 if validation fails
        """
        try:
            # Validate date range
            if request.start_date >= request.end_date:
                raise HTTPException(
                    status_code=400,
                    detail="start_date must be before end_date",
                )

            # Determine auth method and call provider
            if request.access_token:
                # Plaid authentication
                transactions = await provider.get_transactions(
                    access_token=request.access_token,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    account_ids=request.account_ids,
                )
            elif request.user_id and request.user_secret:
                # SnapTrade authentication
                transactions = await provider.get_transactions(
                    access_token=f"{request.user_id}:{request.user_secret}",
                    start_date=request.start_date,
                    end_date=request.end_date,
                    account_ids=request.account_ids,
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either access_token (Plaid) or user_id + user_secret (SnapTrade)",
                )

            return transactions

        except HTTPException:
            # Re-raise HTTPException (400, 401, etc.) without modification
            raise
        except ValueError as e:
            # Invalid credentials or date range
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            # Generic errors
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch transactions: {str(e)}"
            )

    @router.post(
        "/accounts",
        response_model=list[InvestmentAccount],
        summary="List Investment Accounts",
        description="Fetch investment accounts with aggregated holdings and performance",
    )
    async def get_accounts(request: AccountsRequest) -> list[InvestmentAccount]:
        """
        Retrieve investment accounts with aggregated holdings.

        Returns accounts with total value, cost basis, unrealized gain/loss.

        Raises:
            HTTPException: 401 if credentials invalid, 400 if validation fails
        """
        try:
            # Determine auth method and call provider
            if request.access_token:
                # Plaid authentication
                accounts = await provider.get_investment_accounts(
                    access_token=request.access_token,
                )
            elif request.user_id and request.user_secret:
                # SnapTrade authentication
                accounts = await provider.get_investment_accounts(
                    access_token=f"{request.user_id}:{request.user_secret}",
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either access_token (Plaid) or user_id + user_secret (SnapTrade)",
                )

            return accounts

        except ValueError as e:
            # Invalid credentials
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            # Generic errors
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch accounts: {str(e)}"
            )

    @router.post(
        "/allocation",
        response_model=AssetAllocation,
        summary="Asset Allocation",
        description="Calculate portfolio asset allocation by security type and sector",
    )
    async def get_allocation(request: AllocationRequest) -> AssetAllocation:
        """
        Calculate asset allocation from holdings.

        Returns allocation percentages by security type (equity, bond, cash, etc.)
        and sector (Technology, Healthcare, etc.).

        Raises:
            HTTPException: 401 if credentials invalid, 400 if validation fails
        """
        try:
            # Fetch holdings first
            if request.access_token:
                # Plaid authentication
                holdings = await provider.get_holdings(
                    access_token=request.access_token,
                    account_ids=request.account_ids,
                )
            elif request.user_id and request.user_secret:
                # SnapTrade authentication
                holdings = await provider.get_holdings(
                    access_token=f"{request.user_id}:{request.user_secret}",
                    account_ids=request.account_ids,
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either access_token (Plaid) or user_id + user_secret (SnapTrade)",
                )

            # Calculate allocation using base provider helper
            allocation = provider.calculate_allocation(holdings)
            return allocation

        except ValueError as e:
            # Invalid credentials
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            # Generic errors
            raise HTTPException(
                status_code=500, detail=f"Failed to calculate allocation: {str(e)}"
            )

    @router.post(
        "/securities",
        response_model=list[Security],
        summary="Security Details",
        description="Fetch security information (ticker, name, type, price)",
    )
    async def get_securities(request: SecuritiesRequest) -> list[Security]:
        """
        Retrieve security details for given security IDs.

        Returns security information including ticker, name, type, and current price.

        Raises:
            HTTPException: 401 if credentials invalid, 400 if validation fails
        """
        try:
            # Determine auth method and call provider
            if request.access_token:
                # Plaid authentication
                securities = await provider.get_securities(
                    access_token=request.access_token,
                    security_ids=request.security_ids,
                )
            elif request.user_id and request.user_secret:
                # SnapTrade authentication
                securities = await provider.get_securities(
                    access_token=f"{request.user_id}:{request.user_secret}",
                    security_ids=request.security_ids,
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either access_token (Plaid) or user_id + user_secret (SnapTrade)",
                )

            return securities

        except ValueError as e:
            # Invalid credentials
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            # Generic errors
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch securities: {str(e)}"
            )

    # 5. Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    # 6. Scoped docs removed (per architectural decision)
    # All investment endpoints appear in main /docs

    # 7. Return provider instance for programmatic access
    return provider


# Alias for backward compatibility
add_investments_impl = add_investments

__all__ = ["add_investments", "add_investments_impl"]
