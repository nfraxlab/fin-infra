"""Unit tests for insights aggregation logic."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from fin_infra.goals.models import Goal, GoalStatus, GoalType
from fin_infra.insights.aggregator import (
    aggregate_insights,
    get_user_insights,
)
from fin_infra.insights.models import InsightCategory, InsightPriority
from fin_infra.net_worth.models import NetWorthSnapshot
from fin_infra.recurring.models import CadenceType, PatternType, RecurringPattern

# ---- Fixtures ----


@pytest.fixture
def net_worth_snapshots():
    """Sample net worth snapshots."""
    return [
        NetWorthSnapshot(
            id="snap_1",
            user_id="user_123",
            snapshot_date=datetime.now() - timedelta(days=30),
            total_net_worth=100000.0,
            total_assets=120000.0,
            total_liabilities=20000.0,
        ),
        NetWorthSnapshot(
            id="snap_2",
            user_id="user_123",
            snapshot_date=datetime.now(),
            total_net_worth=105000.0,
            total_assets=127000.0,
            total_liabilities=22000.0,
        ),
    ]


# Budget testing removed - Budget model doesn't have spent field
# Budget insights require external spending data, so testing is simplified


@pytest.fixture
def goals_in_progress():
    """Goals with partial progress."""
    return [
        Goal(
            id="goal_1",
            user_id="user_123",
            name="Emergency Fund",
            type=GoalType.SAVINGS,
            status=GoalStatus.ACTIVE,
            target_amount=10000.0,
            current_amount=5000.0,
            deadline=datetime.now() + timedelta(days=365),
        )
    ]


@pytest.fixture
def goals_near_completion():
    """Goals at 75%+ completion."""
    return [
        Goal(
            id="goal_2",
            user_id="user_123",
            name="Vacation Fund",
            type=GoalType.SAVINGS,
            status=GoalStatus.ACTIVE,
            target_amount=5000.0,
            current_amount=4000.0,
            deadline=datetime.now() + timedelta(days=90),
        )
    ]


@pytest.fixture
def goals_achieved():
    """Goals that are 100%+ complete."""
    return [
        Goal(
            id="goal_3",
            user_id="user_123",
            name="New Laptop",
            type=GoalType.SAVINGS,
            status=GoalStatus.COMPLETED,  # Mark as completed
            target_amount=2000.0,
            current_amount=2000.0,  # Must be <= target_amount
            deadline=datetime.now() + timedelta(days=30),
        )
    ]


@pytest.fixture
def recurring_patterns_low_cost():
    """Recurring patterns under $50/month."""
    base_date = datetime.now()
    return [
        RecurringPattern(
            merchant_name="SPOTIFY.COM",
            normalized_merchant="spotify",
            pattern_type=PatternType.FIXED,
            cadence=CadenceType.MONTHLY,
            amount=9.99,
            amount_variance_pct=0.0,
            occurrence_count=12,
            first_date=base_date - timedelta(days=365),
            last_date=base_date - timedelta(days=30),
            next_expected_date=base_date + timedelta(days=15),
            date_std_dev=0.5,
            confidence=0.95,
        )
    ]


@pytest.fixture
def recurring_patterns_high_cost():
    """Recurring patterns over $50/month."""
    base_date = datetime.now()
    return [
        RecurringPattern(
            merchant_name="GEICO INSURANCE",
            normalized_merchant="geico",
            pattern_type=PatternType.FIXED,
            cadence=CadenceType.MONTHLY,
            amount=120.00,
            amount_variance_pct=0.0,
            occurrence_count=12,
            first_date=base_date - timedelta(days=365),
            last_date=base_date - timedelta(days=10),
            next_expected_date=base_date + timedelta(days=20),
            date_std_dev=1.0,
            confidence=0.98,
        ),
        RecurringPattern(
            merchant_name="LA FITNESS",
            normalized_merchant="lafitness",
            pattern_type=PatternType.FIXED,
            cadence=CadenceType.MONTHLY,
            amount=65.00,
            amount_variance_pct=0.0,
            occurrence_count=6,
            first_date=base_date - timedelta(days=180),
            last_date=base_date - timedelta(days=20),
            next_expected_date=base_date + timedelta(days=10),
            date_std_dev=1.5,
            confidence=0.92,
        ),
    ]


# ---- Test aggregate_insights() ----


def test_aggregate_insights_empty():
    """Test aggregation with no data sources."""
    feed = aggregate_insights(user_id="user_123")
    assert feed.user_id == "user_123"
    assert feed.insights == []
    assert feed.unread_count == 0
    assert feed.critical_count == 0


def test_net_worth_increase(net_worth_snapshots):
    """Test insight for net worth increase."""
    feed = aggregate_insights(user_id="user_123", net_worth_snapshots=net_worth_snapshots)

    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.category == InsightCategory.NET_WORTH
    assert insight.priority == InsightPriority.MEDIUM
    assert "Increased" in insight.title
    assert insight.value == Decimal("5000")  # 105000 - 100000


def test_net_worth_decrease():
    """Test insight for net worth decrease."""
    snapshots = [
        NetWorthSnapshot(
            id="snap_1",
            user_id="user_123",
            snapshot_date=datetime.now() - timedelta(days=30),
            total_net_worth=100000.0,
            total_assets=120000.0,
            total_liabilities=20000.0,
        ),
        NetWorthSnapshot(
            id="snap_2",
            user_id="user_123",
            snapshot_date=datetime.now(),
            total_net_worth=90000.0,
            total_assets=110000.0,
            total_liabilities=20000.0,
        ),
    ]

    feed = aggregate_insights(user_id="user_123", net_worth_snapshots=snapshots)
    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.category == InsightCategory.NET_WORTH
    assert insight.priority == InsightPriority.MEDIUM  # <10% decline
    assert "Decreased" in insight.title


def test_net_worth_large_decrease():
    """Test insight for large net worth decrease (>10%)."""
    snapshots = [
        NetWorthSnapshot(
            id="snap_1",
            user_id="user_123",
            snapshot_date=datetime.now() - timedelta(days=30),
            total_net_worth=100000.0,
            total_assets=120000.0,
            total_liabilities=20000.0,
        ),
        NetWorthSnapshot(
            id="snap_2",
            user_id="user_123",
            snapshot_date=datetime.now(),
            total_net_worth=80000.0,
            total_assets=100000.0,
            total_liabilities=20000.0,
        ),
    ]

    feed = aggregate_insights(user_id="user_123", net_worth_snapshots=snapshots)
    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.priority == InsightPriority.HIGH  # >10% decline


# Budget tests removed - Budget model doesn't have spent tracking
# Budget insights require external spending data


def test_goal_in_progress(goals_in_progress):
    """Test no insight for goals under 75% progress."""
    feed = aggregate_insights(user_id="user_123", goals=goals_in_progress)
    # Should not generate insights for goals under 75%
    assert len(feed.insights) == 0


def test_goal_near_completion(goals_near_completion):
    """Test insight for goals at 75%+."""
    feed = aggregate_insights(user_id="user_123", goals=goals_near_completion)

    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.category == InsightCategory.GOAL
    assert insight.priority == InsightPriority.MEDIUM
    assert "Almost There" in insight.title


def test_goal_achieved(goals_achieved):
    """Test high-priority insight for achieved goals."""
    feed = aggregate_insights(user_id="user_123", goals=goals_achieved)

    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.category == InsightCategory.GOAL
    assert insight.priority == InsightPriority.HIGH
    assert "Achieved" in insight.title


def test_recurring_patterns_low_cost(recurring_patterns_low_cost):
    """Test no insight for low-cost recurring patterns."""
    feed = aggregate_insights(user_id="user_123", recurring_patterns=recurring_patterns_low_cost)
    # Should not generate insights for patterns under $50
    assert len(feed.insights) == 0


def test_recurring_patterns_high_cost(recurring_patterns_high_cost):
    """Test insight for high-cost recurring patterns."""
    feed = aggregate_insights(user_id="user_123", recurring_patterns=recurring_patterns_high_cost)

    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.category == InsightCategory.RECURRING
    assert insight.priority == InsightPriority.MEDIUM
    assert "High-Cost Subscriptions" in insight.title
    assert insight.value == Decimal("185.00")  # 120 + 65


def test_portfolio_tracked():
    """Test that portfolio value alone doesn't generate redundant insights.

    Portfolio value is shown in KPI cards, so we don't generate a
    separate "tracked" insight. Only actionable insights are generated.
    """
    feed = aggregate_insights(user_id="user_123", portfolio_value=Decimal("50000"))

    # No insight generated - portfolio value is shown in KPI cards
    assert len(feed.insights) == 0


def test_tax_opportunities():
    """Test insights from tax opportunities."""
    opportunities = [
        {
            "title": "Tax-Loss Harvesting Opportunity",
            "description": "Consider harvesting losses in STOCK1 to offset gains",
            "action": "Review with tax professional before year-end",
            "value": Decimal("500"),
            "metadata": {"symbol": "STOCK1"},
        }
    ]

    feed = aggregate_insights(user_id="user_123", tax_opportunities=opportunities)

    assert len(feed.insights) == 1
    insight = feed.insights[0]
    assert insight.category == InsightCategory.TAX
    assert insight.priority == InsightPriority.HIGH
    assert "Tax-Loss Harvesting" in insight.title


def test_priority_ordering(goals_achieved, recurring_patterns_high_cost):
    """Test insights are ordered by priority."""
    feed = aggregate_insights(
        user_id="user_123",
        goals=goals_achieved,  # HIGH
        recurring_patterns=recurring_patterns_high_cost,  # MEDIUM
    )

    assert len(feed.insights) == 2
    # Should be ordered: HIGH, MEDIUM
    assert feed.insights[0].priority == InsightPriority.HIGH
    assert feed.insights[1].priority == InsightPriority.MEDIUM


def test_unread_count():
    """Test unread count calculation."""
    feed = aggregate_insights(
        user_id="user_123",
        portfolio_value=Decimal("50000"),
    )

    # All insights start unread
    assert feed.unread_count == len(feed.insights)

    # Mark one as read
    if feed.insights:
        feed.insights[0].read = True
        # Note: unread_count is calculated at creation, not dynamic
        # In production, would recalculate or track separately


def test_critical_count():
    """Test critical count calculation."""
    # No critical-priority data sources in current fixtures
    feed = aggregate_insights(user_id="user_123")
    assert feed.critical_count == 0


def test_get_user_insights_stub():
    """Test get_user_insights stub."""
    feed = get_user_insights(user_id="user_123")

    # Stub returns empty feed
    assert feed.user_id == "user_123"
    assert feed.insights == []
    assert feed.unread_count == 0
