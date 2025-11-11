"""
Integration tests for recurring detection with LLM enhancement.

Tests end-to-end pipeline with LLM enabled/disabled.
Note: LLM components are tested in detail in unit tests (test_recurring_normalizers.py,
test_recurring_detectors_llm.py, test_recurring_insights.py). These integration tests
focus on the integration of components and the enable_llm flag behavior.
"""

from datetime import datetime, timedelta

import pytest

from fin_infra.recurring.ease import easy_recurring_detection


class TestLLMDisabled:
    """Test recurring detection with LLM disabled (V1 behavior)."""

    @pytest.fixture
    def detector_v1(self):
        """Create detector with LLM disabled."""
        return easy_recurring_detection(
            enable_llm=False,  # V1 behavior
            min_occurrences=3,
            amount_tolerance=0.10,
            date_tolerance_days=3,
        )

    def test_v1_no_llm_components(self, detector_v1):
        """Test that V1 detector has no LLM components."""
        # Verify LLM components are None
        assert detector_v1.detector.merchant_normalizer is None
        assert detector_v1.detector.variable_detector_llm is None
        assert detector_v1.insights_generator is None

    @pytest.mark.asyncio
    async def test_v1_detect_simple_recurring_pattern(self, detector_v1):
        """Test V1 detects simple recurring pattern without LLM."""
        # Create simple recurring transactions
        base_date = datetime(2024, 1, 15)
        transactions = [
            {
                "id": f"txn{i}",
                "merchant": "netflix",
                "amount": 15.99,
                "date": base_date + timedelta(days=30 * i),
            }
            for i in range(4)
        ]

        # Detect patterns (no LLM calls)
        patterns = detector_v1.detect_patterns(transactions)

        # Verify pattern detected
        assert len(patterns) > 0
        netflix_pattern = next((p for p in patterns if "netflix" in p.merchant_name.lower()), None)
        assert netflix_pattern is not None
        assert netflix_pattern.cadence == "monthly"
        assert abs(netflix_pattern.amount - 15.99) < 0.01
        assert netflix_pattern.occurrence_count >= 4


class TestLLMEnabled:
    """Test recurring detection with LLM enabled (V2 behavior)."""

    def test_v2_initialization_requires_ai_infra(self):
        """Test that V2 initialization requires ai-infra package."""
        try:
            detector_v2 = easy_recurring_detection(
                enable_llm=True,  # V2 behavior
                llm_provider="google",
                llm_model="gemini-2.0-flash-exp",
                min_occurrences=3,
            )
            # If ai-infra is available, check components exist
            assert detector_v2.detector.merchant_normalizer is not None
            assert detector_v2.detector.variable_detector_llm is not None
            assert detector_v2.insights_generator is not None
        except ImportError as e:
            # If ai-infra not available, that's expected
            assert "ai_infra" in str(e)
            pytest.skip("ai-infra not installed, skipping LLM enabled test")


class TestParameterValidation:
    """Test parameter validation for LLM enhancement."""

    def test_invalid_llm_provider_raises_error(self):
        """Test that invalid LLM provider raises ValueError."""
        with pytest.raises(ValueError, match="llm_provider must be"):
            easy_recurring_detection(
                enable_llm=True,
                llm_provider="invalid_provider",
            )

    def test_invalid_confidence_threshold_raises_error(self):
        """Test that invalid confidence threshold raises ValueError."""
        with pytest.raises(ValueError, match="llm_confidence_threshold must be between"):
            easy_recurring_detection(
                enable_llm=True,
                llm_confidence_threshold=1.5,  # Invalid (> 1.0)
            )

    def test_negative_budget_raises_error(self):
        """Test that negative budget raises ValueError."""
        with pytest.raises(ValueError, match="llm_max_cost_per_day must be >= 0"):
            easy_recurring_detection(
                enable_llm=True,
                llm_max_cost_per_day=-0.10,  # Invalid (negative)
            )

    def test_negative_cache_ttl_raises_error(self):
        """Test that negative cache TTL raises ValueError."""
        with pytest.raises(ValueError, match="llm_cache_merchant_ttl must be >= 0"):
            easy_recurring_detection(
                enable_llm=True,
                llm_cache_merchant_ttl=-100,  # Invalid (negative)
            )


class TestBackwardCompatibility:
    """Test backward compatibility with V1."""

    def test_default_is_v1_behavior(self):
        """Test that default behavior is V1 (LLM disabled)."""
        detector = easy_recurring_detection()

        # Should have no LLM components (V1 behavior)
        assert detector.detector.merchant_normalizer is None
        assert detector.detector.variable_detector_llm is None
        assert detector.insights_generator is None

    def test_v1_parameters_still_work(self):
        """Test that V1 parameters still work."""
        detector = easy_recurring_detection(
            min_occurrences=2,
            amount_tolerance=0.15,
            date_tolerance_days=5,
        )

        # Verify V1 parameters are set
        assert detector.detector.min_occurrences == 2
        assert detector.detector.amount_tolerance == 0.15
        assert detector.detector.date_tolerance_days == 5
