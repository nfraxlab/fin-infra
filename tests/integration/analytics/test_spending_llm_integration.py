"""Integration tests for LLM-powered spending insights.

Tests end-to-end flow with analyze_spending() + generate_spending_insights().
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

from fin_infra.analytics.models import PersonalizedSpendingAdvice, TrendDirection
from fin_infra.analytics.spending import analyze_spending, generate_spending_insights
from fin_infra.models import Transaction


# ============================================================================
# Mock Providers
# ============================================================================


class MockLLMProvider:
    """Mock LLM provider for testing (mimics ai-infra CoreLLM API)."""
    
    def __init__(self, response=None):
        self.response = response or self._default_response()
        self.calls = []
    
    async def achat(self, user_msg=None, provider=None, model_name=None, system=None, 
                    output_schema=None, output_method=None, **kwargs):
        """Mock achat method matching CoreLLM signature."""
        self.calls.append({
            "user_msg": user_msg,
            "provider": provider,
            "model_name": model_name,
            "system": system,
            "output_schema": output_schema,
            "output_method": output_method,
            **kwargs
        })
        return self.response
    
    def _default_response(self):
        """Default mock response."""
        return {
            "summary": "Your spending patterns show opportunities for optimization.",
            "key_observations": [
                "Total spending analyzed across multiple categories",
                "Some categories show consistent patterns",
                "Consider setting category budgets for better control",
            ],
            "savings_opportunities": [
                "Review recurring subscriptions for unused services",
                "Compare merchant prices for better deals",
                "Set spending alerts to stay on budget",
            ],
            "positive_habits": ["Consistent transaction tracking"],
            "alerts": [],
            "estimated_monthly_savings": 50.0,
        }


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_and_generate_insights_e2e():
    """Test complete flow: analyze spending → generate LLM insights."""
    # Step 1: Analyze spending
    spending = await analyze_spending("user123", period="30d")
    
    # Verify spending analysis
    assert spending.total_spending > 0
    assert len(spending.top_merchants) > 0
    assert len(spending.category_breakdown) > 0
    
    # Step 2: Generate LLM insights
    mock_llm = MockLLMProvider()
    advice = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    # Verify advice generated
    assert isinstance(advice, PersonalizedSpendingAdvice)
    assert advice.summary
    assert len(advice.key_observations) > 0
    assert len(advice.savings_opportunities) > 0
    
    # Verify LLM was called
    assert len(mock_llm.calls) == 1
    call = mock_llm.calls[0]
    assert call["user_msg"] is not None
    assert call["output_schema"] == PersonalizedSpendingAdvice
    assert call["provider"] == "google_genai"
    assert call["model_name"] == "gemini-2.0-flash-exp"


@pytest.mark.asyncio
async def test_insights_with_high_spending_category():
    """Test LLM insights when one category dominates spending."""
    # Analyze spending (will use mock data with Amazon/Shopping dominance)
    spending = await analyze_spending("user123", period="30d")
    
    # Mock LLM to detect high shopping
    mock_response = {
        "summary": "Shopping spending is significantly higher than other categories.",
        "key_observations": [
            "Shopping category accounts for 45% of total spending",
            "Amazon is the top merchant with frequent purchases",
            "Consider consolidating purchases to reduce shipping costs",
        ],
        "savings_opportunities": [
            "Review Amazon purchases for impulse buys: ~$75/month",
            "Wait 24 hours before non-essential purchases: ~$50/month",
            "Set a monthly Amazon spending limit: prevent overspending",
        ],
        "positive_habits": [],
        "alerts": ["Shopping spending is trending upward"],
        "estimated_monthly_savings": 125.0,
    }
    
    mock_llm = MockLLMProvider(response=mock_response)
    advice = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    assert "Shopping" in advice.summary or "shopping" in advice.summary
    assert any("Amazon" in obs for obs in advice.key_observations)
    assert advice.estimated_monthly_savings == 125.0


@pytest.mark.asyncio
async def test_insights_with_spending_anomalies():
    """Test LLM insights when anomalies detected."""
    # Analyze spending with anomaly-prone data
    spending = await analyze_spending("user123", period="7d")  # Short period for anomalies
    
    # Mock LLM to address anomalies
    mock_response = {
        "summary": "Several spending anomalies detected - review transactions for accuracy.",
        "key_observations": [
            "Utilities spending is 150% above historical average",
            "Possible duplicate charge or billing error",
            "Entertainment spending also elevated",
        ],
        "savings_opportunities": [
            "Contact utility company about high bill",
            "Review bank statements for duplicate charges",
            "Set up spending alerts for unusual transactions",
        ],
        "positive_habits": [],
        "alerts": [
            "Utilities: $85 vs $35 average (143% increase)",
            "Verify all charges are legitimate",
        ],
        "estimated_monthly_savings": None,
    }
    
    mock_llm = MockLLMProvider(response=mock_response)
    advice = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    assert len(advice.alerts) > 0
    assert "anomal" in advice.summary.lower() or "unusual" in advice.summary.lower()


@pytest.mark.asyncio
async def test_insights_with_budget_comparison():
    """Test LLM insights with user budget context."""
    spending = await analyze_spending("user123", period="30d")
    
    # Provide budget context
    user_context = {
        "monthly_income": 6000.0,
        "savings_goal": 1500.0,
        "budget_categories": {
            "Groceries": 400.0,
            "Dining": 150.0,
            "Shopping": 200.0,
            "Entertainment": 100.0,
        },
    }
    
    # Mock LLM response considering budget
    mock_response = {
        "summary": "You're on track with most budgets, but dining needs attention.",
        "key_observations": [
            "Groceries: $230 actual vs $400 budget (on track)",
            "Dining: $195 actual vs $150 budget (30% over)",
            "Shopping: $235 actual vs $200 budget (18% over)",
            "Total spending: 11% of income",
        ],
        "savings_opportunities": [
            "Reduce dining out by 2 meals/week: ~$45/month",
            "Meal prep on Sundays to avoid weekday restaurant trips",
            "Use dining rewards/discounts: ~$20/month",
        ],
        "positive_habits": [
            "Grocery spending is well under budget",
            "Income-to-spending ratio is healthy",
        ],
        "alerts": [],
        "estimated_monthly_savings": 65.0,
    }
    
    mock_llm = MockLLMProvider(response=mock_response)
    advice = await generate_spending_insights(
        spending,
        user_context=user_context,
        llm_provider=mock_llm,
    )
    
    assert "budget" in advice.summary.lower()
    assert len(advice.positive_habits) > 0
    assert advice.estimated_monthly_savings == 65.0


@pytest.mark.asyncio
async def test_insights_prompt_includes_all_context():
    """Test that prompt sent to LLM includes all relevant context."""
    spending = await analyze_spending("user123", period="30d")
    
    user_context = {
        "monthly_income": 5000.0,
        "savings_goal": 1000.0,
    }
    
    mock_llm = MockLLMProvider()
    await generate_spending_insights(
        spending,
        user_context=user_context,
        llm_provider=mock_llm,
    )
    
    # Extract prompt from call
    call = mock_llm.calls[0]
    user_message = call["user_msg"]
    
    # Verify prompt contains spending data
    assert "Total Spending:" in user_message
    assert "Top Merchant:" in user_message
    assert "CATEGORY BREAKDOWN:" in user_message
    
    # Verify prompt contains user context
    assert "Monthly Income: $5000" in user_message
    assert "Savings Goal: $1000" in user_message
    
    # Verify prompt includes few-shot examples
    assert "FEW-SHOT EXAMPLES:" in user_message
    assert "Example 1" in user_message


@pytest.mark.asyncio
async def test_insights_with_category_filter():
    """Test LLM insights for filtered categories."""
    # Analyze only dining and groceries
    spending = await analyze_spending(
        "user123",
        period="30d",
        categories=["Dining", "Groceries"],
    )
    
    # Should only have selected categories
    assert all(cat in ["Dining", "Groceries", "Restaurants"] for cat in spending.category_breakdown.keys())
    
    # Generate insights
    mock_llm = MockLLMProvider(response={
        "summary": "Your food spending is well-balanced between dining and groceries.",
        "key_observations": [
            "Dining and groceries analyzed",
            "Balanced approach to home cooking vs dining out",
        ],
        "savings_opportunities": [
            "Increase home cooking by 1 meal/week: ~$40/month",
        ],
        "positive_habits": ["Good balance of categories"],
        "alerts": [],
        "estimated_monthly_savings": 40.0,
    })
    
    advice = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    assert "food" in advice.summary.lower() or "dining" in advice.summary.lower()


@pytest.mark.asyncio
async def test_insights_fallback_without_llm():
    """Test that rule-based insights work when LLM unavailable."""
    spending = await analyze_spending("user123", period="30d")
    
    # Don't provide LLM, should use rule-based
    advice = await generate_spending_insights(spending)
    
    # Should still get valid advice
    assert isinstance(advice, PersonalizedSpendingAdvice)
    assert advice.summary
    assert len(advice.key_observations) > 0
    assert len(advice.savings_opportunities) > 0


@pytest.mark.asyncio
async def test_insights_consistency_across_calls():
    """Test that multiple calls with same data produce consistent structure."""
    spending = await analyze_spending("user123", period="30d")
    
    mock_llm = MockLLMProvider()
    
    # Generate insights twice
    advice1 = await generate_spending_insights(spending, llm_provider=mock_llm)
    advice2 = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    # Structure should be consistent
    assert len(advice1.key_observations) == len(advice2.key_observations)
    assert len(advice1.savings_opportunities) == len(advice2.savings_opportunities)
    assert advice1.estimated_monthly_savings == advice2.estimated_monthly_savings


@pytest.mark.asyncio
async def test_insights_with_multiple_anomalies():
    """Test LLM handles multiple spending anomalies."""
    # Create spending with anomalies
    spending = await analyze_spending("user123", period="7d")
    
    # Mock LLM to prioritize severe issues
    mock_response = {
        "summary": "Multiple spending anomalies require immediate review.",
        "key_observations": [
            "3 categories show unusual spending patterns",
            "Utilities spending is 143% above average",
            "Entertainment and Shopping also elevated",
        ],
        "savings_opportunities": [
            "Verify all transactions are legitimate",
            "Contact merchants about duplicate charges",
            "Set up fraud alerts with bank",
        ],
        "positive_habits": [],
        "alerts": [
            "Utilities: Possible billing error",
            "Entertainment: Verify streaming charges",
            "Shopping: Check for unauthorized purchases",
        ],
        "estimated_monthly_savings": None,
    }
    
    mock_llm = MockLLMProvider(response=mock_response)
    advice = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    assert len(advice.alerts) >= 2
    assert "anomal" in advice.summary.lower() or "unusual" in advice.summary.lower()


@pytest.mark.asyncio
async def test_insights_respects_output_schema():
    """Test that LLM is called with correct output schema."""
    spending = await analyze_spending("user123", period="30d")
    
    mock_llm = MockLLMProvider()
    await generate_spending_insights(spending, llm_provider=mock_llm)
    
    # Verify output schema and method passed correctly
    call = mock_llm.calls[0]
    assert call["output_schema"] == PersonalizedSpendingAdvice
    assert call["output_method"] == "prompt"
    assert call["provider"] == "google_genai"


@pytest.mark.asyncio
async def test_insights_with_positive_spending_habits():
    """Test LLM recognizes and reinforces positive habits."""
    spending = await analyze_spending("user123", period="30d")
    
    # Mock LLM to highlight positive behaviors
    mock_response = {
        "summary": "Your spending habits are generally healthy with room for optimization.",
        "key_observations": [
            "Consistent spending across months",
            "No unusual spikes or anomalies",
            "Diverse merchant usage (not dependent on one vendor)",
        ],
        "savings_opportunities": [
            "Small optimizations available in dining category",
            "Consider bulk purchasing for groceries: ~$30/month",
        ],
        "positive_habits": [
            "Excellent spending consistency",
            "No impulse purchase patterns detected",
            "Good category diversification",
        ],
        "alerts": [],
        "estimated_monthly_savings": 30.0,
    }
    
    mock_llm = MockLLMProvider(response=mock_response)
    advice = await generate_spending_insights(spending, llm_provider=mock_llm)
    
    assert len(advice.positive_habits) >= 3
    assert "healthy" in advice.summary.lower() or "good" in advice.summary.lower()


@pytest.mark.asyncio
async def test_insights_different_periods():
    """Test insights work correctly for different time periods."""
    # Test 7-day period
    spending_7d = await analyze_spending("user123", period="7d")
    mock_llm = MockLLMProvider()
    advice_7d = await generate_spending_insights(spending_7d, llm_provider=mock_llm)
    
    assert isinstance(advice_7d, PersonalizedSpendingAdvice)
    
    # Test 90-day period
    spending_90d = await analyze_spending("user123", period="90d")
    advice_90d = await generate_spending_insights(spending_90d, llm_provider=mock_llm)
    
    assert isinstance(advice_90d, PersonalizedSpendingAdvice)
    
    # Both should produce valid advice
    assert advice_7d.summary != ""
    assert advice_90d.summary != ""
