"""
Unified insights feed aggregator for financial data.

Aggregates insights from multiple sources:
- Net worth tracking
- Spending analysis
- Portfolio analytics
- Tax opportunities
- Budget tracking
- Cash flow projections
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from .aggregator import aggregate_insights, get_user_insights
from .models import Insight, InsightCategory, InsightFeed, InsightPriority

logger = logging.getLogger(__name__)

__all__ = [
    "Insight",
    "InsightFeed",
    "InsightPriority",
    "InsightCategory",
    "aggregate_insights",
    "get_user_insights",
    "add_insights",
]


def add_insights(
    app: "FastAPI",
    *,
    prefix: str = "/insights",
) -> None:
    """
    Wire insights aggregation endpoints to FastAPI app.

    Mounts REST endpoints for fetching unified financial insights feed
    with user authentication via svc-infra dual routers.

    Mounted Routes:
        GET {prefix}
            Get user's insight feed (all insights or unread only)
            Query: include_read (bool, default: False)
            Response: InsightFeed with prioritized insights

        POST {prefix}/mark-read/{insight_id}
            Mark an insight as read
            Response: {"success": true}

    Args:
        app: FastAPI application instance
        prefix: URL prefix for insights routes (default: "/insights")

    Examples:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.insights import add_insights
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> add_insights(app)
        >>>
        >>> # Routes available:
        >>> # GET /insights?include_read=false
        >>> # POST /insights/mark-read/{insight_id}

    Integration with svc-infra:
        - Uses user_router (requires user authentication)
        - Integrated with svc-infra observability
        - Scoped docs at {prefix}/docs

    Note:
        Currently returns stub data. Full implementation requires:
        - Database integration for insight persistence
        - Real-time aggregation from net worth, budgets, goals, etc.
        - Notification system for critical insights
    """
    from fastapi import Query
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs

    # Import svc-infra user router (requires auth)
    from svc_infra.api.fastapi.dual.protected import user_router

    # Create router
    router = user_router(prefix=prefix, tags=["Insights"])

    @router.get("")
    async def get_insights(
        include_read: bool = Query(False, description="Include already-read insights"),
    ) -> InsightFeed:
        """
        Get user's unified insights feed.

        Returns insights from:
        - Net worth tracking (trend analysis)
        - Budget monitoring (overspending alerts)
        - Goal progress (behind/ahead tracking)
        - Recurring transactions (subscription detection)
        - Portfolio analytics (rebalancing suggestions)
        - Tax opportunities (loss harvesting)

        Insights are sorted by priority (critical > high > medium > low)
        and include unread/critical counts for UI badges.
        """
        # TODO: Get user_id from svc-infra auth context
        user_id = "demo_user"  # Placeholder
        return get_user_insights(user_id, include_read=include_read)

    @router.post("/mark-read/{insight_id}")
    async def mark_insight_read(insight_id: str):
        """Mark an insight as read."""
        # TODO: Update database with user_id from auth context
        return {"success": True, "insight_id": insight_id}

    # Register scoped docs BEFORE mounting router
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Insights Feed",
        auto_exclude_from_root=True,
        visible_envs=None,
    )

    # Mount router
    app.include_router(router, include_in_schema=True)

    logger.info("Insights feed enabled")
