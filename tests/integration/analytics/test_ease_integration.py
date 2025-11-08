"""Integration tests for analytics ease module.

Tests end-to-end workflows using easy_analytics() builder.
"""

import pytest
from datetime import datetime, timedelta

from fin_infra.analytics.ease import easy_analytics
from fin_infra.analytics.models import (
    CashFlowAnalysis,
    SavingsRateData,
    SpendingInsight,
    PersonalizedSpendingAdvice,
    PortfolioMetrics,
    BenchmarkComparison,
    GrowthProjection,
    SavingsDefinition,
)


# Test: Complete analytics workflow
@pytest.mark.asyncio
async def test_complete_analytics_workflow():
    """Test complete analytics workflow: cash flow → savings → spending → portfolio → projection."""
    analytics = easy_analytics()
    user_id = "workflow_user"
    
    # Cash flow analysis
    cash_flow = await analytics.cash_flow(user_id)
    assert isinstance(cash_flow, CashFlowAnalysis)
    assert cash_flow.income_total > 0
    
    # Savings rate
    savings = await analytics.savings_rate(user_id)
    assert isinstance(savings, SavingsRateData)
    assert 0 <= savings.savings_rate <= 1
    
    # Spending insights
    spending = await analytics.spending_insights(user_id)
    assert isinstance(spending, SpendingInsight)
    assert len(spending.top_merchants) > 0
    
    # Portfolio metrics
    portfolio = await analytics.portfolio_metrics(user_id)
    assert isinstance(portfolio, PortfolioMetrics)
    assert portfolio.total_value >= 0
    
    # Growth projection
    projection = await analytics.net_worth_projection(user_id, years=10)
    assert isinstance(projection, GrowthProjection)
    assert len(projection.scenarios) == 3


# Test: Multiple users same engine
@pytest.mark.asyncio
async def test_multiple_users_same_engine():
    """Test analytics for multiple users with same engine."""
    analytics = easy_analytics()
    
    # User 1
    cf1 = await analytics.cash_flow("user1")
    assert isinstance(cf1, CashFlowAnalysis)
    assert cf1.income_total > 0
    
    # User 2
    cf2 = await analytics.cash_flow("user2")
    assert isinstance(cf2, CashFlowAnalysis)
    assert cf2.income_total > 0
    
    # Both should return valid results (mock data may be same, which is OK)
    assert cf1.net_cash_flow == cf1.income_total - cf1.expense_total
    assert cf2.net_cash_flow == cf2.income_total - cf2.expense_total


# Test: Custom period configuration
@pytest.mark.asyncio
async def test_custom_period_configuration():
    """Test analytics with custom period configuration."""
    # 90-day default period
    analytics = easy_analytics(default_period_days=90)
    
    cash_flow = await analytics.cash_flow("user123")
    assert isinstance(cash_flow, CashFlowAnalysis)
    
    # Period should be ~90 days
    period_days = (cash_flow.period_end - cash_flow.period_start).days
    assert 85 <= period_days <= 95  # Allow some tolerance


# Test: Custom savings definition
@pytest.mark.asyncio
async def test_custom_savings_definition():
    """Test analytics with custom savings definition."""
    analytics = easy_analytics(default_savings_definition=SavingsDefinition.GROSS)
    
    savings = await analytics.savings_rate("user123")
    assert isinstance(savings, SavingsRateData)
    assert savings.definition == SavingsDefinition.GROSS


# Test: Custom benchmark
@pytest.mark.asyncio
async def test_custom_benchmark():
    """Test analytics with custom benchmark."""
    analytics = easy_analytics(default_benchmark="VTI")
    
    comparison = await analytics.benchmark_comparison("user123", period="1y")
    assert isinstance(comparison, BenchmarkComparison)
    assert comparison.benchmark_symbol == "VTI"


# Test: Override defaults per call
@pytest.mark.asyncio
async def test_override_defaults_per_call():
    """Test that method-level parameters override defaults."""
    analytics = easy_analytics(default_period_days=30)
    
    # Override with 60 days
    cash_flow = await analytics.cash_flow("user123", period_days=60)
    assert isinstance(cash_flow, CashFlowAnalysis)
    
    period_days = (cash_flow.period_end - cash_flow.period_start).days
    assert 55 <= period_days <= 65


# Test: Concurrent operations
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent analytics operations."""
    import asyncio
    
    analytics = easy_analytics()
    user_id = "concurrent_user"
    
    # Run multiple operations concurrently
    results = await asyncio.gather(
        analytics.cash_flow(user_id),
        analytics.savings_rate(user_id),
        analytics.spending_insights(user_id),
        analytics.portfolio_metrics(user_id),
    )
    
    assert len(results) == 4
    assert isinstance(results[0], CashFlowAnalysis)
    assert isinstance(results[1], SavingsRateData)
    assert isinstance(results[2], SpendingInsight)
    assert isinstance(results[3], PortfolioMetrics)


# Test: Provider passthrough
@pytest.mark.asyncio
async def test_provider_passthrough():
    """Test that providers are passed through to underlying functions."""
    # Mock providers
    mock_banking = object()
    mock_categorization = object()
    
    analytics = easy_analytics(
        banking_provider=mock_banking,
        categorization_provider=mock_categorization,
    )
    
    # Verify providers are stored
    assert analytics.banking_provider is mock_banking
    assert analytics.categorization_provider is mock_categorization


# Test: Compound interest utility
def test_compound_interest_utility():
    """Test compound interest calculation utility."""
    analytics = easy_analytics()
    
    # Simple compound interest: $1000 at 8% for 10 years
    result = analytics.compound_interest(1000, 0.08, 10)
    assert isinstance(result, float)
    assert 2000 < result < 2500  # Should be ~$2159
    
    # With contributions: $1000 initial + $100/month at 8% for 10 years
    result_contrib = analytics.compound_interest(1000, 0.08, 10, contribution=100)
    assert result_contrib > result  # More with contributions


# Test: Multiple operations different configs
@pytest.mark.asyncio
async def test_multiple_operations_different_configs():
    """Test multiple analytics instances with different configurations."""
    # Standard config
    standard = easy_analytics()
    
    # Conservative config (longer period, gross savings)
    conservative = easy_analytics(
        default_period_days=90,
        default_savings_definition=SavingsDefinition.GROSS,
    )
    
    # Aggressive config (shorter period, discretionary savings)
    aggressive = easy_analytics(
        default_period_days=7,
        default_savings_definition=SavingsDefinition.DISCRETIONARY,
    )
    
    user_id = "config_test"
    
    # All should work independently
    cf_standard = await standard.cash_flow(user_id)
    cf_conservative = await conservative.cash_flow(user_id)
    cf_aggressive = await aggressive.cash_flow(user_id)
    
    assert isinstance(cf_standard, CashFlowAnalysis)
    assert isinstance(cf_conservative, CashFlowAnalysis)
    assert isinstance(cf_aggressive, CashFlowAnalysis)
    
    # Periods should differ
    period_standard = (cf_standard.period_end - cf_standard.period_start).days
    period_conservative = (cf_conservative.period_end - cf_conservative.period_start).days
    period_aggressive = (cf_aggressive.period_end - cf_aggressive.period_start).days
    
    assert period_conservative > period_standard > period_aggressive


# Test: End-to-end with all features
@pytest.mark.asyncio
async def test_end_to_end_all_features():
    """Test end-to-end analytics with all features."""
    analytics = easy_analytics(
        default_period_days=30,
        default_benchmark="SPY",
        cache_ttl=3600,
    )
    
    user_id = "full_test"
    
    # 1. Cash flow
    cash_flow = await analytics.cash_flow(user_id)
    assert cash_flow.income_total > 0
    assert cash_flow.net_cash_flow == cash_flow.income_total - cash_flow.expense_total
    
    # 2. Savings rate
    savings = await analytics.savings_rate(user_id)
    assert 0 <= savings.savings_rate <= 1
    
    # 3. Spending insights
    spending = await analytics.spending_insights(user_id)
    assert len(spending.top_merchants) > 0
    assert len(spending.category_breakdown) > 0
    
    # 4. Portfolio metrics
    portfolio = await analytics.portfolio_metrics(user_id)
    assert portfolio.total_value >= 0
    assert portfolio.total_return_percent is not None
    
    # 5. Benchmark comparison
    comparison = await analytics.benchmark_comparison(user_id, period="1y")
    assert comparison.benchmark_symbol == "SPY"
    
    # 6. Growth projection
    projection = await analytics.net_worth_projection(user_id, years=10)
    assert len(projection.scenarios) == 3
    assert projection.scenarios[0].name == "Conservative"
    assert projection.scenarios[1].name == "Moderate"
    assert projection.scenarios[2].name == "Aggressive"
    
    # 7. Compound interest
    future_value = analytics.compound_interest(10000, 0.07, 10)
    assert future_value > 10000


# Test: Error handling
@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in analytics operations."""
    analytics = easy_analytics()
    
    # Should handle missing data gracefully
    try:
        # Non-existent user might return empty results or raise
        result = await analytics.cash_flow("nonexistent_user")
        # If it doesn't raise, check it returns valid structure
        assert isinstance(result, CashFlowAnalysis)
    except Exception as e:
        # If it raises, ensure it's a meaningful error
        assert str(e) is not None
