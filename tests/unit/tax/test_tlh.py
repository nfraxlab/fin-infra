"""Unit tests for tax-loss harvesting logic."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from fin_infra.models.brokerage import Position
from fin_infra.tax.tlh import (
    TLHOpportunity,
    TLHScenario,
    find_tlh_opportunities,
    simulate_tlh_scenario,
    _assess_wash_sale_risk,
    _suggest_replacement,
    _generate_tlh_recommendations,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_losing_position() -> Position:
    """Create a sample position with unrealized loss."""
    return Position(
        symbol="AAPL",
        qty=Decimal("100"),
        side="long",
        avg_entry_price=Decimal("150.00"),
        current_price=Decimal("135.00"),
        market_value=Decimal("13500.00"),
        cost_basis=Decimal("15000.00"),
        unrealized_pl=Decimal("-1500.00"),  # $1,500 loss
        unrealized_plpc=Decimal("-0.10"),  # -10%
        asset_class="us_equity",
    )


@pytest.fixture
def sample_winning_position() -> Position:
    """Create a sample position with unrealized gain."""
    return Position(
        symbol="MSFT",
        qty=Decimal("50"),
        side="long",
        avg_entry_price=Decimal("300.00"),
        current_price=Decimal("330.00"),
        market_value=Decimal("16500.00"),
        cost_basis=Decimal("15000.00"),
        unrealized_pl=Decimal("1500.00"),  # $1,500 gain
        unrealized_plpc=Decimal("0.10"),  # +10%
        asset_class="us_equity",
    )


@pytest.fixture
def sample_small_loss_position() -> Position:
    """Create a position with small loss below min_loss threshold."""
    return Position(
        symbol="GOOGL",
        qty=Decimal("10"),
        side="long",
        avg_entry_price=Decimal("140.00"),
        current_price=Decimal("135.00"),
        market_value=Decimal("1350.00"),
        cost_basis=Decimal("1400.00"),
        unrealized_pl=Decimal("-50.00"),  # $50 loss (below $100 threshold)
        unrealized_plpc=Decimal("-0.0357"),  # -3.57%
        asset_class="us_equity",
    )


@pytest.fixture
def sample_short_position() -> Position:
    """Create a short position (not eligible for TLH)."""
    return Position(
        symbol="TSLA",
        qty=Decimal("50"),
        side="short",
        avg_entry_price=Decimal("200.00"),
        current_price=Decimal("250.00"),
        market_value=Decimal("12500.00"),
        cost_basis=Decimal("10000.00"),
        unrealized_pl=Decimal("-2500.00"),  # Loss on short
        unrealized_plpc=Decimal("-0.25"),
        asset_class="us_equity",
    )


@pytest.fixture
def recent_trades() -> list[dict]:
    """Sample recent trades for wash sale checking."""
    now = datetime.now(timezone.utc)
    return [
        {
            "symbol": "AAPL",
            "date": now - timedelta(days=10),  # Recent purchase (high risk)
            "side": "buy",
        },
        {
            "symbol": "MSFT",
            "date": now - timedelta(days=45),  # Old purchase (low risk)
            "side": "buy",
        },
        {
            "symbol": "GOOGL",
            "date": now - timedelta(days=70),  # Very old (no risk)
            "side": "buy",
        },
        {
            "symbol": "NVDA",
            "date": now - timedelta(days=5),  # Very recent (sell, ignore)
            "side": "sell",
        },
    ]


# ============================================================================
# Model Tests
# ============================================================================


def test_tlh_opportunity_model_valid():
    """Test TLHOpportunity model with valid data."""
    opp = TLHOpportunity(
        position_symbol="AAPL",
        position_qty=Decimal("100"),
        cost_basis=Decimal("15000.00"),
        current_value=Decimal("13500.00"),
        loss_amount=Decimal("1500.00"),
        loss_percent=Decimal("0.10"),
        replacement_ticker="VGT",
        wash_sale_risk="low",
        potential_tax_savings=Decimal("225.00"),
        tax_rate=Decimal("0.15"),
        explanation="Test opportunity",
    )

    assert opp.position_symbol == "AAPL"
    assert opp.loss_amount == Decimal("1500.00")
    assert opp.wash_sale_risk == "low"


def test_tlh_opportunity_model_invalid_wash_sale_risk():
    """Test TLHOpportunity model rejects invalid wash_sale_risk."""
    with pytest.raises(ValueError, match="wash_sale_risk must be one of"):
        TLHOpportunity(
            position_symbol="AAPL",
            position_qty=Decimal("100"),
            cost_basis=Decimal("15000.00"),
            current_value=Decimal("13500.00"),
            loss_amount=Decimal("1500.00"),
            loss_percent=Decimal("0.10"),
            replacement_ticker="VGT",
            wash_sale_risk="invalid",  # Invalid value
            potential_tax_savings=Decimal("225.00"),
            explanation="Test",
        )


def test_tlh_scenario_model_valid():
    """Test TLHScenario model with valid data."""
    scenario = TLHScenario(
        total_loss_harvested=Decimal("5000.00"),
        total_tax_savings=Decimal("750.00"),
        num_opportunities=3,
        avg_tax_rate=Decimal("0.15"),
        wash_sale_risk_summary={"none": 1, "low": 2, "medium": 0, "high": 0},
        total_cost_basis=Decimal("50000.00"),
        total_current_value=Decimal("45000.00"),
        recommendations=["Execute before year-end"],
    )

    assert scenario.total_loss_harvested == Decimal("5000.00")
    assert scenario.num_opportunities == 3
    assert len(scenario.caveats) >= 4  # Default caveats


def test_tlh_scenario_model_empty():
    """Test TLHScenario model with zero opportunities."""
    scenario = TLHScenario(
        total_loss_harvested=Decimal("0"),
        total_tax_savings=Decimal("0"),
        num_opportunities=0,
        avg_tax_rate=Decimal("0"),
        wash_sale_risk_summary={"none": 0, "low": 0, "medium": 0, "high": 0},
        total_cost_basis=Decimal("0"),
        total_current_value=Decimal("0"),
        recommendations=[],
    )

    assert scenario.total_loss_harvested == Decimal("0")
    assert scenario.num_opportunities == 0


# ============================================================================
# find_tlh_opportunities Tests
# ============================================================================


def test_find_tlh_opportunities_single_loss(sample_losing_position):
    """Test finding TLH opportunity with single losing position."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_losing_position],
        min_loss=Decimal("100"),
        tax_rate=Decimal("0.15"),
    )

    assert len(opportunities) == 1
    opp = opportunities[0]
    assert opp.position_symbol == "AAPL"
    assert opp.loss_amount == Decimal("1500.00")
    assert opp.loss_percent == Decimal("0.10")  # 10% loss
    assert opp.replacement_ticker == "VGT"  # Tech ETF
    assert opp.wash_sale_risk == "none"  # No recent trades
    assert opp.potential_tax_savings == Decimal("225.00")  # $1500 * 0.15


def test_find_tlh_opportunities_no_losses(sample_winning_position):
    """Test finding TLH opportunities with only winning positions."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_winning_position],
    )

    assert len(opportunities) == 0  # No losses


def test_find_tlh_opportunities_below_min_loss(sample_small_loss_position):
    """Test TLH ignores losses below min_loss threshold."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_small_loss_position],
        min_loss=Decimal("100"),  # $100 threshold
    )

    assert len(opportunities) == 0  # $50 loss is below threshold


def test_find_tlh_opportunities_short_positions_excluded(sample_short_position):
    """Test TLH excludes short positions."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_short_position],
    )

    assert len(opportunities) == 0  # Short positions excluded


def test_find_tlh_opportunities_multiple_positions(
    sample_losing_position, sample_winning_position, sample_small_loss_position
):
    """Test TLH with mixed positions."""
    # Create another big loss position
    big_loss = Position(
        symbol="NVDA",
        qty=Decimal("200"),
        side="long",
        avg_entry_price=Decimal("500.00"),
        current_price=Decimal("400.00"),
        market_value=Decimal("80000.00"),
        cost_basis=Decimal("100000.00"),
        unrealized_pl=Decimal("-20000.00"),  # $20k loss
        unrealized_plpc=Decimal("-0.20"),
        asset_class="us_equity",
    )

    positions = [
        sample_losing_position,  # $1,500 loss
        sample_winning_position,  # Gain (excluded)
        sample_small_loss_position,  # $50 loss (below threshold)
        big_loss,  # $20,000 loss
    ]

    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=positions,
        min_loss=Decimal("100"),
    )

    # Should find 2 opportunities (AAPL and NVDA)
    assert len(opportunities) == 2

    # Should be sorted by loss amount descending
    assert opportunities[0].position_symbol == "NVDA"  # $20k loss first
    assert opportunities[0].loss_amount == Decimal("20000.00")
    assert opportunities[1].position_symbol == "AAPL"  # $1.5k loss second
    assert opportunities[1].loss_amount == Decimal("1500.00")


def test_find_tlh_opportunities_with_recent_trades(sample_losing_position, recent_trades):
    """Test TLH wash sale risk assessment with recent trades."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_losing_position],
        recent_trades=recent_trades,
    )

    assert len(opportunities) == 1
    opp = opportunities[0]
    # AAPL was purchased 10 days ago (high risk)
    assert opp.wash_sale_risk == "high"
    assert opp.last_purchase_date is not None


def test_find_tlh_opportunities_custom_tax_rate(sample_losing_position):
    """Test TLH with custom tax rate."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_losing_position],
        tax_rate=Decimal("0.20"),  # 20% tax rate
    )

    assert len(opportunities) == 1
    opp = opportunities[0]
    assert opp.tax_rate == Decimal("0.20")
    assert opp.potential_tax_savings == Decimal("300.00")  # $1500 * 0.20


def test_find_tlh_opportunities_empty_positions():
    """Test TLH with no positions."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[],
    )

    assert len(opportunities) == 0


# ============================================================================
# simulate_tlh_scenario Tests
# ============================================================================


def test_simulate_tlh_scenario_single_opportunity(sample_losing_position):
    """Test simulating TLH scenario with single opportunity."""
    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[sample_losing_position],
    )

    scenario = simulate_tlh_scenario(opportunities)

    assert scenario.num_opportunities == 1
    assert scenario.total_loss_harvested == Decimal("1500.00")
    assert scenario.total_tax_savings == Decimal("225.00")  # $1500 * 0.15
    assert scenario.avg_tax_rate == Decimal("0.15")
    assert scenario.wash_sale_risk_summary["none"] == 1
    assert scenario.total_cost_basis == Decimal("15000.00")
    assert scenario.total_current_value == Decimal("13500.00")
    assert len(scenario.recommendations) > 0


def test_simulate_tlh_scenario_multiple_opportunities():
    """Test simulating TLH scenario with multiple opportunities."""
    # Create two losing positions
    pos1 = Position(
        symbol="AAPL",
        qty=Decimal("100"),
        side="long",
        avg_entry_price=Decimal("150.00"),
        current_price=Decimal("135.00"),
        market_value=Decimal("13500.00"),
        cost_basis=Decimal("15000.00"),
        unrealized_pl=Decimal("-1500.00"),
        unrealized_plpc=Decimal("-0.10"),
        asset_class="us_equity",
    )

    pos2 = Position(
        symbol="MSFT",
        qty=Decimal("50"),
        side="long",
        avg_entry_price=Decimal("320.00"),
        current_price=Decimal("300.00"),
        market_value=Decimal("15000.00"),
        cost_basis=Decimal("16000.00"),
        unrealized_pl=Decimal("-1000.00"),
        unrealized_plpc=Decimal("-0.0625"),
        asset_class="us_equity",
    )

    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[pos1, pos2],
    )

    scenario = simulate_tlh_scenario(opportunities)

    assert scenario.num_opportunities == 2
    assert scenario.total_loss_harvested == Decimal("2500.00")  # $1500 + $1000
    assert scenario.total_tax_savings == Decimal("375.00")  # $2500 * 0.15
    assert scenario.total_cost_basis == Decimal("31000.00")  # $15k + $16k
    assert scenario.total_current_value == Decimal("28500.00")  # $13.5k + $15k


def test_simulate_tlh_scenario_with_override_tax_rate():
    """Test simulating TLH scenario with override tax rate."""
    pos = Position(
        symbol="AAPL",
        qty=Decimal("100"),
        side="long",
        avg_entry_price=Decimal("150.00"),
        current_price=Decimal("135.00"),
        market_value=Decimal("13500.00"),
        cost_basis=Decimal("15000.00"),
        unrealized_pl=Decimal("-1500.00"),
        unrealized_plpc=Decimal("-0.10"),
        asset_class="us_equity",
    )

    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=[pos],
        tax_rate=Decimal("0.15"),  # Original rate
    )

    # Override with 20% rate in simulation
    scenario = simulate_tlh_scenario(opportunities, tax_rate=Decimal("0.20"))

    assert scenario.avg_tax_rate == Decimal("0.20")
    assert scenario.total_tax_savings == Decimal("300.00")  # $1500 * 0.20 (override)


def test_simulate_tlh_scenario_empty_opportunities():
    """Test simulating TLH scenario with no opportunities."""
    scenario = simulate_tlh_scenario([])

    assert scenario.num_opportunities == 0
    assert scenario.total_loss_harvested == Decimal("0")
    assert scenario.total_tax_savings == Decimal("0")
    assert scenario.avg_tax_rate == Decimal("0")
    assert scenario.wash_sale_risk_summary == {
        "none": 0,
        "low": 0,
        "medium": 0,
        "high": 0,
    }
    assert scenario.total_cost_basis == Decimal("0")
    assert scenario.total_current_value == Decimal("0")
    assert len(scenario.recommendations) == 0


def test_simulate_tlh_scenario_wash_sale_risk_summary():
    """Test scenario correctly summarizes wash sale risk levels."""
    now = datetime.now(timezone.utc)
    recent_trades = [
        {"symbol": "AAPL", "date": now - timedelta(days=5), "side": "buy"},  # High
        {"symbol": "MSFT", "date": now - timedelta(days=25), "side": "buy"},  # Medium
        {"symbol": "GOOGL", "date": now - timedelta(days=50), "side": "buy"},  # Low
    ]

    positions = [
        Position(
            symbol=sym,
            qty=Decimal("100"),
            side="long",
            avg_entry_price=Decimal("100.00"),
            current_price=Decimal("90.00"),
            market_value=Decimal("9000.00"),
            cost_basis=Decimal("10000.00"),
            unrealized_pl=Decimal("-1000.00"),
            unrealized_plpc=Decimal("-0.10"),
            asset_class="us_equity",
        )
        for sym in ["AAPL", "MSFT", "GOOGL", "NVDA"]  # NVDA has no recent trade
    ]

    opportunities = find_tlh_opportunities(
        user_id="test_user",
        positions=positions,
        recent_trades=recent_trades,
    )

    scenario = simulate_tlh_scenario(opportunities)

    assert scenario.wash_sale_risk_summary["high"] == 1  # AAPL
    assert scenario.wash_sale_risk_summary["medium"] == 1  # MSFT
    assert scenario.wash_sale_risk_summary["low"] == 1  # GOOGL
    assert scenario.wash_sale_risk_summary["none"] == 1  # NVDA


# ============================================================================
# Helper Function Tests
# ============================================================================


def test_assess_wash_sale_risk_no_purchase():
    """Test wash sale risk with no recent purchase."""
    risk = _assess_wash_sale_risk("AAPL", None)
    assert risk == "none"


def test_assess_wash_sale_risk_very_old_purchase():
    """Test wash sale risk with very old purchase (>60 days)."""
    old_date = datetime.now(timezone.utc) - timedelta(days=70)
    risk = _assess_wash_sale_risk("AAPL", old_date)
    assert risk == "none"


def test_assess_wash_sale_risk_low():
    """Test wash sale risk with purchase 31-60 days ago (low risk)."""
    date = datetime.now(timezone.utc) - timedelta(days=45)
    risk = _assess_wash_sale_risk("AAPL", date)
    assert risk == "low"


def test_assess_wash_sale_risk_medium():
    """Test wash sale risk with purchase 16-30 days ago (medium risk)."""
    date = datetime.now(timezone.utc) - timedelta(days=25)
    risk = _assess_wash_sale_risk("AAPL", date)
    assert risk == "medium"


def test_assess_wash_sale_risk_high():
    """Test wash sale risk with recent purchase (0-15 days, high risk)."""
    date = datetime.now(timezone.utc) - timedelta(days=10)
    risk = _assess_wash_sale_risk("AAPL", date)
    assert risk == "high"


def test_assess_wash_sale_risk_boundary_30_days():
    """Test wash sale risk boundary at 30 days."""
    # Exactly 30 days ago should be medium risk
    date = datetime.now(timezone.utc) - timedelta(days=30)
    risk = _assess_wash_sale_risk("AAPL", date)
    assert risk == "medium"


def test_assess_wash_sale_risk_boundary_60_days():
    """Test wash sale risk boundary at 60 days."""
    # Exactly 60 days ago should be low risk
    date = datetime.now(timezone.utc) - timedelta(days=60)
    risk = _assess_wash_sale_risk("AAPL", date)
    assert risk == "low"


def test_suggest_replacement_tech_stocks():
    """Test replacement suggestions for tech stocks."""
    assert _suggest_replacement("AAPL", "us_equity") == "VGT"  # Tech ETF
    assert _suggest_replacement("MSFT", "us_equity") == "VGT"
    assert _suggest_replacement("NVDA", "us_equity") == "SOXX"  # Semiconductor ETF


def test_suggest_replacement_finance():
    """Test replacement suggestions for finance stocks."""
    assert _suggest_replacement("JPM", "us_equity") == "XLF"  # Financials ETF
    assert _suggest_replacement("BAC", "us_equity") == "XLF"


def test_suggest_replacement_healthcare():
    """Test replacement suggestions for healthcare stocks."""
    assert _suggest_replacement("JNJ", "us_equity") == "XLV"  # Healthcare ETF
    assert _suggest_replacement("MRNA", "us_equity") == "XBI"  # Biotech ETF


def test_suggest_replacement_crypto():
    """Test replacement suggestions for crypto."""
    assert _suggest_replacement("BTC", "crypto") == "ETH"  # Swap cryptos
    assert _suggest_replacement("ETH", "crypto") == "BTC"


def test_suggest_replacement_unknown_symbol():
    """Test replacement suggestions for unknown symbols."""
    # Should default to SPY (broad market)
    assert _suggest_replacement("UNKNOWN", "us_equity") == "SPY"


def test_suggest_replacement_unknown_crypto():
    """Test replacement suggestions for unknown crypto."""
    # Should default to COIN (Coinbase stock)
    assert _suggest_replacement("UNKNOWN", "crypto") == "COIN"


def test_generate_tlh_recommendations_year_end_near():
    """Test recommendations generation near year-end."""
    # Mock opportunities with no wash sale risk
    opportunities = [
        TLHOpportunity(
            position_symbol="AAPL",
            position_qty=Decimal("100"),
            cost_basis=Decimal("15000"),
            current_value=Decimal("13500"),
            loss_amount=Decimal("1500"),
            loss_percent=Decimal("0.10"),
            replacement_ticker="VGT",
            wash_sale_risk="none",
            potential_tax_savings=Decimal("225"),
            explanation="Test",
        )
    ]

    risk_summary = {"none": 1, "low": 0, "medium": 0, "high": 0}
    recommendations = _generate_tlh_recommendations(opportunities, risk_summary)

    # Should have multiple recommendations
    assert len(recommendations) > 0

    # Should mention replacement securities
    assert any("replacement" in r.lower() for r in recommendations)

    # Should mention 31-day wait period
    assert any("31 days" in r.lower() for r in recommendations)


def test_generate_tlh_recommendations_high_wash_sale_risk():
    """Test recommendations generation with high wash sale risk."""
    opportunities = [
        TLHOpportunity(
            position_symbol="AAPL",
            position_qty=Decimal("100"),
            cost_basis=Decimal("15000"),
            current_value=Decimal("13500"),
            loss_amount=Decimal("1500"),
            loss_percent=Decimal("0.10"),
            replacement_ticker="VGT",
            wash_sale_risk="high",
            potential_tax_savings=Decimal("225"),
            explanation="Test",
        )
    ]

    risk_summary = {"none": 0, "low": 0, "medium": 0, "high": 1}
    recommendations = _generate_tlh_recommendations(opportunities, risk_summary)

    # Should have WARNING for high risk
    assert any("WARNING" in r and "HIGH" in r for r in recommendations)


def test_generate_tlh_recommendations_medium_wash_sale_risk():
    """Test recommendations generation with medium wash sale risk."""
    opportunities = [
        TLHOpportunity(
            position_symbol="AAPL",
            position_qty=Decimal("100"),
            cost_basis=Decimal("15000"),
            current_value=Decimal("13500"),
            loss_amount=Decimal("1500"),
            loss_percent=Decimal("0.10"),
            replacement_ticker="VGT",
            wash_sale_risk="medium",
            potential_tax_savings=Decimal("225"),
            explanation="Test",
        )
    ]

    risk_summary = {"none": 0, "low": 0, "medium": 1, "high": 0}
    recommendations = _generate_tlh_recommendations(opportunities, risk_summary)

    # Should mention MEDIUM risk
    assert any("MEDIUM" in r for r in recommendations)
