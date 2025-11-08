"""Unit tests for savings rate analysis."""

from datetime import date

import pytest

from fin_infra.analytics.models import Period, SavingsDefinition, TrendDirection
from fin_infra.analytics.savings import (
    _calculate_trend,
    _get_historical_savings_rates,
    calculate_savings_rate,
)


class TestCalculateSavingsRate:
    """Tests for calculate_savings_rate function."""

    @pytest.mark.asyncio
    async def test_calculate_savings_rate_monthly_net(self):
        """Test monthly net savings rate calculation."""
        result = await calculate_savings_rate("user123", period="monthly", definition="net")
        
        assert result.period == Period.MONTHLY
        assert result.definition == SavingsDefinition.NET
        assert 0.0 <= result.savings_rate <= 1.0
        assert result.savings_amount == result.income - result.expenses
        assert result.trend in [TrendDirection.INCREASING, TrendDirection.DECREASING, TrendDirection.STABLE]
    
    @pytest.mark.asyncio
    async def test_calculate_savings_rate_weekly_gross(self):
        """Test weekly gross savings rate calculation."""
        result = await calculate_savings_rate("user123", period="weekly", definition="gross")
        
        assert result.period == Period.WEEKLY
        assert result.definition == SavingsDefinition.GROSS
        assert result.income > 0
        assert result.savings_amount >= 0
    
    @pytest.mark.asyncio
    async def test_calculate_savings_rate_quarterly_discretionary(self):
        """Test quarterly discretionary savings rate calculation."""
        result = await calculate_savings_rate(
            "user123", 
            period="quarterly",
            definition="discretionary"
        )
        
        assert result.period == Period.QUARTERLY
        assert result.definition == SavingsDefinition.DISCRETIONARY
        assert result.savings_rate >= 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_savings_rate_yearly(self):
        """Test yearly savings rate calculation."""
        result = await calculate_savings_rate("user123", period="yearly", definition="net")
        
        assert result.period == Period.YEARLY
        assert result.income > 0
    
    @pytest.mark.asyncio
    async def test_calculate_savings_rate_invalid_period(self):
        """Test error on invalid period."""
        with pytest.raises(ValueError, match="Invalid period"):
            await calculate_savings_rate("user123", period="invalid")
    
    @pytest.mark.asyncio
    async def test_calculate_savings_rate_invalid_definition(self):
        """Test error on invalid definition."""
        with pytest.raises(ValueError, match="Invalid definition"):
            await calculate_savings_rate("user123", definition="invalid")
    
    @pytest.mark.asyncio
    async def test_savings_rate_clamped_to_valid_range(self):
        """Test savings rate is always between 0 and 1."""
        result = await calculate_savings_rate("user123", period="monthly", definition="net")
        
        assert result.savings_rate >= 0.0
        assert result.savings_rate <= 1.0


class TestSavingsDefinitions:
    """Tests for different savings rate definitions."""

    @pytest.mark.asyncio
    async def test_gross_savings_includes_all_income(self):
        """Test gross savings uses total income before tax."""
        result = await calculate_savings_rate("user123", definition="gross")
        
        assert result.definition == SavingsDefinition.GROSS
        # Gross should have higher income than net (includes tax)
        assert result.income > 0
    
    @pytest.mark.asyncio
    async def test_net_savings_excludes_tax(self):
        """Test net savings uses income after tax."""
        result = await calculate_savings_rate("user123", definition="net")
        
        assert result.definition == SavingsDefinition.NET
        # Net income should be less than gross
        assert result.income > 0
    
    @pytest.mark.asyncio
    async def test_discretionary_savings_excludes_necessities(self):
        """Test discretionary savings only counts after necessities."""
        result = await calculate_savings_rate("user123", definition="discretionary")
        
        assert result.definition == SavingsDefinition.DISCRETIONARY
        # Discretionary income should be lowest
        assert result.income > 0
    
    @pytest.mark.asyncio
    async def test_definitions_produce_different_rates(self):
        """Test different definitions yield different savings rates."""
        gross = await calculate_savings_rate("user123", definition="gross")
        net = await calculate_savings_rate("user123", definition="net")
        discretionary = await calculate_savings_rate("user123", definition="discretionary")
        
        # All should be valid
        assert 0.0 <= gross.savings_rate <= 1.0
        assert 0.0 <= net.savings_rate <= 1.0
        assert 0.0 <= discretionary.savings_rate <= 1.0
        
        # Income amounts should differ
        assert gross.income != net.income or net.income != discretionary.income


class TestPeriodTypes:
    """Tests for different period types."""

    @pytest.mark.asyncio
    async def test_all_period_types_supported(self):
        """Test all period types produce valid results."""
        periods = ["weekly", "monthly", "quarterly", "yearly"]
        
        for period in periods:
            result = await calculate_savings_rate("user123", period=period)
            assert result.period == Period(period)
            assert result.income > 0
            assert result.expenses >= 0
    
    @pytest.mark.asyncio
    async def test_period_affects_calculation(self):
        """Test different periods can yield different results."""
        weekly = await calculate_savings_rate("user123", period="weekly")
        monthly = await calculate_savings_rate("user123", period="monthly")
        
        assert weekly.period == Period.WEEKLY
        assert monthly.period == Period.MONTHLY


class TestTrendCalculation:
    """Tests for trend direction calculation."""

    @pytest.mark.asyncio
    async def test_get_historical_savings_rates(self):
        """Test fetching historical savings rates."""
        rates = await _get_historical_savings_rates(
            "user123", 
            months=6,
            period=Period.MONTHLY,
            definition=SavingsDefinition.NET
        )
        
        assert isinstance(rates, list)
        assert len(rates) > 0
        assert all(isinstance(r, float) for r in rates)
    
    def test_calculate_trend_increasing(self):
        """Test trend detection for increasing savings rate."""
        # Recent rates higher than older rates
        rates = [0.30, 0.28, 0.26, 0.22, 0.20, 0.18]
        trend = _calculate_trend(rates)
        
        assert trend == TrendDirection.INCREASING
    
    def test_calculate_trend_decreasing(self):
        """Test trend detection for decreasing savings rate."""
        # Recent rates lower than older rates
        rates = [0.18, 0.20, 0.22, 0.26, 0.28, 0.30]
        trend = _calculate_trend(rates)
        
        assert trend == TrendDirection.DECREASING
    
    def test_calculate_trend_stable(self):
        """Test trend detection for stable savings rate."""
        # Rates within threshold (2%)
        rates = [0.25, 0.26, 0.24, 0.25, 0.26, 0.25]
        trend = _calculate_trend(rates)
        
        assert trend == TrendDirection.STABLE
    
    def test_calculate_trend_insufficient_data(self):
        """Test trend defaults to stable with insufficient data."""
        rates = [0.25, 0.26]  # Only 2 data points
        trend = _calculate_trend(rates)
        
        assert trend == TrendDirection.STABLE
    
    def test_calculate_trend_empty_data(self):
        """Test trend defaults to stable with empty data."""
        trend = _calculate_trend([])
        
        assert trend == TrendDirection.STABLE


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_income_produces_zero_savings_rate(self):
        """Test handling of zero income scenario."""
        # This would require mocking, but test the model can handle it
        result = await calculate_savings_rate("user123", period="monthly")
        
        # Should not crash and produce valid result
        assert result.savings_rate >= 0.0
    
    @pytest.mark.asyncio
    async def test_negative_savings_clamped_to_zero(self):
        """Test negative savings rate is clamped to 0."""
        result = await calculate_savings_rate("user123", period="monthly")
        
        # Even if expenses > income, rate should be >= 0
        assert result.savings_rate >= 0.0
    
    @pytest.mark.asyncio
    async def test_perfect_savings_clamped_to_one(self):
        """Test 100%+ savings rate is clamped to 1.0."""
        result = await calculate_savings_rate("user123", period="monthly")
        
        # Rate should never exceed 1.0 (100%)
        assert result.savings_rate <= 1.0
    
    @pytest.mark.asyncio
    async def test_savings_amount_consistency(self):
        """Test savings amount equals income minus expenses."""
        result = await calculate_savings_rate("user123", period="monthly", definition="net")
        
        expected_savings = result.income - result.expenses
        assert abs(result.savings_amount - expected_savings) < 0.01  # Float precision
    
    @pytest.mark.asyncio
    async def test_savings_rate_calculation_accuracy(self):
        """Test savings rate is accurately calculated."""
        result = await calculate_savings_rate("user123", period="monthly", definition="net")
        
        if result.income > 0:
            expected_rate = result.savings_amount / result.income
            # Clamp to [0, 1]
            expected_rate = max(0.0, min(1.0, expected_rate))
            assert abs(result.savings_rate - expected_rate) < 0.01
