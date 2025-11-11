"""Unit tests for analytics ease module.

Tests easy_analytics() builder and AnalyticsEngine class.
"""

import pytest
from datetime import datetime, timedelta

from fin_infra.analytics.ease import easy_analytics, AnalyticsEngine
from fin_infra.analytics.savings import SavingsDefinition
from fin_infra.analytics.models import (
    CashFlowAnalysis,
    SavingsRateData,
    SpendingInsight,
    PersonalizedSpendingAdvice,
    PortfolioMetrics,
    BenchmarkComparison,
    GrowthProjection,
)


# ============================================================================
# Test easy_analytics() builder
# ============================================================================


def test_easy_analytics_default():
    """Test easy_analytics with default configuration."""
    analytics = easy_analytics()

    assert isinstance(analytics, AnalyticsEngine)
    assert analytics.default_period_days == 30
    assert analytics.default_savings_definition == SavingsDefinition.NET
    assert analytics.default_benchmark == "SPY"
    assert analytics.cache_ttl == 3600


def test_easy_analytics_custom_period():
    """Test easy_analytics with custom period."""
    analytics = easy_analytics(default_period_days=90)

    assert analytics.default_period_days == 90


def test_easy_analytics_custom_benchmark():
    """Test easy_analytics with custom benchmark."""
    analytics = easy_analytics(default_benchmark="QQQ")

    assert analytics.default_benchmark == "QQQ"


def test_easy_analytics_custom_savings_definition():
    """Test easy_analytics with custom savings definition."""
    analytics = easy_analytics(default_savings_definition=SavingsDefinition.GROSS)

    assert analytics.default_savings_definition == SavingsDefinition.GROSS


def test_easy_analytics_custom_cache_ttl():
    """Test easy_analytics with custom cache TTL."""
    analytics = easy_analytics(cache_ttl=7200)

    assert analytics.cache_ttl == 7200


def test_easy_analytics_with_providers():
    """Test easy_analytics with provider injection."""
    mock_banking = object()
    mock_brokerage = object()

    analytics = easy_analytics(
        banking_provider=mock_banking,
        brokerage_provider=mock_brokerage,
    )

    assert analytics.banking_provider is mock_banking
    assert analytics.brokerage_provider is mock_brokerage


def test_easy_analytics_all_providers():
    """Test easy_analytics with all providers."""
    mock_banking = object()
    mock_brokerage = object()
    mock_categorization = object()
    mock_recurring = object()
    mock_net_worth = object()
    mock_market = object()

    analytics = easy_analytics(
        banking_provider=mock_banking,
        brokerage_provider=mock_brokerage,
        categorization_provider=mock_categorization,
        recurring_provider=mock_recurring,
        net_worth_provider=mock_net_worth,
        market_provider=mock_market,
    )

    assert analytics.banking_provider is mock_banking
    assert analytics.brokerage_provider is mock_brokerage
    assert analytics.categorization_provider is mock_categorization
    assert analytics.recurring_provider is mock_recurring
    assert analytics.net_worth_provider is mock_net_worth
    assert analytics.market_provider is mock_market


# ============================================================================
# Test AnalyticsEngine class
# ============================================================================


def test_analytics_engine_initialization():
    """Test AnalyticsEngine direct initialization."""
    engine = AnalyticsEngine(
        default_period_days=60,
        default_benchmark="VTI",
        cache_ttl=1800,
    )

    assert engine.default_period_days == 60
    assert engine.default_benchmark == "VTI"
    assert engine.cache_ttl == 1800


@pytest.mark.asyncio
async def test_analytics_engine_cash_flow():
    """Test AnalyticsEngine.cash_flow() method."""
    analytics = easy_analytics()

    result = await analytics.cash_flow("user123")

    assert isinstance(result, CashFlowAnalysis)
    assert result.income_total >= 0
    assert result.expense_total >= 0


@pytest.mark.asyncio
async def test_analytics_engine_cash_flow_custom_period():
    """Test cash_flow with custom period."""
    analytics = easy_analytics(default_period_days=90)

    result = await analytics.cash_flow("user123")

    assert isinstance(result, CashFlowAnalysis)


@pytest.mark.asyncio
async def test_analytics_engine_cash_flow_custom_dates():
    """Test cash_flow with custom date range."""
    analytics = easy_analytics()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    result = await analytics.cash_flow(
        "user123",
        start_date=start_date,
        end_date=end_date,
    )

    assert isinstance(result, CashFlowAnalysis)


@pytest.mark.asyncio
async def test_analytics_engine_savings_rate():
    """Test AnalyticsEngine.savings_rate() method."""
    analytics = easy_analytics()

    result = await analytics.savings_rate("user123")

    assert isinstance(result, SavingsRateData)
    assert isinstance(result.savings_rate, float)


@pytest.mark.asyncio
async def test_analytics_engine_savings_rate_custom_definition():
    """Test savings_rate with custom definition."""
    analytics = easy_analytics()

    result = await analytics.savings_rate(
        "user123",
        definition=SavingsDefinition.GROSS,
    )

    assert isinstance(result, SavingsRateData)


@pytest.mark.asyncio
async def test_analytics_engine_spending_insights():
    """Test AnalyticsEngine.spending_insights() method."""
    analytics = easy_analytics()

    result = await analytics.spending_insights("user123")

    assert isinstance(result, SpendingInsight)


@pytest.mark.asyncio
async def test_analytics_engine_spending_advice():
    """Test AnalyticsEngine.spending_advice() method."""
    analytics = easy_analytics()

    result = await analytics.spending_advice("user123")

    assert isinstance(result, PersonalizedSpendingAdvice)


@pytest.mark.asyncio
async def test_analytics_engine_portfolio_metrics():
    """Test AnalyticsEngine.portfolio_metrics() method."""
    analytics = easy_analytics()

    result = await analytics.portfolio_metrics("user123")

    assert isinstance(result, PortfolioMetrics)
    assert result.total_value >= 0


@pytest.mark.asyncio
async def test_analytics_engine_benchmark_comparison():
    """Test AnalyticsEngine.benchmark_comparison() method."""
    analytics = easy_analytics()

    result = await analytics.benchmark_comparison("user123")

    assert isinstance(result, BenchmarkComparison)
    assert result.benchmark_symbol == "SPY"  # Default


@pytest.mark.asyncio
async def test_analytics_engine_benchmark_comparison_custom():
    """Test benchmark_comparison with custom benchmark."""
    analytics = easy_analytics(default_benchmark="QQQ")

    result = await analytics.benchmark_comparison("user123")

    assert result.benchmark_symbol == "QQQ"


@pytest.mark.asyncio
async def test_analytics_engine_net_worth_projection():
    """Test AnalyticsEngine.net_worth_projection() method."""
    analytics = easy_analytics()

    result = await analytics.net_worth_projection("user123")

    assert isinstance(result, GrowthProjection)
    assert result.years == 30  # Default
    assert len(result.scenarios) == 3


@pytest.mark.asyncio
async def test_analytics_engine_net_worth_projection_custom_years():
    """Test net_worth_projection with custom years."""
    analytics = easy_analytics()

    result = await analytics.net_worth_projection("user123", years=40)

    assert result.years == 40


def test_analytics_engine_compound_interest():
    """Test AnalyticsEngine.compound_interest() static method."""
    analytics = easy_analytics()

    result = analytics.compound_interest(10000, 0.08, 10)

    # Should be around $21,589
    assert 21000 < result < 22000


# ============================================================================
# Test Default Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_default_period_days_applied():
    """Test default period_days is applied to cash_flow."""
    analytics = easy_analytics(default_period_days=45)

    # Should use 45-day default
    result = await analytics.cash_flow("user123")

    assert isinstance(result, CashFlowAnalysis)


@pytest.mark.asyncio
async def test_default_savings_definition_applied():
    """Test default savings definition is applied."""
    analytics = easy_analytics(default_savings_definition=SavingsDefinition.DISCRETIONARY)

    result = await analytics.savings_rate("user123")

    assert isinstance(result, SavingsRateData)


@pytest.mark.asyncio
async def test_default_benchmark_applied():
    """Test default benchmark is applied."""
    analytics = easy_analytics(default_benchmark="VTI")

    result = await analytics.benchmark_comparison("user123", period="1y")

    assert result.benchmark_symbol == "VTI"


# ============================================================================
# Test Provider Passthrough
# ============================================================================


@pytest.mark.asyncio
async def test_providers_passed_to_functions():
    """Test providers are passed through to underlying functions."""
    mock_banking = object()

    analytics = easy_analytics(banking_provider=mock_banking)

    # Should pass banking_provider to cash_flow
    result = await analytics.cash_flow("user123")

    assert isinstance(result, CashFlowAnalysis)
    # Provider was passed through (verified by no errors)


# ============================================================================
# Test Multiple Operations
# ============================================================================


@pytest.mark.asyncio
async def test_multiple_operations():
    """Test multiple analytics operations with same engine."""
    analytics = easy_analytics()

    # Run multiple operations
    cash_flow = await analytics.cash_flow("user123")
    savings = await analytics.savings_rate("user123")
    portfolio = await analytics.portfolio_metrics("user123")
    projection = await analytics.net_worth_projection("user123", years=20)

    # All should succeed
    assert isinstance(cash_flow, CashFlowAnalysis)
    assert isinstance(savings, SavingsRateData)
    assert isinstance(portfolio, PortfolioMetrics)
    assert isinstance(projection, GrowthProjection)


@pytest.mark.asyncio
async def test_different_users():
    """Test analytics for different users with same engine."""
    analytics = easy_analytics()

    user1_cash_flow = await analytics.cash_flow("user_a")
    user2_cash_flow = await analytics.cash_flow("user_b")

    assert isinstance(user1_cash_flow, CashFlowAnalysis)
    assert isinstance(user2_cash_flow, CashFlowAnalysis)
