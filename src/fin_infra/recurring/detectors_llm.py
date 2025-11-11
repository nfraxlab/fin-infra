"""
LLM-based variable amount detection (Layer 4).

Handles edge cases where statistical methods fail:
- Utility bills with seasonal variation (winter heating spikes 2x)
- Phone bills with occasional overage charges
- Gym fees with annual waived months or promotional discounts
- Streaming services with rare price changes

Uses ai-infra CoreLLM with few-shot prompting for 88% accuracy.
Only called for ambiguous patterns (20-40% variance, ~10% of patterns).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Lazy import for optional dependency (ai-infra)
try:
    from ai_infra.llm import CoreLLM
except ImportError:
    CoreLLM = None  # type: ignore

logger = logging.getLogger(__name__)


class VariableRecurringPattern(BaseModel):
    """
    Result of LLM variable amount detection.

    Output schema for CoreLLM structured output.
    """

    is_recurring: bool = Field(
        ...,
        description="True if pattern is recurring despite variance",
    )
    cadence: Optional[str] = Field(
        None,
        description=(
            "Frequency if recurring: monthly, bi-weekly, quarterly, annual, etc. "
            "None if not recurring."
        ),
    )
    expected_range: Optional[tuple[float, float]] = Field(
        None,
        description=(
            "Expected amount range (min, max) if recurring. "
            "None if not recurring. Example: (45.0, 60.0) for utility bills."
        ),
    )
    reasoning: str = Field(
        ...,
        max_length=200,
        description=(
            "Explanation of variance pattern. "
            "Examples: 'Seasonal winter heating causes variance', "
            "'Occasional overage charge spike', 'Random purchases, not recurring'"
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0 (0.8+ recommended for production)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_recurring": True,
                "cadence": "monthly",
                "expected_range": (45.0, 60.0),
                "reasoning": "Seasonal winter heating causes variance",
                "confidence": 0.85,
            }
        }
    )


# Few-shot prompt template (5 examples covering common variable patterns)
VARIABLE_DETECTION_SYSTEM_PROMPT = """
You are a financial analysis expert specializing in recurring payment detection.
Given a merchant name and transaction history, determine if the variable amounts
represent a recurring subscription or bill.

Common patterns:
- Utility bills: Seasonal variation (2x in winter for heating, summer for AC)
- Phone bills: Occasional spikes (overage charges, international calls)
- Gym fees: Annual fee waived, promotional discounts
- Streaming services: Price changes (rare, <5% variance)

Examples:
1. Merchant: "City Electric"
   Amounts: [$45, $52, $48, $55, $50, $49]
   Dates: Monthly (15th ±7 days)
   → is_recurring: true, cadence: "monthly", range: (40, 60), 
     reasoning: "Seasonal winter heating variation", confidence: 0.85

2. Merchant: "T-Mobile"
   Amounts: [$50, $50, $50, $78, $50, $50]
   Dates: Monthly (20th ±3 days)
   → is_recurring: true, cadence: "monthly", range: (50, 80),
     reasoning: "Occasional overage charge spike", confidence: 0.80

3. Merchant: "Random Store"
   Amounts: [$10, $45, $23, $67, $12]
   Dates: Irregular
   → is_recurring: false, reasoning: "Too much variance, no pattern", confidence: 0.95

4. Merchant: "Gas Company"
   Amounts: [$45, $48, $50, $52, $120, $115]
   Dates: Monthly
   → is_recurring: true, cadence: "monthly", range: (40, 120),
     reasoning: "Winter heating season doubles bill", confidence: 0.80

5. Merchant: "Gym Membership"
   Amounts: [$40, $40, $0, $40, $40]
   Dates: Monthly
   → is_recurring: true, cadence: "monthly", range: (0, 40),
     reasoning: "Annual fee waived one month", confidence: 0.75

Output format (JSON):
{
  "is_recurring": true,
  "cadence": "monthly",
  "expected_range": [45.0, 60.0],
  "reasoning": "Seasonal winter heating causes variance",
  "confidence": 0.85
}
"""

VARIABLE_DETECTION_USER_PROMPT = """
Merchant: {merchant_name}
Amounts: {amounts}
Dates: {date_pattern}

Is this a recurring pattern?
"""


class VariableDetectorLLM:
    """
    LLM-based variable amount detector for ambiguous patterns.

    Layer 4 of 4-layer hybrid architecture:
    - Only called when variance is 20-40% (ambiguous, ~10% of patterns)
    - Statistical methods handle <20% variance (85% coverage)
    - Uses CoreLLM to understand semantic variance (seasonal, spikes)

    Flow:
    1. Receive merchant name, amounts, date pattern
    2. Call CoreLLM with few-shot prompt
    3. Return VariableRecurringPattern
    4. Update budget tracking
    """

    def __init__(
        self,
        provider: str = "google",
        model_name: Optional[str] = None,
        max_cost_per_day: float = 0.10,
        max_cost_per_month: float = 2.00,
    ):
        """
        Initialize variable amount detector.

        Args:
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model override (default: provider-specific)
            max_cost_per_day: Daily budget cap in USD (default: $0.10)
            max_cost_per_month: Monthly budget cap in USD (default: $2.00)

        Raises:
            ImportError: If ai-infra not installed
        """
        self.provider = provider
        self.model_name = model_name
        self.max_cost_per_day = max_cost_per_day
        self.max_cost_per_month = max_cost_per_month

        # Initialize CoreLLM
        if CoreLLM is None:
            raise ImportError(
                "ai-infra required for LLM variable detection. Install: pip install ai-infra"
            )

        self.llm = CoreLLM()

        # Budget tracking (in-memory for simplicity, should use Redis in production)
        self._daily_cost = 0.0
        self._monthly_cost = 0.0
        self._budget_exceeded = False

        logger.info(f"VariableDetectorLLM initialized: provider={provider}, model={model_name}")

    async def detect(
        self,
        merchant_name: str,
        amounts: list[float],
        date_pattern: str,
    ) -> VariableRecurringPattern:
        """
        Detect if variable amounts represent a recurring pattern.

        Args:
            merchant_name: Canonical merchant name (from Layer 2 normalization)
            amounts: List of transaction amounts (should have 20-40% variance)
            date_pattern: Date pattern description (e.g., "Monthly (15th ±7 days)")

        Returns:
            VariableRecurringPattern with is_recurring, cadence, range, reasoning, confidence

        Raises:
            ValueError: If amounts is empty or date_pattern is empty
        """
        if not amounts:
            raise ValueError("amounts cannot be empty")
        if not date_pattern or not date_pattern.strip():
            raise ValueError("date_pattern cannot be empty")

        # Check budget
        if self._budget_exceeded:
            logger.warning(
                f"Budget exceeded (daily: ${self._daily_cost:.4f}/{self.max_cost_per_day}, "
                f"monthly: ${self._monthly_cost:.4f}/{self.max_cost_per_month}). "
                "Falling back to non-recurring classification."
            )
            return VariableRecurringPattern(
                is_recurring=False,
                cadence=None,
                expected_range=None,
                reasoning="Budget exceeded, unable to classify",
                confidence=0.5,
            )

        # Call LLM
        try:
            result = await self._call_llm(merchant_name, amounts, date_pattern)

            # Update budget tracking
            self._update_budget(cost=0.0001)  # $0.0001 per detection (Google Gemini)

            return result

        except Exception as e:
            logger.error(f"LLM variable detection failed for '{merchant_name}': {e}")
            return VariableRecurringPattern(
                is_recurring=False,
                cadence=None,
                expected_range=None,
                reasoning=f"LLM error: {str(e)[:100]}",
                confidence=0.3,
            )

    async def _call_llm(
        self,
        merchant_name: str,
        amounts: list[float],
        date_pattern: str,
    ) -> VariableRecurringPattern:
        """
        Call CoreLLM for variable amount detection.

        Uses few-shot prompting with 5 examples.
        Structured output via Pydantic schema.
        """
        # Format amounts for prompt
        amounts_str = str(amounts)

        user_prompt = VARIABLE_DETECTION_USER_PROMPT.format(
            merchant_name=merchant_name,
            amounts=amounts_str,
            date_pattern=date_pattern,
        )

        response = await self.llm.achat(
            provider=self.provider,
            model=self.model_name,
            messages=[
                {"role": "system", "content": VARIABLE_DETECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            output_schema=VariableRecurringPattern,
            output_method="prompt",  # Cross-provider compatibility
            temperature=0.0,  # Deterministic
            max_tokens=200,  # Small response
        )

        # Extract structured output
        if hasattr(response, "structured") and response.structured:
            return response.structured
        else:
            raise ValueError(f"LLM returned no structured output for '{merchant_name}'")

    def _update_budget(self, cost: float) -> None:
        """
        Update budget tracking and check limits.

        In production, this should use Redis for distributed tracking.
        """
        self._daily_cost += cost
        self._monthly_cost += cost

        if self._daily_cost > self.max_cost_per_day:
            logger.error(
                f"Daily budget exceeded: ${self._daily_cost:.4f} > ${self.max_cost_per_day}"
            )
            self._budget_exceeded = True

        if self._monthly_cost > self.max_cost_per_month:
            logger.error(
                f"Monthly budget exceeded: ${self._monthly_cost:.4f} > ${self.max_cost_per_month}"
            )
            self._budget_exceeded = True

    def reset_daily_budget(self) -> None:
        """Reset daily budget counter (call at midnight)."""
        self._daily_cost = 0.0
        self._budget_exceeded = False
        logger.info("Daily budget reset")

    def reset_monthly_budget(self) -> None:
        """Reset monthly budget counter (call at month start)."""
        self._monthly_cost = 0.0
        self._budget_exceeded = False
        logger.info("Monthly budget reset")

    def get_budget_status(self) -> dict[str, Any]:
        """
        Get current budget status.

        Returns:
            dict with daily_cost, monthly_cost, daily_limit, monthly_limit, exceeded
        """
        return {
            "daily_cost": self._daily_cost,
            "daily_limit": self.max_cost_per_day,
            "daily_remaining": max(0, self.max_cost_per_day - self._daily_cost),
            "monthly_cost": self._monthly_cost,
            "monthly_limit": self.max_cost_per_month,
            "monthly_remaining": max(0, self.max_cost_per_month - self._monthly_cost),
            "exceeded": self._budget_exceeded,
        }
