"""Unit tests for portfolio analytics.

Tests portfolio metrics calculation, benchmark comparison, and helper functions.
"""

import pytest
from datetime import datetime

from fin_infra.analytics.models import (
    AssetAllocation,
    BenchmarkComparison,
    PortfolioMetrics,
)
from fin_infra.analytics.portfolio import (
    calculate_portfolio_metrics,
    compare_to_benchmark,
    _parse_benchmark_period,
    _calculate_ytd_return,
    _calculate_mtd_return,
    _calculate_day_change,
    _calculate_asset_allocation,
    _generate_mock_holdings,
)


# ============================================================================
# Test calculate_portfolio_metrics()
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_basic():
    """Test basic portfolio metrics calculation."""
    metrics = await calculate_portfolio_metrics("user123")

    assert isinstance(metrics, PortfolioMetrics)
    assert metrics.total_value > 0
    assert metrics.total_return != 0  # Should have some return
    assert isinstance(metrics.allocation_by_asset_class, list)
    assert len(metrics.allocation_by_asset_class) > 0


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_returns():
    """Test all return metrics are calculated."""
    metrics = await calculate_portfolio_metrics("user123")

    # Check all return fields exist and are numeric
    assert isinstance(metrics.total_return, float)
    assert isinstance(metrics.total_return_percent, float)
    assert isinstance(metrics.ytd_return, float)
    assert isinstance(metrics.ytd_return_percent, float)
    assert isinstance(metrics.mtd_return, float)
    assert isinstance(metrics.mtd_return_percent, float)
    assert isinstance(metrics.day_change, float)
    assert isinstance(metrics.day_change_percent, float)


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_asset_allocation():
    """Test asset allocation is calculated correctly."""
    metrics = await calculate_portfolio_metrics("user123")

    assert len(metrics.allocation_by_asset_class) > 0

    # Check allocation structure
    for allocation in metrics.allocation_by_asset_class:
        assert isinstance(allocation, AssetAllocation)
        assert allocation.asset_class
        assert allocation.value >= 0
        assert 0 <= allocation.percentage <= 100

    # Check percentages sum to ~100%
    total_percentage = sum(a.percentage for a in metrics.allocation_by_asset_class)
    assert 99.0 <= total_percentage <= 101.0  # Allow small rounding errors


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_total_value_matches_allocation():
    """Test total value equals sum of asset allocations."""
    metrics = await calculate_portfolio_metrics("user123")

    allocation_total = sum(a.value for a in metrics.allocation_by_asset_class)

    # Should match total_value (within floating point precision)
    assert abs(metrics.total_value - allocation_total) < 0.01


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_with_account_filter():
    """Test filtering by specific accounts."""
    # With accounts filter
    metrics = await calculate_portfolio_metrics(
        "user123",
        accounts=["account_1", "account_2"],
    )

    assert isinstance(metrics, PortfolioMetrics)
    assert metrics.total_value > 0


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_positive_returns():
    """Test portfolio with positive returns."""
    metrics = await calculate_portfolio_metrics("user123")

    # Mock data should show positive returns
    assert metrics.total_return > 0
    assert metrics.total_return_percent > 0


@pytest.mark.asyncio
async def test_calculate_portfolio_metrics_allocation_sorted():
    """Test asset allocation is sorted by value (descending)."""
    metrics = await calculate_portfolio_metrics("user123")

    values = [a.value for a in metrics.allocation_by_asset_class]

    # Should be sorted descending
    assert values == sorted(values, reverse=True)


# ============================================================================
# Test compare_to_benchmark()
# ============================================================================


@pytest.mark.asyncio
async def test_compare_to_benchmark_basic():
    """Test basic benchmark comparison."""
    comparison = await compare_to_benchmark("user123", benchmark="SPY", period="1y")

    assert isinstance(comparison, BenchmarkComparison)
    assert comparison.benchmark_symbol == "SPY"
    assert comparison.period == "1y"


@pytest.mark.asyncio
async def test_compare_to_benchmark_alpha_calculation():
    """Test alpha (excess return) is calculated."""
    comparison = await compare_to_benchmark("user123", benchmark="SPY", period="1y")

    # Alpha should be portfolio return - benchmark return
    expected_alpha = comparison.portfolio_return_percent - comparison.benchmark_return_percent

    assert abs(comparison.alpha - expected_alpha) < 0.01


@pytest.mark.asyncio
async def test_compare_to_benchmark_beta():
    """Test beta is calculated."""
    comparison = await compare_to_benchmark("user123", benchmark="SPY", period="1y")

    assert comparison.beta is not None
    assert isinstance(comparison.beta, float)
    # Beta typically ranges from 0 to 2 for most portfolios
    assert 0 <= comparison.beta <= 3.0


@pytest.mark.asyncio
async def test_compare_to_benchmark_different_periods():
    """Test benchmark comparison for different time periods."""
    periods = ["1y", "3y", "5y", "ytd"]

    for period in periods:
        comparison = await compare_to_benchmark("user123", benchmark="SPY", period=period)

        assert comparison.period == period
        assert isinstance(comparison.portfolio_return_percent, float)
        assert isinstance(comparison.benchmark_return_percent, float)


@pytest.mark.asyncio
async def test_compare_to_benchmark_different_benchmarks():
    """Test comparison with different benchmark symbols."""
    benchmarks = ["SPY", "QQQ", "VTI"]

    for benchmark in benchmarks:
        comparison = await compare_to_benchmark("user123", benchmark=benchmark, period="1y")

        assert comparison.benchmark_symbol == benchmark


@pytest.mark.asyncio
async def test_compare_to_benchmark_positive_alpha():
    """Test portfolio outperforming benchmark (positive alpha)."""
    # Mock data should show portfolio outperforming SPY
    comparison = await compare_to_benchmark("user123", benchmark="SPY", period="1y")

    # Portfolio return should be greater than benchmark
    assert comparison.alpha > 0  # Positive alpha = outperformance


@pytest.mark.asyncio
async def test_compare_to_benchmark_with_accounts():
    """Test benchmark comparison with account filtering."""
    comparison = await compare_to_benchmark(
        "user123",
        benchmark="SPY",
        period="1y",
        accounts=["taxable_brokerage"],
    )

    assert isinstance(comparison, BenchmarkComparison)


# ============================================================================
# Test _parse_benchmark_period()
# ============================================================================


def test_parse_benchmark_period_1y():
    """Test parsing 1 year period."""
    days = _parse_benchmark_period("1y")
    assert days == 365


def test_parse_benchmark_period_3y():
    """Test parsing 3 year period."""
    days = _parse_benchmark_period("3y")
    assert days == 1095  # 3 * 365


def test_parse_benchmark_period_5y():
    """Test parsing 5 year period."""
    days = _parse_benchmark_period("5y")
    assert days == 1825  # 5 * 365


def test_parse_benchmark_period_ytd():
    """Test parsing year-to-date period."""
    days = _parse_benchmark_period("ytd")

    # Should be days since Jan 1
    today = datetime.now()
    year_start = datetime(today.year, 1, 1)
    expected_days = (today - year_start).days

    assert days == expected_days


def test_parse_benchmark_period_max():
    """Test parsing maximum period."""
    days = _parse_benchmark_period("max")
    assert days == 10950  # 30 years


def test_parse_benchmark_period_months():
    """Test parsing month periods."""
    days = _parse_benchmark_period("6m")
    assert days == 180  # 6 * 30


def test_parse_benchmark_period_case_insensitive():
    """Test period parsing is case insensitive."""
    assert _parse_benchmark_period("1Y") == 365
    assert _parse_benchmark_period("YTD") == _parse_benchmark_period("ytd")
    assert _parse_benchmark_period("MAX") == 10950


def test_parse_benchmark_period_invalid():
    """Test invalid period format raises error."""
    with pytest.raises(ValueError, match="Invalid period format"):
        _parse_benchmark_period("invalid")

    with pytest.raises(ValueError):
        _parse_benchmark_period("10x")

    with pytest.raises(ValueError):
        _parse_benchmark_period("abc")


# ============================================================================
# Test _calculate_ytd_return()
# ============================================================================


def test_calculate_ytd_return():
    """Test YTD return calculation."""
    holdings = [
        {"current_value": 10000.0, "ytd_value_start": 9000.0},
        {"current_value": 5000.0, "ytd_value_start": 4800.0},
    ]

    ytd_dollars, ytd_percent = _calculate_ytd_return(holdings)

    # Total: 15000 current, 13800 start
    # Return: 1200 dollars, 8.7% (1200/13800)
    assert ytd_dollars == 1200.0
    assert abs(ytd_percent - 8.696) < 0.01


def test_calculate_ytd_return_zero_start():
    """Test YTD return with zero start value."""
    holdings = [{"current_value": 0.0, "ytd_value_start": 0.0}]

    ytd_dollars, ytd_percent = _calculate_ytd_return(holdings)

    assert ytd_dollars == 0.0
    assert ytd_percent == 0.0


def test_calculate_ytd_return_negative():
    """Test YTD return with loss."""
    holdings = [{"current_value": 9000.0, "ytd_value_start": 10000.0}]

    ytd_dollars, ytd_percent = _calculate_ytd_return(holdings)

    assert ytd_dollars == -1000.0
    assert ytd_percent == -10.0


# ============================================================================
# Test _calculate_mtd_return()
# ============================================================================


def test_calculate_mtd_return():
    """Test MTD return calculation."""
    holdings = [
        {"current_value": 10000.0, "mtd_value_start": 9800.0},
        {"current_value": 5000.0, "mtd_value_start": 4950.0},
    ]

    mtd_dollars, mtd_percent = _calculate_mtd_return(holdings)

    # Total: 15000 current, 14750 start
    # Return: 250 dollars, 1.695% (250/14750)
    assert mtd_dollars == 250.0
    assert abs(mtd_percent - 1.695) < 0.01


def test_calculate_mtd_return_zero_start():
    """Test MTD return with zero start value."""
    holdings = [{"current_value": 0.0, "mtd_value_start": 0.0}]

    mtd_dollars, mtd_percent = _calculate_mtd_return(holdings)

    assert mtd_dollars == 0.0
    assert mtd_percent == 0.0


# ============================================================================
# Test _calculate_day_change()
# ============================================================================


def test_calculate_day_change():
    """Test day change calculation."""
    holdings = [
        {"current_value": 10000.0, "prev_day_value": 9950.0},
        {"current_value": 5000.0, "prev_day_value": 4980.0},
    ]

    day_dollars, day_percent = _calculate_day_change(holdings)

    # Total: 15000 current, 14930 previous
    # Change: 70 dollars, 0.469% (70/14930)
    assert day_dollars == 70.0
    assert abs(day_percent - 0.469) < 0.01


def test_calculate_day_change_zero_previous():
    """Test day change with zero previous value."""
    holdings = [{"current_value": 0.0, "prev_day_value": 0.0}]

    day_dollars, day_percent = _calculate_day_change(holdings)

    assert day_dollars == 0.0
    assert day_percent == 0.0


def test_calculate_day_change_negative():
    """Test day change with loss."""
    holdings = [{"current_value": 9800.0, "prev_day_value": 10000.0}]

    day_dollars, day_percent = _calculate_day_change(holdings)

    assert day_dollars == -200.0
    assert day_percent == -2.0


# ============================================================================
# Test _calculate_asset_allocation()
# ============================================================================


def test_calculate_asset_allocation():
    """Test asset allocation calculation."""
    holdings = [
        {"asset_class": "Stocks", "current_value": 10000.0},
        {"asset_class": "Stocks", "current_value": 5000.0},
        {"asset_class": "Bonds", "current_value": 3000.0},
        {"asset_class": "Cash", "current_value": 2000.0},
    ]
    total_value = 20000.0

    allocation = _calculate_asset_allocation(holdings, total_value)

    # Should have 3 asset classes
    assert len(allocation) == 3

    # Check stocks (largest)
    stocks = next(a for a in allocation if a.asset_class == "Stocks")
    assert stocks.value == 15000.0
    assert stocks.percentage == 75.0

    # Check bonds
    bonds = next(a for a in allocation if a.asset_class == "Bonds")
    assert bonds.value == 3000.0
    assert bonds.percentage == 15.0

    # Check cash
    cash = next(a for a in allocation if a.asset_class == "Cash")
    assert cash.value == 2000.0
    assert cash.percentage == 10.0


def test_calculate_asset_allocation_sorted():
    """Test asset allocation is sorted by value."""
    holdings = [
        {"asset_class": "Cash", "current_value": 2000.0},
        {"asset_class": "Stocks", "current_value": 15000.0},
        {"asset_class": "Bonds", "current_value": 3000.0},
    ]
    total_value = 20000.0

    allocation = _calculate_asset_allocation(holdings, total_value)

    # Should be sorted by value descending
    assert allocation[0].asset_class == "Stocks"
    assert allocation[1].asset_class == "Bonds"
    assert allocation[2].asset_class == "Cash"


def test_calculate_asset_allocation_percentages_sum_to_100():
    """Test allocation percentages sum to 100%."""
    holdings = [
        {"asset_class": "Stocks", "current_value": 7000.0},
        {"asset_class": "Bonds", "current_value": 2000.0},
        {"asset_class": "Cash", "current_value": 1000.0},
    ]
    total_value = 10000.0

    allocation = _calculate_asset_allocation(holdings, total_value)

    total_percentage = sum(a.percentage for a in allocation)
    assert abs(total_percentage - 100.0) < 0.01


def test_calculate_asset_allocation_single_class():
    """Test allocation with single asset class."""
    holdings = [
        {"asset_class": "Stocks", "current_value": 10000.0},
        {"asset_class": "Stocks", "current_value": 5000.0},
    ]
    total_value = 15000.0

    allocation = _calculate_asset_allocation(holdings, total_value)

    assert len(allocation) == 1
    assert allocation[0].asset_class == "Stocks"
    assert allocation[0].value == 15000.0
    assert allocation[0].percentage == 100.0


def test_calculate_asset_allocation_zero_total():
    """Test allocation with zero total value."""
    holdings = []
    total_value = 0.0

    allocation = _calculate_asset_allocation(holdings, total_value)

    assert len(allocation) == 0


# ============================================================================
# Test _generate_mock_holdings()
# ============================================================================


def test_generate_mock_holdings():
    """Test mock holdings generation."""
    holdings = _generate_mock_holdings("user123")

    assert len(holdings) > 0

    # Check holding structure
    for holding in holdings:
        assert "symbol" in holding
        assert "name" in holding
        assert "asset_class" in holding
        assert "quantity" in holding
        assert "current_price" in holding
        assert "current_value" in holding
        assert "cost_basis" in holding


def test_generate_mock_holdings_has_multiple_asset_classes():
    """Test mock holdings include diverse asset classes."""
    holdings = _generate_mock_holdings("user123")

    asset_classes = {h["asset_class"] for h in holdings}

    # Should have at least 3 different asset classes
    assert len(asset_classes) >= 3


def test_generate_mock_holdings_values_consistent():
    """Test mock holdings have consistent values."""
    holdings = _generate_mock_holdings("user123")

    for holding in holdings:
        # current_value should equal quantity * current_price (approximately)
        expected_value = holding["quantity"] * holding["current_price"]
        assert abs(holding["current_value"] - expected_value) < 0.01


def test_generate_mock_holdings_with_accounts():
    """Test mock holdings generation with account filter."""
    holdings = _generate_mock_holdings("user123", accounts=["account_1"])

    # Should still return holdings (filtering not implemented in mock)
    assert len(holdings) > 0
