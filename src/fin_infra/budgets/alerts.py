"""Budget alerts and notifications.

Detects overspending, approaching limits, and unusual spending patterns.
Integrates with svc-infra webhooks for alert delivery.

Alert Types:
- Overspending: Spent > budgeted amount
- Approaching limit: Spent > 80% of budgeted
- Unusual spending: Spike in category (compared to historical average)

Generic Design:
- Configurable thresholds per category
- Works with all budget types
- Integrates with svc-infra webhooks for notifications

Example:
    >>> from fin_infra.budgets import BudgetTracker, check_budget_alerts
    >>>
    >>> # Create tracker and get alerts
    >>> tracker = BudgetTracker(db_engine=engine)
    >>> alerts = await check_budget_alerts(
    ...     budget_id="bud_123",
    ...     tracker=tracker,
    ...     thresholds={"Groceries": 90.0, "default": 80.0}
    ... )
    >>>
    >>> # Process alerts
    >>> for alert in alerts:
    ...     if alert.severity == "critical":
    ...         send_urgent_notification(alert.message)
    ...     elif alert.severity == "warning":
    ...         send_notification(alert.message)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from fin_infra.budgets.models import (
    AlertSeverity,
    AlertType,
    BudgetAlert,
    BudgetCategory,
)

if TYPE_CHECKING:
    from fin_infra.budgets.tracker import BudgetTracker


async def check_budget_alerts(
    budget_id: str,
    tracker: BudgetTracker,
    thresholds: Optional[dict[str, float]] = None,
) -> List[BudgetAlert]:
    """
    Check budget for alerts (overspending, approaching limits, unusual patterns).

    Detects three types of alerts:
    1. Overspending: Category spent > budgeted (severity: critical)
    2. Approaching limit: Category spent > threshold% of budgeted (severity: warning)
    3. Unusual spending: Spending spike compared to historical average (severity: info)

    Generic across applications:
    - Personal finance: Alert on dining overspending
    - Household: Alert on utility bill spikes
    - Business: Alert on department budget overruns
    - Project: Alert on project cost overruns

    Args:
        budget_id: Budget UUID to check
        tracker: BudgetTracker instance to get budget progress
        thresholds: Per-category alert thresholds (percentage of budget).
                   Example: {"Groceries": 90.0, "Restaurants": 85.0, "default": 80.0}
                   Default: {"default": 80.0} (80% threshold for all categories)

    Returns:
        List of BudgetAlert objects (may be empty if no alerts)

    Raises:
        ValueError: Budget not found

    Example:
        >>> # Check with default 80% threshold
        >>> alerts = await check_budget_alerts("bud_123", tracker)
        >>> print(len(alerts))  # 2
        >>> print(alerts[0].message)  # "Restaurants: $180.25 spent of $200.00 (90%)"
        >>>
        >>> # Check with custom thresholds
        >>> alerts = await check_budget_alerts(
        ...     "bud_123",
        ...     tracker,
        ...     thresholds={"Groceries": 90.0, "default": 80.0}
        ... )
        >>> for alert in alerts:
        ...     print(f"{alert.severity}: {alert.message}")
        warning: Restaurants spending at 90% of budget
        critical: Entertainment spent $120 of $100 budgeted (overspending)

    Integration:
        >>> # With svc-infra webhooks (Task 17 implementation)
        >>> # from svc_infra.webhooks import send_webhook
        >>> # for alert in alerts:
        >>> #     if alert.severity == "critical":
        >>> #         await send_webhook("budget_alert", alert.dict())
    """
    # Default threshold: 80% of budget
    if thresholds is None:
        thresholds = {"default": 80.0}

    # Get budget progress
    progress = await tracker.get_budget_progress(budget_id)

    alerts: List[BudgetAlert] = []

    # Check each category for alerts
    for category in progress.categories:
        # Skip if no spending
        if category.spent_amount == 0:
            continue

        # 1. Check for overspending (spent > budgeted)
        if category.spent_amount > category.budgeted_amount:
            alerts.append(
                _create_overspending_alert(
                    budget_id=budget_id,
                    category=category,
                )
            )
            continue  # Don't also trigger approaching_limit for overspending

        # 2. Check for approaching limit (spent > threshold% of budgeted)
        threshold = thresholds.get(category.category_name, thresholds.get("default", 80.0))
        if category.percent_used >= threshold:
            alerts.append(
                _create_approaching_limit_alert(
                    budget_id=budget_id,
                    category=category,
                    threshold=threshold,
                )
            )

    # 3. TODO (v2): Check for unusual spending patterns
    # This requires historical data and statistical analysis
    # Future implementation: Compare current spending to 3-month average
    # If current > (average * 1.5), create unusual_spending alert

    return alerts


def _create_overspending_alert(
    budget_id: str,
    category: BudgetCategory,
) -> BudgetAlert:
    """
    Create overspending alert (critical severity).

    Args:
        budget_id: Budget UUID
        category: Category with overspending

    Returns:
        BudgetAlert with critical severity

    Example:
        >>> category = BudgetCategory(
        ...     category_name="Restaurants",
        ...     budgeted_amount=200.00,
        ...     spent_amount=225.50,
        ...     remaining_amount=-25.50,
        ...     percent_used=112.75
        ... )
        >>> alert = _create_overspending_alert("bud_123", category)
        >>> print(alert.message)
        "Restaurants overspending: $225.50 spent of $200.00 budgeted (112.8% over)"
    """
    overage = category.spent_amount - category.budgeted_amount
    overage_pct = (overage / category.budgeted_amount) * 100

    message = (
        f"{category.category_name} overspending: "
        f"${category.spent_amount:.2f} spent of ${category.budgeted_amount:.2f} budgeted "
        f"(${overage:.2f} over, {overage_pct:.1f}% over budget)"
    )

    return BudgetAlert(
        budget_id=budget_id,
        category=category.category_name,
        alert_type=AlertType.OVERSPENDING,
        threshold=100.0,  # Threshold is 100% for overspending
        message=message,
        triggered_at=datetime.now(),
        severity=AlertSeverity.CRITICAL,
    )


def _create_approaching_limit_alert(
    budget_id: str,
    category: BudgetCategory,
    threshold: float,
) -> BudgetAlert:
    """
    Create approaching limit alert (warning severity).

    Args:
        budget_id: Budget UUID
        category: Category approaching limit
        threshold: Threshold percentage that triggered alert

    Returns:
        BudgetAlert with warning severity

    Example:
        >>> category = BudgetCategory(
        ...     category_name="Groceries",
        ...     budgeted_amount=600.00,
        ...     spent_amount=510.00,
        ...     remaining_amount=90.00,
        ...     percent_used=85.0
        ... )
        >>> alert = _create_approaching_limit_alert("bud_123", category, 80.0)
        >>> print(alert.message)
        "Groceries at 85.0% of budget: $510.00 spent of $600.00 (threshold: 80%)"
    """
    message = (
        f"{category.category_name} at {category.percent_used:.1f}% of budget: "
        f"${category.spent_amount:.2f} spent of ${category.budgeted_amount:.2f} "
        f"(${category.remaining_amount:.2f} remaining, threshold: {threshold:.0f}%)"
    )

    return BudgetAlert(
        budget_id=budget_id,
        category=category.category_name,
        alert_type=AlertType.APPROACHING_LIMIT,
        threshold=threshold,
        message=message,
        triggered_at=datetime.now(),
        severity=AlertSeverity.WARNING,
    )


def _create_unusual_spending_alert(
    budget_id: str,
    category: BudgetCategory,
    historical_avg: float,
    spike_threshold: float = 1.5,
) -> BudgetAlert:
    """
    Create unusual spending alert (info severity).

    TODO (v2): Implement with historical spending data.
    Requires storing spending history and calculating moving averages.

    Args:
        budget_id: Budget UUID
        category: Category with unusual spending
        historical_avg: Historical average spending for this category
        spike_threshold: Multiplier for unusual detection (default: 1.5x average)

    Returns:
        BudgetAlert with info severity

    Example:
        >>> # When implemented:
        >>> category = BudgetCategory(
        ...     category_name="Entertainment",
        ...     budgeted_amount=150.00,
        ...     spent_amount=225.00,
        ...     remaining_amount=-75.00,
        ...     percent_used=150.0
        ... )
        >>> alert = _create_unusual_spending_alert("bud_123", category, 100.0)
        >>> print(alert.message)
        "Entertainment unusual spending: $225.00 spent vs $100.00 average (2.25x spike)"
    """
    spike_multiplier = category.spent_amount / historical_avg

    message = (
        f"{category.category_name} unusual spending: "
        f"${category.spent_amount:.2f} spent vs ${historical_avg:.2f} average "
        f"({spike_multiplier:.2f}x spike detected)"
    )

    return BudgetAlert(
        budget_id=budget_id,
        category=category.category_name,
        alert_type=AlertType.UNUSUAL_SPENDING,
        threshold=spike_threshold * 100,  # Convert to percentage
        message=message,
        triggered_at=datetime.now(),
        severity=AlertSeverity.INFO,
    )
