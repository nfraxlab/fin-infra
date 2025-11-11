"""
Unit tests for recurring/normalizers.py (Layer 2 - LLM merchant normalization).

Tests merchant name normalization with mocked CoreLLM responses.
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fin_infra.recurring.normalizers import (
    MerchantNormalized,
    MerchantNormalizer,
    MERCHANT_NORMALIZATION_SYSTEM_PROMPT,
)


class TestMerchantNormalized:
    """Test MerchantNormalized Pydantic model."""

    def test_valid_model(self):
        """Test valid MerchantNormalized creation."""
        result = MerchantNormalized(
            canonical_name="Netflix",
            merchant_type="streaming",
            confidence=0.95,
            reasoning="NFLX is Netflix subscription prefix",
        )

        assert result.canonical_name == "Netflix"
        assert result.merchant_type == "streaming"
        assert result.confidence == 0.95
        assert result.reasoning == "NFLX is Netflix subscription prefix"

    def test_confidence_validation(self):
        """Test confidence must be between 0.0 and 1.0."""
        # Valid confidence
        MerchantNormalized(
            canonical_name="Netflix",
            merchant_type="streaming",
            confidence=0.8,
            reasoning="test",
        )

        # Invalid confidence (too high)
        with pytest.raises(ValueError):
            MerchantNormalized(
                canonical_name="Netflix",
                merchant_type="streaming",
                confidence=1.5,
                reasoning="test",
            )

        # Invalid confidence (negative)
        with pytest.raises(ValueError):
            MerchantNormalized(
                canonical_name="Netflix",
                merchant_type="streaming",
                confidence=-0.1,
                reasoning="test",
            )


class TestMerchantNormalizer:
    """Test MerchantNormalizer with mocked CoreLLM."""

    @pytest.fixture
    def mock_llm(self):
        """Mock CoreLLM for testing."""
        with patch("fin_infra.recurring.normalizers.CoreLLM") as mock:
            yield mock

    @pytest.fixture
    def normalizer(self, mock_llm):
        """Create MerchantNormalizer with mocked dependencies."""
        return MerchantNormalizer(
            provider="google",
            model_name="gemini-2.0-flash-exp",
            cache_ttl=604800,  # 7 days
            enable_cache=False,  # Disable cache for unit tests
            confidence_threshold=0.8,
        )

    @pytest.mark.asyncio
    async def test_normalize_cryptic_merchant_name(self, normalizer, mock_llm):
        """Test normalization of cryptic merchant names (NFLX*SUB → Netflix)."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Netflix",
            merchant_type="streaming",
            confidence=0.95,
            reasoning="NFLX is Netflix subscription prefix",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Normalize cryptic name
        result = await normalizer.normalize("NFLX*SUB #12345")

        # Verify result
        assert result.canonical_name == "Netflix"
        assert result.merchant_type == "streaming"
        assert result.confidence == 0.95
        assert "NFLX" in result.reasoning

        # Verify LLM was called with correct parameters
        normalizer.llm.achat.assert_called_once()
        call_args = normalizer.llm.achat.call_args
        assert call_args.kwargs["provider"] == "google"
        assert call_args.kwargs["model"] == "gemini-2.0-flash-exp"
        assert call_args.kwargs["output_schema"] == MerchantNormalized
        assert call_args.kwargs["output_method"] == "prompt"
        assert call_args.kwargs["temperature"] == 0.0

        # Verify prompt contains system and user messages
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == MERCHANT_NORMALIZATION_SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert "NFLX*SUB #12345" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_normalize_payment_processor_prefix(self, normalizer, mock_llm):
        """Test normalization of payment processor prefixes (SQ *CAFE → Cozy Cafe)."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Cozy Cafe",
            merchant_type="coffee_shop",
            confidence=0.92,
            reasoning="SQ is Square payment processor, actual merchant is Cozy Cafe",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Normalize Square transaction
        result = await normalizer.normalize("SQ *COZY CAFE")

        # Verify result
        assert result.canonical_name == "Cozy Cafe"
        assert result.merchant_type == "coffee_shop"
        assert result.confidence == 0.92
        assert "Square" in result.reasoning or "SQ" in result.reasoning

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_hit(self, normalizer, mock_llm, mock_cache):
        """Test that cached results are returned without calling LLM."""
        # Mock cache hit
        cached_result = {
            "canonical_name": "Netflix",
            "merchant_type": "streaming",
            "confidence": 0.95,
            "reasoning": "Cached result",
        }
        mock_cache.get = AsyncMock(return_value=cached_result)

        # Normalize merchant (should use cache)
        result = await normalizer.normalize("NFLX*SUB")

        # Verify cache was checked
        mock_cache.get.assert_called_once()

        # Verify LLM was NOT called
        normalizer.llm.achat.assert_not_called()

        # Verify result from cache
        assert result.canonical_name == "Netflix"
        assert result.merchant_type == "streaming"
        assert result.confidence == 0.95
        assert result.reasoning == "Cached result"

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_miss_calls_llm_and_caches_result(self, normalizer, mock_llm, mock_cache):
        """Test that cache miss triggers LLM call and caches the result."""
        # Mock cache miss
        mock_cache.get = AsyncMock(return_value=None)

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Starbucks",
            merchant_type="coffee_shop",
            confidence=0.93,
            reasoning="TST is Toast POS system, merchant is Starbucks",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Normalize merchant
        result = await normalizer.normalize("TST* STARBUCKS")

        # Verify cache was checked
        mock_cache.get.assert_called_once()

        # Verify LLM was called
        normalizer.llm.achat.assert_called_once()

        # Verify result was cached
        mock_cache.set.assert_called_once()
        cache_call = mock_cache.set.call_args
        assert cache_call.kwargs["ttl"] == 604800  # 7 days

        # Verify cache key format
        cache_key_arg = cache_call.args[0]
        assert cache_key_arg.startswith("merchant_norm:")

        # Verify result
        assert result.canonical_name == "Starbucks"
        assert result.merchant_type == "coffee_shop"

    @pytest.mark.skip(reason="Cache tests require svc-infra cache integration (test in acceptance)")
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, normalizer):
        """Test cache key generation uses MD5 hash of lowercase merchant name."""
        merchant_name = "NFLX*SUB #12345"
        cache_key = normalizer._make_cache_key(merchant_name)

        # Verify format
        assert cache_key.startswith("merchant_norm:")

        # Verify uses lowercase
        normalized = merchant_name.lower().strip()
        expected_hash = hashlib.md5(normalized.encode()).hexdigest()
        assert cache_key == f"merchant_norm:{expected_hash}"

        # Verify case-insensitive (same key for different cases)
        key1 = normalizer._make_cache_key("Netflix")
        key2 = normalizer._make_cache_key("NETFLIX")
        key3 = normalizer._make_cache_key("netflix")
        assert key1 == key2 == key3

    @pytest.mark.asyncio
    async def test_fallback_when_confidence_below_threshold(self, normalizer, mock_llm):
        """Test fallback to basic normalization when LLM confidence < threshold."""
        # Mock LLM response with low confidence
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Unknown Merchant",
            merchant_type="unknown",
            confidence=0.5,  # Below 0.8 threshold
            reasoning="Unable to identify merchant",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Normalize merchant
        result = await normalizer.normalize("XYZ*UNKNOWN")

        # Verify fallback was used
        assert result.confidence == 0.5  # Fallback confidence
        assert result.reasoning == "Fallback normalization (LLM unavailable)"
        assert result.merchant_type == "unknown"

    @pytest.mark.asyncio
    async def test_fallback_when_llm_error(self, normalizer, mock_llm):
        """Test fallback to basic normalization when LLM raises error."""
        # Mock LLM error
        normalizer.llm.achat = AsyncMock(side_effect=Exception("LLM timeout"))

        # Normalize merchant (should use fallback)
        result = await normalizer.normalize("NFLX*SUB")

        # Verify fallback was used
        assert result.confidence == 0.5
        assert "Fallback normalization" in result.reasoning
        assert result.canonical_name == "Nflx Sub"  # Basic preprocessing

    @pytest.mark.asyncio
    async def test_fallback_preprocessing_removes_prefixes(self, normalizer, mock_llm):
        """Test fallback preprocessing removes payment processor prefixes."""
        # Mock LLM error to trigger fallback
        normalizer.llm.achat = AsyncMock(side_effect=Exception("LLM error"))

        # Test SQ * prefix removal
        result = await normalizer.normalize("SQ *COZY CAFE")
        assert "cozy cafe" in result.canonical_name.lower()
        assert "sq" not in result.canonical_name.lower()

        # Test TST* prefix removal
        result = await normalizer.normalize("TST* STARBUCKS")
        assert "starbucks" in result.canonical_name.lower()
        assert "tst" not in result.canonical_name.lower()

    @pytest.mark.asyncio
    async def test_fallback_preprocessing_removes_store_numbers(self, normalizer, mock_llm):
        """Test fallback preprocessing removes store numbers."""
        # Mock LLM error to trigger fallback
        normalizer.llm.achat = AsyncMock(side_effect=Exception("LLM error"))

        # Test store number removal
        result = await normalizer.normalize("STARBUCKS #1234")
        assert "starbucks" in result.canonical_name.lower()
        assert "1234" not in result.canonical_name

    @pytest.mark.asyncio
    async def test_fallback_preprocessing_removes_legal_entities(self, normalizer, mock_llm):
        """Test fallback preprocessing removes legal entities (Inc, LLC, Corp)."""
        # Mock LLM error to trigger fallback
        normalizer.llm.achat = AsyncMock(side_effect=Exception("LLM error"))

        # Test Inc removal
        result = await normalizer.normalize("Netflix Inc")
        assert "netflix" in result.canonical_name.lower()
        assert "inc" not in result.canonical_name.lower()

        # Test LLC removal
        result = await normalizer.normalize("Amazon LLC")
        assert "amazon" in result.canonical_name.lower()
        assert "llc" not in result.canonical_name.lower()

    @pytest.mark.asyncio
    async def test_budget_tracking(self, normalizer, mock_llm):
        """Test budget tracking increments after LLM calls."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Netflix",
            merchant_type="streaming",
            confidence=0.95,
            reasoning="test",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Initial budget
        assert normalizer._daily_cost == 0.0
        assert normalizer._monthly_cost == 0.0

        # Call normalize
        await normalizer.normalize("NFLX*SUB")

        # Verify budget increased
        assert normalizer._daily_cost == 0.00008  # Google Gemini cost per request
        assert normalizer._monthly_cost == 0.00008

        # Call again
        await normalizer.normalize("SPFY*PREMIUM")

        # Verify budget doubled
        assert normalizer._daily_cost == 0.00016
        assert normalizer._monthly_cost == 0.00016

    @pytest.mark.asyncio
    async def test_budget_exceeded_returns_fallback(self, normalizer, mock_llm):
        """Test that exceeding budget triggers fallback without LLM call."""
        # Set budget exceeded flag
        normalizer._budget_exceeded = True

        # Try to normalize
        result = await normalizer.normalize("NFLX*SUB")

        # Verify LLM was NOT called
        normalizer.llm.achat.assert_not_called()

        # Verify fallback was used
        assert result.confidence == 0.5
        assert "Fallback normalization" in result.reasoning

    @pytest.mark.asyncio
    async def test_budget_exceeded_when_daily_limit_hit(self, normalizer, mock_llm):
        """Test budget exceeded flag set when daily limit is hit."""
        # Set daily cost very close to limit (one call away)
        normalizer._daily_cost = 0.09999  # Just below $0.10 limit (normalize() adds $0.0001)
        normalizer.max_cost_per_day = 0.10

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Netflix",
            merchant_type="streaming",
            confidence=0.95,
            reasoning="test",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Make request that pushes over limit (0.09999 + 0.0001 = 0.10009 > 0.10)
        await normalizer.normalize("NFLX*SUB")

        # Verify budget exceeded flag is set
        assert normalizer._budget_exceeded is True
        assert normalizer._daily_cost > normalizer.max_cost_per_day

    def test_reset_daily_budget(self, normalizer):
        """Test daily budget reset."""
        # Set some costs
        normalizer._daily_cost = 0.05
        normalizer._budget_exceeded = True

        # Reset daily budget
        normalizer.reset_daily_budget()

        # Verify reset
        assert normalizer._daily_cost == 0.0
        assert normalizer._budget_exceeded is False

        # Monthly cost should NOT be reset
        normalizer._monthly_cost = 1.0
        normalizer.reset_daily_budget()
        assert normalizer._monthly_cost == 1.0

    def test_reset_monthly_budget(self, normalizer):
        """Test monthly budget reset."""
        # Set some costs
        normalizer._monthly_cost = 1.5
        normalizer._budget_exceeded = True

        # Reset monthly budget
        normalizer.reset_monthly_budget()

        # Verify reset
        assert normalizer._monthly_cost == 0.0
        assert normalizer._budget_exceeded is False

    def test_get_budget_status(self, normalizer):
        """Test budget status reporting."""
        # Set some costs
        normalizer._daily_cost = 0.05
        normalizer._monthly_cost = 1.0
        normalizer.max_cost_per_day = 0.10
        normalizer.max_cost_per_month = 2.00

        # Get status
        status = normalizer.get_budget_status()

        # Verify status
        assert status["daily_cost"] == 0.05
        assert status["daily_limit"] == 0.10
        assert status["daily_remaining"] == 0.05
        assert status["monthly_cost"] == 1.0
        assert status["monthly_limit"] == 2.00
        assert status["monthly_remaining"] == 1.0
        assert status["exceeded"] is False

    @pytest.mark.asyncio
    async def test_empty_merchant_name_raises_error(self, normalizer):
        """Test that empty merchant name raises ValueError."""
        with pytest.raises(ValueError, match="merchant_name cannot be empty"):
            await normalizer.normalize("")

        with pytest.raises(ValueError, match="merchant_name cannot be empty"):
            await normalizer.normalize("   ")

    @pytest.mark.asyncio
    async def test_normalize_strips_whitespace(self, normalizer, mock_llm):
        """Test that merchant name is stripped of leading/trailing whitespace."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = MerchantNormalized(
            canonical_name="Netflix",
            merchant_type="streaming",
            confidence=0.95,
            reasoning="test",
        )
        normalizer.llm.achat = AsyncMock(return_value=mock_response)

        # Normalize with whitespace
        await normalizer.normalize("  NFLX*SUB  ")

        # Verify LLM received stripped name
        call_args = normalizer.llm.achat.call_args
        user_message = call_args.kwargs["messages"][1]["content"]
        assert "NFLX*SUB" in user_message
        assert "  NFLX*SUB  " not in user_message
