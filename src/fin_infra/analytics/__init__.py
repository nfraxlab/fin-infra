"""Analytics module for financial calculations and analysis.

This module provides comprehensive financial analytics capabilities including:
- Cash flow analysis (income vs expenses, forecasting)
- Savings rate calculation (gross, net, discretionary)
- Spending insights (top merchants, category breakdown, anomalies)
- Portfolio analytics (returns, allocation, benchmarking)
- Growth projections (net worth forecasting with scenarios)

Serves multiple use cases:
- Personal finance apps (cash flow, savings tracking)
- Wealth management platforms (portfolio analytics, projections)
- Banking apps (spending insights, cash flow management)
- Investment trackers (portfolio performance, benchmarking)
- Business accounting (cash flow analysis, financial planning)

Example usage:
    from fin_infra.analytics import easy_analytics

    # Zero config (uses sensible defaults)
    analytics = easy_analytics()

    # Get cash flow analysis
    cash_flow = await analytics.calculate_cash_flow(
        user_id="user123",
        start_date="2025-01-01",
        end_date="2025-01-31"
    )

    # With FastAPI
    from svc_infra.api.fastapi.ease import easy_service_app
    from fin_infra.analytics import add_analytics

    app = easy_service_app(name="FinanceAPI")
    analytics = add_analytics(app, prefix="/analytics")

Dependencies:
    - fin_infra.banking (transaction data)
    - fin_infra.brokerage (investment data)
    - fin_infra.categorization (expense categorization)
    - fin_infra.recurring (predictable income/expenses)
    - fin_infra.net_worth (net worth snapshots)
    - svc_infra.cache (expensive calculation caching)
"""

from __future__ import annotations

__all__ = ["easy_analytics", "add_analytics"]


def easy_analytics(**config):
    """Create configured analytics engine with sensible defaults.

    This is the simplest way to get started with analytics. The function
    returns a ready-to-use AnalyticsEngine instance with all dependencies
    configured.

    Args:
        **config: Optional configuration overrides
            - cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
            - default_period_days: Default analysis period (default: 30)
            - savings_definition: "gross", "net", or "discretionary" (default: "net")
            - benchmark_symbol: Default benchmark ticker (default: "SPY")

    Returns:
        Configured AnalyticsEngine instance ready to use

    Raises:
        ValueError: If invalid configuration provided

    Example:
        >>> analytics = easy_analytics()
        >>> cash_flow = await analytics.calculate_cash_flow("user123", "2025-01-01", "2025-01-31")
        >>> print(f"Net cash flow: ${cash_flow.net_cash_flow}")
    """
    # TODO: Implement in Task 8
    raise NotImplementedError("easy_analytics() will be implemented in Task 8")


def add_analytics(app, prefix: str = "/analytics", provider=None):
    """Add analytics endpoints to FastAPI application.

    Mounts analytics endpoints and registers scoped documentation on the landing page.
    Uses svc-infra user_router for authenticated endpoints.

    Args:
        app: FastAPI application instance
        prefix: URL prefix for analytics endpoints (default: "/analytics")
        provider: Optional pre-configured AnalyticsEngine instance

    Returns:
        AnalyticsEngine instance (either provided or newly created)

    Example:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.analytics import add_analytics
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> analytics = add_analytics(app)
        >>>
        >>> # Access at /analytics/cash-flow, /analytics/savings-rate, etc.

    Endpoints mounted:
        - GET /analytics/cash-flow?user_id=...&start_date=...&end_date=...
        - GET /analytics/savings-rate?user_id=...&period=monthly
        - GET /analytics/spending-insights?user_id=...&period=30d
        - GET /analytics/portfolio?user_id=...&accounts=...
        - GET /analytics/performance?user_id=...&benchmark=SPY&period=1y
        - POST /analytics/forecast-net-worth (body: user_id, years, assumptions)
    """
    # TODO: Implement in Task 9
    raise NotImplementedError("add_analytics() will be implemented in Task 9")
