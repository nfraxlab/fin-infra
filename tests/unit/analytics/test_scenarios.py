"""Unit tests for scenario modeling."""

from decimal import Decimal

import pytest

from fin_infra.analytics.scenarios import (
    ScenarioDataPoint,
    ScenarioRequest,
    ScenarioType,
    model_scenario,
)


# ---- Test Models ----


def test_scenario_request_defaults():
    """Test ScenarioRequest with default values."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.SAVINGS_GOAL,
    )

    assert req.starting_amount == Decimal("0")
    assert req.monthly_contribution == Decimal("0")
    assert req.annual_return_rate == Decimal("7")
    assert req.inflation_rate == Decimal("3")
    assert req.years_projection == 30


def test_scenario_request_validation():
    """Test ScenarioRequest field validation."""
    # Valid request
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.RETIREMENT,
        current_age=30,
        target_age=65,
        annual_return_rate=Decimal("7"),
    )
    assert req.current_age == 30

    # Invalid age
    with pytest.raises(ValueError):
        ScenarioRequest(
            user_id="user_123",
            scenario_type=ScenarioType.RETIREMENT,
            current_age=150,  # Too old
        )


def test_scenario_data_point_creation():
    """Test ScenarioDataPoint model."""
    point = ScenarioDataPoint(
        year=5,
        age=35,
        balance=Decimal("50000"),
        contributions=Decimal("30000"),
        growth=Decimal("20000"),
        real_value=Decimal("45000"),
    )

    assert point.year == 5
    assert point.age == 35
    assert point.balance == Decimal("50000")


# ---- Test model_scenario() ----


def test_scenario_basic_savings():
    """Test basic savings scenario with no growth."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.SAVINGS_GOAL,
        starting_amount=Decimal("0"),
        monthly_contribution=Decimal("500"),
        annual_return_rate=Decimal("0"),  # No growth
        years_projection=5,
    )

    result = model_scenario(req)

    assert result.user_id == "user_123"
    assert result.scenario_type == ScenarioType.SAVINGS_GOAL
    assert len(result.projections) == 6  # Year 0-5

    # After 5 years: 500 * 12 * 5 = 30,000
    assert result.final_balance == Decimal("30000")
    assert result.total_contributions == Decimal("30000")
    assert result.total_growth == Decimal("0")


def test_scenario_with_starting_balance():
    """Test scenario with starting balance and no contributions."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.INVESTMENT,
        starting_amount=Decimal("10000"),
        monthly_contribution=Decimal("0"),
        annual_return_rate=Decimal("10"),
        years_projection=10,
    )

    result = model_scenario(req)

    # Should have compound growth on starting balance
    assert result.final_balance > Decimal("10000")
    assert result.total_contributions == Decimal("0")
    assert result.total_growth > Decimal("0")

    # 10-year compound growth at 10%: ~2.59x
    # 10000 * (1.1)^10 ≈ 25,937
    assert result.final_balance > Decimal("25000")


def test_scenario_retirement_projection():
    """Test retirement scenario with age tracking."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.RETIREMENT,
        starting_amount=Decimal("100000"),
        current_age=30,
        target_age=65,
        monthly_contribution=Decimal("1000"),
        annual_return_rate=Decimal("7"),
        inflation_rate=Decimal("3"),
        years_projection=35,
    )

    result = model_scenario(req)

    assert len(result.projections) == 36  # Year 0-35

    # Check age progression
    assert result.projections[0].age == 30
    assert result.projections[35].age == 65

    # Should have substantial growth
    assert result.final_balance > Decimal("1000000")

    # Real value should be less than nominal due to inflation
    final_projection = result.projections[-1]
    assert final_projection.real_value < final_projection.balance


def test_scenario_target_amount_reached():
    """Test scenario reaching target amount."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.SAVINGS_GOAL,
        starting_amount=Decimal("5000"),
        target_amount=Decimal("20000"),
        monthly_contribution=Decimal("500"),
        annual_return_rate=Decimal("5"),
        years_projection=10,
    )

    result = model_scenario(req)

    # Should reach target before 10 years
    assert result.years_to_target is not None
    assert result.years_to_target < 10

    # Balance at target year should be >= target
    target_year_balance = result.projections[result.years_to_target].balance
    assert target_year_balance >= req.target_amount


def test_scenario_target_not_reached():
    """Test scenario where target is not reached."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.SAVINGS_GOAL,
        starting_amount=Decimal("0"),
        target_amount=Decimal("1000000"),  # Very high target
        monthly_contribution=Decimal("100"),
        annual_return_rate=Decimal("5"),
        years_projection=5,  # Short timeline
    )

    result = model_scenario(req)

    # Should NOT reach target
    assert result.years_to_target is None
    assert result.final_balance < req.target_amount


def test_scenario_annual_raise():
    """Test scenario with annual contribution increases."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.SAVINGS_GOAL,
        starting_amount=Decimal("0"),
        monthly_contribution=Decimal("500"),
        annual_raise=Decimal("5"),  # 5% annual increase
        annual_return_rate=Decimal("0"),  # No growth for simplicity
        years_projection=3,
    )

    result = model_scenario(req)

    # Year 1: 500 * 12 = 6,000
    # Year 2: 525 * 12 = 6,300 (5% raise)
    # Year 3: 551.25 * 12 = 6,615
    # Total ≈ 18,915
    assert result.total_contributions > Decimal("18000")
    assert result.total_contributions < Decimal("20000")


def test_scenario_inflation_adjustment():
    """Test inflation-adjusted real value calculations."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.RETIREMENT,
        starting_amount=Decimal("100000"),
        monthly_contribution=Decimal("0"),
        annual_return_rate=Decimal("7"),
        inflation_rate=Decimal("3"),
        years_projection=10,
    )

    result = model_scenario(req)

    # Final nominal balance should be ~2x starting
    assert result.final_balance > Decimal("190000")

    # Real value should be less due to inflation
    final_projection = result.projections[-1]
    assert final_projection.real_value < final_projection.balance

    # Real value should be ~1.5x starting (7% growth - 3% inflation ≈ 4% real)
    assert final_projection.real_value > Decimal("140000")


def test_scenario_compound_growth():
    """Test compound interest calculations."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.INVESTMENT,
        starting_amount=Decimal("10000"),
        monthly_contribution=Decimal("500"),
        annual_return_rate=Decimal("8"),
        years_projection=20,
    )

    result = model_scenario(req)

    # Total contributions: 500 * 12 * 20 = 120,000
    assert result.total_contributions == Decimal("120000")

    # Starting: 10,000
    # Total money in: 130,000
    # With compound growth, final should be much higher
    assert result.final_balance > Decimal("300000")

    # Growth should be substantial
    assert result.total_growth > Decimal("170000")


def test_scenario_zero_contributions():
    """Test scenario with no ongoing contributions."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.INVESTMENT,
        starting_amount=Decimal("50000"),
        monthly_contribution=Decimal("0"),
        annual_return_rate=Decimal("6"),
        years_projection=15,
    )

    result = model_scenario(req)

    assert result.total_contributions == Decimal("0")
    assert result.final_balance > req.starting_amount

    # Should have warning about no contributions
    assert any("no ongoing contributions" in w.lower() for w in result.warnings)


def test_scenario_recommendations_shortfall():
    """Test recommendations for retirement shortfall."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.RETIREMENT,
        starting_amount=Decimal("50000"),
        target_amount=Decimal("1000000"),
        monthly_contribution=Decimal("200"),  # Too low
        annual_return_rate=Decimal("7"),
        years_projection=30,
    )

    result = model_scenario(req)

    # Should have shortfall
    assert result.final_balance < req.target_amount

    # Should have recommendation about shortfall
    assert len(result.recommendations) > 0
    assert any("shortfall" in r.lower() for r in result.recommendations)


def test_scenario_recommendations_on_track():
    """Test recommendations when on track to exceed goal."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.RETIREMENT,
        starting_amount=Decimal("200000"),
        target_amount=Decimal("500000"),
        monthly_contribution=Decimal("2000"),
        annual_return_rate=Decimal("7"),
        years_projection=15,
    )

    result = model_scenario(req)

    # Should exceed target
    assert result.final_balance > req.target_amount

    # Should have positive recommendation
    assert len(result.recommendations) > 0
    assert any("on track" in r.lower() or "exceed" in r.lower() for r in result.recommendations)


def test_scenario_warnings_high_return():
    """Test warnings for aggressive return assumptions."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.INVESTMENT,
        starting_amount=Decimal("10000"),
        annual_return_rate=Decimal("15"),  # Very high
        years_projection=20,
    )

    result = model_scenario(req)

    # Should have warning about aggressive returns
    assert len(result.warnings) > 0
    assert any("aggressive" in w.lower() for w in result.warnings)


def test_scenario_warnings_low_inflation():
    """Test warnings for low inflation assumptions."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.RETIREMENT,
        starting_amount=Decimal("100000"),
        inflation_rate=Decimal("1"),  # Too low
        years_projection=30,
    )

    result = model_scenario(req)

    # Should have warning about low inflation
    assert any("inflation" in w.lower() for w in result.warnings)


def test_scenario_savings_goal_timeline():
    """Test savings goal with specific timeline."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.SAVINGS_GOAL,
        starting_amount=Decimal("1000"),
        target_amount=Decimal("10000"),
        monthly_contribution=Decimal("300"),
        annual_return_rate=Decimal("5"),
        years_projection=5,
    )

    result = model_scenario(req)

    # Should reach target
    assert result.years_to_target is not None
    assert result.years_to_target <= 5

    # Should have recommendation about timeline
    assert any("reach" in r.lower() for r in result.recommendations)


def test_scenario_all_projections_have_data():
    """Test that all projection years have complete data."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.INVESTMENT,
        starting_amount=Decimal("10000"),
        monthly_contribution=Decimal("500"),
        annual_return_rate=Decimal("7"),
        years_projection=10,
    )

    result = model_scenario(req)

    assert len(result.projections) == 11  # Year 0-10

    for i, projection in enumerate(result.projections):
        assert projection.year == i
        assert projection.balance >= Decimal("0")
        assert projection.contributions >= Decimal("0")
        assert projection.growth >= Decimal("0")
        assert projection.real_value > Decimal("0")


def test_scenario_debt_payoff():
    """Test debt payoff scenario (negative starting balance)."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.DEBT_PAYOFF,
        starting_amount=Decimal("-20000"),  # Debt
        monthly_contribution=Decimal("500"),  # Payments
        annual_return_rate=Decimal("-6"),  # Interest rate (negative for debt)
        years_projection=5,
    )

    result = model_scenario(req)

    # Balance should increase toward zero (debt payoff)
    assert result.final_balance > req.starting_amount


def test_scenario_income_change():
    """Test income change scenario."""
    req = ScenarioRequest(
        user_id="user_123",
        scenario_type=ScenarioType.INCOME_CHANGE,
        starting_amount=Decimal("20000"),
        monthly_contribution=Decimal("1000"),  # Increased savings from raise
        annual_return_rate=Decimal("5"),
        years_projection=10,
    )

    result = model_scenario(req)

    # Should have substantial growth from increased savings
    assert result.final_balance > Decimal("120000")
