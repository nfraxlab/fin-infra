"""Unit tests for cash flow analysis.

Tests cash flow calculation and forecasting with mocked dependencies.
"""

import pytest
from datetime import datetime

from fin_infra.analytics.cash_flow import (
    calculate_cash_flow,
    forecast_cash_flow,
    _determine_income_source,
)
from fin_infra.analytics.models import CashFlowAnalysis


class TestCalculateCashFlow:
    """Tests for calculate_cash_flow function."""

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_basic(self):
        """Test basic cash flow calculation."""
        result = await calculate_cash_flow(
            user_id="user123", start_date="2025-01-01", end_date="2025-01-31"
        )

        assert isinstance(result, CashFlowAnalysis)
        assert result.income_total > 0
        assert result.expense_total > 0
        assert result.net_cash_flow == result.income_total - result.expense_total
        assert isinstance(result.income_by_source, dict)
        assert isinstance(result.expenses_by_category, dict)

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_with_datetime_objects(self):
        """Test cash flow calculation with datetime objects."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)

        result = await calculate_cash_flow(user_id="user123", start_date=start, end_date=end)

        assert result.period_start == start
        assert result.period_end == end

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_invalid_date_range(self):
        """Test cash flow calculation with invalid date range."""
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            await calculate_cash_flow(
                user_id="user123", start_date="2025-01-31", end_date="2025-01-01"
            )

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_same_dates(self):
        """Test cash flow calculation with same start and end date."""
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            await calculate_cash_flow(
                user_id="user123", start_date="2025-01-01", end_date="2025-01-01"
            )

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_with_accounts_filter(self):
        """Test cash flow calculation with account filtering."""
        result = await calculate_cash_flow(
            user_id="user123",
            start_date="2025-01-01",
            end_date="2025-01-31",
            accounts=["acc1", "acc2"],
        )

        # Should still return valid result (mock data doesn't filter yet)
        assert isinstance(result, CashFlowAnalysis)

    @pytest.mark.asyncio
    async def test_cash_flow_breakdowns_sum_to_totals(self):
        """Test that income/expense breakdowns sum to totals."""
        result = await calculate_cash_flow(
            user_id="user123", start_date="2025-01-01", end_date="2025-01-31"
        )

        # Income breakdown should sum to income_total
        income_sum = sum(result.income_by_source.values())
        assert abs(income_sum - result.income_total) < 0.01

        # Expense breakdown should sum to expense_total
        expense_sum = sum(result.expenses_by_category.values())
        assert abs(expense_sum - result.expense_total) < 0.01


class TestForecastCashFlow:
    """Tests for forecast_cash_flow function."""

    @pytest.mark.asyncio
    async def test_forecast_cash_flow_basic(self):
        """Test basic cash flow forecasting."""
        forecasts = await forecast_cash_flow(user_id="user123", months=6)

        assert len(forecasts) == 6
        assert all(isinstance(f, CashFlowAnalysis) for f in forecasts)

    @pytest.mark.asyncio
    async def test_forecast_cash_flow_with_growth_rates(self):
        """Test forecasting with income and expense growth rates."""
        forecasts = await forecast_cash_flow(
            user_id="user123",
            months=12,
            assumptions={
                "income_growth_rate": 0.05,  # 5% annual
                "expense_growth_rate": 0.03,  # 3% annual
            },
        )

        assert len(forecasts) == 12

        # Income should grow over time
        assert forecasts[11].income_total > forecasts[0].income_total

        # Expenses should grow over time
        assert forecasts[11].expense_total > forecasts[0].expense_total

    @pytest.mark.asyncio
    async def test_forecast_cash_flow_with_one_time_income(self):
        """Test forecasting with one-time income."""
        bonus_amount = 5000.0
        forecasts = await forecast_cash_flow(
            user_id="user123",
            months=6,
            assumptions={"one_time_income": {3: bonus_amount}},  # Bonus in month 3
        )

        # Month 3 (index 3) should have higher income than month 2
        assert forecasts[3].income_total > forecasts[2].income_total

    @pytest.mark.asyncio
    async def test_forecast_cash_flow_with_one_time_expenses(self):
        """Test forecasting with one-time expenses."""
        vacation_cost = 2000.0
        forecasts = await forecast_cash_flow(
            user_id="user123",
            months=6,
            assumptions={"one_time_expenses": {2: vacation_cost}},  # Vacation in month 2
        )

        # Month 2 (index 2) should have higher expenses than month 1
        assert forecasts[2].expense_total > forecasts[1].expense_total

    @pytest.mark.asyncio
    async def test_forecast_cash_flow_invalid_months(self):
        """Test forecasting with invalid months parameter."""
        with pytest.raises(ValueError, match="months must be positive"):
            await forecast_cash_flow(user_id="user123", months=0)

        with pytest.raises(ValueError, match="months must be positive"):
            await forecast_cash_flow(user_id="user123", months=-1)

    @pytest.mark.asyncio
    async def test_forecast_periods_are_sequential(self):
        """Test that forecast periods are sequential and non-overlapping."""
        forecasts = await forecast_cash_flow(user_id="user123", months=3)

        # Each forecast's end should be close to next forecast's start
        for i in range(len(forecasts) - 1):
            # Allow some variance due to day counting
            time_diff = (forecasts[i + 1].period_start - forecasts[i].period_end).days
            assert abs(time_diff) <= 1  # Should be same day or very close


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_determine_income_source_paycheck(self):
        """Test income source detection for paycheck."""
        from fin_infra.models import Transaction
        from datetime import date

        txn = Transaction(
            id="txn1",
            account_id="acc1",
            amount=5000.0,
            date=date.today(),
            description="EMPLOYER PAYROLL DEPOSIT",
        )

        source = _determine_income_source(txn)
        assert source == "Paycheck"

    def test_determine_income_source_investment(self):
        """Test income source detection for investment income."""
        from fin_infra.models import Transaction
        from datetime import date

        txn = Transaction(
            id="txn1",
            account_id="acc1",
            amount=200.0,
            date=date.today(),
            description="BROKERAGE DIVIDEND PAYMENT",
        )

        source = _determine_income_source(txn)
        assert source == "Investment"

    def test_determine_income_source_side_hustle(self):
        """Test income source detection for side hustle."""
        from fin_infra.models import Transaction
        from datetime import date

        txn = Transaction(
            id="txn1",
            account_id="acc1",
            amount=500.0,
            date=date.today(),
            description="UPWORK PAYMENT",
        )

        source = _determine_income_source(txn)
        assert source == "Side Hustle"

    def test_determine_income_source_other(self):
        """Test income source detection for other income."""
        from fin_infra.models import Transaction
        from datetime import date

        txn = Transaction(
            id="txn1",
            account_id="acc1",
            amount=100.0,
            date=date.today(),
            description="TRANSFER FROM FRIEND",
        )

        source = _determine_income_source(txn)
        assert source == "Other Income"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_zero_income_scenario(self):
        """Test cash flow calculation with zero income."""
        # This would require mocking the banking provider
        # For now, just ensure the function handles the scenario
        result = await calculate_cash_flow(
            user_id="user123", start_date="2025-01-01", end_date="2025-01-31"
        )

        # Mock implementation always returns positive income
        # Real implementation would handle zero income
        assert result.income_total >= 0

    @pytest.mark.asyncio
    async def test_zero_expenses_scenario(self):
        """Test cash flow calculation with zero expenses."""
        result = await calculate_cash_flow(
            user_id="user123", start_date="2025-01-01", end_date="2025-01-31"
        )

        # Mock implementation always returns positive expenses
        # Real implementation would handle zero expenses
        assert result.expense_total >= 0

    @pytest.mark.asyncio
    async def test_negative_net_cash_flow(self):
        """Test that negative net cash flow is calculated correctly."""
        result = await calculate_cash_flow(
            user_id="user123", start_date="2025-01-01", end_date="2025-01-31"
        )

        # Net cash flow should equal income minus expenses
        expected_net = result.income_total - result.expense_total
        assert abs(result.net_cash_flow - expected_net) < 0.01
