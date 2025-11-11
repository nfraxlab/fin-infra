"""Recurring transaction summary aggregation and analysis.

This module provides functionality to aggregate all detected recurring transactions
for a user and generate insights about their subscriptions, recurring bills, and
potential savings opportunities.

Features:
- Aggregate all recurring patterns for a user
- Separate subscriptions (expenses) vs recurring income
- Calculate total monthly cost
- Group patterns by category
- Identify cancellation opportunities (unused subscriptions, duplicate services)
- Track recurring income sources

Example usage:
    from fin_infra.recurring.summary import get_recurring_summary

    # Get summary for a user
    summary = get_recurring_summary(
        user_id="user_123",
        transactions=user_transactions
    )

    print(f"Total monthly cost: ${summary.total_monthly_cost:.2f}")
    print(f"Active subscriptions: {len(summary.subscriptions)}")
    print(f"Cancellation opportunities: {len(summary.cancellation_opportunities)}")

Integration with svc-infra:
- Cache: Results cached with 24h TTL (use svc_infra.cache)
- Storage: User transaction data from svc_infra.db
- Jobs: Background updates via svc_infra.jobs
"""

from __future__ import annotations

from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from pydantic import BaseModel, Field, ConfigDict

from fin_infra.recurring.models import RecurringPattern, PatternType


__all__ = [
    "RecurringItem",
    "CancellationOpportunity",
    "RecurringSummary",
    "get_recurring_summary",
]


class RecurringItem(BaseModel):
    """A single recurring transaction item (subscription or recurring bill)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_name": "Netflix",
                "category": "entertainment",
                "amount": 15.99,
                "cadence": "monthly",
                "monthly_cost": 15.99,
                "is_subscription": True,
                "next_charge_date": "2025-12-15",
                "confidence": 0.98,
            }
        }
    )

    merchant_name: str = Field(..., description="Normalized merchant name")
    category: str = Field(..., description="Transaction category")
    amount: float = Field(..., description="Recurring amount (or average for variable)")
    cadence: str = Field(..., description="Recurrence frequency (monthly, quarterly, annual)")
    monthly_cost: float = Field(..., description="Normalized monthly cost")
    is_subscription: bool = Field(
        ..., description="True if subscription, False if recurring income"
    )
    next_charge_date: str = Field(..., description="Next expected charge date (ISO format)")
    confidence: float = Field(..., description="Detection confidence (0.0-1.0)")


class CancellationOpportunity(BaseModel):
    """A potential opportunity to cancel or optimize a recurring charge."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_name": "Hulu",
                "reason": "Duplicate streaming service - also subscribed to Netflix",
                "monthly_savings": 7.99,
                "category": "entertainment",
            }
        }
    )

    merchant_name: str = Field(..., description="Merchant to consider canceling")
    reason: str = Field(..., description="Why this might be worth canceling")
    monthly_savings: float = Field(..., description="Potential monthly savings")
    category: str = Field(..., description="Transaction category")


class RecurringSummary(BaseModel):
    """Complete summary of user's recurring transactions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_123",
                "total_monthly_cost": 145.50,
                "total_monthly_income": 2500.00,
                "subscriptions": [],
                "recurring_income": [],
                "by_category": {"entertainment": 31.98, "utilities": 113.52},
                "cancellation_opportunities": [],
                "generated_at": "2025-11-10T12:00:00Z",
            }
        }
    )

    user_id: str = Field(..., description="User identifier")
    total_monthly_cost: float = Field(..., description="Total monthly recurring expenses")
    total_monthly_income: float = Field(0.0, description="Total monthly recurring income")
    subscriptions: List[RecurringItem] = Field(
        default_factory=list, description="List of recurring expense items"
    )
    recurring_income: List[RecurringItem] = Field(
        default_factory=list, description="List of recurring income items"
    )
    by_category: Dict[str, float] = Field(
        default_factory=dict, description="Monthly cost grouped by category"
    )
    cancellation_opportunities: List[CancellationOpportunity] = Field(
        default_factory=list, description="Potential subscriptions to cancel"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When this summary was generated",
    )


def _calculate_monthly_cost(amount: float, cadence: str) -> float:
    """Convert any cadence to monthly cost.

    Args:
        amount: Transaction amount
        cadence: Cadence type (monthly, quarterly, annual, biweekly)

    Returns:
        Monthly cost normalized from the cadence
    """
    cadence_lower = cadence.lower()

    if cadence_lower == "monthly":
        return amount
    elif cadence_lower == "quarterly":
        return amount / 3.0
    elif cadence_lower == "annual":
        return amount / 12.0
    elif cadence_lower == "biweekly":
        return amount * 26.0 / 12.0  # 26 biweekly periods per year
    else:
        # Default to monthly if unknown
        return amount


def _identify_cancellation_opportunities(
    subscriptions: List[RecurringItem],
) -> List[CancellationOpportunity]:
    """Identify potential cancellation opportunities from subscriptions.

    Looks for:
    - Duplicate services in the same category
    - Low-value subscriptions
    - Suspicious patterns

    Args:
        subscriptions: List of subscription items

    Returns:
        List of cancellation opportunities
    """
    opportunities = []

    # Group by category
    by_category: Dict[str, List[RecurringItem]] = defaultdict(list)
    for sub in subscriptions:
        by_category[sub.category].append(sub)

    # Check for duplicates in entertainment (streaming services)
    if "entertainment" in by_category:
        entertainment = by_category["entertainment"]
        streaming_keywords = ["netflix", "hulu", "disney", "hbo", "prime", "apple", "paramount"]
        streaming_services = [
            s
            for s in entertainment
            if any(kw in s.merchant_name.lower() for kw in streaming_keywords)
        ]

        if len(streaming_services) > 2:
            # More than 2 streaming services might be excessive
            # Suggest canceling the most expensive one after the top 2
            sorted_streaming = sorted(
                streaming_services, key=lambda s: s.monthly_cost, reverse=True
            )
            for service in sorted_streaming[2:]:  # Skip top 2
                opportunities.append(
                    CancellationOpportunity(
                        merchant_name=service.merchant_name,
                        reason=f"Multiple streaming services detected ({len(streaming_services)} total) - consider consolidating",
                        monthly_savings=service.monthly_cost,
                        category="entertainment",
                    )
                )

    # Check for duplicate cloud storage services
    storage_categories = ["software", "utilities", "technology"]
    for cat in storage_categories:
        if cat in by_category:
            items = by_category[cat]
            storage_keywords = ["dropbox", "icloud", "google", "onedrive", "box"]
            storage_services = [
                s for s in items if any(kw in s.merchant_name.lower() for kw in storage_keywords)
            ]

            if len(storage_services) > 1:
                # Suggest canceling all but the cheapest
                sorted_storage = sorted(storage_services, key=lambda s: s.monthly_cost)
                for service in sorted_storage[1:]:  # Keep cheapest, suggest canceling others
                    opportunities.append(
                        CancellationOpportunity(
                            merchant_name=service.merchant_name,
                            reason=f"Duplicate cloud storage service - also subscribed to {sorted_storage[0].merchant_name}",
                            monthly_savings=service.monthly_cost,
                            category=cat,
                        )
                    )

    # Check for low-confidence subscriptions (might be errors or infrequent)
    low_confidence = [s for s in subscriptions if s.confidence < 0.7]
    for sub in low_confidence:
        opportunities.append(
            CancellationOpportunity(
                merchant_name=sub.merchant_name,
                reason=f"Low detection confidence ({sub.confidence:.1%}) - verify if still active",
                monthly_savings=sub.monthly_cost,
                category=sub.category,
            )
        )

    return opportunities


def get_recurring_summary(
    user_id: str,
    patterns: List[RecurringPattern],
    category_map: Optional[Dict[str, str]] = None,
) -> RecurringSummary:
    """Generate a comprehensive recurring transaction summary for a user.

    Aggregates all detected recurring patterns and calculates statistics,
    identifies opportunities, and groups by category.

    Args:
        user_id: User identifier
        patterns: List of detected recurring patterns
        category_map: Optional mapping of merchant names to categories

    Returns:
        RecurringSummary with aggregated data and insights

    Examples:
        >>> patterns = detect_recurring_patterns(transactions)
        >>> summary = get_recurring_summary("user_123", patterns)
        >>> print(f"Monthly cost: ${summary.total_monthly_cost:.2f}")
        >>> for opp in summary.cancellation_opportunities:
        ...     print(f"Consider canceling {opp.merchant_name}: {opp.reason}")

    Notes:
        - Results should be cached with 24h TTL in production
        - Income patterns are identified by negative amounts
        - Category mapping can be provided or defaults to "uncategorized"
    """
    subscriptions = []
    recurring_income = []
    by_category: Dict[str, float] = defaultdict(float)

    for pattern in patterns:
        # Determine amount (use fixed amount or average of range)
        if pattern.pattern_type == PatternType.FIXED and pattern.amount is not None:
            amount = pattern.amount
        elif pattern.amount_range is not None:
            # Use average of range
            amount = sum(pattern.amount_range) / 2.0
        else:
            # Fallback to 0 if no amount info
            amount = 0.0

        # Calculate monthly cost
        monthly_cost = _calculate_monthly_cost(abs(amount), pattern.cadence.value)

        # Determine category
        merchant_lower = pattern.normalized_merchant.lower()
        if category_map and merchant_lower in category_map:
            category = category_map[merchant_lower]
        else:
            # Simple category inference
            if any(kw in merchant_lower for kw in ["netflix", "spotify", "hulu", "disney", "hbo"]):
                category = "entertainment"
            elif any(kw in merchant_lower for kw in ["gym", "fitness", "yoga"]):
                category = "fitness"
            elif any(
                kw in merchant_lower for kw in ["electric", "gas", "water", "internet", "phone"]
            ):
                category = "utilities"
            elif any(kw in merchant_lower for kw in ["insurance", "medical", "health"]):
                category = "insurance"
            elif any(kw in merchant_lower for kw in ["dropbox", "icloud", "adobe", "microsoft"]):
                category = "software"
            else:
                category = "other"

        # Create recurring item
        item = RecurringItem(
            merchant_name=pattern.normalized_merchant,
            category=category,
            amount=abs(amount),
            cadence=pattern.cadence.value,
            monthly_cost=monthly_cost,
            is_subscription=(amount > 0),  # Positive = expense, negative = income
            next_charge_date=pattern.next_expected_date.isoformat(),
            confidence=pattern.confidence,
        )

        # Categorize as subscription or income
        if amount > 0:
            subscriptions.append(item)
            by_category[category] += monthly_cost
        else:
            recurring_income.append(item)

    # Calculate totals
    total_monthly_cost = sum(s.monthly_cost for s in subscriptions)
    total_monthly_income = sum(s.monthly_cost for s in recurring_income)

    # Identify cancellation opportunities
    cancellation_opportunities = _identify_cancellation_opportunities(subscriptions)

    return RecurringSummary(
        user_id=user_id,
        total_monthly_cost=total_monthly_cost,
        total_monthly_income=total_monthly_income,
        subscriptions=subscriptions,
        recurring_income=recurring_income,
        by_category=dict(by_category),
        cancellation_opportunities=cancellation_opportunities,
    )


# Production integration notes:
#
# 1. Caching (via svc-infra):
#    from svc_infra.cache import cache_read
#
#    @cache_read(ttl=86400)  # 24 hours
#    def get_recurring_summary_cached(user_id: str, patterns: List[RecurringPattern]):
#        return get_recurring_summary(user_id, patterns)
#
# 2. Background updates (via svc-infra jobs):
#    from svc_infra.jobs import easy_jobs
#
#    @worker.task(schedule="0 2 * * *")  # Daily at 2am
#    async def update_recurring_summaries():
#        """Update recurring summaries for all users."""
#        users = get_all_users()
#        for user in users:
#            patterns = get_user_recurring_patterns(user.id)
#            summary = get_recurring_summary(user.id, patterns)
#            cache_recurring_summary(user.id, summary)
#
# 3. Category enrichment:
#    from fin_infra.categorization import categorize_transaction
#
#    category_map = {}
#    for pattern in patterns:
#        category = categorize_transaction(pattern.merchant_name)
#        category_map[pattern.normalized_merchant.lower()] = category
#
#    summary = get_recurring_summary(user_id, patterns, category_map)
