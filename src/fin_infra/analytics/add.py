"""FastAPI integration for analytics module.

Provides add_analytics() helper to mount analytics endpoints.
MUST use svc-infra dual routers (user_router) - NEVER generic APIRouter.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fastapi import FastAPI

from .ease import easy_analytics, AnalyticsEngine
from .models import (
    CashFlowAnalysis,
    SavingsRateData,
    SpendingInsight,
    PersonalizedSpendingAdvice,
    PortfolioMetrics,
    BenchmarkComparison,
    GrowthProjection,
)


# Request/Response models for API
class NetWorthForecastRequest(BaseModel):
    """Request model for net worth forecast endpoint."""

    user_id: str = Field(..., description="User identifier")
    years: int = Field(default=30, ge=1, le=50, description="Projection years (1-50)")
    initial_net_worth: Optional[float] = Field(None, description="Override initial net worth")
    annual_contribution: Optional[float] = Field(None, description="Annual savings contribution")
    conservative_return: Optional[float] = Field(
        None, description="Conservative return rate (e.g., 0.05 = 5%)"
    )
    moderate_return: Optional[float] = Field(
        None, description="Moderate return rate (e.g., 0.07 = 7%)"
    )
    aggressive_return: Optional[float] = Field(
        None, description="Aggressive return rate (e.g., 0.10 = 10%)"
    )


def add_analytics(
    app: FastAPI,
    prefix: str = "/analytics",
    provider: Optional[AnalyticsEngine] = None,
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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period_days: Optional[int] = None,
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
        period_days: Optional[int] = None,
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
        period_days: Optional[int] = None,
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
        description="Calculate portfolio performance metrics",
    )
    async def get_portfolio_metrics(
        user_id: str,
        accounts: Optional[list[str]] = None,
    ) -> PortfolioMetrics:
        """
        Calculate portfolio performance metrics.

        Provides returns, allocation, and Sharpe ratio.
        """
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
        benchmark: Optional[str] = None,
        period: str = "1y",
        accounts: Optional[list[str]] = None,
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
