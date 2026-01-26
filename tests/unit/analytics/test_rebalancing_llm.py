"""Unit tests for LLM-powered rebalancing module."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fin_infra.analytics.rebalancing_llm import (
    LLMRebalancingPlan,
    LLMTrade,
)
from fin_infra.models.brokerage import Position


def make_position(
    symbol: str,
    qty: float,
    market_value: float,
    cost_basis: float | None = None,
    asset_class: str = "equity",
    name: str | None = None,
) -> Position:
    """Create a Position for testing."""
    qty_d = Decimal(str(qty))
    market_value_d = Decimal(str(market_value))
    cost_basis_d = Decimal(str(cost_basis)) if cost_basis else market_value_d * Decimal("0.9")

    return Position(
        symbol=symbol,
        qty=qty_d,
        side="long",
        avg_entry_price=cost_basis_d / qty_d if qty_d else Decimal("0"),
        current_price=market_value_d / qty_d if qty_d else Decimal("0"),
        market_value=market_value_d,
        cost_basis=cost_basis_d,
        unrealized_pl=market_value_d - cost_basis_d,
        unrealized_plpc=((market_value_d - cost_basis_d) / cost_basis_d * 100)
        if cost_basis_d
        else Decimal("0"),
        account_id="test_account",
        asset_class=asset_class,
        name=name or symbol,
    )


class TestLLMTrade:
    """Tests for LLMTrade model."""

    def test_trade_creation(self):
        """Test creating a valid trade."""
        trade = LLMTrade(
            symbol="VTI",
            action="buy",
            percentage_of_portfolio=10.0,
            reasoning="Diversify with index fund",
        )
        assert trade.symbol == "VTI"
        assert trade.action == "buy"
        assert trade.percentage_of_portfolio == 10.0

    def test_trade_sell_action(self):
        """Test sell trade."""
        trade = LLMTrade(
            symbol="AAPL",
            action="sell",
            percentage_of_portfolio=5.0,
            reasoning="Reduce concentration",
        )
        assert trade.action == "sell"

    def test_trade_serialization(self):
        """Test trade can be serialized to dict."""
        trade = LLMTrade(
            symbol="VTI",
            action="buy",
            percentage_of_portfolio=10.0,
            reasoning="Diversify",
        )
        data = trade.model_dump()
        assert data["symbol"] == "VTI"
        assert data["action"] == "buy"


class TestLLMRebalancingPlan:
    """Tests for LLMRebalancingPlan model."""

    def test_minimal_plan(self):
        """Test creating a plan with minimal fields."""
        plan = LLMRebalancingPlan(
            summary="Portfolio is balanced",
            analysis="Analysis shows good diversification",
        )
        assert plan.summary == "Portfolio is balanced"
        assert plan.trades == []
        assert plan.is_balanced is False  # Default

    def test_full_plan(self):
        """Test creating a complete plan."""
        plan = LLMRebalancingPlan(
            summary="Portfolio needs rebalancing",
            analysis="High concentration in tech sector",
            trades=[
                LLMTrade(
                    symbol="VTI",
                    action="buy",
                    percentage_of_portfolio=10.0,
                    reasoning="Add index exposure",
                )
            ],
            recommendations=["Consider tax-loss harvesting", "Review quarterly"],
            risk_warnings=["High tech concentration"],
            is_balanced=False,
        )
        assert len(plan.trades) == 1
        assert len(plan.recommendations) == 2
        assert len(plan.risk_warnings) == 1

    def test_plan_serialization(self):
        """Test plan can be serialized to dict."""
        plan = LLMRebalancingPlan(
            summary="Test summary",
            analysis="Test analysis",
            is_balanced=True,
        )
        data = plan.model_dump()
        assert data["summary"] == "Test summary"
        assert data["is_balanced"] is True

    def test_plan_json_round_trip(self):
        """Test plan can round-trip through JSON."""
        plan = LLMRebalancingPlan(
            summary="Test",
            analysis="Analysis",
            trades=[
                LLMTrade(
                    symbol="AAPL",
                    action="sell",
                    percentage_of_portfolio=5.0,
                    reasoning="Reduce",
                )
            ],
            is_balanced=False,
        )
        json_str = plan.model_dump_json()
        plan2 = LLMRebalancingPlan.model_validate_json(json_str)
        assert plan2.summary == plan.summary
        assert len(plan2.trades) == 1


class TestRebalancingInsightsGenerator:
    """Tests for RebalancingInsightsGenerator."""

    @patch("ai_infra.llm.LLM")
    def test_generator_init(self, mock_llm_class):
        """Test generator initialization."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator(provider="anthropic", model_name="test-model")
        assert gen.provider == "anthropic"
        assert gen.model_name == "test-model"
        assert gen.cache_ttl == 86400  # Default is 24 hours
        assert gen.enable_cache is True

    @patch("ai_infra.llm.LLM")
    def test_positions_to_holdings(self, mock_llm_class):
        """Test converting positions to holdings list."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        positions = [
            make_position("AAPL", 10, 1000.0, asset_class="equity"),
            make_position("VTI", 20, 3000.0, asset_class="etf"),
            make_position("USD", 100, 1000.0, asset_class="cash"),
        ]

        holdings = gen._positions_to_holdings(positions)

        assert len(holdings) == 3
        # Should be sorted by market value descending
        assert holdings[0]["symbol"] == "VTI"
        assert holdings[0]["market_value"] == 3000.0
        assert holdings[0]["percentage"] == 60.0

    @patch("ai_infra.llm.LLM")
    def test_empty_portfolio_response(self, mock_llm_class):
        """Test response for empty portfolio."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()
        response = gen._empty_portfolio_response()

        assert "empty" in response.summary.lower()
        assert response.trades == []
        assert response.is_balanced is True
        assert len(response.recommendations) > 0

    @patch("ai_infra.llm.LLM")
    def test_fallback_response(self, mock_llm_class):
        """Test fallback response when LLM unavailable."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        holdings = [
            {"symbol": "AAPL", "market_value": 5000, "percentage": 50.0, "asset_class": "equity"},
            {"symbol": "VTI", "market_value": 3000, "percentage": 30.0, "asset_class": "etf"},
            {"symbol": "USD", "market_value": 2000, "percentage": 20.0, "asset_class": "cash"},
        ]

        response = gen._fallback_response(holdings)

        assert "holdings" in response.summary.lower()
        assert "$10,000" in response.summary
        assert response.is_balanced is True  # Conservative default

    @patch("ai_infra.llm.LLM")
    def test_fallback_response_concentration_warning(self, mock_llm_class):
        """Test fallback response includes concentration warning."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        holdings = [
            {"symbol": "AAPL", "market_value": 8000, "percentage": 80.0, "asset_class": "equity"},
            {"symbol": "VTI", "market_value": 2000, "percentage": 20.0, "asset_class": "etf"},
        ]

        response = gen._fallback_response(holdings)

        # Should warn about high concentration
        assert any("AAPL" in w for w in response.risk_warnings)

    @patch("ai_infra.llm.LLM")
    def test_cache_key_generation(self, mock_llm_class):
        """Test cache key generation is stable."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        holdings = [
            {"symbol": "AAPL", "market_value": 5000, "percentage": 50.0},
            {"symbol": "VTI", "market_value": 5000, "percentage": 50.0},
        ]

        key1 = gen._generate_cache_key(holdings, None, None)
        key2 = gen._generate_cache_key(holdings, None, None)

        assert key1 == key2
        assert key1.startswith("rebalance:")

    @patch("ai_infra.llm.LLM")
    def test_cache_key_user_specific(self, mock_llm_class):
        """Test cache key includes user_id when provided."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        holdings = [{"symbol": "AAPL", "market_value": 5000, "percentage": 100.0}]

        key_no_user = gen._generate_cache_key(holdings, None, None)
        key_with_user = gen._generate_cache_key(holdings, None, "user123")

        assert "user123" in key_with_user
        assert "user123" not in key_no_user

    @patch("ai_infra.llm.LLM")
    def test_cache_key_target_allocation(self, mock_llm_class):
        """Test cache key changes with target allocation."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        holdings = [{"symbol": "AAPL", "market_value": 5000, "percentage": 100.0}]
        target1 = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        target2 = {"stocks": Decimal("80"), "bonds": Decimal("20")}

        key1 = gen._generate_cache_key(holdings, target1, None)
        key2 = gen._generate_cache_key(holdings, target2, None)

        assert key1 != key2

    @patch("ai_infra.llm.LLM")
    def test_normalize_llm_response_minimal(self, mock_llm_class):
        """Test normalizing response with minimal data."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        data = {
            "summary": "Test summary",
            "analysis": "Test analysis",
        }

        normalized = gen._normalize_llm_response(data)

        assert normalized["summary"] == "Test summary"
        assert normalized["trades"] == []
        assert normalized["recommendations"] == []
        assert normalized["is_balanced"] is False

    @patch("ai_infra.llm.LLM")
    def test_normalize_llm_response_truncation(self, mock_llm_class):
        """Test response truncation to max lengths."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()

        data = {
            "summary": "x" * 600,  # Over 500 char limit
            "analysis": "y" * 900,  # Over 800 char limit
            "trades": [{"symbol": f"SYM{i}", "action": "buy"} for i in range(10)],  # Over 5
            "recommendations": [f"Rec {i}" for i in range(10)],  # Over 3
            "risk_warnings": [f"Warn {i}" for i in range(10)],  # Over 3
        }

        normalized = gen._normalize_llm_response(data)

        assert len(normalized["summary"]) == 500
        assert normalized["summary"].endswith("...")
        assert len(normalized["analysis"]) == 800
        assert len(normalized["trades"]) == 5
        assert len(normalized["recommendations"]) == 3
        assert len(normalized["risk_warnings"]) == 3


class TestRebalancingInsightsGeneratorAsync:
    """Async tests for RebalancingInsightsGenerator."""

    @pytest.mark.asyncio
    @patch("ai_infra.llm.LLM")
    async def test_generate_empty_portfolio(self, mock_llm_class):
        """Test generate returns empty response for no positions."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        gen = RebalancingInsightsGenerator()
        result = await gen.generate([])

        assert result.is_balanced is True
        assert "empty" in result.summary.lower()

    @pytest.mark.asyncio
    @patch("fin_infra.analytics.rebalancing_llm.HAS_SVC_CACHE", False)
    @patch("ai_infra.llm.LLM")
    async def test_generate_with_positions_llm_error(self, mock_llm_class):
        """Test generate falls back gracefully on LLM error."""
        from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator

        mock_llm = MagicMock()
        mock_llm.achat = AsyncMock(side_effect=Exception("LLM unavailable"))
        mock_llm_class.return_value = mock_llm

        gen = RebalancingInsightsGenerator()
        positions = [make_position("AAPL", 10, 1000.0)]

        result = await gen.generate(positions)

        # Should return fallback response
        assert result.is_balanced is True
        assert "holdings" in result.summary.lower()
