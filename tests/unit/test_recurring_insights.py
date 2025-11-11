"""
Unit tests for recurring/insights.py (Layer 5 - LLM subscription insights generation).

Tests subscription insights generation with mocked CoreLLM responses.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fin_infra.recurring.insights import (
    SubscriptionInsights,
    SubscriptionInsightsGenerator,
    INSIGHTS_GENERATION_SYSTEM_PROMPT,
)


class TestSubscriptionInsights:
    """Test SubscriptionInsights Pydantic model."""

    def test_valid_model_with_recommendations(self):
        """Test valid SubscriptionInsights with recommendations."""
        result = SubscriptionInsights(
            summary="You're spending $64.95/month on 5 streaming services",
            top_subscriptions=[
                {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
                {"merchant": "Hulu", "amount": 17.99, "cadence": "monthly"},
            ],
            recommendations=[
                "Consider Disney+ bundle to save $29.98/month",
                "Amazon Prime includes Prime Video",
            ],
            total_monthly_cost=64.95,
            potential_savings=29.98,
        )

        assert "64.95" in result.summary
        assert len(result.top_subscriptions) == 2
        assert len(result.recommendations) == 2
        assert result.total_monthly_cost == 64.95
        assert result.potential_savings == 29.98

    def test_valid_model_no_recommendations(self):
        """Test valid SubscriptionInsights without recommendations."""
        result = SubscriptionInsights(
            summary="You're spending $10.99/month on 1 subscription",
            top_subscriptions=[
                {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
            ],
            recommendations=[],
            total_monthly_cost=10.99,
            potential_savings=0.0,
        )

        assert len(result.recommendations) == 0
        assert result.potential_savings == 0.0

    def test_max_top_subscriptions(self):
        """Test that top_subscriptions is limited to 5."""
        # Valid with 5
        SubscriptionInsights(
            summary="test",
            top_subscriptions=[
                {"merchant": f"Sub{i}", "amount": 10.0, "cadence": "monthly"} for i in range(5)
            ],
            recommendations=[],
            total_monthly_cost=50.0,
            potential_savings=0.0,
        )

        # Invalid with 6 (should work but we'll test the validation logic)
        # Note: Pydantic validation for max_length=5 will reject 6 items
        with pytest.raises(ValueError):
            SubscriptionInsights(
                summary="test",
                top_subscriptions=[
                    {"merchant": f"Sub{i}", "amount": 10.0, "cadence": "monthly"} for i in range(6)
                ],
                recommendations=[],
                total_monthly_cost=60.0,
                potential_savings=0.0,
            )

    def test_max_recommendations(self):
        """Test that recommendations is limited to 3."""
        # Valid with 3
        SubscriptionInsights(
            summary="test",
            top_subscriptions=[],
            recommendations=["Rec1", "Rec2", "Rec3"],
            total_monthly_cost=0.0,
            potential_savings=0.0,
        )

        # Invalid with 4
        with pytest.raises(ValueError):
            SubscriptionInsights(
                summary="test",
                top_subscriptions=[],
                recommendations=["Rec1", "Rec2", "Rec3", "Rec4"],
                total_monthly_cost=0.0,
                potential_savings=0.0,
            )


class TestSubscriptionInsightsGenerator:
    """Test SubscriptionInsightsGenerator with mocked CoreLLM."""

    @pytest.fixture
    def mock_llm(self):
        """Mock CoreLLM for testing."""
        with patch("fin_infra.recurring.insights.CoreLLM") as mock:
            yield mock

    @pytest.fixture
    def generator(self, mock_llm):
        """Create SubscriptionInsightsGenerator with mocked dependencies."""
        return SubscriptionInsightsGenerator(
            provider="google",
            model_name="gemini-2.0-flash-exp",
            cache_ttl=86400,  # 24 hours
            enable_cache=False,  # Disable cache for unit tests
        )

    @pytest.mark.asyncio
    async def test_generate_insights_for_streaming_services(self, generator, mock_llm):
        """Test insights generation for multiple streaming services."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = SubscriptionInsights(
            summary="You're spending $64.95/month on 5 streaming services, which is above average. Consider consolidating to save money.",
            top_subscriptions=[
                {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
                {"merchant": "Hulu", "amount": 17.99, "cadence": "monthly"},
                {"merchant": "Disney+", "amount": 10.99, "cadence": "monthly"},
                {"merchant": "Apple TV+", "amount": 9.99, "cadence": "monthly"},
                {"merchant": "Prime Video", "amount": 9.99, "cadence": "monthly"},
            ],
            recommendations=[
                "Consider the Disney+ bundle ($19.99) which includes Hulu and ESPN+ - saves you $29.98/month",
                "You have Amazon Prime which includes Prime Video, consider canceling standalone Prime Video if duplicate",
                "Netflix and Hulu together cost $33.98 - Disney+ bundle ($19.99) includes Hulu and saves $13.99/month",
            ],
            total_monthly_cost=64.95,
            potential_savings=29.98,
        )
        generator.llm.achat = AsyncMock(return_value=mock_response)

        # Subscriptions
        subscriptions = [
            {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
            {"merchant": "Hulu", "amount": 17.99, "cadence": "monthly"},
            {"merchant": "Disney+", "amount": 10.99, "cadence": "monthly"},
            {"merchant": "Apple TV+", "amount": 9.99, "cadence": "monthly"},
            {"merchant": "Prime Video", "amount": 9.99, "cadence": "monthly"},
        ]

        # Generate insights
        result = await generator.generate(subscriptions, user_id="user123")

        # Verify result
        assert "64.95" in result.summary
        assert len(result.top_subscriptions) == 5
        assert len(result.recommendations) == 3
        assert result.total_monthly_cost == 64.95
        assert result.potential_savings == 29.98
        assert (
            "Disney+" in result.recommendations[0] or "bundle" in result.recommendations[0].lower()
        )

        # Verify LLM was called with correct parameters
        generator.llm.achat.assert_called_once()
        call_args = generator.llm.achat.call_args
        assert call_args.kwargs["provider"] == "google"
        assert call_args.kwargs["model"] == "gemini-2.0-flash-exp"
        assert call_args.kwargs["output_schema"] == SubscriptionInsights
        assert call_args.kwargs["temperature"] == 0.3  # Slight creativity

        # Verify prompt
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == INSIGHTS_GENERATION_SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert "Netflix" in messages[1]["content"]
        assert "$15.99" in messages[1]["content"] or "15.99" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_generate_insights_for_duplicate_services(self, generator, mock_llm):
        """Test insights generation detects duplicate music services."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = SubscriptionInsights(
            summary="You have both Spotify and Apple Music ($20.98/month total). Choose one to save $10.99/month.",
            top_subscriptions=[
                {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
                {"merchant": "Apple Music", "amount": 9.99, "cadence": "monthly"},
            ],
            recommendations=[
                "Cancel either Spotify or Apple Music to save $10.99/month - they provide the same service",
            ],
            total_monthly_cost=20.98,
            potential_savings=10.99,
        )
        generator.llm.achat = AsyncMock(return_value=mock_response)

        # Duplicate subscriptions
        subscriptions = [
            {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
            {"merchant": "Apple Music", "amount": 9.99, "cadence": "monthly"},
        ]

        # Generate insights
        result = await generator.generate(subscriptions)

        # Verify result
        assert "Spotify" in result.summary and "Apple Music" in result.summary
        assert result.total_monthly_cost == 20.98
        assert result.potential_savings == 10.99
        assert any("cancel" in rec.lower() for rec in result.recommendations)

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_hit(self, generator, mock_llm, mock_cache):
        """Test that cached results are returned without calling LLM."""
        # Mock cache hit
        cached_result = {
            "summary": "Cached summary",
            "top_subscriptions": [{"merchant": "Test", "amount": 10.0, "cadence": "monthly"}],
            "recommendations": ["Cached recommendation"],
            "total_monthly_cost": 10.0,
            "potential_savings": 0.0,
        }
        mock_cache.get = AsyncMock(return_value=cached_result)

        # Generate insights (should use cache)
        subscriptions = [{"merchant": "Test", "amount": 10.0, "cadence": "monthly"}]
        result = await generator.generate(subscriptions, user_id="user123")

        # Verify cache was checked
        mock_cache.get.assert_called_once()

        # Verify LLM was NOT called
        generator.llm.achat.assert_not_called()

        # Verify result from cache
        assert result.summary == "Cached summary"
        assert len(result.recommendations) == 1

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_miss_calls_llm_and_caches_result(self, generator, mock_llm, mock_cache):
        """Test that cache miss triggers LLM call and caches the result."""
        # Mock cache miss
        mock_cache.get = AsyncMock(return_value=None)

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = SubscriptionInsights(
            summary="Test summary",
            top_subscriptions=[{"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"}],
            recommendations=["Test recommendation"],
            total_monthly_cost=15.99,
            potential_savings=0.0,
        )
        generator.llm.achat = AsyncMock(return_value=mock_response)

        # Generate insights
        subscriptions = [{"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"}]
        result = await generator.generate(subscriptions, user_id="user123")

        # Verify cache was checked
        mock_cache.get.assert_called_once()

        # Verify LLM was called
        generator.llm.achat.assert_called_once()

        # Verify result was cached
        mock_cache.set.assert_called_once()
        cache_call = mock_cache.set.call_args
        assert cache_call.kwargs["ttl"] == 86400  # 24 hours

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_key_with_user_id(self, generator):
        """Test cache key generation with user_id."""
        cache_key = generator._make_cache_key(user_id="user123")

        # Verify format
        assert cache_key == "insights:user123"

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_key_without_user_id(self, generator):
        """Test cache key generation without user_id uses subscriptions hash."""
        subscriptions = [
            {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
            {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
        ]

        cache_key = generator._make_cache_key(subscriptions=subscriptions)

        # Verify format
        assert cache_key.startswith("insights:")
        assert cache_key != "insights:user123"  # Different from user_id format

        # Verify deterministic (same subscriptions = same key)
        cache_key2 = generator._make_cache_key(subscriptions=subscriptions)
        assert cache_key == cache_key2

    @pytest.mark.asyncio
    async def test_fallback_when_llm_error(self, generator, mock_llm):
        """Test fallback to basic insights when LLM raises error."""
        # Mock LLM error
        generator.llm.achat = AsyncMock(side_effect=Exception("LLM timeout"))

        # Generate insights (should use fallback)
        subscriptions = [
            {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
            {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
        ]
        result = await generator.generate(subscriptions)

        # Verify fallback was used
        assert "26.98" in result.summary or "total" in result.summary.lower()
        assert len(result.top_subscriptions) == 2
        assert len(result.recommendations) == 0  # No LLM recommendations
        assert result.total_monthly_cost == 26.98
        assert result.potential_savings is None  # No savings calculation without LLM

    @pytest.mark.asyncio
    async def test_fallback_basic_summary(self, generator, mock_llm):
        """Test fallback generates basic summary without LLM."""
        # Mock LLM error to trigger fallback
        generator.llm.achat = AsyncMock(side_effect=Exception("LLM error"))

        # Generate insights
        subscriptions = [
            {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
            {"merchant": "Spotify", "amount": 10.99, "cadence": "monthly"},
            {"merchant": "Gym", "amount": 40.00, "cadence": "monthly"},
        ]
        result = await generator.generate(subscriptions)

        # Verify basic summary
        assert "66.98" in result.summary  # Total cost
        assert len(result.top_subscriptions) == 3
        assert result.recommendations == []  # No recommendations without LLM

    @pytest.mark.asyncio
    async def test_empty_subscriptions_returns_empty_insights(self, generator):
        """Test that empty subscriptions list raises ValueError."""
        with pytest.raises(ValueError, match="subscriptions cannot be empty"):
            await generator.generate([])

    @pytest.mark.asyncio
    async def test_top_subscriptions_limited_to_5(self, generator, mock_llm):
        """Test that only top 5 subscriptions are returned."""
        # Mock LLM response with 5 subscriptions
        mock_response = MagicMock()
        mock_response.structured = SubscriptionInsights(
            summary="Test",
            top_subscriptions=[
                {"merchant": f"Sub{i}", "amount": 10.0 + i, "cadence": "monthly"} for i in range(5)
            ],
            recommendations=[],
            total_monthly_cost=70.0,
            potential_savings=0.0,
        )
        generator.llm.achat = AsyncMock(return_value=mock_response)

        # 10 subscriptions
        subscriptions = [
            {"merchant": f"Sub{i}", "amount": 10.0 + i, "cadence": "monthly"} for i in range(10)
        ]

        result = await generator.generate(subscriptions)

        # Verify only 5 returned
        assert len(result.top_subscriptions) <= 5

    @pytest.mark.asyncio
    async def test_budget_tracking(self, generator, mock_llm):
        """Test budget tracking increments after LLM calls."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = SubscriptionInsights(
            summary="Test",
            top_subscriptions=[],
            recommendations=[],
            total_monthly_cost=0.0,
            potential_savings=0.0,
        )
        generator.llm.achat = AsyncMock(return_value=mock_response)

        # Initial budget
        assert generator._daily_cost == 0.0
        assert generator._monthly_cost == 0.0

        # Generate insights
        await generator.generate([{"merchant": "Test", "amount": 10.0, "cadence": "monthly"}])

        # Verify budget increased
        assert generator._daily_cost == 0.0002  # Google Gemini cost per generation
        assert generator._monthly_cost == 0.0002

    @pytest.mark.asyncio
    async def test_budget_exceeded_returns_fallback(self, generator, mock_llm):
        """Test that exceeding budget triggers fallback without LLM call."""
        # Set budget exceeded flag
        generator._budget_exceeded = True

        # Generate insights
        subscriptions = [{"merchant": "Test", "amount": 10.0, "cadence": "monthly"}]
        result = await generator.generate(subscriptions)

        # Verify LLM was NOT called
        generator.llm.achat.assert_not_called()

        # Verify fallback was used
        assert len(result.recommendations) == 0  # No LLM recommendations

    def test_reset_daily_budget(self, generator):
        """Test daily budget reset."""
        # Set some costs
        generator._daily_cost = 0.05
        generator._budget_exceeded = True

        # Reset daily budget
        generator.reset_daily_budget()

        # Verify reset
        assert generator._daily_cost == 0.0
        assert generator._budget_exceeded is False

    def test_get_budget_status(self, generator):
        """Test budget status reporting."""
        # Set some costs
        generator._daily_cost = 0.05
        generator._monthly_cost = 1.0
        generator.max_cost_per_day = 0.10
        generator.max_cost_per_month = 2.00

        # Get status
        status = generator.get_budget_status()

        # Verify status
        assert status["daily_cost"] == 0.05
        assert status["daily_limit"] == 0.10
        assert status["daily_remaining"] == 0.05
        assert status["monthly_cost"] == 1.0
        assert status["monthly_limit"] == 2.00
        assert status["monthly_remaining"] == 1.0
        assert status["exceeded"] is False
