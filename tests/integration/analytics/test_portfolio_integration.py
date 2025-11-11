"""Integration tests for portfolio analytics.

Tests end-to-end portfolio metrics and benchmark comparison workflows.
"""

import pytest

from fin_infra.analytics.models import (
    AssetAllocation,
    BenchmarkComparison,
    PortfolioMetrics,
)
from fin_infra.analytics.portfolio import (
    calculate_portfolio_metrics,
    compare_to_benchmark,
)


# ============================================================================
# Test End-to-End Portfolio Metrics
# ============================================================================


@pytest.mark.asyncio
async def test_portfolio_metrics_end_to_end():
    """Test complete portfolio metrics calculation workflow."""
    metrics = await calculate_portfolio_metrics("integration_user_1")

    # Verify structure
    assert isinstance(metrics, PortfolioMetrics)
    assert metrics.total_value > 0

    # Verify returns
    assert isinstance(metrics.total_return, float)
    assert isinstance(metrics.total_return_percent, float)
    assert isinstance(metrics.ytd_return, float)
    assert isinstance(metrics.ytd_return_percent, float)
    assert isinstance(metrics.mtd_return, float)
    assert isinstance(metrics.mtd_return_percent, float)
    assert isinstance(metrics.day_change, float)
    assert isinstance(metrics.day_change_percent, float)

    # Verify asset allocation
    assert len(metrics.allocation_by_asset_class) > 0
    for allocation in metrics.allocation_by_asset_class:
        assert isinstance(allocation, AssetAllocation)
        assert allocation.value >= 0
        assert 0 <= allocation.percentage <= 100

    # Verify percentages sum correctly
    total_pct = sum(a.percentage for a in metrics.allocation_by_asset_class)
    assert 99.0 <= total_pct <= 101.0


@pytest.mark.asyncio
async def test_portfolio_metrics_multi_account():
    """Test portfolio metrics with multiple accounts."""
    # Test with specific accounts
    metrics_filtered = await calculate_portfolio_metrics(
        "integration_user_1",
        accounts=["taxable", "ira"],
    )

    # Test with all accounts
    metrics_all = await calculate_portfolio_metrics("integration_user_1")

    # Both should return valid metrics
    assert metrics_filtered.total_value > 0
    assert metrics_all.total_value > 0

    # Verify structure is consistent
    assert len(metrics_filtered.allocation_by_asset_class) > 0
    assert len(metrics_all.allocation_by_asset_class) > 0


@pytest.mark.asyncio
async def test_portfolio_metrics_consistency():
    """Test portfolio metrics are internally consistent."""
    metrics = await calculate_portfolio_metrics("integration_user_1")

    # Total value should match sum of asset allocation
    allocation_total = sum(a.value for a in metrics.allocation_by_asset_class)
    assert abs(metrics.total_value - allocation_total) < 0.01

    # Allocation percentages should sum to 100%
    total_pct = sum(a.percentage for a in metrics.allocation_by_asset_class)
    assert 99.0 <= total_pct <= 101.0

    # Asset allocation should be sorted by value
    values = [a.value for a in metrics.allocation_by_asset_class]
    assert values == sorted(values, reverse=True)


@pytest.mark.asyncio
async def test_portfolio_metrics_realistic_values():
    """Test portfolio metrics have realistic values."""
    metrics = await calculate_portfolio_metrics("integration_user_1")

    # Total value should be positive and reasonable
    assert 1000 <= metrics.total_value <= 10_000_000  # $1K to $10M

    # Return percentages should be realistic (not 1000% or -100%)
    assert -50.0 <= metrics.total_return_percent <= 200.0
    assert -30.0 <= metrics.ytd_return_percent <= 100.0
    assert -20.0 <= metrics.mtd_return_percent <= 50.0
    assert -10.0 <= metrics.day_change_percent <= 10.0

    # Asset allocation should be diverse
    assert len(metrics.allocation_by_asset_class) >= 2


# ============================================================================
# Test End-to-End Benchmark Comparison
# ============================================================================


@pytest.mark.asyncio
async def test_benchmark_comparison_end_to_end():
    """Test complete benchmark comparison workflow."""
    comparison = await compare_to_benchmark(
        "integration_user_1",
        benchmark="SPY",
        period="1y",
    )

    # Verify structure
    assert isinstance(comparison, BenchmarkComparison)
    assert comparison.benchmark_symbol == "SPY"
    assert comparison.period == "1y"

    # Verify returns
    assert isinstance(comparison.portfolio_return, float)
    assert isinstance(comparison.portfolio_return_percent, float)
    assert isinstance(comparison.benchmark_return, float)
    assert isinstance(comparison.benchmark_return_percent, float)

    # Verify alpha calculation
    expected_alpha = comparison.portfolio_return_percent - comparison.benchmark_return_percent
    assert abs(comparison.alpha - expected_alpha) < 0.01

    # Verify beta
    assert isinstance(comparison.beta, float)
    assert 0 <= comparison.beta <= 3.0  # Realistic beta range


@pytest.mark.asyncio
async def test_benchmark_comparison_multiple_periods():
    """Test benchmark comparison across different time periods."""
    user_id = "integration_user_1"
    periods = ["1y", "3y", "5y", "ytd"]

    results = []
    for period in periods:
        comparison = await compare_to_benchmark(
            user_id,
            benchmark="SPY",
            period=period,
        )
        results.append(comparison)

    # Verify all comparisons succeeded
    assert len(results) == len(periods)

    for comparison, period in zip(results, periods):
        assert comparison.period == period
        assert isinstance(comparison.alpha, float)
        assert isinstance(comparison.beta, float)


@pytest.mark.asyncio
async def test_benchmark_comparison_multiple_benchmarks():
    """Test comparing portfolio to different benchmarks."""
    user_id = "integration_user_1"
    benchmarks = ["SPY", "QQQ", "VTI"]

    results = []
    for benchmark in benchmarks:
        comparison = await compare_to_benchmark(
            user_id,
            benchmark=benchmark,
            period="1y",
        )
        results.append(comparison)

    # Verify all comparisons succeeded
    assert len(results) == len(benchmarks)

    for comparison, benchmark in zip(results, benchmarks):
        assert comparison.benchmark_symbol == benchmark
        assert isinstance(comparison.alpha, float)
        assert isinstance(comparison.beta, float)


@pytest.mark.asyncio
async def test_benchmark_comparison_realistic_alpha():
    """Test alpha values are realistic."""
    comparison = await compare_to_benchmark(
        "integration_user_1",
        benchmark="SPY",
        period="1y",
    )

    # Alpha should be reasonable (most portfolios don't beat market by >20%)
    assert -30.0 <= comparison.alpha <= 30.0

    # Alpha should match portfolio vs benchmark
    calculated_alpha = comparison.portfolio_return_percent - comparison.benchmark_return_percent
    assert abs(comparison.alpha - calculated_alpha) < 0.01


@pytest.mark.asyncio
async def test_benchmark_comparison_realistic_beta():
    """Test beta values are realistic."""
    comparison = await compare_to_benchmark(
        "integration_user_1",
        benchmark="SPY",
        period="1y",
    )

    # Beta typically ranges from 0 to 2 for most portfolios
    # 0 = no correlation, 1 = same volatility as market, >1 = more volatile
    assert 0 <= comparison.beta <= 2.5


# ============================================================================
# Test Portfolio + Benchmark Integration
# ============================================================================


@pytest.mark.asyncio
async def test_portfolio_and_benchmark_consistency():
    """Test portfolio metrics and benchmark comparison are consistent."""
    user_id = "integration_user_1"

    # Get portfolio metrics
    metrics = await calculate_portfolio_metrics(user_id)

    # Get benchmark comparison for same period
    comparison_1y = await compare_to_benchmark(user_id, benchmark="SPY", period="1y")

    # Portfolio values should be consistent
    assert metrics.total_value > 0
    assert comparison_1y.portfolio_return != 0


@pytest.mark.asyncio
async def test_portfolio_metrics_with_different_users():
    """Test portfolio metrics for different users."""
    users = ["user_a", "user_b", "user_c"]

    results = []
    for user_id in users:
        metrics = await calculate_portfolio_metrics(user_id)
        results.append(metrics)

    # All users should have valid metrics
    for metrics in results:
        assert metrics.total_value > 0
        assert len(metrics.allocation_by_asset_class) > 0


@pytest.mark.asyncio
async def test_benchmark_comparison_with_accounts():
    """Test benchmark comparison with account filtering."""
    comparison = await compare_to_benchmark(
        "integration_user_1",
        benchmark="SPY",
        period="1y",
        accounts=["taxable"],
    )

    assert isinstance(comparison, BenchmarkComparison)
    assert comparison.benchmark_symbol == "SPY"


# ============================================================================
# Test Error Handling and Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_portfolio_metrics_empty_user():
    """Test portfolio metrics with user who has no holdings."""
    # Mock implementation should still return valid structure
    metrics = await calculate_portfolio_metrics("empty_user")

    assert isinstance(metrics, PortfolioMetrics)
    # Mock data will still show holdings, but structure should be valid


@pytest.mark.asyncio
async def test_benchmark_comparison_invalid_period():
    """Test benchmark comparison with invalid period."""
    with pytest.raises(ValueError, match="Invalid period format"):
        await compare_to_benchmark(
            "integration_user_1",
            benchmark="SPY",
            period="invalid",
        )


@pytest.mark.asyncio
async def test_benchmark_comparison_ytd_period():
    """Test benchmark comparison with YTD period."""
    comparison = await compare_to_benchmark(
        "integration_user_1",
        benchmark="SPY",
        period="ytd",
    )

    assert comparison.period == "ytd"
    assert isinstance(comparison.alpha, float)


@pytest.mark.asyncio
async def test_benchmark_comparison_max_period():
    """Test benchmark comparison with maximum period."""
    comparison = await compare_to_benchmark(
        "integration_user_1",
        benchmark="SPY",
        period="max",
    )

    assert comparison.period == "max"
    assert isinstance(comparison.alpha, float)


# ============================================================================
# Test Performance and Concurrency
# ============================================================================


@pytest.mark.asyncio
async def test_portfolio_metrics_concurrent_requests():
    """Test multiple concurrent portfolio metrics requests."""
    import asyncio

    user_ids = ["user_1", "user_2", "user_3", "user_4", "user_5"]

    # Run concurrent requests
    tasks = [calculate_portfolio_metrics(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks)

    # All requests should succeed
    assert len(results) == len(user_ids)

    for metrics in results:
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.total_value > 0


@pytest.mark.asyncio
async def test_benchmark_comparison_concurrent_requests():
    """Test multiple concurrent benchmark comparisons."""
    import asyncio

    benchmarks = ["SPY", "QQQ", "VTI", "IWM", "DIA"]
    user_id = "integration_user_1"

    # Run concurrent comparisons
    tasks = [compare_to_benchmark(user_id, benchmark=bm, period="1y") for bm in benchmarks]
    results = await asyncio.gather(*tasks)

    # All comparisons should succeed
    assert len(results) == len(benchmarks)

    for comparison, benchmark in zip(results, benchmarks):
        assert comparison.benchmark_symbol == benchmark
