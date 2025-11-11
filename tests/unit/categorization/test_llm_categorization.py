"""
Unit tests for LLM-based categorization (Layer 4).

Tests LLMCategorizer with mocked ai-infra responses:
- Basic categorization with structured output
- Retry logic with transient failures
- Budget tracking and cost enforcement
- Graceful fallback to sklearn when LLM fails
- Hybrid flow (exact → regex → sklearn → LLM)
"""

import pytest
from unittest.mock import AsyncMock, patch

from fin_infra.categorization import Category, CategorizationEngine, CategorizationMethod

# LLM layer (skip tests if not available)
try:
    from fin_infra.categorization.llm_layer import LLMCategorizer, CategoryPrediction

    HAS_LLM = True
except ImportError:
    HAS_LLM = False

pytestmark = pytest.mark.skipif(not HAS_LLM, reason="LLM support requires ai-infra package")


@pytest.fixture
def mock_llm_response():
    """Mock LLM response with CategoryPrediction."""
    return CategoryPrediction(
        category="Coffee Shops",
        confidence=0.92,
        reasoning="Starbucks is a well-known coffee chain",
    )


@pytest.fixture
def mock_core_llm():
    """Mock ai-infra CoreLLM."""
    with patch("fin_infra.categorization.llm_layer.CoreLLM") as mock:
        yield mock


class TestLLMCategorizerBasic:
    """Test basic LLMCategorizer functionality."""

    @pytest.mark.asyncio
    async def test_llm_categorizer_basic(self, mock_core_llm, mock_llm_response):
        """Test basic LLM categorization with mocked response."""
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.achat.return_value = mock_llm_response
        mock_core_llm.return_value = mock_instance

        # Create categorizer
        categorizer = LLMCategorizer(
            provider="google_genai",
            model_name="gemini-2.0-flash-exp",
        )

        # Categorize
        result = await categorizer.categorize("Starbucks", user_id="user123")

        # Verify
        assert result.category == "Coffee Shops"
        assert result.confidence == 0.92
        assert "coffee" in result.reasoning.lower()
        assert categorizer.daily_cost > 0  # Cost tracked

    @pytest.mark.asyncio
    async def test_llm_structured_output(self, mock_core_llm, mock_llm_response):
        """Test that LLM uses structured output with Pydantic schema."""
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.achat.return_value = mock_llm_response
        mock_core_llm.return_value = mock_instance

        # Create categorizer
        categorizer = LLMCategorizer(provider="openai", model_name="gpt-4o-mini")

        # Categorize
        await categorizer.categorize("Amazon", user_id="user123")

        # Verify CoreLLM.achat called with structured output
        mock_instance.achat.assert_called_once()
        call_kwargs = mock_instance.achat.call_args.kwargs
        assert call_kwargs["output_schema"] == CategoryPrediction
        assert call_kwargs["output_method"] == "prompt"


class TestLLMRetryLogic:
    """Test LLM retry logic with transient failures."""

    @pytest.mark.asyncio
    async def test_llm_retry_on_transient_failure(self, mock_core_llm, mock_llm_response):
        """
        Test that LLM retries on transient failures.

        NOTE: Retry logic is handled by ai-infra CoreLLM, not LLMCategorizer.
        This test verifies that CoreLLM.achat is called with retry config.
        """
        # Setup mock: succeed immediately (CoreLLM handles retries internally)
        mock_instance = AsyncMock()
        mock_instance.achat.return_value = mock_llm_response
        mock_core_llm.return_value = mock_instance

        # Create categorizer
        categorizer = LLMCategorizer(provider="anthropic", model_name="claude-3-5-haiku-20241022")

        # Categorize (should succeed)
        result = await categorizer.categorize("Walmart", user_id="user123")

        # Verify retry config passed to CoreLLM.achat
        call_kwargs = mock_instance.achat.call_args.kwargs
        assert "extra" in call_kwargs
        assert "retry" in call_kwargs["extra"]
        assert call_kwargs["extra"]["retry"]["max_tries"] == 3
        assert result.category == "Coffee Shops"  # Mock response

    @pytest.mark.asyncio
    async def test_llm_fail_after_max_retries(self, mock_core_llm):
        """Test that LLM raises exception when CoreLLM fails after retries."""
        # Setup mock: always fail (CoreLLM already tried retries)
        mock_instance = AsyncMock()
        mock_instance.achat.side_effect = Exception("Persistent failure")
        mock_core_llm.return_value = mock_instance

        # Create categorizer
        categorizer = LLMCategorizer(provider="google_genai", model_name="gemini-2.0-flash-exp")

        # Categorize should raise exception
        with pytest.raises(Exception, match="Persistent failure"):
            await categorizer.categorize("Unknown Merchant", user_id="user123")


class TestLLMBudgetTracking:
    """Test LLM cost tracking and budget enforcement."""

    @pytest.mark.asyncio
    async def test_llm_cost_tracking(self, mock_core_llm, mock_llm_response):
        """Test that LLM tracks costs per request."""
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.achat.return_value = mock_llm_response
        mock_core_llm.return_value = mock_instance

        # Create categorizer
        categorizer = LLMCategorizer(provider="google_genai", model_name="gemini-2.0-flash-exp")

        # Initial costs should be zero
        assert categorizer.daily_cost == 0
        assert categorizer.monthly_cost == 0

        # Categorize (costs should increase)
        await categorizer.categorize("Target", user_id="user123")
        assert categorizer.daily_cost > 0
        assert categorizer.monthly_cost > 0

        # Second request should accumulate
        first_daily = categorizer.daily_cost
        await categorizer.categorize("Whole Foods", user_id="user123")
        assert categorizer.daily_cost > first_daily

    @pytest.mark.asyncio
    async def test_llm_daily_budget_exceeded(self, mock_core_llm, mock_llm_response):
        """Test that LLM raises exception when daily budget exceeded."""
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.achat.return_value = mock_llm_response
        mock_core_llm.return_value = mock_instance

        # Create categorizer with low daily budget
        categorizer = LLMCategorizer(
            provider="google_genai",
            model_name="gemini-2.0-flash-exp",
            max_cost_per_day=0.0001,  # Very low budget
        )

        # First request should succeed
        await categorizer.categorize("Starbucks", user_id="user123")

        # Manually exceed budget
        categorizer.daily_cost = 0.0002

        # Second request should fail with RuntimeError
        with pytest.raises(RuntimeError, match="LLM budget exceeded"):
            await categorizer.categorize("Another Merchant", user_id="user123")

    @pytest.mark.asyncio
    async def test_llm_monthly_budget_exceeded(self, mock_core_llm, mock_llm_response):
        """Test that LLM raises exception when monthly budget exceeded."""
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.achat.return_value = mock_llm_response
        mock_core_llm.return_value = mock_instance

        # Create categorizer with low monthly budget
        categorizer = LLMCategorizer(
            provider="google_genai",
            model_name="gemini-2.0-flash-exp",
            max_cost_per_month=0.0005,  # Very low budget
        )

        # Manually exceed budget
        categorizer.monthly_cost = 0.0006

        # Request should fail with RuntimeError
        with pytest.raises(RuntimeError, match="LLM budget exceeded"):
            await categorizer.categorize("Merchant", user_id="user123")

    def test_llm_cost_reset_daily(self):
        """Test that daily cost can be reset."""
        categorizer = LLMCategorizer(provider="google_genai", model_name="gemini-2.0-flash-exp")
        categorizer.daily_cost = 0.05
        categorizer.monthly_cost = 0.10

        categorizer.reset_daily_cost()

        assert categorizer.daily_cost == 0
        assert categorizer.monthly_cost == 0.10  # Monthly not reset

    def test_llm_cost_reset_monthly(self):
        """Test that monthly cost can be reset."""
        categorizer = LLMCategorizer(provider="google_genai", model_name="gemini-2.0-flash-exp")
        categorizer.daily_cost = 0.05
        categorizer.monthly_cost = 0.50

        categorizer.reset_monthly_cost()

        assert categorizer.daily_cost == 0.05  # Daily not reset
        assert categorizer.monthly_cost == 0


class TestHybridWithLLM:
    """Test hybrid categorization with LLM fallback (Layer 4)."""

    @pytest.mark.asyncio
    async def test_hybrid_exact_match_skip_llm(self):
        """Test that exact match skips LLM."""
        # Create engine with LLM (but exact match should win)
        with patch("fin_infra.categorization.llm_layer.CoreLLM") as mock_llm:
            mock_instance = AsyncMock()
            mock_llm.return_value = mock_instance

            categorizer_llm = LLMCategorizer(
                provider="google_genai", model_name="gemini-2.0-flash-exp"
            )
            engine = CategorizationEngine(
                enable_ml=False,
                enable_llm=True,
                llm_categorizer=categorizer_llm,
            )

            # Categorize exact match
            result = await engine.categorize("STARBUCKS")

            # Verify exact match used, LLM not called
            assert result.method == CategorizationMethod.EXACT
            assert result.category == Category.VAR_COFFEE_SHOPS
            assert result.confidence == 1.0
            mock_instance.achat.assert_not_called()

    @pytest.mark.asyncio
    async def test_hybrid_regex_match_skip_llm(self):
        """Test that regex match skips LLM."""
        with patch("fin_infra.categorization.llm_layer.CoreLLM") as mock_llm:
            mock_instance = AsyncMock()
            mock_llm.return_value = mock_instance

            categorizer_llm = LLMCategorizer(
                provider="google_genai", model_name="gemini-2.0-flash-exp"
            )
            engine = CategorizationEngine(
                enable_ml=False,
                enable_llm=True,
                llm_categorizer=categorizer_llm,
            )

            # Categorize regex match
            result = await engine.categorize("Uber Trip #12345")

            # Verify regex match used, LLM not called
            assert result.method == CategorizationMethod.REGEX
            assert result.confidence >= 0.7
            mock_instance.achat.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_fallback_when_sklearn_low_confidence(self, mock_llm_response):
        """Test that LLM is called when sklearn confidence < threshold."""
        # Mock sklearn prediction with low confidence
        with patch("fin_infra.categorization.llm_layer.CoreLLM") as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.achat.return_value = mock_llm_response
            mock_llm.return_value = mock_instance

            categorizer_llm = LLMCategorizer(
                provider="google_genai", model_name="gemini-2.0-flash-exp"
            )
            engine = CategorizationEngine(
                enable_ml=True,
                enable_llm=True,
                confidence_threshold=0.6,
                llm_categorizer=categorizer_llm,
            )

            # Mock sklearn to return low confidence
            with patch.object(engine, "_predict_ml") as mock_ml:
                from fin_infra.categorization.models import CategoryPrediction

                mock_ml.return_value = CategoryPrediction(
                    merchant_name="Unknown Coffee",
                    normalized_name="unknown coffee",
                    category=Category.UNCATEGORIZED,
                    confidence=0.45,  # Below threshold
                    method=CategorizationMethod.ML,
                    alternatives=[],
                )

                # Categorize
                result = await engine.categorize("Unknown Coffee Shop")

                # Verify LLM was called
                mock_instance.achat.assert_called_once()
                assert result.method == CategorizationMethod.LLM
                assert result.confidence == 0.92  # From mock_llm_response

    @pytest.mark.asyncio
    async def test_llm_fallback_to_sklearn_on_exception(self):
        """Test that sklearn prediction is used when LLM fails."""
        with patch("fin_infra.categorization.llm_layer.CoreLLM") as mock_llm:
            # LLM always fails
            mock_instance = AsyncMock()
            mock_instance.achat.side_effect = Exception("LLM API error")
            mock_llm.return_value = mock_instance

            categorizer_llm = LLMCategorizer(
                provider="google_genai", model_name="gemini-2.0-flash-exp"
            )
            engine = CategorizationEngine(
                enable_ml=True,
                enable_llm=True,
                confidence_threshold=0.6,
                llm_categorizer=categorizer_llm,
            )

            # Mock sklearn to return low confidence
            with patch.object(engine, "_predict_ml") as mock_ml:
                from fin_infra.categorization.models import CategoryPrediction

                sklearn_prediction = CategoryPrediction(
                    merchant_name="Unknown Store",
                    normalized_name="unknown store",
                    category=Category.VAR_SHOPPING_GENERAL,  # Correct enum name
                    confidence=0.50,  # Low but exists
                    method=CategorizationMethod.ML,
                    alternatives=[],
                )
                mock_ml.return_value = sklearn_prediction

                # Categorize
                result = await engine.categorize("Unknown Store")

                # Verify sklearn prediction used as fallback
                assert result.method == CategorizationMethod.ML
                assert result.category == Category.VAR_SHOPPING_GENERAL
                assert result.confidence == 0.50

    @pytest.mark.asyncio
    async def test_hybrid_stats_tracking(self, mock_llm_response):
        """Test that stats track LLM predictions."""
        with patch("fin_infra.categorization.llm_layer.CoreLLM") as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.achat.return_value = mock_llm_response
            mock_llm.return_value = mock_instance

            categorizer_llm = LLMCategorizer(
                provider="google_genai", model_name="gemini-2.0-flash-exp"
            )
            engine = CategorizationEngine(
                enable_ml=True,
                enable_llm=True,
                confidence_threshold=0.6,
                llm_categorizer=categorizer_llm,
            )

            # Mock sklearn to return low confidence
            with patch.object(engine, "_predict_ml") as mock_ml:
                from fin_infra.categorization.models import CategoryPrediction

                mock_ml.return_value = CategoryPrediction(
                    merchant_name="Test",
                    normalized_name="test",
                    category=Category.UNCATEGORIZED,
                    confidence=0.40,
                    method=CategorizationMethod.ML,
                    alternatives=[],
                )

                # Categorize
                await engine.categorize("Test Merchant")

                # Verify stats
                assert engine.stats["llm_predictions"] == 1
                assert engine.stats["exact_matches"] == 0
                assert engine.stats["regex_matches"] == 0
