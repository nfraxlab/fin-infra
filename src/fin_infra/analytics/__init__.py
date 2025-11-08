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

# Import actual implementations
from .ease import easy_analytics, AnalyticsEngine
from .add import add_analytics

__all__ = [
    "easy_analytics",
    "add_analytics",
    "AnalyticsEngine",
]
