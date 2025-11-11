"""Insights aggregation logic for unified feed."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from .models import Insight, InsightCategory, InsightFeed, InsightPriority

if TYPE_CHECKING:
    from fin_infra.budgets.models import Budget
    from fin_infra.goals.models import Goal
    from fin_infra.net_worth.models import NetWorthSnapshot
    from fin_infra.recurring.models import RecurringPattern


def aggregate_insights(
    user_id: str,
    net_worth_snapshots: list[NetWorthSnapshot] | None = None,
    budgets: list[Budget] | None = None,
    goals: list[Goal] | None = None,
    recurring_patterns: list[RecurringPattern] | None = None,
    portfolio_value: Decimal | None = None,
    tax_opportunities: list[dict] | None = None,
) -> InsightFeed:
    """
    Aggregate insights from multiple financial data sources.

    Args:
        user_id: User identifier
        net_worth_snapshots: Recent net worth data points
        budgets: User's budgets
        goals: User's financial goals
        recurring_patterns: Detected recurring transactions
        portfolio_value: Current portfolio value
        tax_opportunities: Tax-loss harvesting or other tax insights

    Returns:
        InsightFeed with prioritized insights

    Example:
        >>> insights = aggregate_insights(
        ...     user_id="user_123",
        ...     budgets=[budget1, budget2],
        ...     goals=[goal1],
        ... )
        >>> print(insights.critical_count)
        2
    """
    insights: list[Insight] = []

    # Net worth insights
    if net_worth_snapshots and len(net_worth_snapshots) >= 2:
        insights.extend(_generate_net_worth_insights(user_id, net_worth_snapshots))

    # Budget insights (critical if overspending)
    if budgets:
        insights.extend(_generate_budget_insights(user_id, budgets))

    # Goal insights
    if goals:
        insights.extend(_generate_goal_insights(user_id, goals))

    # Recurring pattern insights
    if recurring_patterns:
        insights.extend(_generate_recurring_insights(user_id, recurring_patterns))

    # Portfolio insights
    if portfolio_value:
        insights.extend(_generate_portfolio_insights(user_id, portfolio_value))

    # Tax insights (high priority)
    if tax_opportunities:
        insights.extend(_generate_tax_insights(user_id, tax_opportunities))

    # Sort by priority: critical > high > medium > low
    priority_order = {
        InsightPriority.CRITICAL: 0,
        InsightPriority.HIGH: 1,
        InsightPriority.MEDIUM: 2,
        InsightPriority.LOW: 3,
    }
    insights.sort(key=lambda x: (priority_order[x.priority], x.created_at), reverse=False)

    # Calculate counts
    unread_count = sum(1 for i in insights if not i.read)
    critical_count = sum(1 for i in insights if i.priority == InsightPriority.CRITICAL)

    return InsightFeed(
        user_id=user_id,
        insights=insights,
        unread_count=unread_count,
        critical_count=critical_count,
    )


def get_user_insights(user_id: str, include_read: bool = False) -> InsightFeed:
    """
    Get insights for a user (stub for database integration).

    In production, this would query stored insights from database.

    Args:
        user_id: User identifier
        include_read: Whether to include already-read insights

    Returns:
        InsightFeed for the user
    """
    # Stub: In production, query insights from database
    # For now, return empty feed
    return InsightFeed(user_id=user_id, insights=[])


def _generate_net_worth_insights(user_id: str, snapshots: list[NetWorthSnapshot]) -> list[Insight]:
    """Generate insights from net worth trends."""
    insights = []

    # Sort by date
    sorted_snapshots = sorted(snapshots, key=lambda x: x.snapshot_date)
    latest = sorted_snapshots[-1]
    previous = sorted_snapshots[-2]

    # Calculate change
    change = Decimal(str(latest.total_net_worth)) - Decimal(str(previous.total_net_worth))
    change_pct = (
        (change / Decimal(str(previous.total_net_worth)) * 100)
        if previous.total_net_worth != 0
        else Decimal("0")
    )

    if change > 0:
        insights.append(
            Insight(
                id=f"nw_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.NET_WORTH,
                priority=InsightPriority.MEDIUM,
                title="Net Worth Increased",
                description=f"Your net worth grew by ${change:,.2f} ({change_pct:.1f}%) this period",
                value=change,
            )
        )
    elif change < 0:
        priority = InsightPriority.HIGH if abs(change_pct) > 10 else InsightPriority.MEDIUM
        insights.append(
            Insight(
                id=f"nw_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.NET_WORTH,
                priority=priority,
                title="Net Worth Decreased",
                description=f"Your net worth declined by ${abs(change):,.2f} ({abs(change_pct):.1f}%) this period",
                action="Review recent transactions and market changes",
                value=change,
            )
        )

    return insights


def _generate_budget_insights(user_id: str, budgets: list[Budget]) -> list[Insight]:
    """Generate insights from budget tracking."""
    insights: list[Insight] = []

    for budget in budgets:
        # For aggregation, we expect budgets to provide spent amounts somehow
        # Since Budget model doesn't have a "spent" field, we rely on external tracking
        # For now, treat budget categories dict as {category: limit}
        # This is a stub - production would query actual spending
        pass

    return insights


def _generate_goal_insights(user_id: str, goals: list[Goal]) -> list[Insight]:
    """Generate insights from goal progress."""
    insights = []

    for goal in goals:
        current = Decimal(str(goal.current_amount))  # Convert float to Decimal
        target = Decimal(str(goal.target_amount))
        pct = Decimal((current / target * 100) if target > 0 else "0")

        # Goal milestones
        if pct >= 100:
            insights.append(
                Insight(
                    id=f"goal_{goal.id}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    category=InsightCategory.GOAL,
                    priority=InsightPriority.HIGH,
                    title=f"Goal '{goal.name}' Achieved!",
                    description=f"You've reached your ${target:,.2f} goal",
                    action="Consider setting a new goal or increasing this one",
                    value=current,
                    metadata={"goal_id": goal.id},
                )
            )
        elif pct >= 75:
            insights.append(
                Insight(
                    id=f"goal_{goal.id}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    category=InsightCategory.GOAL,
                    priority=InsightPriority.MEDIUM,
                    title=f"Goal '{goal.name}' Almost There",
                    description=f"${current:,.2f} of ${target:,.2f} saved ({pct:.0f}%)",
                    action=f"${target - current:,.2f} more to reach your goal",
                    value=current,
                    metadata={"goal_id": goal.id},
                )
            )

    return insights


def _generate_recurring_insights(user_id: str, patterns: list[RecurringPattern]) -> list[Insight]:
    """Generate insights from recurring transactions."""
    insights = []

    # High-cost subscriptions (using amount field)
    high_cost = [
        p
        for p in patterns
        if p.amount is not None and p.amount > 50 or (p.amount_range and p.amount_range[1] > 50)
    ]
    if high_cost:
        total = Decimal("0")
        for p in high_cost:
            if p.amount is not None:
                total += Decimal(str(p.amount))
            elif p.amount_range:
                # Use average of range
                total += Decimal(str((p.amount_range[0] + p.amount_range[1]) / 2))

        insights.append(
            Insight(
                id=f"recurring_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.RECURRING,
                priority=InsightPriority.MEDIUM,
                title="High-Cost Subscriptions Detected",
                description=f"You have {len(high_cost)} subscriptions over $50/month totaling ${total:,.2f}",
                action="Review if all subscriptions are still needed",
                value=total,
            )
        )

    return insights


def _generate_portfolio_insights(user_id: str, portfolio_value: Decimal) -> list[Insight]:
    """Generate insights from portfolio analysis."""
    insights = []

    # Simple insight: portfolio exists
    if portfolio_value > 0:
        insights.append(
            Insight(
                id=f"portfolio_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.PORTFOLIO,
                priority=InsightPriority.LOW,
                title="Portfolio Tracked",
                description=f"Your portfolio is valued at ${portfolio_value:,.2f}",
                value=portfolio_value,
            )
        )

    return insights


def _generate_tax_insights(user_id: str, opportunities: list[dict]) -> list[Insight]:
    """Generate insights from tax opportunities."""
    insights = []

    for opp in opportunities:
        insights.append(
            Insight(
                id=f"tax_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.TAX,
                priority=InsightPriority.HIGH,
                title=opp.get("title", "Tax Opportunity"),
                description=opp.get("description", "Review this tax opportunity"),
                action=opp.get("action", "Consult with tax professional"),
                value=opp.get("value"),
                metadata=opp.get("metadata"),
            )
        )

    return insights
