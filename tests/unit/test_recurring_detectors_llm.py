"""
Unit tests for recurring/detectors_llm.py (Layer 4 - LLM variable amount detection).

Tests variable recurring pattern detection with mocked LLM responses.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fin_infra.recurring.detectors_llm import (
    VariableDetectorLLM,
    VariableRecurringPattern,
    VARIABLE_DETECTION_SYSTEM_PROMPT,
)


class TestVariableRecurringPattern:
    """Test VariableRecurringPattern Pydantic model."""

    def test_valid_model_recurring(self):
        """Test valid VariableRecurringPattern for recurring pattern."""
        result = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(45.0, 55.0),  # Tuple of floats, not string
            reasoning="Seasonal winter heating variation",
            confidence=0.88,
        )

        assert result.is_recurring is True
        assert result.cadence == "monthly"
        assert result.expected_range == (45.0, 55.0)
        assert result.reasoning == "Seasonal winter heating variation"
        assert result.confidence == 0.88

    def test_valid_model_not_recurring(self):
        """Test valid VariableRecurringPattern for non-recurring pattern."""
        result = VariableRecurringPattern(
            is_recurring=False,
            cadence=None,
            expected_range=None,
            reasoning="Too much variance, no seasonal pattern",
            confidence=0.75,
        )

        assert result.is_recurring is False
        assert result.cadence is None
        assert result.expected_range is None
        assert "variance" in result.reasoning
        assert result.confidence == 0.75

    def test_confidence_validation(self):
        """Test confidence must be between 0.0 and 1.0."""
        # Valid confidence
        VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(50.0, 50.0),  # Tuple of floats
            reasoning="test",
            confidence=0.8,
        )

        # Invalid confidence (too high)
        with pytest.raises(ValueError):
            VariableRecurringPattern(
                is_recurring=True,
                cadence="monthly",
                expected_range=(50.0, 50.0),  # Tuple of floats
                reasoning="test",
                confidence=1.5,
            )


class TestVariableDetectorLLM:
    """Test VariableDetectorLLM with mocked LLM."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        with patch("fin_infra.recurring.detectors_llm.LLM") as mock:
            yield mock

    @pytest.fixture
    def detector(self, mock_llm):
        """Create VariableDetectorLLM with mocked dependencies."""
        return VariableDetectorLLM(
            provider="google",
            model_name="gemini-2.0-flash-exp",
            max_cost_per_day=0.10,
            max_cost_per_month=2.00,
        )

    @pytest.mark.asyncio
    async def test_detect_seasonal_utility_bills(self, detector, mock_llm):
        """Test detection of seasonal utility bills ($45-$55 monthly)."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(45.0, 55.0),  # Tuple of floats
            reasoning="Seasonal winter heating variation causes 20% fluctuation",
            confidence=0.88,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Transaction pattern
        amounts = [45.50, 52.30, 48.75, 54.20]
        date_pattern = "Monthly (15th ±3 days)"

        # Detect pattern
        result = await detector.detect("City Electric", amounts, date_pattern)

        # Verify result
        assert result.is_recurring is True
        assert result.cadence == "monthly"
        assert result.expected_range == (45.0, 55.0)
        assert "seasonal" in result.reasoning.lower() or "winter" in result.reasoning.lower()
        assert result.confidence >= 0.85

        # Verify LLM was called with correct parameters
        detector.llm.achat.assert_called_once()
        call_args = detector.llm.achat.call_args
        assert call_args.kwargs["provider"] == "google"
        assert call_args.kwargs["model_name"] == "gemini-2.0-flash-exp"
        assert call_args.kwargs["output_schema"] == VariableRecurringPattern
        assert call_args.kwargs["temperature"] == 0.0

        # Verify prompt contains system and user messages
        assert call_args.kwargs["system"] == VARIABLE_DETECTION_SYSTEM_PROMPT
        user_msg = call_args.kwargs["user_msg"]
        assert "City Electric" in user_msg
        assert (
            "45.5" in user_msg or "52.3" in user_msg
        )  # Float amounts, not dollar strings

    @pytest.mark.asyncio
    async def test_detect_phone_overage_spikes(self, detector, mock_llm):
        """Test detection of phone bills with occasional overage spikes."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(50.0, 80.0),  # Tuple covering normal and spike range
            reasoning="Regular monthly bill with occasional overage charge spikes",
            confidence=0.86,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Transaction pattern with spike
        amounts = [50.00, 78.50, 50.00, 50.00]
        date_pattern = "Monthly (15th ±2 days)"

        # Detect pattern
        result = await detector.detect("T-Mobile", amounts, date_pattern)

        # Verify result
        assert result.is_recurring is True
        assert "spike" in result.reasoning.lower() or "overage" in result.reasoning.lower()
        assert result.confidence >= 0.80

    @pytest.mark.asyncio
    async def test_detect_random_variance_not_recurring(self, detector, mock_llm):
        """Test detection rejects random variance as not recurring."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=False,
            cadence=None,
            expected_range=None,
            reasoning="Too much variance with no seasonal or usage-based pattern",
            confidence=0.82,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Random transaction pattern
        amounts = [25.00, 150.00, 40.00, 200.00]
        date_pattern = "Monthly (15th ±10 days)"

        # Detect pattern
        result = await detector.detect("Random Store", amounts, date_pattern)

        # Verify result
        assert result.is_recurring is False
        assert result.cadence is None
        assert result.expected_range is None
        assert "variance" in result.reasoning.lower() or "random" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_detect_winter_heating_seasonal_pattern(self, detector, mock_llm):
        """Test detection of winter heating bills that double in cold months."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(45.0, 120.0),  # Tuple covering seasonal range
            reasoning="Winter heating season doubles bill from summer baseline",
            confidence=0.90,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Seasonal pattern (winter spike)
        amounts = [45.00, 120.00, 115.00, 50.00]
        date_pattern = "Monthly (15th ±5 days)"

        # Detect pattern
        result = await detector.detect("Gas Company", amounts, date_pattern)

        # Verify result
        assert result.is_recurring is True
        assert "seasonal" in result.reasoning.lower() or "winter" in result.reasoning.lower()
        assert result.confidence >= 0.85

    @pytest.mark.asyncio
    async def test_detect_gym_membership_with_annual_fee_waiver(self, detector, mock_llm):
        """Test detection of gym membership with one month waived annual fee."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(0.0, 40.0),  # Tuple covering waiver and regular fee
            reasoning="Regular membership with annual fee waived one month per year",
            confidence=0.87,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Pattern with one $0 month
        amounts = [40.00, 40.00, 0.00, 40.00]
        date_pattern = "Monthly (15th ±1 day)"

        # Detect pattern
        result = await detector.detect("Gym Membership", amounts, date_pattern)

        # Verify result
        assert result.is_recurring is True
        assert "annual" in result.reasoning.lower() or "waiv" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_budget_tracking(self, detector, mock_llm):
        """Test budget tracking increments after LLM calls."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(50.0, 50.0),  # Tuple of floats
            reasoning="test",
            confidence=0.85,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Initial budget
        assert detector._daily_cost == 0.0
        assert detector._monthly_cost == 0.0

        # Call detect
        amounts = [50.00]
        date_pattern = "Monthly (15th)"
        await detector.detect("Test", amounts, date_pattern)

        # Verify budget increased
        assert detector._daily_cost == 0.0001  # Google Gemini cost per detection
        assert detector._monthly_cost == 0.0001

        # Call again
        await detector.detect("Test2", amounts, date_pattern)

        # Verify budget doubled
        assert detector._daily_cost == 0.0002
        assert detector._monthly_cost == 0.0002

    @pytest.mark.asyncio
    async def test_budget_exceeded_returns_not_recurring(self, detector, mock_llm):
        """Test that exceeding budget returns is_recurring=false without LLM call."""
        # Set budget exceeded flag
        detector._budget_exceeded = True

        # Try to detect
        amounts = [50.00]
        date_pattern = "Monthly (15th)"
        result = await detector.detect("Test", amounts, date_pattern)

        # Verify LLM was NOT called
        detector.llm.achat.assert_not_called()

        # Verify fallback result
        assert result.is_recurring is False
        assert result.confidence == 0.5
        assert (
            "budget exceeded" in result.reasoning.lower()
            or "unavailable" in result.reasoning.lower()
        )

    @pytest.mark.asyncio
    async def test_budget_exceeded_when_daily_limit_hit(self, detector, mock_llm):
        """Test budget exceeded flag set when daily limit is hit."""
        # Set daily cost very close to limit (one call away)
        detector._daily_cost = 0.09999  # Just below $0.10 limit (detect() adds $0.0001)
        detector.max_cost_per_day = 0.10

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(50.0, 50.0),  # Tuple of floats
            reasoning="test",
            confidence=0.85,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Make request that pushes over limit (0.09999 + 0.0001 = 0.10009 > 0.10)
        amounts = [50.00]
        date_pattern = "Monthly (15th)"
        await detector.detect("Test", amounts, date_pattern)

        # Verify budget exceeded flag is set
        assert detector._budget_exceeded is True
        assert detector._daily_cost > detector.max_cost_per_day

    @pytest.mark.asyncio
    async def test_llm_error_returns_low_confidence(self, detector, mock_llm):
        """Test that LLM errors return is_recurring=false with low confidence."""
        # Mock LLM error
        detector.llm.achat = AsyncMock(side_effect=Exception("LLM timeout"))

        # Try to detect
        amounts = [50.00]
        date_pattern = "Monthly (15th)"
        result = await detector.detect("Test", amounts, date_pattern)

        # Verify fallback result
        assert result.is_recurring is False
        assert result.confidence == 0.3  # Lower confidence for errors
        assert "error" in result.reasoning.lower() or "unavailable" in result.reasoning.lower()

    def test_reset_daily_budget(self, detector):
        """Test daily budget reset."""
        # Set some costs
        detector._daily_cost = 0.05
        detector._budget_exceeded = True

        # Reset daily budget
        detector.reset_daily_budget()

        # Verify reset
        assert detector._daily_cost == 0.0
        assert detector._budget_exceeded is False

        # Monthly cost should NOT be reset
        detector._monthly_cost = 1.0
        detector.reset_daily_budget()
        assert detector._monthly_cost == 1.0

    def test_reset_monthly_budget(self, detector):
        """Test monthly budget reset."""
        # Set some costs
        detector._monthly_cost = 1.5
        detector._budget_exceeded = True

        # Reset monthly budget
        detector.reset_monthly_budget()

        # Verify reset
        assert detector._monthly_cost == 0.0
        assert detector._budget_exceeded is False

    def test_get_budget_status(self, detector):
        """Test budget status reporting."""
        # Set some costs
        detector._daily_cost = 0.05
        detector._monthly_cost = 1.0
        detector.max_cost_per_day = 0.10
        detector.max_cost_per_month = 2.00

        # Get status
        status = detector.get_budget_status()

        # Verify status
        assert status["daily_cost"] == 0.05
        assert status["daily_limit"] == 0.10
        assert status["daily_remaining"] == 0.05
        assert status["monthly_cost"] == 1.0
        assert status["monthly_limit"] == 2.00
        assert status["monthly_remaining"] == 1.0
        assert status["exceeded"] is False

    @pytest.mark.asyncio
    async def test_empty_transactions_raises_error(self, detector):
        """Test that empty amounts list raises ValueError."""
        with pytest.raises(ValueError, match="amounts cannot be empty"):
            await detector.detect("Test", [], "Monthly (15th)")

    @pytest.mark.asyncio
    async def test_user_prompt_formatting(self, detector, mock_llm):
        """Test that user prompt is formatted correctly with transaction data."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.structured = VariableRecurringPattern(
            is_recurring=True,
            cadence="monthly",
            expected_range=(50.0, 55.0),  # Tuple of floats
            reasoning="test",
            confidence=0.85,
        )
        detector.llm.achat = AsyncMock(return_value=mock_response)

        # Amounts and date pattern
        amounts = [50.00, 55.00]
        date_pattern = "Monthly (15th ±2 days)"

        # Detect
        await detector.detect("Test Merchant", amounts, date_pattern)

        # Verify user prompt
        call_args = detector.llm.achat.call_args
        user_message = call_args.kwargs["user_msg"]

        # Should contain merchant name
        assert "Test Merchant" in user_message

        # Should contain amounts (floats without trailing zeros: 50.0, 55.0)
        assert "50.0" in user_message or "50.00" in user_message
        assert "55.0" in user_message or "55.00" in user_message

        # Should contain date pattern
        assert "Monthly" in user_message
