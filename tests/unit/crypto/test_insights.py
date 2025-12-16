"""Unit tests for crypto insights with mocked LLM calls."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from fin_infra.crypto.insights import (
    CryptoHolding,
    CryptoInsight,
    generate_crypto_insights,
)


# ---- Fixtures ----


@pytest.fixture
def btc_holding():
    """Sample Bitcoin holding with gains."""
    return CryptoHolding(
        symbol="BTC",
        quantity=Decimal("0.5"),
        current_price=Decimal("45000"),
        cost_basis=Decimal("40000"),
        market_value=Decimal("22500"),  # 0.5 * 45000
    )


@pytest.fixture
def eth_holding():
    """Sample Ethereum holding with losses."""
    return CryptoHolding(
        symbol="ETH",
        quantity=Decimal("10"),
        current_price=Decimal("2000"),
        cost_basis=Decimal("3000"),
        market_value=Decimal("20000"),  # 10 * 2000
    )


@pytest.fixture
def doge_holding():
    """Sample Dogecoin holding (small allocation)."""
    return CryptoHolding(
        symbol="DOGE",
        quantity=Decimal("10000"),
        current_price=Decimal("0.08"),
        cost_basis=Decimal("0.10"),
        market_value=Decimal("800"),  # 10000 * 0.08
    )


@pytest.fixture
def mock_llm():
    """Mock ai-infra LLM."""
    llm = MagicMock()
    llm.model = "gemini-2.0-flash-exp"

    # Mock response
    mock_response = MagicMock()
    mock_response.content = "Your crypto portfolio shows strong Bitcoin allocation. Consider diversifying into Ethereum and stablecoins to reduce volatility risk. Not financial advice - consult a certified advisor."

    llm.achat = AsyncMock(return_value=mock_response)
    return llm


# ---- Test CryptoInsight Model ----


def test_crypto_insight_creation():
    """Test CryptoInsight model creation."""
    insight = CryptoInsight(
        id="insight_123",
        user_id="user_456",
        symbol="BTC",
        category="allocation",
        priority="high",
        title="Bitcoin represents 60% of portfolio",
        description="High concentration in BTC. Consider diversifying.",
        action="Review allocation",
        value=Decimal("60.0"),
        metadata={"allocation_pct": 60.0},
    )

    assert insight.id == "insight_123"
    assert insight.user_id == "user_456"
    assert insight.symbol == "BTC"
    assert insight.category == "allocation"
    assert insight.priority == "high"
    assert insight.value == Decimal("60.0")


def test_crypto_insight_optional_fields():
    """Test CryptoInsight with optional fields."""
    insight = CryptoInsight(
        id="insight_123",
        user_id="user_456",
        category="performance",
        priority="medium",
        title="Portfolio up 10%",
        description="Overall gains this week",
    )

    assert insight.symbol is None
    assert insight.action is None
    assert insight.value is None
    assert insight.metadata is None


# ---- Test CryptoHolding Model ----


def test_crypto_holding_creation(btc_holding):
    """Test CryptoHolding model creation."""
    assert btc_holding.symbol == "BTC"
    assert btc_holding.quantity == Decimal("0.5")
    assert btc_holding.current_price == Decimal("45000")
    assert btc_holding.cost_basis == Decimal("40000")
    assert btc_holding.market_value == Decimal("22500")


# ---- Test generate_crypto_insights ----


@pytest.mark.asyncio
async def test_generate_insights_empty_holdings():
    """Test with no holdings."""
    insights = await generate_crypto_insights("user_123", [])
    assert insights == []


@pytest.mark.asyncio
async def test_generate_insights_high_concentration(btc_holding):
    """Test allocation insight for high concentration."""
    # BTC is 100% of crypto portfolio
    insights = await generate_crypto_insights("user_123", [btc_holding])

    assert len(insights) >= 1

    # Find allocation insight
    alloc_insights = [i for i in insights if i.category == "allocation"]
    assert len(alloc_insights) == 1

    insight = alloc_insights[0]
    assert insight.symbol == "BTC"
    assert insight.priority == "high"
    assert "100%" in insight.title
    assert "diversif" in insight.description.lower()


@pytest.mark.asyncio
async def test_generate_insights_diversified_portfolio(btc_holding, eth_holding, doge_holding):
    """Test with diversified portfolio (no concentration warnings)."""
    # BTC: 52%, ETH: 46%, DOGE: 2%
    insights = await generate_crypto_insights("user_123", [btc_holding, eth_holding, doge_holding])

    # Should have allocation warning for BTC (>50%)
    alloc_insights = [i for i in insights if i.category == "allocation"]
    assert len(alloc_insights) == 1
    assert alloc_insights[0].symbol == "BTC"


@pytest.mark.asyncio
async def test_generate_insights_significant_gains(btc_holding):
    """Test performance insight for significant gains (>25%)."""
    # BTC: cost_basis=40000, current_price=45000 → +12.5% gain
    # Modify to have >25% gain
    btc_holding.current_price = Decimal("60000")  # 50% gain
    btc_holding.market_value = Decimal("30000")

    insights = await generate_crypto_insights("user_123", [btc_holding])

    # Find opportunity insight
    opp_insights = [i for i in insights if i.category == "opportunity"]
    assert len(opp_insights) == 1

    insight = opp_insights[0]
    assert insight.symbol == "BTC"
    assert insight.priority == "medium"
    assert "profit" in insight.title.lower()
    assert insight.value > 0  # Positive gain


@pytest.mark.asyncio
async def test_generate_insights_significant_losses(eth_holding):
    """Test risk insight for significant losses (>25%)."""
    # ETH: cost_basis=3000, current_price=2000 → -33% loss
    insights = await generate_crypto_insights("user_123", [eth_holding])

    # Find risk insight
    risk_insights = [i for i in insights if i.category == "risk"]
    assert len(risk_insights) == 1

    insight = risk_insights[0]
    assert insight.symbol == "ETH"
    assert insight.priority == "high"
    assert "down" in insight.title.lower()
    assert insight.value < 0  # Negative loss


@pytest.mark.asyncio
async def test_generate_insights_with_llm(btc_holding, mock_llm):
    """Test LLM-powered insights (MOCKED - no real LLM call)."""
    insights = await generate_crypto_insights("user_123", [btc_holding], llm=mock_llm)

    # Should have rule-based insights + 1 LLM insight
    assert len(insights) >= 2

    # Find LLM insight
    llm_insights = [i for i in insights if "AI Portfolio" in i.title]
    assert len(llm_insights) == 1

    insight = llm_insights[0]
    assert insight.category == "performance"
    assert insight.priority == "medium"
    assert "diversif" in insight.description.lower()
    assert insight.metadata["source"] == "ai-infra-llm"
    assert insight.metadata["model"] == "gemini-2.0-flash-exp"

    # Verify LLM was called with correct prompt
    mock_llm.achat.assert_called_once()
    call_args = mock_llm.achat.call_args
    user_msg = call_args.kwargs["user_msg"]
    assert "crypto portfolio advisor" in user_msg.lower() or "BTC" in user_msg
    assert "BTC" in user_msg
    assert "$22,500" in user_msg


@pytest.mark.asyncio
async def test_generate_insights_with_total_portfolio_value(btc_holding, eth_holding):
    """Test insights with total portfolio value context."""
    total_portfolio = Decimal("100000")  # Crypto is 42.5%

    insights = await generate_crypto_insights(
        "user_123",
        [btc_holding, eth_holding],
        total_portfolio_value=total_portfolio,
    )

    # Should generate insights based on crypto allocation % of total portfolio
    assert len(insights) >= 1


@pytest.mark.asyncio
async def test_generate_insights_llm_failure_graceful(btc_holding):
    """Test graceful degradation when LLM fails."""
    # Mock LLM that raises exception
    failing_llm = MagicMock()
    failing_llm.model = "gemini-2.0-flash-exp"
    failing_llm.achat = AsyncMock(side_effect=Exception("LLM API error"))

    # Should still return rule-based insights
    insights = await generate_crypto_insights("user_123", [btc_holding], llm=failing_llm)

    # Should have rule-based insights (allocation, performance)
    assert len(insights) >= 1

    # Should NOT have LLM insights
    llm_insights = [i for i in insights if "AI Portfolio" in i.title]
    assert len(llm_insights) == 0


@pytest.mark.asyncio
async def test_generate_insights_multiple_holdings_all_categories(btc_holding, eth_holding):
    """Test comprehensive insights across all categories."""
    # Modify holdings for diverse insights
    btc_holding.current_price = Decimal("60000")  # Large gain
    btc_holding.market_value = Decimal("30000")

    insights = await generate_crypto_insights("user_123", [btc_holding, eth_holding])

    # Should have multiple insight types
    categories = {i.category for i in insights}
    assert "allocation" in categories
    assert "opportunity" in categories or "risk" in categories


@pytest.mark.asyncio
async def test_insight_ids_unique(btc_holding, eth_holding):
    """Test that insight IDs are unique."""
    insights = await generate_crypto_insights("user_123", [btc_holding, eth_holding])

    ids = [i.id for i in insights]
    assert len(ids) == len(set(ids))  # All unique


@pytest.mark.asyncio
async def test_insight_timestamps(btc_holding):
    """Test that insights have valid timestamps."""
    before = datetime.now()
    insights = await generate_crypto_insights("user_123", [btc_holding])
    after = datetime.now()

    for insight in insights:
        assert before <= insight.created_at <= after


@pytest.mark.asyncio
async def test_llm_prompt_includes_holdings_summary(btc_holding, eth_holding, mock_llm):
    """Test that LLM prompt includes detailed holdings summary."""
    await generate_crypto_insights(
        "user_123",
        [btc_holding, eth_holding],
        llm=mock_llm,
        total_portfolio_value=Decimal("100000"),
    )

    call_args = mock_llm.achat.call_args
    prompt = call_args.kwargs["user_msg"]

    # Should include holdings details
    assert "BTC" in prompt
    assert "ETH" in prompt
    assert "$22,500" in prompt  # BTC market value
    assert "$20,000" in prompt  # ETH market value
    assert "gain/loss" in prompt.lower()


@pytest.mark.asyncio
async def test_no_llm_insights_when_llm_not_provided(btc_holding):
    """Test that no LLM insights generated when llm=None."""
    insights = await generate_crypto_insights("user_123", [btc_holding], llm=None)

    # Should only have rule-based insights
    llm_insights = [i for i in insights if "AI" in i.title]
    assert len(llm_insights) == 0
