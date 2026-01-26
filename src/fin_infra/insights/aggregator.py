"""Insights aggregation logic for unified feed."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from .models import Insight, InsightCategory, InsightFeed, InsightPriority

# Tone type for insight text generation
InsightTone = Literal["professional", "fun"]

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
    tone: InsightTone = "professional",
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
        tone: Insight text tone - "professional" (formal) or "fun" (casual with emojis)

    Returns:
        InsightFeed with prioritized insights

    Example:
        >>> insights = aggregate_insights(
        ...     user_id="user_123",
        ...     budgets=[budget1, budget2],
        ...     goals=[goal1],
        ...     tone="fun",
        ... )
        >>> print(insights.critical_count)
        2
    """
    insights: list[Insight] = []

    # Net worth insights
    if net_worth_snapshots and len(net_worth_snapshots) >= 2:
        insights.extend(_generate_net_worth_insights(user_id, net_worth_snapshots, tone))

    # Budget insights (critical if overspending)
    if budgets:
        insights.extend(_generate_budget_insights(user_id, budgets, tone))

    # Goal insights
    if goals:
        insights.extend(_generate_goal_insights(user_id, goals, tone))

    # Recurring pattern insights
    if recurring_patterns:
        insights.extend(_generate_recurring_insights(user_id, recurring_patterns, tone))

    # Portfolio insights
    if portfolio_value:
        insights.extend(_generate_portfolio_insights(user_id, portfolio_value, tone))

    # Tax insights (high priority)
    if tax_opportunities:
        insights.extend(_generate_tax_insights(user_id, tax_opportunities, tone))

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


def _generate_net_worth_insights(
    user_id: str, snapshots: list[NetWorthSnapshot], tone: InsightTone
) -> list[Insight]:
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
        if tone == "fun":
            title = "Net Worth Glow Up! 📈"
            desc = f"You're up ${change:,.2f} ({change_pct:.1f}%)! That's what we call winning 💪"
        else:
            title = "Net Worth Increased"
            desc = f"Your net worth grew by ${change:,.2f} ({change_pct:.1f}%) this period"
        insights.append(
            Insight(
                id=f"nw_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.NET_WORTH,
                priority=InsightPriority.MEDIUM,
                title=title,
                description=desc,
                value=change,
            )
        )
    elif change < 0:
        priority = InsightPriority.HIGH if abs(change_pct) > 10 else InsightPriority.MEDIUM
        if tone == "fun":
            title = "Net Worth Took a Hit 📉"
            desc = f"Down ${abs(change):,.2f} ({abs(change_pct):.1f}%) - no stress, let's figure this out"
            action = "Time to check what's up with your transactions 🔍"
        else:
            title = "Net Worth Decreased"
            desc = f"Your net worth declined by ${abs(change):,.2f} ({abs(change_pct):.1f}%) this period"
            action = "Review recent transactions and market changes"
        insights.append(
            Insight(
                id=f"nw_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.NET_WORTH,
                priority=priority,
                title=title,
                description=desc,
                action=action,
                value=change,
            )
        )

    return insights


def _generate_budget_insights(
    user_id: str, budgets: list[Budget], tone: InsightTone
) -> list[Insight]:
    """Generate insights from budget tracking."""
    insights: list[Insight] = []

    for budget in budgets:
        # For aggregation, we expect budgets to provide spent amounts somehow
        # Since Budget model doesn't have a "spent" field, we rely on external tracking
        # For now, treat budget categories dict as {category: limit}
        # This is a stub - production would query actual spending
        pass

    return insights


def _generate_goal_insights(user_id: str, goals: list[Goal], tone: InsightTone) -> list[Insight]:
    """Generate insights from goal progress."""
    insights = []

    for goal in goals:
        current = Decimal(str(goal.current_amount))  # Convert float to Decimal
        target = Decimal(str(goal.target_amount))
        pct = Decimal((current / target * 100) if target > 0 else "0")

        # Goal milestones
        if pct >= 100:
            if tone == "fun":
                title = f"🎉 '{goal.name}' Goal Crushed!"
                desc = f"You hit ${target:,.2f}! Absolute legend 👑"
                action = "Time to dream bigger - what's the next goal? 🚀"
            else:
                title = f"Goal '{goal.name}' Achieved!"
                desc = f"You've reached your ${target:,.2f} goal"
                action = "Consider setting a new goal or increasing this one"
            insights.append(
                Insight(
                    id=f"goal_{goal.id}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    category=InsightCategory.GOAL,
                    priority=InsightPriority.HIGH,
                    title=title,
                    description=desc,
                    action=action,
                    value=current,
                    metadata={"goal_id": goal.id},
                )
            )
        elif pct >= 75:
            if tone == "fun":
                title = f"🔥 '{goal.name}' Almost There!"
                desc = f"${current:,.2f} of ${target:,.2f} - you're {pct:.0f}% there, keep going!"
                action = f"Just ${target - current:,.2f} more and you're golden ✨"
            else:
                title = f"Goal '{goal.name}' Almost There"
                desc = f"${current:,.2f} of ${target:,.2f} saved ({pct:.0f}%)"
                action = f"${target - current:,.2f} more to reach your goal"
            insights.append(
                Insight(
                    id=f"goal_{goal.id}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    category=InsightCategory.GOAL,
                    priority=InsightPriority.MEDIUM,
                    title=title,
                    description=desc,
                    action=action,
                    value=current,
                    metadata={"goal_id": goal.id},
                )
            )

    return insights


def _generate_recurring_insights(
    user_id: str, patterns: list[RecurringPattern], tone: InsightTone
) -> list[Insight]:
    """Generate insights from recurring transactions."""
    insights = []

    # High-cost subscriptions (using amount field)
    high_cost = [
        p
        for p in patterns
        if (p.amount is not None and p.amount > 50) or (p.amount_range and p.amount_range[1] > 50)
    ]
    if high_cost:
        total = Decimal("0")
        for p in high_cost:
            if p.amount is not None:
                total += Decimal(str(p.amount))
            elif p.amount_range:
                # Use average of range
                total += Decimal(str((p.amount_range[0] + p.amount_range[1]) / 2))

        if tone == "fun":
            title = "💸 Subscription Check!"
            desc = f"{len(high_cost)} subscriptions over $50/mo = ${total:,.2f}. That's some serious recurring vibes"
            action = "Time for a subscription audit? 🧐"
        else:
            title = "High-Cost Subscriptions Detected"
            desc = f"You have {len(high_cost)} subscriptions over $50/month totaling ${total:,.2f}"
            action = "Review if all subscriptions are still needed"
        insights.append(
            Insight(
                id=f"recurring_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.RECURRING,
                priority=InsightPriority.MEDIUM,
                title=title,
                description=desc,
                action=action,
                value=total,
            )
        )

    return insights


def _generate_portfolio_insights(
    user_id: str, portfolio_value: Decimal, tone: InsightTone
) -> list[Insight]:
    """Generate insights from portfolio analysis.

    Focus on actionable insights, not redundant value statements.
    """
    insights = []

    # Skip the basic "portfolio is valued at X" - that's shown in KPI cards
    # Only generate insights when there's something actionable

    # Example: Diversification check (would need account breakdown data)
    # This is a placeholder - in production, pass account-level data

    # Example: Rebalancing reminder based on market conditions
    # This would integrate with market data APIs

    return insights


def _generate_tax_insights(
    user_id: str, opportunities: list[dict], tone: InsightTone
) -> list[Insight]:
    """Generate insights from tax opportunities."""
    insights = []

    for opp in opportunities:
        # Tax insights use the provided text, but we can add tone to default values
        if tone == "fun":
            default_title = "💰 Tax Savings Alert!"
            default_desc = "Found a way to keep more of your money 🎉"
            default_action = "Chat with a tax pro to lock this in 🔐"
        else:
            default_title = "Tax Opportunity"
            default_desc = "Review this tax opportunity"
            default_action = "Consult with tax professional"
        insights.append(
            Insight(
                id=f"tax_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                category=InsightCategory.TAX,
                priority=InsightPriority.HIGH,
                title=opp.get("title", default_title),
                description=opp.get("description", default_desc),
                action=opp.get("action", default_action),
                value=opp.get("value"),
                metadata=opp.get("metadata"),
            )
        )

    return insights
