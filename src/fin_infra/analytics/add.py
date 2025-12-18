"""FastAPI integration for analytics module.

Provides add_analytics() helper to mount analytics endpoints.
MUST use svc-infra dual routers (user_router) - NEVER generic APIRouter.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fastapi import FastAPI

from .ease import AnalyticsEngine, easy_analytics
from .models import (
    BenchmarkComparison,
    CashFlowAnalysis,
    GrowthProjection,
    PersonalizedSpendingAdvice,
    PortfolioMetrics,
    SavingsRateData,
    SpendingInsight,
)


# Request/Response models for API
class NetWorthForecastRequest(BaseModel):
    """Request model for net worth forecast endpoint."""

    user_id: str = Field(..., description="User identifier")
    years: int = Field(default=30, ge=1, le=50, description="Projection years (1-50)")
    initial_net_worth: float | None = Field(None, description="Override initial net worth")
    annual_contribution: float | None = Field(None, description="Annual savings contribution")
    conservative_return: float | None = Field(
        None, description="Conservative return rate (e.g., 0.05 = 5%)"
    )
    moderate_return: float | None = Field(
        None, description="Moderate return rate (e.g., 0.07 = 7%)"
    )
    aggressive_return: float | None = Field(
        None, description="Aggressive return rate (e.g., 0.10 = 10%)"
    )


def add_analytics(
    app: FastAPI,
    prefix: str = "/analytics",
    provider: AnalyticsEngine | None = None,
    include_in_schema: bool = True,
) -> AnalyticsEngine:
    """Add analytics endpoints to FastAPI application.

    Mounts analytics endpoints and registers scoped documentation on the landing page.
    Uses svc-infra user_router for authenticated endpoints (MANDATORY).

    Args:
        app: FastAPI application instance
        prefix: URL prefix for analytics endpoints (default: "/analytics")
        provider: Optional pre-configured AnalyticsEngine instance
        include_in_schema: Include in OpenAPI schema (default: True)

    Returns:
        AnalyticsEngine instance (either provided or newly created)

    Raises:
        ValueError: If invalid configuration provided

    Example:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.analytics import add_analytics
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> analytics = add_analytics(app)
        >>>
        >>> # Access at /analytics/cash-flow, /analytics/savings-rate, etc.
        >>> # Visit /docs to see "Analytics" card on landing page

    Endpoints mounted:
        - GET /analytics/cash-flow - Cash flow analysis
        - GET /analytics/savings-rate - Savings rate calculation
        - GET /analytics/spending-insights - Spending pattern analysis
        - GET /analytics/spending-advice - AI-powered spending advice
        - GET /analytics/portfolio - Portfolio performance metrics
        - GET /analytics/performance - Portfolio vs benchmark comparison
        - POST /analytics/forecast-net-worth - Long-term net worth projection

    API Compliance:
        - Uses svc-infra public_router (user_id as query parameter)
        - Calls add_prefixed_docs() for landing page card
        - Stores provider on app.state.analytics_engine
        - Returns provider for programmatic access

    Note:
        Analytics endpoints use public_router and take user_id as a query parameter
        rather than user_router with auth tokens. This is because analytics aggregate
        data from multiple providers and don't require database-backed authentication.
        For production, add authentication middleware at the app level.
    """
    # 1. Create or use provided analytics engine
    if provider is None:
        provider = easy_analytics()

    # 2. Store on app state
    app.state.analytics_engine = provider

    # 3. Import public_router from svc-infra
    # Note: Using public_router instead of user_router because analytics endpoints
    # take user_id as query parameter (not from auth token) and don't need database
    from svc_infra.api.fastapi.dual.public import public_router

    router = public_router(prefix=prefix, tags=["Analytics"])

    # 4. Define endpoint handlers

    @router.get(
        "/cash-flow",
        response_model=CashFlowAnalysis,
        summary="Cash Flow Analysis",
        description="Analyze income and expenses over a period",
    )
    async def get_cash_flow(
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        period_days: int | None = None,
    ) -> CashFlowAnalysis:
        """
        Calculate cash flow analysis for a user.

        Provides income, expenses, and net cash flow with breakdowns.
        """
        return await provider.cash_flow(
            user_id,
            start_date=start_date,
            end_date=end_date,
            period_days=period_days,
        )

    @router.get("/savings-rate", response_model=SavingsRateData)
    async def get_savings_rate(
        user_id: str,
        definition: str = Query("net", description="Savings definition: gross/net/discretionary"),
        period: str = Query("monthly", description="Period: weekly/monthly/quarterly/yearly"),
    ) -> SavingsRateData:
        """Calculate user's savings rate."""
        try:
            return await provider.savings_rate(
                user_id=user_id,
                definition=definition,
                period=period,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get(
        "/spending-insights",
        response_model=SpendingInsight,
        summary="Spending Insights",
        description="Analyze spending patterns and trends",
    )
    async def get_spending_insights(
        user_id: str,
        period_days: int | None = None,
        include_trends: bool = True,
    ) -> SpendingInsight:
        """
        Analyze spending patterns for a user.

        Provides top merchants, category breakdowns, and trend analysis.
        """
        return await provider.spending_insights(
            user_id,
            period_days=period_days,
            include_trends=include_trends,
        )

    @router.get(
        "/spending-advice",
        response_model=PersonalizedSpendingAdvice,
        summary="Spending Advice",
        description="Get AI-powered personalized spending recommendations",
    )
    async def get_spending_advice(
        user_id: str,
        period_days: int | None = None,
    ) -> PersonalizedSpendingAdvice:
        """
        Generate personalized spending advice using AI.

        Provides tailored recommendations based on spending patterns.
        """
        return await provider.spending_advice(
            user_id,
            period_days=period_days,
        )

    @router.get(
        "/portfolio",
        response_model=PortfolioMetrics,
        summary="Portfolio Metrics",
        description="Calculate portfolio performance metrics with optional real holdings data",
    )
    async def get_portfolio_metrics(
        user_id: str,
        accounts: list[str] | None = None,
        with_holdings: bool = Query(
            False, description="Use real holdings data from investment provider for accurate P/L"
        ),
        access_token: str | None = Query(
            None, description="Investment provider access token (required if with_holdings=true)"
        ),
    ) -> PortfolioMetrics:
        """
        Calculate portfolio performance metrics.

        By default, uses account balance data for portfolio calculations (mock holdings).
        When with_holdings=true and investment provider available, fetches real holdings
        for accurate profit/loss, cost basis, and asset allocation.

        Query Parameters:
            - user_id: User identifier
            - accounts: Optional list of account IDs to include
            - with_holdings: Use real holdings data (default: false)
            - access_token: Investment provider token (Plaid/SnapTrade, required if with_holdings=true)

        Returns:
            PortfolioMetrics with performance analysis

        Examples:
            # Mock-based calculation (balance only)
            GET /analytics/portfolio?user_id=user123

            # Real holdings calculation (accurate P/L)
            GET /analytics/portfolio?user_id=user123&with_holdings=true&access_token=plaid-token

        Note:
            Real holdings provide:
            - Accurate cost basis → real profit/loss
            - Security types → precise asset allocation
            - Current values → live portfolio tracking
        """
        # If with_holdings requested and investment provider available
        if with_holdings:
            # Check if investment provider is available on app state
            investment_provider = getattr(app.state, "investment_provider", None)

            if investment_provider and access_token:
                try:
                    # Fetch real holdings from investment provider
                    from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings

                    holdings = await investment_provider.get_holdings(
                        access_token=access_token,
                        account_ids=accounts,
                    )

                    # Calculate metrics from real holdings
                    return portfolio_metrics_with_holdings(holdings)

                except Exception as e:
                    # Fall back to balance-only calculation on error
                    # Log error but don't fail the request
                    import logging

                    logging.warning(f"Failed to fetch holdings, falling back to balance-only: {e}")
            elif with_holdings and not access_token:
                raise HTTPException(
                    status_code=400, detail="access_token required when with_holdings=true"
                )

        # Default: Use balance-only calculation (existing behavior)
        return await provider.portfolio_metrics(
            user_id,
            accounts=accounts,
        )

    @router.get(
        "/performance",
        response_model=BenchmarkComparison,
        summary="Portfolio Performance",
        description="Compare portfolio performance to benchmark",
    )
    async def get_benchmark_comparison(
        user_id: str,
        benchmark: str | None = None,
        period: str = "1y",
        accounts: list[str] | None = None,
    ) -> BenchmarkComparison:
        """
        Compare portfolio to benchmark (e.g., SPY, VTI).

        Provides alpha, beta, and relative performance metrics.
        """
        return await provider.benchmark_comparison(
            user_id,
            benchmark=benchmark,
            period=period,
            accounts=accounts,
        )

    @router.post(
        "/forecast-net-worth",
        response_model=GrowthProjection,
        summary="Net Worth Forecast",
        description="Project net worth growth over time",
    )
    async def forecast_net_worth(
        request: NetWorthForecastRequest,
    ) -> GrowthProjection:
        """
        Project net worth growth with multiple scenarios.

        Provides conservative, moderate, and aggressive projections.
        """
        # Build assumptions dict from request
        assumptions = {}
        if request.initial_net_worth is not None:
            assumptions["initial_net_worth"] = request.initial_net_worth
        if request.annual_contribution is not None:
            assumptions["annual_contribution"] = request.annual_contribution
        if request.conservative_return is not None:
            assumptions["conservative_return"] = request.conservative_return
        if request.moderate_return is not None:
            assumptions["moderate_return"] = request.moderate_return
        if request.aggressive_return is not None:
            assumptions["aggressive_return"] = request.aggressive_return

        return await provider.net_worth_projection(
            request.user_id,
            years=request.years,
            assumptions=assumptions if assumptions else None,
        )

    # 6. Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    # 7. Scoped docs removed (per architectural decision)
    # All analytics endpoints appear in main /docs

    # 8. Return analytics instance for programmatic access
    return provider
