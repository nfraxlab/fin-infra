"""Integration tests for growth projections.

Tests end-to-end projection workflows, realistic scenarios, and multi-year forecasts.
"""

import pytest

from fin_infra.analytics.models import GrowthProjection, Scenario
from fin_infra.analytics.projections import (
    calculate_compound_interest,
    project_net_worth,
)


# ============================================================================
# Test End-to-End Projections
# ============================================================================


@pytest.mark.asyncio
async def test_projection_end_to_end():
    """Test complete projection workflow."""
    projection = await project_net_worth("integration_user_1", years=20)

    # Verify structure
    assert isinstance(projection, GrowthProjection)
    assert projection.years == 20
    assert projection.current_net_worth > 0
    assert projection.monthly_contribution > 0

    # Verify scenarios
    assert len(projection.scenarios) == 3
    for scenario in projection.scenarios:
        assert isinstance(scenario, Scenario)
        assert len(scenario.projected_values) == 21  # 0-20
        assert scenario.final_value > projection.current_net_worth

    # Verify confidence intervals
    assert projection.confidence_intervals is not None
    assert len(projection.confidence_intervals) == 3


@pytest.mark.asyncio
async def test_projection_realistic_retirement_scenario():
    """Test realistic 30-year retirement projection."""
    # Custom assumptions for retirement planning
    assumptions = {
        "conservative_return": 0.05,  # Bond-heavy near retirement
        "moderate_return": 0.07,  # Balanced portfolio
        "aggressive_return": 0.09,  # Equity-heavy early years
        "inflation": 0.03,
        "contribution_growth": 0.02,  # Salary increases
    }

    projection = await project_net_worth(
        "retirement_planner",
        years=30,
        assumptions=assumptions,
    )

    # Verify 30-year projection structure
    assert projection.years == 30

    # Check scenario outcomes
    conservative = next(s for s in projection.scenarios if s.name == "Conservative")
    moderate = next(s for s in projection.scenarios if s.name == "Moderate")
    aggressive = next(s for s in projection.scenarios if s.name == "Aggressive")

    # All should show significant growth over 30 years
    assert conservative.final_value > projection.current_net_worth * 2
    assert moderate.final_value > conservative.final_value
    assert aggressive.final_value > moderate.final_value

    # Check confidence intervals are reasonable
    for scenario_name in ["conservative", "moderate", "aggressive"]:
        lower, upper = projection.confidence_intervals[scenario_name]
        scenario = next(s for s in projection.scenarios if s.name.lower() == scenario_name)

        # Interval should bracket the final value
        assert lower < scenario.final_value < upper

        # Interval width should be reasonable (not too wide or narrow)
        interval_width = upper - lower
        assert interval_width > 0
        assert interval_width < scenario.final_value * 2  # Not more than 2x final value


@pytest.mark.asyncio
async def test_projection_wealth_accumulation():
    """Test wealth accumulation over different time horizons."""
    horizons = [5, 10, 20, 30]
    user_id = "wealth_builder"

    projections = []
    for years in horizons:
        projection = await project_net_worth(user_id, years=years)
        projections.append(projection)

    # Verify longer horizons have higher final values
    for i in range(len(projections) - 1):
        current_proj = projections[i]
        next_proj = projections[i + 1]

        # Compare moderate scenarios
        current_moderate = next(s for s in current_proj.scenarios if s.name == "Moderate")
        next_moderate = next(s for s in next_proj.scenarios if s.name == "Moderate")

        # Longer projection should have higher final value
        assert next_moderate.final_value > current_moderate.final_value


@pytest.mark.asyncio
async def test_projection_scenario_comparison():
    """Test comparing different investment strategies."""
    projection = await project_net_worth("strategy_comparison", years=25)

    conservative = next(s for s in projection.scenarios if s.name == "Conservative")
    moderate = next(s for s in projection.scenarios if s.name == "Moderate")
    aggressive = next(s for s in projection.scenarios if s.name == "Aggressive")

    # Calculate growth multiples
    conservative_multiple = conservative.final_value / projection.current_net_worth
    moderate_multiple = moderate.final_value / projection.current_net_worth
    aggressive_multiple = aggressive.final_value / projection.current_net_worth

    # Higher risk should yield higher returns
    assert conservative_multiple < moderate_multiple < aggressive_multiple

    # All should show meaningful growth over 25 years
    assert conservative_multiple >= 2.0  # At least 2x
    assert aggressive_multiple >= 5.0  # Aggressive should be substantial


@pytest.mark.asyncio
async def test_projection_consistency_across_calls():
    """Test projection is consistent for same user."""
    user_id = "consistent_user"

    projection1 = await project_net_worth(user_id, years=15)
    projection2 = await project_net_worth(user_id, years=15)

    # Same inputs should yield same outputs
    assert projection1.current_net_worth == projection2.current_net_worth
    assert projection1.monthly_contribution == projection2.monthly_contribution

    # Scenarios should match
    for i in range(3):
        assert projection1.scenarios[i].name == projection2.scenarios[i].name
        assert projection1.scenarios[i].expected_return == projection2.scenarios[i].expected_return
        assert projection1.scenarios[i].final_value == projection2.scenarios[i].final_value


# ============================================================================
# Test Compound Interest Integration
# ============================================================================


def test_compound_interest_retirement_401k():
    """Test 401k retirement calculation."""
    # Starting balance: $50,000
    # Annual return: 8%
    # Years: 30
    # Monthly contribution: $1,000 ($12,000/year)

    # Convert to annual compounding
    principal = 50000
    annual_rate = 0.08
    years = 30
    annual_contribution = 12000

    result = calculate_compound_interest(principal, annual_rate, years, annual_contribution)

    # Should be over $1.5M (power of compound interest!)
    assert result > 1500000


def test_compound_interest_college_savings():
    """Test 529 college savings calculation."""
    # Starting: $10,000
    # Annual return: 6%
    # Years: 18 (until college)
    # Monthly contribution: $500 ($6,000/year)

    result = calculate_compound_interest(10000, 0.06, 18, 6000)

    # Should be over $200,000
    assert result > 200000


def test_compound_interest_emergency_fund():
    """Test emergency fund growth (low-risk)."""
    # Starting: $5,000
    # Annual return: 3% (HYSA)
    # Years: 5
    # Monthly contribution: $200 ($2,400/year)

    result = calculate_compound_interest(5000, 0.03, 5, 2400)

    # Should be around $18,000-$19,000
    assert 18000 <= result <= 19000


def test_compound_interest_monthly_vs_annual():
    """Test monthly compounding vs annual compounding."""
    principal = 10000
    annual_rate = 0.08
    years = 10
    annual_contribution = 6000

    # Annual compounding
    annual_result = calculate_compound_interest(principal, annual_rate, years, annual_contribution)

    # Monthly compounding
    monthly_rate = annual_rate / 12
    months = years * 12
    monthly_contribution = annual_contribution / 12
    monthly_result = calculate_compound_interest(
        principal, monthly_rate, months, monthly_contribution
    )

    # Monthly compounding should yield slightly higher result
    assert monthly_result > annual_result


# ============================================================================
# Test Custom Assumptions
# ============================================================================


@pytest.mark.asyncio
async def test_projection_conservative_investor():
    """Test projection for conservative investor."""
    assumptions = {
        "conservative_return": 0.04,  # 4% - very conservative
        "moderate_return": 0.06,  # 6% - still conservative
        "aggressive_return": 0.08,  # 8% - moderate by normal standards
    }

    projection = await project_net_worth(
        "conservative_investor",
        years=20,
        assumptions=assumptions,
    )

    # Verify custom returns were used
    conservative = next(s for s in projection.scenarios if s.name == "Conservative")
    assert conservative.expected_return == 0.04


@pytest.mark.asyncio
async def test_projection_aggressive_investor():
    """Test projection for aggressive investor."""
    assumptions = {
        "conservative_return": 0.08,  # 8% - moderate baseline
        "moderate_return": 0.11,  # 11% - aggressive
        "aggressive_return": 0.14,  # 14% - very aggressive
    }

    projection = await project_net_worth(
        "aggressive_investor",
        years=20,
        assumptions=assumptions,
    )

    # Verify custom returns were used
    aggressive = next(s for s in projection.scenarios if s.name == "Aggressive")
    assert aggressive.expected_return == 0.14

    # Aggressive strategy should show very high growth
    growth_multiple = aggressive.final_value / projection.current_net_worth
    assert growth_multiple > 10.0  # Over 10x in 20 years at 14%


@pytest.mark.asyncio
async def test_projection_with_high_inflation():
    """Test projection accounting for high inflation."""
    assumptions = {
        "inflation": 0.05,  # 5% inflation (above normal)
    }

    projection = await project_net_worth(
        "inflation_scenario",
        years=20,
        assumptions=assumptions,
    )

    # Inflation stored in assumptions
    assert projection.assumptions["inflation"] == 0.05


# ============================================================================
# Test Multi-User Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_projection_multiple_users():
    """Test projections for multiple users."""
    users = ["user_a", "user_b", "user_c", "user_d", "user_e"]

    projections = []
    for user_id in users:
        projection = await project_net_worth(user_id, years=15)
        projections.append(projection)

    # All projections should be valid
    for projection in projections:
        assert isinstance(projection, GrowthProjection)
        assert projection.years == 15
        assert len(projection.scenarios) == 3


@pytest.mark.asyncio
async def test_projection_concurrent_requests():
    """Test multiple concurrent projection requests."""
    import asyncio

    users = ["user_1", "user_2", "user_3", "user_4", "user_5"]

    # Run concurrent projections
    tasks = [project_net_worth(uid, years=20) for uid in users]
    projections = await asyncio.gather(*tasks)

    # All should succeed
    assert len(projections) == len(users)

    for projection in projections:
        assert isinstance(projection, GrowthProjection)
        assert projection.years == 20


# ============================================================================
# Test Real-World Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_projection_early_career():
    """Test projection for early career professional (high growth potential)."""
    assumptions = {
        "contribution_growth": 0.05,  # 5% annual raises
    }

    projection = await project_net_worth(
        "early_career",
        years=35,
        assumptions=assumptions,
    )

    # Long horizon + contribution growth should yield substantial wealth
    moderate = next(s for s in projection.scenarios if s.name == "Moderate")

    # Should accumulate significant wealth over 35 years
    assert moderate.final_value > projection.current_net_worth * 10


@pytest.mark.asyncio
async def test_projection_mid_career():
    """Test projection for mid-career professional (15-20 years to retirement)."""
    projection = await project_net_worth("mid_career", years=18)

    # All scenarios should show strong growth
    for scenario in projection.scenarios:
        growth_multiple = scenario.final_value / projection.current_net_worth
        assert growth_multiple >= 2.0  # At least 2x over 18 years


@pytest.mark.asyncio
async def test_projection_near_retirement():
    """Test projection near retirement (conservative, shorter horizon)."""
    assumptions = {
        "conservative_return": 0.04,  # Very conservative near retirement
        "moderate_return": 0.05,
        "aggressive_return": 0.06,
    }

    projection = await project_net_worth(
        "near_retirement",
        years=8,
        assumptions=assumptions,
    )

    # Shorter horizon + lower returns = more modest growth
    conservative = next(s for s in projection.scenarios if s.name == "Conservative")

    # Should still grow (contributions boost growth significantly)
    growth_multiple = conservative.final_value / projection.current_net_worth
    assert 1.2 <= growth_multiple <= 5.0  # Contributions boost even conservative scenarios


# ============================================================================
# Test Edge Cases and Validation
# ============================================================================


@pytest.mark.asyncio
async def test_projection_minimum_years():
    """Test projection with minimum time period."""
    projection = await project_net_worth("min_years", years=1)

    assert projection.years == 1

    for scenario in projection.scenarios:
        assert len(scenario.projected_values) == 2  # Year 0 and 1


@pytest.mark.asyncio
async def test_projection_very_long_term():
    """Test very long-term projection (40+ years)."""
    projection = await project_net_worth("long_term", years=50)

    assert projection.years == 50

    # Should show massive compound growth over 50 years
    aggressive = next(s for s in projection.scenarios if s.name == "Aggressive")
    growth_multiple = aggressive.final_value / projection.current_net_worth

    assert growth_multiple > 50.0  # Over 50x in 50 years with contributions
