"""Unit tests for budget alerts."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fin_infra.budgets.alerts import (
    check_budget_alerts,
    _create_overspending_alert,
    _create_approaching_limit_alert,
    _create_unusual_spending_alert,
)
from fin_infra.budgets.models import (
    AlertSeverity,
    AlertType,
    BudgetCategory,
    BudgetProgress,
)


@pytest.fixture
def mock_tracker():
    """Mock BudgetTracker with get_budget_progress method."""
    tracker = MagicMock()
    tracker.get_budget_progress = AsyncMock()
    return tracker


@pytest.fixture
def sample_categories():
    """Sample budget categories with various spending levels."""
    return [
        BudgetCategory(
            category_name="Groceries",
            budgeted_amount=600.00,
            spent_amount=425.50,
            remaining_amount=174.50,
            percent_used=70.92,
        ),
        BudgetCategory(
            category_name="Restaurants",
            budgeted_amount=200.00,
            spent_amount=180.25,
            remaining_amount=19.75,
            percent_used=90.13,
        ),
        BudgetCategory(
            category_name="Transportation",
            budgeted_amount=150.00,
            spent_amount=175.00,
            remaining_amount=-25.00,
            percent_used=116.67,
        ),
        BudgetCategory(
            category_name="Entertainment",
            budgeted_amount=100.00,
            spent_amount=15.00,
            remaining_amount=85.00,
            percent_used=15.0,
        ),
    ]


@pytest.fixture
def sample_progress(sample_categories):
    """Sample BudgetProgress with multiple categories."""
    return BudgetProgress(
        budget_id="bud_123",
        current_period="November 2025",
        categories=sample_categories,
        total_budgeted=1050.00,
        total_spent=795.75,
        total_remaining=254.25,
        percent_used=75.79,
        period_days_elapsed=15,
        period_days_total=30,
    )


class TestCheckBudgetAlerts:
    """Test check_budget_alerts() function."""

    @pytest.mark.asyncio
    async def test_no_alerts_when_under_threshold(self, mock_tracker):
        """Should return empty list when all spending under threshold."""
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Groceries",
                    budgeted_amount=600.00,
                    spent_amount=300.00,
                    remaining_amount=300.00,
                    percent_used=50.0,
                ),
            ],
            total_budgeted=600.00,
            total_spent=300.00,
            total_remaining=300.00,
            percent_used=50.0,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        assert alerts == []
        mock_tracker.get_budget_progress.assert_called_once_with("bud_123")

    @pytest.mark.asyncio
    async def test_detect_overspending_alert(self, mock_tracker):
        """Should detect overspending (spent > budgeted)."""
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Transportation",
                    budgeted_amount=150.00,
                    spent_amount=175.00,
                    remaining_amount=-25.00,
                    percent_used=116.67,
                ),
            ],
            total_budgeted=150.00,
            total_spent=175.00,
            total_remaining=-25.00,
            percent_used=116.67,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == AlertType.OVERSPENDING
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.category == "Transportation"
        assert alert.threshold == 100.0
        assert "$175.00 spent of $150.00 budgeted" in alert.message

    @pytest.mark.asyncio
    async def test_detect_approaching_limit_alert(self, mock_tracker):
        """Should detect approaching limit (spent > 80% by default)."""
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Restaurants",
                    budgeted_amount=200.00,
                    spent_amount=180.00,
                    remaining_amount=20.00,
                    percent_used=90.0,
                ),
            ],
            total_budgeted=200.00,
            total_spent=180.00,
            total_remaining=20.00,
            percent_used=90.0,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == AlertType.APPROACHING_LIMIT
        assert alert.severity == AlertSeverity.WARNING
        assert alert.category == "Restaurants"
        assert alert.threshold == 80.0
        assert "90.0% of budget" in alert.message

    @pytest.mark.asyncio
    async def test_custom_threshold_per_category(self, mock_tracker):
        """Should use custom thresholds per category."""
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Groceries",
                    budgeted_amount=600.00,
                    spent_amount=540.00,
                    remaining_amount=60.00,
                    percent_used=90.0,
                ),
                BudgetCategory(
                    category_name="Restaurants",
                    budgeted_amount=200.00,
                    spent_amount=170.00,
                    remaining_amount=30.00,
                    percent_used=85.0,
                ),
            ],
            total_budgeted=800.00,
            total_spent=710.00,
            total_remaining=90.00,
            percent_used=88.75,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        # Groceries: 90% threshold, Restaurants: default 80%
        alerts = await check_budget_alerts(
            "bud_123", mock_tracker, thresholds={"Groceries": 95.0, "default": 80.0}
        )

        # Only Restaurants should trigger (85% > 80%)
        # Groceries should not trigger (90% < 95%)
        assert len(alerts) == 1
        assert alerts[0].category == "Restaurants"
        assert alerts[0].threshold == 80.0

    @pytest.mark.asyncio
    async def test_multiple_alerts(self, mock_tracker, sample_progress):
        """Should detect multiple alerts across categories."""
        mock_tracker.get_budget_progress.return_value = sample_progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        # Transportation: overspending (116.67%)
        # Restaurants: approaching limit (90.13% > 80%)
        assert len(alerts) == 2

        # Check overspending alert
        overspending = [a for a in alerts if a.alert_type == AlertType.OVERSPENDING]
        assert len(overspending) == 1
        assert overspending[0].category == "Transportation"
        assert overspending[0].severity == AlertSeverity.CRITICAL

        # Check approaching limit alert
        approaching = [a for a in alerts if a.alert_type == AlertType.APPROACHING_LIMIT]
        assert len(approaching) == 1
        assert approaching[0].category == "Restaurants"
        assert approaching[0].severity == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_skip_categories_with_zero_spending(self, mock_tracker):
        """Should not create alerts for categories with no spending."""
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Entertainment",
                    budgeted_amount=100.00,
                    spent_amount=0.00,
                    remaining_amount=100.00,
                    percent_used=0.0,
                ),
            ],
            total_budgeted=100.00,
            total_spent=0.00,
            total_remaining=100.00,
            percent_used=0.0,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        assert alerts == []

    @pytest.mark.asyncio
    async def test_overspending_does_not_trigger_approaching_limit(self, mock_tracker):
        """Should not trigger approaching_limit alert if already overspending."""
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Shopping",
                    budgeted_amount=100.00,
                    spent_amount=120.00,
                    remaining_amount=-20.00,
                    percent_used=120.0,
                ),
            ],
            total_budgeted=100.00,
            total_spent=120.00,
            total_remaining=-20.00,
            percent_used=120.0,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        # Should only have overspending alert, not approaching_limit
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.OVERSPENDING

    @pytest.mark.asyncio
    async def test_budget_not_found_raises_error(self, mock_tracker):
        """Should propagate ValueError when budget not found."""
        mock_tracker.get_budget_progress.side_effect = ValueError("Budget not found")

        with pytest.raises(ValueError, match="Budget not found"):
            await check_budget_alerts("nonexistent", mock_tracker)


class TestCreateOverspendingAlert:
    """Test _create_overspending_alert() helper."""

    def test_create_overspending_alert(self):
        """Should create critical overspending alert."""
        category = BudgetCategory(
            category_name="Restaurants",
            budgeted_amount=200.00,
            spent_amount=225.50,
            remaining_amount=-25.50,
            percent_used=112.75,
        )

        alert = _create_overspending_alert("bud_123", category)

        assert alert.budget_id == "bud_123"
        assert alert.category == "Restaurants"
        assert alert.alert_type == AlertType.OVERSPENDING
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.threshold == 100.0
        assert "Restaurants overspending" in alert.message
        assert "$225.50 spent of $200.00 budgeted" in alert.message
        assert "$25.50 over" in alert.message
        assert isinstance(alert.triggered_at, datetime)

    def test_overspending_message_formatting(self):
        """Should format overspending message correctly."""
        category = BudgetCategory(
            category_name="Transportation",
            budgeted_amount=150.00,
            spent_amount=175.00,
            remaining_amount=-25.00,
            percent_used=116.67,
        )

        alert = _create_overspending_alert("bud_123", category)

        assert "$175.00 spent" in alert.message
        assert "$150.00 budgeted" in alert.message
        assert "$25.00 over" in alert.message
        assert "16.7% over budget" in alert.message


class TestCreateApproachingLimitAlert:
    """Test _create_approaching_limit_alert() helper."""

    def test_create_approaching_limit_alert(self):
        """Should create warning approaching limit alert."""
        category = BudgetCategory(
            category_name="Groceries",
            budgeted_amount=600.00,
            spent_amount=510.00,
            remaining_amount=90.00,
            percent_used=85.0,
        )

        alert = _create_approaching_limit_alert("bud_123", category, 80.0)

        assert alert.budget_id == "bud_123"
        assert alert.category == "Groceries"
        assert alert.alert_type == AlertType.APPROACHING_LIMIT
        assert alert.severity == AlertSeverity.WARNING
        assert alert.threshold == 80.0
        assert "Groceries at 85.0% of budget" in alert.message
        assert "$510.00 spent of $600.00" in alert.message
        assert "$90.00 remaining" in alert.message
        assert "threshold: 80%" in alert.message

    def test_approaching_limit_with_custom_threshold(self):
        """Should use custom threshold in alert."""
        category = BudgetCategory(
            category_name="Entertainment",
            budgeted_amount=100.00,
            spent_amount=95.00,
            remaining_amount=5.00,
            percent_used=95.0,
        )

        alert = _create_approaching_limit_alert("bud_123", category, 90.0)

        assert alert.threshold == 90.0
        assert "threshold: 90%" in alert.message


class TestCreateUnusualSpendingAlert:
    """Test _create_unusual_spending_alert() helper."""

    def test_create_unusual_spending_alert(self):
        """Should create info unusual spending alert."""
        category = BudgetCategory(
            category_name="Entertainment",
            budgeted_amount=150.00,
            spent_amount=225.00,
            remaining_amount=-75.00,
            percent_used=150.0,
        )

        alert = _create_unusual_spending_alert("bud_123", category, 100.0)

        assert alert.budget_id == "bud_123"
        assert alert.category == "Entertainment"
        assert alert.alert_type == AlertType.UNUSUAL_SPENDING
        assert alert.severity == AlertSeverity.INFO
        assert alert.threshold == 150.0  # 1.5x * 100
        assert "Entertainment unusual spending" in alert.message
        assert "$225.00 spent vs $100.00 average" in alert.message
        assert "2.25x spike detected" in alert.message

    def test_unusual_spending_with_custom_spike_threshold(self):
        """Should use custom spike threshold."""
        category = BudgetCategory(
            category_name="Shopping",
            budgeted_amount=200.00,
            spent_amount=400.00,
            remaining_amount=-200.00,
            percent_used=200.0,
        )

        alert = _create_unusual_spending_alert("bud_123", category, 100.0, spike_threshold=2.0)

        assert alert.threshold == 200.0  # 2.0x * 100
        assert "4.00x spike detected" in alert.message


class TestAlertIntegration:
    """Integration tests for alert detection."""

    @pytest.mark.asyncio
    async def test_full_alert_workflow(self, mock_tracker):
        """Should handle full alert detection workflow."""
        # Setup progress with various spending levels
        progress = BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                # Under threshold - no alert
                BudgetCategory(
                    category_name="Utilities",
                    budgeted_amount=200.00,
                    spent_amount=100.00,
                    remaining_amount=100.00,
                    percent_used=50.0,
                ),
                # At 85% - approaching limit
                BudgetCategory(
                    category_name="Groceries",
                    budgeted_amount=600.00,
                    spent_amount=510.00,
                    remaining_amount=90.00,
                    percent_used=85.0,
                ),
                # At 92% - approaching limit
                BudgetCategory(
                    category_name="Restaurants",
                    budgeted_amount=200.00,
                    spent_amount=184.00,
                    remaining_amount=16.00,
                    percent_used=92.0,
                ),
                # Overspending - critical
                BudgetCategory(
                    category_name="Entertainment",
                    budgeted_amount=100.00,
                    spent_amount=125.00,
                    remaining_amount=-25.00,
                    percent_used=125.0,
                ),
            ],
            total_budgeted=1100.00,
            total_spent=919.00,
            total_remaining=181.00,
            percent_used=83.55,
            period_days_elapsed=15,
            period_days_total=30,
        )
        mock_tracker.get_budget_progress.return_value = progress

        alerts = await check_budget_alerts("bud_123", mock_tracker)

        # Should have 3 alerts: 1 critical (overspending) + 2 warnings (approaching)
        assert len(alerts) == 3

        # Verify alert types
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        warnings = [a for a in alerts if a.severity == AlertSeverity.WARNING]

        assert len(critical) == 1
        assert len(warnings) == 2

        # Verify critical alert
        assert critical[0].category == "Entertainment"
        assert critical[0].alert_type == AlertType.OVERSPENDING

        # Verify warning alerts
        warning_categories = {a.category for a in warnings}
        assert warning_categories == {"Groceries", "Restaurants"}
