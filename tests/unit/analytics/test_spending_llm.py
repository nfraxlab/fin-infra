"""Unit tests for LLM-powered spending insights.

Tests ai-infra integration for personalized spending advice generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fin_infra.analytics.models import (
    PersonalizedSpendingAdvice,
    SpendingAnomaly,
    SpendingInsight,
    TrendDirection,
)
from fin_infra.analytics.spending import (
    generate_spending_insights,
    _build_spending_insights_prompt,
    _generate_rule_based_insights,
)


# ============================================================================
# Test generate_spending_insights()
# ============================================================================


@pytest.mark.asyncio
async def test_generate_spending_insights_with_llm():
    """Test LLM-powered insight generation."""
    # Create sample spending insight
    insight = SpendingInsight(
        top_merchants=[("Amazon", -250.0), ("Safeway", -180.0)],
        category_breakdown={"Shopping": 250.0, "Groceries": 180.0, "Dining": 120.0},
        spending_trends={
            "Shopping": TrendDirection.INCREASING,
            "Groceries": TrendDirection.STABLE,
            "Dining": TrendDirection.DECREASING,
        },
        anomalies=[
            SpendingAnomaly(
                category="Shopping",
                current_amount=250.0,
                average_amount=150.0,
                deviation_percent=66.7,
                severity="severe",
            )
        ],
        period_days=30,
        total_spending=550.0,
    )

    # Mock LLM response
    mock_response = {
        "summary": "Shopping spending has increased significantly this month.",
        "key_observations": [
            "Shopping spending up 67% from average",
            "Amazon is top merchant at $250",
            "Dining spending is trending down (positive)",
        ],
        "savings_opportunities": [
            "Review Amazon purchases for unnecessary items: ~$50/month",
            "Set spending alerts for Shopping category: prevent overspending",
        ],
        "positive_habits": ["Successfully reducing dining expenses"],
        "alerts": ["Shopping category spending is 67% above normal"],
        "estimated_monthly_savings": 50.0,
    }

    # Mock CoreLLM
    mock_llm = AsyncMock()
    mock_llm.achat = AsyncMock(return_value=mock_response)

    # Generate insights
    advice = await generate_spending_insights(insight, llm_provider=mock_llm)

    # Verify result
    assert isinstance(advice, PersonalizedSpendingAdvice)
    assert "Shopping" in advice.summary
    assert len(advice.key_observations) >= 3
    assert len(advice.savings_opportunities) >= 2
    assert advice.estimated_monthly_savings == 50.0

    # Verify LLM was called correctly
    mock_llm.achat.assert_called_once()
    call_args = mock_llm.achat.call_args
    # Check keyword arguments
    kwargs = call_args.kwargs if hasattr(call_args, "kwargs") else call_args[1]
    assert kwargs["output_schema"] == PersonalizedSpendingAdvice
    assert kwargs["output_method"] == "prompt"
    assert kwargs["provider"] == "google_genai"
    assert kwargs["model_name"] == "gemini-2.0-flash-exp"


@pytest.mark.asyncio
async def test_generate_spending_insights_with_user_context():
    """Test LLM insights with user context (income, budget, goals)."""
    insight = SpendingInsight(
        top_merchants=[("Starbucks", -120.0)],
        category_breakdown={"Dining": 400.0, "Groceries": 300.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=700.0,
    )

    user_context = {
        "monthly_income": 5000.0,
        "savings_goal": 1000.0,
        "budget_categories": {"Dining": 200.0, "Groceries": 400.0},
    }

    mock_response = {
        "summary": "Dining spending is 100% over budget, impacting savings goal.",
        "key_observations": [
            "Dining: $400 actual vs $200 budget (OVER BUDGET)",
            "Groceries: $300 actual vs $400 budget (on track)",
            "Total spending: 14% of monthly income",
        ],
        "savings_opportunities": [
            "Reduce dining out to meet $200 budget: ~$200/month savings",
            "This would allow you to reach your $1000 savings goal",
        ],
        "positive_habits": ["Grocery spending is under budget"],
        "alerts": ["Dining budget exceeded by $200"],
        "estimated_monthly_savings": 200.0,
    }

    mock_llm = AsyncMock()
    mock_llm.achat = AsyncMock(return_value=mock_response)

    advice = await generate_spending_insights(
        insight,
        user_context=user_context,
        llm_provider=mock_llm,
    )

    assert "budget" in advice.summary.lower()
    assert any("OVER BUDGET" in obs for obs in advice.key_observations)
    assert advice.estimated_monthly_savings == 200.0

    # Verify prompt includes user context
    call_args = mock_llm.achat.call_args
    kwargs = call_args.kwargs if hasattr(call_args, "kwargs") else call_args[1]
    user_message = kwargs["user_msg"]
    assert "Monthly Income: $5000" in user_message
    assert "Savings Goal: $1000" in user_message
    assert "Budget:" in user_message


@pytest.mark.asyncio
async def test_generate_spending_insights_fallback_on_import_error():
    """Test graceful degradation when ai-infra not available."""
    insight = SpendingInsight(
        top_merchants=[("Target", -150.0)],
        category_breakdown={"Shopping": 150.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=150.0,
    )

    # Mock ImportError for ai_infra.llm - need to patch the import itself
    with patch.dict("sys.modules", {"ai_infra.llm": None}):
        # Force re-import to trigger ImportError
        advice = await generate_spending_insights(insight)

        # Should return rule-based insights
        assert isinstance(advice, PersonalizedSpendingAdvice)
        assert advice.summary  # Has content
        assert advice.key_observations
        # Rule-based insights should still be useful


@pytest.mark.asyncio
async def test_generate_spending_insights_fallback_on_llm_error():
    """Test fallback to rule-based insights on LLM error."""
    insight = SpendingInsight(
        top_merchants=[("Walmart", -200.0)],
        category_breakdown={"Groceries": 200.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=200.0,
    )

    # Mock LLM that raises exception
    mock_llm = AsyncMock()
    mock_llm.achat = AsyncMock(side_effect=Exception("API rate limit"))

    advice = await generate_spending_insights(insight, llm_provider=mock_llm)

    # Should fallback to rule-based
    assert isinstance(advice, PersonalizedSpendingAdvice)
    assert advice.summary
    assert advice.key_observations


@pytest.mark.asyncio
async def test_generate_spending_insights_handles_dict_response():
    """Test handling LLM response as dict (standard format)."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=0.0,
    )

    mock_response = {
        "summary": "Test summary",
        "key_observations": ["Observation 1"],
        "savings_opportunities": ["Opportunity 1"],
        "positive_habits": [],
        "alerts": [],
        "estimated_monthly_savings": None,
    }

    mock_llm = AsyncMock()
    mock_llm.achat = AsyncMock(return_value=mock_response)

    advice = await generate_spending_insights(insight, llm_provider=mock_llm)

    assert advice.summary == "Test summary"
    assert advice.key_observations == ["Observation 1"]


@pytest.mark.asyncio
async def test_generate_spending_insights_handles_pydantic_response():
    """Test handling LLM response as Pydantic model."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=0.0,
    )

    # Create mock Pydantic-like response
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "summary": "Test summary",
        "key_observations": ["Observation 1"],
        "savings_opportunities": ["Opportunity 1"],
        "positive_habits": [],
        "alerts": [],
        "estimated_monthly_savings": None,
    }

    mock_llm = AsyncMock()
    mock_llm.achat = AsyncMock(return_value=mock_response)

    advice = await generate_spending_insights(insight, llm_provider=mock_llm)

    assert advice.summary == "Test summary"


@pytest.mark.asyncio
async def test_generate_spending_insights_system_message():
    """Test that system message includes financial advisor disclaimer."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=0.0,
    )

    mock_llm = AsyncMock()
    mock_llm.achat = AsyncMock(
        return_value={
            "summary": "Test",
            "key_observations": ["Test"],
            "savings_opportunities": ["Test"],
        }
    )

    await generate_spending_insights(insight, llm_provider=mock_llm)

    # Check system message
    call_args = mock_llm.achat.call_args
    kwargs = call_args.kwargs if hasattr(call_args, "kwargs") else call_args[1]
    system_message = kwargs["system"]

    assert "financial advisor" in system_message.lower()
    assert "not a substitute" in system_message.lower()


# ============================================================================
# Test _build_spending_insights_prompt()
# ============================================================================


def test_build_spending_insights_prompt_basic():
    """Test prompt building with basic spending data."""
    insight = SpendingInsight(
        top_merchants=[("Amazon", -250.0), ("Safeway", -180.0)],
        category_breakdown={"Shopping": 250.0, "Groceries": 180.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=430.0,
    )

    prompt = _build_spending_insights_prompt(insight)

    assert "Period: 30 days" in prompt
    assert "Total Spending: $430.00" in prompt
    assert "Amazon" in prompt
    assert "250.00" in prompt
    assert "Shopping: $250.00" in prompt
    assert "Groceries: $180.00" in prompt


def test_build_spending_insights_prompt_with_trends():
    """Test prompt includes spending trends."""
    insight = SpendingInsight(
        top_merchants=[("Target", -100.0)],
        category_breakdown={"Shopping": 100.0},
        spending_trends={
            "Shopping": TrendDirection.INCREASING,
            "Dining": TrendDirection.DECREASING,
        },
        anomalies=[],
        period_days=30,
        total_spending=100.0,
    )

    prompt = _build_spending_insights_prompt(insight)

    assert "INCREASING SPENDING IN:" in prompt
    assert "Shopping" in prompt


def test_build_spending_insights_prompt_with_anomalies():
    """Test prompt includes spending anomalies."""
    anomaly = SpendingAnomaly(
        category="Utilities",
        current_amount=200.0,
        average_amount=100.0,
        deviation_percent=100.0,
        severity="severe",
    )

    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Utilities": 200.0},
        spending_trends={},
        anomalies=[anomaly],
        period_days=30,
        total_spending=200.0,
    )

    prompt = _build_spending_insights_prompt(insight)

    assert "SPENDING ANOMALIES:" in prompt
    assert "Utilities" in prompt
    assert "$200.00" in prompt
    assert "avg: $100.00" in prompt
    assert "100% deviation" in prompt


def test_build_spending_insights_prompt_with_user_context():
    """Test prompt includes user context when provided."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Dining": 400.0, "Groceries": 300.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=700.0,
    )

    user_context = {
        "monthly_income": 5000.0,
        "savings_goal": 1000.0,
        "budget_categories": {"Dining": 200.0, "Groceries": 400.0},
    }

    prompt = _build_spending_insights_prompt(insight, user_context)

    assert "USER CONTEXT:" in prompt
    assert "Monthly Income: $5000.00" in prompt
    assert "Savings Goal: $1000.00" in prompt
    assert "Budget:" in prompt
    assert "Dining: $200.00 budget, $400.00 actual (OVER BUDGET)" in prompt
    assert "Groceries: $400.00 budget, $300.00 actual (on track)" in prompt


def test_build_spending_insights_prompt_includes_examples():
    """Test prompt includes few-shot examples."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=0.0,
    )

    prompt = _build_spending_insights_prompt(insight)

    assert "FEW-SHOT EXAMPLES:" in prompt
    assert "Example 1" in prompt
    assert "Example 2" in prompt
    assert "High dining spending" in prompt
    assert "Subscription creep" in prompt


def test_build_spending_insights_prompt_limits_anomalies():
    """Test prompt only includes top 3 anomalies."""
    anomalies = [
        SpendingAnomaly(
            category=f"Category{i}",
            current_amount=100.0,
            average_amount=50.0,
            deviation_percent=100.0,
            severity="severe",
        )
        for i in range(10)  # 10 anomalies
    ]

    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={},
        spending_trends={},
        anomalies=anomalies,
        period_days=30,
        total_spending=1000.0,
    )

    prompt = _build_spending_insights_prompt(insight)

    # Should only include first 3
    assert "Category0" in prompt
    assert "Category1" in prompt
    assert "Category2" in prompt
    # Later ones shouldn't be in prompt
    assert "Category9" not in prompt


# ============================================================================
# Test _generate_rule_based_insights()
# ============================================================================


def test_generate_rule_based_insights_basic():
    """Test rule-based insights generation."""
    insight = SpendingInsight(
        top_merchants=[("Amazon", -250.0)],
        category_breakdown={"Shopping": 250.0, "Groceries": 100.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=350.0,
    )

    advice = _generate_rule_based_insights(insight)

    assert isinstance(advice, PersonalizedSpendingAdvice)
    assert advice.summary
    assert len(advice.key_observations) > 0
    assert len(advice.savings_opportunities) > 0


def test_generate_rule_based_insights_high_category_spending():
    """Test rule detects high spending in one category."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Dining": 400.0, "Groceries": 100.0},  # Dining is 80%
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=500.0,
    )

    advice = _generate_rule_based_insights(insight)

    # Should suggest reducing Dining since it's >30% of total
    assert any("Dining" in opp for opp in advice.savings_opportunities)
    assert advice.estimated_monthly_savings is not None
    assert advice.estimated_monthly_savings > 0


def test_generate_rule_based_insights_increasing_trends():
    """Test rule detects increasing spending trends."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Shopping": 200.0},
        spending_trends={"Shopping": TrendDirection.INCREASING},
        anomalies=[],
        period_days=30,
        total_spending=200.0,
    )

    advice = _generate_rule_based_insights(insight)

    assert any("Shopping" in obs and "trending up" in obs for obs in advice.key_observations)


def test_generate_rule_based_insights_decreasing_trends():
    """Test rule recognizes positive habits (decreasing spending)."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Dining": 100.0},
        spending_trends={"Dining": TrendDirection.DECREASING},
        anomalies=[],
        period_days=30,
        total_spending=100.0,
    )

    advice = _generate_rule_based_insights(insight)

    assert len(advice.positive_habits) > 0
    assert any("Dining" in habit for habit in advice.positive_habits)


def test_generate_rule_based_insights_anomaly_alerts():
    """Test rule creates alerts for spending anomalies."""
    anomaly = SpendingAnomaly(
        category="Utilities",
        current_amount=200.0,
        average_amount=100.0,
        deviation_percent=100.0,
        severity="severe",
    )

    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Utilities": 200.0},
        spending_trends={},
        anomalies=[anomaly],
        period_days=30,
        total_spending=200.0,
    )

    advice = _generate_rule_based_insights(insight)

    assert len(advice.alerts) > 0
    assert any("Utilities" in alert for alert in advice.alerts)
    assert any("100%" in alert for alert in advice.alerts)


def test_generate_rule_based_insights_with_budget_context():
    """Test rule compares spending to budget when provided."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Dining": 400.0, "Groceries": 300.0},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=700.0,
    )

    user_context = {
        "budget_categories": {"Dining": 200.0, "Groceries": 400.0},
    }

    advice = _generate_rule_based_insights(insight, user_context)

    # Should detect Dining over budget
    assert any("Dining" in opp and "budget" in opp for opp in advice.savings_opportunities)
    # Estimated savings should be at least the overage ($200)
    assert advice.estimated_monthly_savings >= 200.0


def test_generate_rule_based_insights_default_content():
    """Test rule provides default content for minimal data."""
    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={},
        spending_trends={},
        anomalies=[],
        period_days=30,
        total_spending=0.0,
    )

    advice = _generate_rule_based_insights(insight)

    # Should still provide useful content
    assert advice.summary
    assert len(advice.key_observations) > 0
    assert len(advice.savings_opportunities) > 0
    # Should have at least one positive habit even with no data
    assert len(advice.positive_habits) > 0


def test_generate_rule_based_insights_limits_list_lengths():
    """Test rule limits observations and opportunities to 5 items."""
    # Create insight with many categories
    categories = {f"Category{i}": 100.0 for i in range(20)}

    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown=categories,
        spending_trends={cat: TrendDirection.INCREASING for cat in categories},
        anomalies=[],
        period_days=30,
        total_spending=2000.0,
    )

    advice = _generate_rule_based_insights(insight)

    # Should limit to 5 items
    assert len(advice.key_observations) <= 5
    assert len(advice.savings_opportunities) <= 5
    assert len(advice.positive_habits) <= 3


def test_generate_rule_based_insights_summary_prioritizes_alerts():
    """Test rule prioritizes alerts in summary when present."""
    anomaly = SpendingAnomaly(
        category="Entertainment",
        current_amount=500.0,
        average_amount=100.0,
        deviation_percent=400.0,
        severity="severe",
    )

    insight = SpendingInsight(
        top_merchants=[],
        category_breakdown={"Entertainment": 500.0},
        spending_trends={},
        anomalies=[anomaly],
        period_days=30,
        total_spending=500.0,
    )

    advice = _generate_rule_based_insights(insight)

    # Summary should mention alerts
    assert "alert" in advice.summary.lower()
