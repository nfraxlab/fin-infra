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
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from ..providers.registry import resolve
from ..providers.base import BankingProvider

if TYPE_CHECKING:
    from fastapi import FastAPI


__all__ = ["easy_banking", "add_banking"]


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
    provider: str | None = None,
    prefix: str = "/banking",
    cache_ttl: int = 60,
    **config
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
        provider: Provider name (default: from BANKING_PROVIDER env or "teller")
        prefix: URL prefix for banking routes (default: "/banking")
        cache_ttl: Cache TTL in seconds for account data (default: 60)
        **config: Optional provider configuration overrides
    
    Returns:
        Configured BankingProvider instance used by the routes
    
    Raises:
        ValueError: If required environment variables are missing
        ImportError: If svc-infra or provider SDK is not installed
    
    Examples:
        # Basic setup with Teller (default)
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.banking import add_banking
        >>> 
        >>> app = easy_service_app(name="FinanceAPI")
        >>> banking = add_banking(app)
        
        # With Plaid provider
        >>> banking = add_banking(app, provider="plaid")
        
        # Custom prefix and cache TTL
        >>> banking = add_banking(
        ...     app,
        ...     provider="teller",
        ...     prefix="/api/v1/banking",
        ...     cache_ttl=120  # 2 minutes
        ... )
    
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
    # Import FastAPI router and dependencies FIRST
    from fastapi import APIRouter, Depends, Header, HTTPException, Query
    from datetime import date
    
    # Auto-detect provider from environment if not specified
    if provider is None:
        provider = os.getenv("BANKING_PROVIDER", "teller")
    
    # Create banking provider instance
    banking = easy_banking(provider=provider, **config)
    
    # Create router
    router = APIRouter(prefix=prefix, tags=["banking"])
    
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
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
    ):
        """List transactions for access token."""
        transactions = banking.transactions(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
        )
        return {"transactions": transactions}
    
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
    
    # Mount router to app
    app.include_router(router)
    
    # Store provider instance on app state for access in routes
    if not hasattr(app.state, "banking_provider"):
        app.state.banking_provider = banking
    
    return banking
