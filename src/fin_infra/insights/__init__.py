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

from .models import Insight, InsightFeed, InsightPriority, InsightCategory
from .aggregator import aggregate_insights, get_user_insights

__all__ = [
    "Insight",
    "InsightFeed",
    "InsightPriority",
    "InsightCategory",
    "aggregate_insights",
    "get_user_insights",
]
