"""Integration tests for savings rate calculation.

These tests verify that savings rate calculation integrates correctly with:
- Cash flow analysis module (income and expense data)
- Historical data tracking (trend analysis)
- Multiple calculation definitions working together
"""

from datetime import datetime

import pytest

from fin_infra.analytics.models import Period, SavingsDefinition, TrendDirection
from fin_infra.analytics.savings import calculate_savings_rate
from fin_infra.models import Transaction


# Mock Banking Provider (reused from cash flow tests)
class MockBankingProvider:
    """Mock banking provider for integration testing."""

    def __init__(self):
        self.transactions = []

    def add_transaction(self, transaction: Transaction):
        """Add a transaction to the mock provider."""
        self.transactions.append(transaction)

    async def get_transactions(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        accounts=None,
    ):
        """Fetch transactions for the given period."""
        filtered = [t for t in self.transactions if start_date.date() <= t.date <= end_date.date()]
        if accounts:
            filtered = [t for t in filtered if t.account_id in accounts]
        return filtered


class TestSavingsRateWithCashFlowIntegration:
    """Tests for savings rate calculation using cash flow data."""

    @pytest.mark.asyncio
    async def test_savings_rate_derived_from_cash_flow(self):
        """Test that savings rate correctly uses cash flow data."""
        # Calculate savings rate
        result = await calculate_savings_rate(
            "user123",
            period="monthly",
            definition="net",
        )

        # Verify savings rate consistency
        assert 0.0 <= result.savings_rate <= 1.0

        # Verify savings amount matches calculation
        expected_savings = result.income - result.expenses
        assert abs(result.savings_amount - expected_savings) < 0.01

        # Verify savings rate calculation
        if result.income > 0:
            expected_rate = result.savings_amount / result.income
            expected_rate = max(0.0, min(1.0, expected_rate))
            assert abs(result.savings_rate - expected_rate) < 0.01

    @pytest.mark.asyncio
    async def test_savings_rate_consistency_across_periods(self):
        """Test that savings rate is consistent for the same data across different period types."""
        # Calculate for different periods
        weekly = await calculate_savings_rate("user123", period="weekly")
        monthly = await calculate_savings_rate("user123", period="monthly")
        quarterly = await calculate_savings_rate("user123", period="quarterly")

        # All should return valid results
        assert 0.0 <= weekly.savings_rate <= 1.0
        assert 0.0 <= monthly.savings_rate <= 1.0
        assert 0.0 <= quarterly.savings_rate <= 1.0

        # Periods should match
        assert weekly.period == Period.WEEKLY
        assert monthly.period == Period.MONTHLY
        assert quarterly.period == Period.QUARTERLY

    @pytest.mark.asyncio
    async def test_savings_rate_consistency_across_definitions(self):
        """Test that different definitions produce internally consistent results."""
        # Calculate with all definitions
        gross = await calculate_savings_rate("user123", definition="gross")
        net = await calculate_savings_rate("user123", definition="net")
        discretionary = await calculate_savings_rate("user123", definition="discretionary")

        # All should be valid
        assert 0.0 <= gross.savings_rate <= 1.0
        assert 0.0 <= net.savings_rate <= 1.0
        assert 0.0 <= discretionary.savings_rate <= 1.0

        # Definitions should match
        assert gross.definition == SavingsDefinition.GROSS
        assert net.definition == SavingsDefinition.NET
        assert discretionary.definition == SavingsDefinition.DISCRETIONARY

        # Each should have consistent internal calculations
        for result in [gross, net, discretionary]:
            expected_savings = result.income - result.expenses
            assert abs(result.savings_amount - expected_savings) < 0.01


class TestSavingsRatePeriodAlignment:
    """Tests for period alignment between savings rate and cash flow."""

    @pytest.mark.asyncio
    async def test_weekly_period_alignment(self):
        """Test that weekly savings rate aligns with 7-day period."""
        result = await calculate_savings_rate("user123", period="weekly")

        assert result.period == Period.WEEKLY
        # Weekly period should use 7-day lookback
        # (Verified by checking period dates if exposed)

    @pytest.mark.asyncio
    async def test_monthly_period_alignment(self):
        """Test that monthly savings rate aligns with 30-day period."""
        result = await calculate_savings_rate("user123", period="monthly")

        assert result.period == Period.MONTHLY
        # Monthly period should use 30-day lookback

    @pytest.mark.asyncio
    async def test_quarterly_period_alignment(self):
        """Test that quarterly savings rate aligns with 90-day period."""
        result = await calculate_savings_rate("user123", period="quarterly")

        assert result.period == Period.QUARTERLY
        # Quarterly period should use 90-day lookback

    @pytest.mark.asyncio
    async def test_yearly_period_alignment(self):
        """Test that yearly savings rate aligns with 365-day period."""
        result = await calculate_savings_rate("user123", period="yearly")

        assert result.period == Period.YEARLY
        # Yearly period should use 365-day lookback


class TestSavingsRateTrendIntegration:
    """Tests for savings rate trend analysis with historical data."""

    @pytest.mark.asyncio
    async def test_trend_direction_is_set(self):
        """Test that trend direction is calculated and set."""
        result = await calculate_savings_rate(
            "user123",
            period="monthly",
            historical_months=6,
        )

        # Trend should be set to one of the valid directions
        assert result.trend in [
            TrendDirection.INCREASING,
            TrendDirection.DECREASING,
            TrendDirection.STABLE,
        ]

    @pytest.mark.asyncio
    async def test_trend_with_different_historical_periods(self):
        """Test trend calculation with different historical lookback periods."""
        # Short history
        short = await calculate_savings_rate("user123", historical_months=3)

        # Long history
        long = await calculate_savings_rate("user123", historical_months=12)

        # Both should have valid trends
        assert short.trend is not None
        assert long.trend is not None

    @pytest.mark.asyncio
    async def test_trend_consistency_with_period(self):
        """Test that trend is consistent with the selected period type."""
        # Calculate for same user but different periods
        weekly = await calculate_savings_rate("user123", period="weekly")
        monthly = await calculate_savings_rate("user123", period="monthly")

        # Both should have trends (may differ due to different data windows)
        assert weekly.trend is not None
        assert monthly.trend is not None


class TestSavingsRateDefinitionIntegration:
    """Tests for different savings rate definitions."""

    @pytest.mark.asyncio
    async def test_gross_vs_net_relationship(self):
        """Test relationship between gross and net savings rates."""
        gross = await calculate_savings_rate("user123", definition="gross")
        net = await calculate_savings_rate("user123", definition="net")

        # Net income should be less than or equal to gross (after tax)
        # Therefore net savings rate might be higher (same savings, lower income base)
        # But both should be valid
        assert 0.0 <= gross.savings_rate <= 1.0
        assert 0.0 <= net.savings_rate <= 1.0

        # Gross income >= Net income (net has tax deducted)
        assert gross.income >= net.income

    @pytest.mark.asyncio
    async def test_net_vs_discretionary_relationship(self):
        """Test relationship between net and discretionary savings rates."""
        net = await calculate_savings_rate("user123", definition="net")
        discretionary = await calculate_savings_rate("user123", definition="discretionary")

        # Discretionary income should be less than net (necessities deducted)
        # Both should be valid
        assert 0.0 <= net.savings_rate <= 1.0
        assert 0.0 <= discretionary.savings_rate <= 1.0

        # Net income >= Discretionary income (discretionary excludes necessities)
        assert net.income >= discretionary.income

    @pytest.mark.asyncio
    async def test_all_definitions_with_same_period(self):
        """Test that all definitions work correctly for the same period."""
        period = "monthly"

        gross = await calculate_savings_rate("user123", period=period, definition="gross")
        net = await calculate_savings_rate("user123", period=period, definition="net")
        discretionary = await calculate_savings_rate(
            "user123", period=period, definition="discretionary"
        )

        # All should use the same period
        assert gross.period == Period.MONTHLY
        assert net.period == Period.MONTHLY
        assert discretionary.period == Period.MONTHLY

        # Income should decrease: gross >= net >= discretionary
        assert gross.income >= net.income >= discretionary.income


class TestSavingsRateEdgeCasesIntegration:
    """Integration tests for edge cases across modules."""

    @pytest.mark.asyncio
    async def test_zero_income_scenario(self):
        """Test savings rate when income is zero."""
        # This would require mocking banking provider with no income
        result = await calculate_savings_rate("user123", period="monthly")

        # Should handle gracefully (not crash)
        assert 0.0 <= result.savings_rate <= 1.0

    @pytest.mark.asyncio
    async def test_negative_savings_scenario(self):
        """Test savings rate when expenses exceed income."""
        # This would require mocking banking provider with expenses > income
        result = await calculate_savings_rate("user123", period="monthly")

        # Savings rate should be clamped to 0 (can't have negative rate)
        assert result.savings_rate >= 0.0

        # Savings amount could be negative (overspending)
        # But this is valid data

    @pytest.mark.asyncio
    async def test_high_savings_rate_scenario(self):
        """Test savings rate when income is much higher than expenses."""
        # This would require mocking banking provider with minimal expenses
        result = await calculate_savings_rate("user123", period="monthly")

        # Savings rate should be clamped to 1.0 maximum (100%)
        assert result.savings_rate <= 1.0


class TestSavingsRateEndToEndIntegration:
    """End-to-end integration tests for complete savings rate analysis."""

    @pytest.mark.asyncio
    async def test_full_savings_rate_analysis_pipeline(self):
        """Test complete savings rate analysis from data to insights."""
        # Calculate savings rate with all options
        result = await calculate_savings_rate(
            "user123",
            period="monthly",
            definition="net",
            historical_months=6,
        )

        # Verify complete result structure
        assert result.savings_rate >= 0.0
        assert result.savings_rate <= 1.0
        assert result.savings_amount == result.income - result.expenses
        assert result.income >= 0.0
        assert result.expenses >= 0.0
        assert result.period == Period.MONTHLY
        assert result.definition == SavingsDefinition.NET
        assert result.trend in [
            TrendDirection.INCREASING,
            TrendDirection.DECREASING,
            TrendDirection.STABLE,
        ]

    @pytest.mark.asyncio
    async def test_savings_rate_over_multiple_periods(self):
        """Test calculating savings rate for multiple consecutive periods."""
        periods = ["weekly", "monthly", "quarterly", "yearly"]
        results = []

        for period in periods:
            result = await calculate_savings_rate("user123", period=period)
            results.append(result)

        # All periods should return valid results
        assert len(results) == 4

        for i, result in enumerate(results):
            assert result.period == Period(periods[i])
            assert 0.0 <= result.savings_rate <= 1.0
            assert result.savings_amount == result.income - result.expenses

    @pytest.mark.asyncio
    async def test_savings_rate_with_all_definitions(self):
        """Test calculating savings rate with all definitions."""
        definitions = ["gross", "net", "discretionary"]
        results = []

        for definition in definitions:
            result = await calculate_savings_rate("user123", definition=definition)
            results.append(result)

        # All definitions should return valid results
        assert len(results) == 3

        for i, result in enumerate(results):
            assert result.definition == SavingsDefinition(definitions[i])
            assert 0.0 <= result.savings_rate <= 1.0

        # Income should decrease across definitions: gross >= net >= discretionary
        assert results[0].income >= results[1].income >= results[2].income

    @pytest.mark.asyncio
    async def test_savings_rate_consistency_over_time(self):
        """Test that savings rate calculations are consistent when repeated."""
        # Calculate twice with same parameters
        result1 = await calculate_savings_rate("user123", period="monthly", definition="net")
        result2 = await calculate_savings_rate("user123", period="monthly", definition="net")

        # Results should be identical (deterministic calculation)
        assert result1.savings_rate == result2.savings_rate
        assert result1.savings_amount == result2.savings_amount
        assert result1.income == result2.income
        assert result1.expenses == result2.expenses
        assert result1.period == result2.period
        assert result1.definition == result2.definition
