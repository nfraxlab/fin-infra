"""Unit tests for growth projections.

Tests compound interest calculations, net worth projections, and scenario generation.
"""

import pytest
import math

from fin_infra.analytics.models import GrowthProjection, Scenario
from fin_infra.analytics.projections import (
    calculate_compound_interest,
    project_net_worth,
)


# ============================================================================
# Test calculate_compound_interest()
# ============================================================================


def test_calculate_compound_interest_basic():
    """Test basic compound interest without contributions."""
    # $10,000 at 8% for 10 years
    result = calculate_compound_interest(10000, 0.08, 10)
    
    # Expected: 10000 * (1.08)^10 = 21,589.25
    expected = 10000 * math.pow(1.08, 10)
    assert abs(result - expected) < 0.01


def test_calculate_compound_interest_with_contributions():
    """Test compound interest with periodic contributions."""
    # $10,000 at 8% for 10 years with $500 per period
    result = calculate_compound_interest(10000, 0.08, 10, 500)
    
    # Principal growth: 10000 * (1.08)^10
    principal_fv = 10000 * math.pow(1.08, 10)
    
    # Contribution growth: 500 * [((1.08)^10 - 1) / 0.08]
    contribution_fv = 500 * ((math.pow(1.08, 10) - 1) / 0.08)
    
    expected = principal_fv + contribution_fv
    assert abs(result - expected) < 0.01


def test_calculate_compound_interest_zero_rate():
    """Test compound interest with 0% rate."""
    # $10,000 at 0% for 10 years with $500 contributions
    result = calculate_compound_interest(10000, 0.0, 10, 500)
    
    # Should be principal + (contribution * periods)
    expected = 10000 + (500 * 10)
    assert result == expected


def test_calculate_compound_interest_zero_periods():
    """Test compound interest with 0 periods."""
    result = calculate_compound_interest(10000, 0.08, 0, 500)
    
    # Should return just the principal
    assert result == 10000


def test_calculate_compound_interest_negative_periods():
    """Test compound interest with negative periods."""
    result = calculate_compound_interest(10000, 0.08, -5, 500)
    
    # Should return principal (no compounding)
    assert result == 10000


def test_calculate_compound_interest_high_rate():
    """Test compound interest with high rate."""
    # $10,000 at 20% for 5 years
    result = calculate_compound_interest(10000, 0.20, 5)
    
    expected = 10000 * math.pow(1.20, 5)
    assert abs(result - expected) < 0.01


def test_calculate_compound_interest_monthly_compounding():
    """Test compound interest with monthly compounding."""
    # $10,000 at 8% annual (0.67% monthly) for 10 years (120 months)
    # with $500 monthly contributions
    monthly_rate = 0.08 / 12
    months = 10 * 12
    
    result = calculate_compound_interest(10000, monthly_rate, months, 500)
    
    # Should be significantly higher due to monthly compounding
    assert result > 80000  # Rough check


def test_calculate_compound_interest_small_principal():
    """Test compound interest with small principal."""
    # $100 at 10% for 5 years
    result = calculate_compound_interest(100, 0.10, 5)
    
    expected = 100 * math.pow(1.10, 5)
    assert abs(result - expected) < 0.01


def test_calculate_compound_interest_large_principal():
    """Test compound interest with large principal."""
    # $1,000,000 at 6% for 20 years
    result = calculate_compound_interest(1000000, 0.06, 20)
    
    expected = 1000000 * math.pow(1.06, 20)
    assert abs(result - expected) < 1.0  # Allow $1 rounding


def test_calculate_compound_interest_fractional_rate():
    """Test compound interest with fractional rate."""
    # $10,000 at 7.25% for 15 years
    result = calculate_compound_interest(10000, 0.0725, 15)
    
    expected = 10000 * math.pow(1.0725, 15)
    assert abs(result - expected) < 0.01


# ============================================================================
# Test project_net_worth()
# ============================================================================


@pytest.mark.asyncio
async def test_project_net_worth_basic():
    """Test basic net worth projection."""
    projection = await project_net_worth("user123", years=10)
    
    assert isinstance(projection, GrowthProjection)
    assert projection.years == 10
    assert projection.current_net_worth > 0
    assert projection.monthly_contribution > 0


@pytest.mark.asyncio
async def test_project_net_worth_scenarios():
    """Test projection generates 3 scenarios."""
    projection = await project_net_worth("user123", years=10)
    
    assert len(projection.scenarios) == 3
    
    # Check scenario names
    names = [s.name for s in projection.scenarios]
    assert "Conservative" in names
    assert "Moderate" in names
    assert "Aggressive" in names


@pytest.mark.asyncio
async def test_project_net_worth_scenario_ordering():
    """Test scenarios are ordered by return rate."""
    projection = await project_net_worth("user123", years=10)
    
    # Conservative should have lowest final value
    # Aggressive should have highest final value
    conservative = next(s for s in projection.scenarios if s.name == "Conservative")
    moderate = next(s for s in projection.scenarios if s.name == "Moderate")
    aggressive = next(s for s in projection.scenarios if s.name == "Aggressive")
    
    assert conservative.final_value < moderate.final_value
    assert moderate.final_value < aggressive.final_value


@pytest.mark.asyncio
async def test_project_net_worth_scenario_returns():
    """Test scenario return rates are reasonable."""
    projection = await project_net_worth("user123", years=10)
    
    for scenario in projection.scenarios:
        # All scenarios should have positive returns
        assert scenario.expected_return > 0
        
        # Returns should be between 4% and 15%
        assert 0.04 <= scenario.expected_return <= 0.15


@pytest.mark.asyncio
async def test_project_net_worth_projected_values():
    """Test projected values include all years."""
    projection = await project_net_worth("user123", years=10)
    
    for scenario in projection.scenarios:
        # Should have 11 values (year 0 through year 10)
        assert len(scenario.projected_values) == 11
        
        # First value should be current net worth
        assert scenario.projected_values[0] == projection.current_net_worth
        
        # Values should generally increase
        assert scenario.projected_values[-1] > scenario.projected_values[0]


@pytest.mark.asyncio
async def test_project_net_worth_final_value_matches():
    """Test final value matches last projected value."""
    projection = await project_net_worth("user123", years=10)
    
    for scenario in projection.scenarios:
        assert scenario.final_value == scenario.projected_values[-1]


@pytest.mark.asyncio
async def test_project_net_worth_confidence_intervals():
    """Test confidence intervals are calculated."""
    projection = await project_net_worth("user123", years=10)
    
    assert projection.confidence_intervals is not None
    assert len(projection.confidence_intervals) == 3
    
    # Check each scenario has confidence interval
    for scenario in projection.scenarios:
        scenario_name = scenario.name.lower()
        assert scenario_name in projection.confidence_intervals
        
        lower, upper = projection.confidence_intervals[scenario_name]
        
        # Lower bound should be less than upper bound
        assert lower < upper
        
        # Bounds should bracket the final value
        assert lower < scenario.final_value < upper


@pytest.mark.asyncio
async def test_project_net_worth_custom_assumptions():
    """Test projection with custom assumptions."""
    custom_assumptions = {
        "conservative_return": 0.04,
        "moderate_return": 0.07,
        "aggressive_return": 0.10,
        "inflation": 0.02,
    }
    
    projection = await project_net_worth(
        "user123",
        years=10,
        assumptions=custom_assumptions,
    )
    
    # Check assumptions were applied
    conservative = next(s for s in projection.scenarios if s.name == "Conservative")
    moderate = next(s for s in projection.scenarios if s.name == "Moderate")
    aggressive = next(s for s in projection.scenarios if s.name == "Aggressive")
    
    assert conservative.expected_return == 0.04
    assert moderate.expected_return == 0.07
    assert aggressive.expected_return == 0.10


@pytest.mark.asyncio
async def test_project_net_worth_short_term():
    """Test projection for short time period."""
    projection = await project_net_worth("user123", years=5)
    
    assert projection.years == 5
    
    for scenario in projection.scenarios:
        assert len(scenario.projected_values) == 6  # 0-5


@pytest.mark.asyncio
async def test_project_net_worth_long_term():
    """Test projection for long time period."""
    projection = await project_net_worth("user123", years=40)
    
    assert projection.years == 40
    
    for scenario in projection.scenarios:
        assert len(scenario.projected_values) == 41  # 0-40
        
        # Long-term growth should be substantial
        growth_multiple = scenario.final_value / projection.current_net_worth
        assert growth_multiple > 2.0  # At least 2x over 40 years


@pytest.mark.asyncio
async def test_project_net_worth_different_users():
    """Test projections for different users."""
    projection1 = await project_net_worth("user_a", years=10)
    projection2 = await project_net_worth("user_b", years=10)
    
    # Different users should have different starting points (due to hash)
    # Note: There's a small chance they're the same, but unlikely
    assert projection1.current_net_worth != projection2.current_net_worth or \
           projection1.monthly_contribution != projection2.monthly_contribution


@pytest.mark.asyncio
async def test_project_net_worth_assumptions_stored():
    """Test assumptions are stored in projection."""
    projection = await project_net_worth("user123", years=10)
    
    assert projection.assumptions is not None
    assert "conservative_return" in projection.assumptions
    assert "moderate_return" in projection.assumptions
    assert "aggressive_return" in projection.assumptions
    assert "inflation" in projection.assumptions
    assert "contribution_growth" in projection.assumptions


@pytest.mark.asyncio
async def test_project_net_worth_growth_with_contributions():
    """Test net worth grows faster with contributions."""
    projection = await project_net_worth("user123", years=20)
    
    # Calculate expected growth with contributions
    # Should be significantly more than just compound interest on principal
    conservative = next(s for s in projection.scenarios if s.name == "Conservative")
    
    # Without contributions, would be just principal * (1 + r)^n
    simple_growth = projection.current_net_worth * math.pow(
        1 + conservative.expected_return,
        20
    )
    
    # With contributions, should be higher
    assert conservative.final_value > simple_growth


@pytest.mark.asyncio
async def test_project_net_worth_confidence_intervals_widen_over_time():
    """Test confidence intervals are wider for longer projections."""
    projection_10y = await project_net_worth("user123", years=10)
    projection_30y = await project_net_worth("user123", years=30)
    
    # 30-year intervals should be wider than 10-year
    for scenario_name in ["conservative", "moderate", "aggressive"]:
        lower_10y, upper_10y = projection_10y.confidence_intervals[scenario_name]
        lower_30y, upper_30y = projection_30y.confidence_intervals[scenario_name]
        
        interval_10y = upper_10y - lower_10y
        interval_30y = upper_30y - lower_30y
        
        # Longer time = wider confidence interval
        assert interval_30y > interval_10y


@pytest.mark.asyncio
async def test_project_net_worth_positive_growth():
    """Test all scenarios show positive growth."""
    projection = await project_net_worth("user123", years=20)
    
    for scenario in projection.scenarios:
        # Final value should be greater than starting net worth
        assert scenario.final_value > projection.current_net_worth
        
        # All intermediate values should be >= previous value (monotonic growth)
        for i in range(1, len(scenario.projected_values)):
            assert scenario.projected_values[i] >= scenario.projected_values[i - 1]


@pytest.mark.asyncio
async def test_project_net_worth_realistic_values():
    """Test projection produces realistic values."""
    projection = await project_net_worth("user123", years=30)
    
    # Starting net worth should be reasonable
    assert 10000 <= projection.current_net_worth <= 500000
    
    # Monthly contributions should be reasonable
    assert 100 <= projection.monthly_contribution <= 5000
    
    # Final values should be achievable
    for scenario in projection.scenarios:
        # 30 years of growth should be significant but not absurd
        growth_multiple = scenario.final_value / projection.current_net_worth
        assert 2.0 <= growth_multiple <= 100.0


@pytest.mark.asyncio
async def test_project_net_worth_one_year():
    """Test projection for single year."""
    projection = await project_net_worth("user123", years=1)
    
    assert projection.years == 1
    
    for scenario in projection.scenarios:
        # Should have 2 values (year 0 and year 1)
        assert len(scenario.projected_values) == 2


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_calculate_compound_interest_zero_principal():
    """Test compound interest with zero principal."""
    # $0 principal but $500 contributions for 10 years at 8%
    result = calculate_compound_interest(0, 0.08, 10, 500)
    
    # Should be future value of annuity only
    expected = 500 * ((math.pow(1.08, 10) - 1) / 0.08)
    assert abs(result - expected) < 0.01


def test_calculate_compound_interest_very_small_rate():
    """Test compound interest with very small rate."""
    # $10,000 at 0.1% for 10 years
    result = calculate_compound_interest(10000, 0.001, 10)
    
    expected = 10000 * math.pow(1.001, 10)
    assert abs(result - expected) < 0.01


@pytest.mark.asyncio
async def test_project_net_worth_zero_years():
    """Test projection with zero years (should still work)."""
    projection = await project_net_worth("user123", years=0)
    
    assert projection.years == 0
    
    for scenario in projection.scenarios:
        # Should have 1 value (just current)
        assert len(scenario.projected_values) == 1
        assert scenario.final_value == projection.current_net_worth
