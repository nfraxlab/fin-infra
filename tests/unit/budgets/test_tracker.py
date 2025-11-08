"""Unit tests for BudgetTracker class."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fin_infra.budgets.tracker import BudgetTracker
from fin_infra.budgets.models import BudgetType, BudgetPeriod


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy async engine."""
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


@pytest.fixture
def tracker(mock_engine):
    """BudgetTracker instance with mock engine."""
    return BudgetTracker(db_engine=mock_engine)


class TestBudgetTrackerInit:
    """Test BudgetTracker initialization."""

    def test_init_with_engine(self, mock_engine):
        """Should initialize with db_engine."""
        tracker = BudgetTracker(db_engine=mock_engine)
        assert tracker.db_engine == mock_engine
        assert tracker.session_maker is not None


class TestCreateBudget:
    """Test create_budget() method."""

    @pytest.mark.asyncio
    async def test_create_personal_monthly_budget(self, tracker):
        """Should create a personal monthly budget."""
        budget = await tracker.create_budget(
            user_id="user123",
            name="November 2025",
            type="personal",
            period="monthly",
            categories={"Groceries": 600.00, "Restaurants": 200.00},
        )

        assert budget.id is not None
        assert budget.user_id == "user123"
        assert budget.name == "November 2025"
        assert budget.type == BudgetType.PERSONAL
        assert budget.period == BudgetPeriod.MONTHLY
        assert budget.categories == {"Groceries": 600.00, "Restaurants": 200.00}
        assert budget.rollover_enabled is False

    @pytest.mark.asyncio
    async def test_create_budget_with_rollover(self, tracker):
        """Should create budget with rollover enabled."""
        budget = await tracker.create_budget(
            user_id="user123",
            name="Q4 Budget",
            type="business",
            period="quarterly",
            categories={"Marketing": 5000.00, "Operations": 10000.00},
            rollover_enabled=True,
        )

        assert budget.rollover_enabled is True
        assert budget.type == BudgetType.BUSINESS
        assert budget.period == BudgetPeriod.QUARTERLY

    @pytest.mark.asyncio
    async def test_create_budget_invalid_type(self, tracker):
        """Should raise ValueError for invalid budget type."""
        with pytest.raises(ValueError, match="Invalid budget type"):
            await tracker.create_budget(
                user_id="user123",
                name="Test",
                type="invalid_type",
                period="monthly",
                categories={"Food": 500.00},
            )

    @pytest.mark.asyncio
    async def test_create_budget_invalid_period(self, tracker):
        """Should raise ValueError for invalid period."""
        with pytest.raises(ValueError, match="Invalid budget period"):
            await tracker.create_budget(
                user_id="user123",
                name="Test",
                type="personal",
                period="invalid_period",
                categories={"Food": 500.00},
            )

    @pytest.mark.asyncio
    async def test_create_budget_empty_categories(self, tracker):
        """Should raise ValueError for empty categories."""
        with pytest.raises(ValueError, match="at least one category"):
            await tracker.create_budget(
                user_id="user123",
                name="Test",
                type="personal",
                period="monthly",
                categories={},
            )

    @pytest.mark.asyncio
    async def test_create_budget_negative_amount(self, tracker):
        """Should raise ValueError for negative category amounts."""
        with pytest.raises(ValueError, match="cannot be negative"):
            await tracker.create_budget(
                user_id="user123",
                name="Test",
                type="personal",
                period="monthly",
                categories={"Food": -100.00},
            )

    @pytest.mark.asyncio
    async def test_create_budget_with_custom_start_date(self, tracker):
        """Should create budget with custom start date."""
        start = datetime(2025, 12, 1)
        budget = await tracker.create_budget(
            user_id="user123",
            name="December Budget",
            type="personal",
            period="monthly",
            categories={"Food": 500.00},
            start_date=start,
        )

        assert budget.start_date == start
        # Monthly budget should end ~30 days later
        assert (budget.end_date - start).days >= 27


class TestGetBudgets:
    """Test get_budgets() method."""

    @pytest.mark.asyncio
    async def test_get_budgets_empty(self, tracker):
        """Should return empty list when no budgets exist."""
        budgets = await tracker.get_budgets("user123")
        assert budgets == []

    @pytest.mark.asyncio
    async def test_get_budgets_with_type_filter(self, tracker):
        """Should return empty list with type filter (DB not implemented)."""
        budgets = await tracker.get_budgets("user123", type="personal")
        assert budgets == []


class TestGetBudget:
    """Test get_budget() method."""

    @pytest.mark.asyncio
    async def test_get_budget_not_found(self, tracker):
        """Should raise ValueError when budget not found."""
        with pytest.raises(ValueError, match="Budget not found"):
            await tracker.get_budget("nonexistent-id")


class TestUpdateBudget:
    """Test update_budget() method."""

    @pytest.mark.asyncio
    async def test_update_budget_not_found(self, tracker):
        """Should raise ValueError when budget not found."""
        with pytest.raises(ValueError, match="Budget not found"):
            await tracker.update_budget(
                "nonexistent-id",
                updates={"name": "Updated Name"},
            )

    @pytest.mark.asyncio
    async def test_update_budget_empty_categories(self, tracker):
        """Should raise ValueError for empty categories update."""
        with pytest.raises(ValueError, match="at least one category"):
            await tracker.update_budget(
                "some-id",
                updates={"categories": {}},
            )

    @pytest.mark.asyncio
    async def test_update_budget_negative_amounts(self, tracker):
        """Should raise ValueError for negative category amounts."""
        with pytest.raises(ValueError, match="cannot be negative"):
            await tracker.update_budget(
                "some-id",
                updates={"categories": {"Food": -50.00}},
            )


class TestDeleteBudget:
    """Test delete_budget() method."""

    @pytest.mark.asyncio
    async def test_delete_budget_not_found(self, tracker):
        """Should raise ValueError when budget not found."""
        with pytest.raises(ValueError, match="Budget not found"):
            await tracker.delete_budget("nonexistent-id")


class TestGetBudgetProgress:
    """Test get_budget_progress() method."""

    @pytest.mark.asyncio
    async def test_get_budget_progress_not_found(self, tracker):
        """Should raise ValueError when budget not found."""
        with pytest.raises(ValueError, match="Budget not found"):
            await tracker.get_budget_progress("nonexistent-id")


class TestCalculateEndDate:
    """Test _calculate_end_date() helper method."""

    def test_calculate_weekly_end_date(self, tracker):
        """Should add 7 days for weekly budget."""
        start = datetime(2025, 11, 1)
        end = tracker._calculate_end_date(start, "weekly")
        assert (end - start).days == 7

    def test_calculate_biweekly_end_date(self, tracker):
        """Should add 14 days for biweekly budget."""
        start = datetime(2025, 11, 1)
        end = tracker._calculate_end_date(start, "biweekly")
        assert (end - start).days == 14

    def test_calculate_monthly_end_date(self, tracker):
        """Should add ~30 days for monthly budget."""
        start = datetime(2025, 11, 1)
        end = tracker._calculate_end_date(start, "monthly")
        assert end.month == 12
        assert end.year == 2025

    def test_calculate_monthly_end_date_year_wrap(self, tracker):
        """Should handle year wrap for monthly budget."""
        start = datetime(2025, 12, 1)
        end = tracker._calculate_end_date(start, "monthly")
        assert end.month == 1
        assert end.year == 2026

    def test_calculate_quarterly_end_date(self, tracker):
        """Should add 3 months for quarterly budget."""
        start = datetime(2025, 11, 1)
        end = tracker._calculate_end_date(start, "quarterly")
        assert end.month == 2  # 11 + 3 = 14 -> 2 (next year)
        assert end.year == 2026

    def test_calculate_yearly_end_date(self, tracker):
        """Should add 1 year for yearly budget."""
        start = datetime(2025, 11, 1)
        end = tracker._calculate_end_date(start, "yearly")
        assert end.year == 2026
        assert end.month == 11

    def test_calculate_invalid_period(self, tracker):
        """Should raise ValueError for invalid period."""
        start = datetime(2025, 11, 1)
        with pytest.raises(ValueError, match="Invalid period"):
            tracker._calculate_end_date(start, "invalid")


class TestBudgetTrackerIntegration:
    """Integration tests for BudgetTracker (end-to-end)."""

    @pytest.mark.asyncio
    async def test_full_budget_lifecycle(self, tracker):
        """Should handle full budget creation lifecycle."""
        # Create budget
        budget = await tracker.create_budget(
            user_id="user123",
            name="Test Budget",
            type="personal",
            period="monthly",
            categories={"Groceries": 600.00, "Dining": 200.00},
            rollover_enabled=True,
        )

        # Verify budget properties
        assert budget.id is not None
        assert budget.user_id == "user123"
        assert budget.type == BudgetType.PERSONAL
        assert budget.period == BudgetPeriod.MONTHLY
        assert len(budget.categories) == 2
        assert budget.rollover_enabled is True

        # Verify date calculations
        assert budget.start_date is not None
        assert budget.end_date > budget.start_date
        assert (budget.end_date - budget.start_date).days >= 27  # ~1 month

    @pytest.mark.asyncio
    async def test_budget_types_and_periods(self, tracker):
        """Should support all budget types and periods."""
        types = ["personal", "household", "business", "project", "custom"]
        periods = ["weekly", "biweekly", "monthly", "quarterly", "yearly"]

        for budget_type in types:
            for period in periods:
                budget = await tracker.create_budget(
                    user_id="user123",
                    name=f"{budget_type} {period}",
                    type=budget_type,
                    period=period,
                    categories={"Test": 100.00},
                )
                assert budget.type.value == budget_type
                assert budget.period.value == period
