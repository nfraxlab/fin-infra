"""
Natural language subscription insights generation (Layer 5).

Provides on-demand insights for users:
- Monthly spending summary
- Top subscriptions by cost
- Cost-saving recommendations (bundle deals, unused subscriptions)

Uses ai-infra CoreLLM with few-shot prompting.
Caches results for 24 hours (80% hit rate expected) → <1ms latency.
Triggered via GET /recurring/insights API endpoint (not automatic).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Lazy import for optional dependency (ai-infra)
try:
    from ai_infra.llm import CoreLLM
except ImportError:
    CoreLLM = None  # type: ignore

logger = logging.getLogger(__name__)


class SubscriptionInsights(BaseModel):
    """
    Natural language subscription insights.

    Output schema for CoreLLM structured output.
    """

    summary: str = Field(
        ...,
        max_length=500,
        description=(
            "Overall subscription spending summary. "
            "Example: 'You have 5 streaming subscriptions totaling $64.95/month.'"
        ),
    )
    top_subscriptions: list[dict[str, Any]] = Field(
        ...,
        description="Top 5 subscriptions by cost",
        max_length=5,
    )
    recommendations: list[str] = Field(
        ...,
        description="Actionable recommendations (max 3)",
        max_length=3,
    )
    total_monthly_cost: float = Field(
        ...,
        ge=0.0,
        description="Total monthly subscription cost",
    )
    potential_savings: Optional[float] = Field(
        None,
        ge=0.0,
        description="Potential monthly savings from recommendations (if applicable)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "You have 5 streaming subscriptions totaling $64.95/month.",
                "top_subscriptions": [
                    {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
                    {"merchant": "Spotify", "amount": 9.99, "cadence": "monthly"},
                    {"merchant": "Hulu", "amount": 12.99, "cadence": "monthly"},
                    {"merchant": "Disney Plus", "amount": 10.99, "cadence": "monthly"},
                    {"merchant": "Amazon Prime", "amount": 14.99, "cadence": "monthly"},
                ],
                "recommendations": [
                    "Consider Disney+ bundle (Disney+, Hulu, ESPN+ for $19.99) to save $29.98/month",
                    "Amazon Prime includes Prime Video - you may be able to cancel Netflix or Hulu",
                    "Review your streaming usage - consolidating to 2-3 services could save $30/month",
                ],
                "total_monthly_cost": 64.95,
                "potential_savings": 30.00,
            }
        }
    )


# Few-shot prompt template (3 examples covering common scenarios)
INSIGHTS_GENERATION_SYSTEM_PROMPT = """
You are a personal finance advisor specializing in subscription management.
Given a user's detected subscriptions, provide insights and recommendations
to help them save money and optimize their spending.

Guidelines:
- Be conversational and friendly
- Focus on actionable recommendations (bundle deals, unused subscriptions)
- Highlight potential savings with specific dollar amounts
- Limit to top 3 recommendations
- Consider common bundles: Disney+ bundle ($19.99 for Disney+, Hulu, ESPN+), Amazon Prime includes Prime Video

Examples:
1. Subscriptions: Netflix $15.99, Hulu $12.99, Disney+ $10.99, Spotify $9.99, Amazon Prime $14.99
   → "You have 5 subscriptions totaling $64.95/month. Consider the Disney+ bundle 
      (Disney+, Hulu, ESPN+ for $19.99) to save $29.98/month. Also, Amazon Prime 
      includes Prime Video - you may be able to cancel Netflix or Hulu."
   → total_monthly_cost: 64.95
   → potential_savings: 30.00

2. Subscriptions: Spotify $9.99, Apple Music $10.99
   → "You're paying for both Spotify and Apple Music ($20.98/month). Cancel one 
      to save $10.99/month."
   → total_monthly_cost: 20.98
   → potential_savings: 10.99

3. Subscriptions: LA Fitness $40, Planet Fitness $10
   → "You have 2 gym memberships totaling $50/month. Consider consolidating to 
      just Planet Fitness to save $40/month."
   → total_monthly_cost: 50.00
   → potential_savings: 40.00

Output format (JSON):
{
  "summary": "You have 5 streaming subscriptions totaling $64.95/month.",
  "top_subscriptions": [
    {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
    {"merchant": "Hulu", "amount": 12.99, "cadence": "monthly"}
  ],
  "recommendations": [
    "Consider Disney+ bundle to save $30/month",
    "Amazon Prime includes Prime Video - cancel Netflix/Hulu"
  ],
  "total_monthly_cost": 64.95,
  "potential_savings": 30.00
}
"""

INSIGHTS_GENERATION_USER_PROMPT = """
User's subscriptions:
{subscriptions_json}

Provide insights and recommendations.
"""


class SubscriptionInsightsGenerator:
    """
    LLM-based subscription insights generator with caching.

    Layer 5 of 4-layer hybrid architecture (on-demand, optional):
    1. Check cache first (80% hit rate, 24h TTL) → <1ms
    2. Call CoreLLM if cache miss → 300-500ms
    3. Cache result for 24 hours
    4. Return SubscriptionInsights

    Triggered via GET /recurring/insights API endpoint.
    """

    def __init__(
        self,
        provider: str = "google",
        model_name: Optional[str] = None,
        cache_ttl: int = 86400,  # 24 hours
        enable_cache: bool = True,
        max_cost_per_day: float = 0.10,
        max_cost_per_month: float = 2.00,
    ):
        """
        Initialize insights generator.

        Args:
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model override (default: provider-specific)
            cache_ttl: Cache TTL in seconds (default: 86400 = 24 hours)
            enable_cache: Enable caching (default: True)
            max_cost_per_day: Daily budget cap in USD (default: $0.10)
            max_cost_per_month: Monthly budget cap in USD (default: $2.00)

        Raises:
            ImportError: If ai-infra or svc-infra not installed
        """
        self.provider = provider
        self.model_name = model_name
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.max_cost_per_day = max_cost_per_day
        self.max_cost_per_month = max_cost_per_month

        # Initialize CoreLLM
        if CoreLLM is None:
            raise ImportError(
                "ai-infra required for insights generation. Install: pip install ai-infra"
            )

        self.llm = CoreLLM()

        # Initialize cache if enabled
        self.cache = None
        if enable_cache:
            try:
                from svc_infra.cache import get_cache
            except ImportError:
                logger.warning(
                    "svc-infra cache not available. Caching disabled. "
                    "Install: pip install svc-infra[redis]"
                )
                self.enable_cache = False
            else:
                self.cache = get_cache()
                if self.cache is None:
                    logger.warning(
                        "Cache not initialized. Call init_cache() first. Caching disabled."
                    )
                    self.enable_cache = False

        # Budget tracking (in-memory for simplicity, should use Redis in production)
        self._daily_cost = 0.0
        self._monthly_cost = 0.0
        self._budget_exceeded = False

        logger.info(
            f"SubscriptionInsightsGenerator initialized: provider={provider}, "
            f"model={model_name}, cache_ttl={cache_ttl}s"
        )

    async def generate(
        self,
        subscriptions: list[dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> SubscriptionInsights:
        """
        Generate subscription insights with natural language recommendations.

        Flow:
        1. Check cache (80% hit rate, key: insights:{user_id}) → <1ms
        2. Check budget (daily/monthly caps)
        3. Call CoreLLM if cache miss → 300-500ms
        4. Cache result (24h TTL)
        5. Return SubscriptionInsights

        Args:
            subscriptions: List of subscription dicts with merchant, amount, cadence
            user_id: Optional user ID for caching (default: hash of subscriptions)

        Returns:
            SubscriptionInsights with summary, top subscriptions, recommendations

        Raises:
            ValueError: If subscriptions is empty
        """
        if not subscriptions:
            raise ValueError("subscriptions cannot be empty")

        # Check cache first
        if self.enable_cache:
            cached_result = await self._get_cached(subscriptions, user_id)
            if cached_result:
                logger.debug("Cache hit for insights")
                return cached_result

        # Check budget
        if self._budget_exceeded:
            logger.warning(
                f"Budget exceeded (daily: ${self._daily_cost:.4f}/{self.max_cost_per_day}, "
                f"monthly: ${self._monthly_cost:.4f}/{self.max_cost_per_month}). "
                "Returning basic summary without recommendations."
            )
            return self._fallback_insights(subscriptions)

        # Call LLM
        try:
            result = await self._call_llm(subscriptions)

            # Cache result
            if self.enable_cache:
                await self._cache_result(subscriptions, result, user_id)

            # Update budget tracking
            self._update_budget(cost=0.0002)  # $0.0002 per generation (Google Gemini)

            return result

        except Exception as e:
            logger.error(f"LLM insights generation failed: {e}")
            return self._fallback_insights(subscriptions)

    async def _get_cached(
        self,
        subscriptions: list[dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> Optional[SubscriptionInsights]:
        """
        Get cached insights.

        Cache key: insights:{user_id} or insights:{md5(subscriptions_json)}
        Expected hit rate: 80%
        """
        if not self.cache:
            return None

        cache_key = self._make_cache_key(subscriptions, user_id)

        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return SubscriptionInsights(**cached_data)
        except Exception as e:
            logger.warning(f"Cache get failed for insights: {e}")

        return None

    async def _cache_result(
        self,
        subscriptions: list[dict[str, Any]],
        result: SubscriptionInsights,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Cache insights result.

        Cache key: insights:{user_id} or insights:{md5(subscriptions_json)}
        TTL: 24 hours (86400 seconds)
        """
        if not self.cache:
            return

        cache_key = self._make_cache_key(subscriptions, user_id)

        try:
            await self.cache.set(cache_key, result.model_dump(), ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for insights: {e}")

    def _make_cache_key(
        self,
        subscriptions: list[dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generate cache key for insights.

        Uses user_id if provided, otherwise MD5 hash of subscriptions JSON.
        Format: insights:{user_id} or insights:{md5_hex}
        """
        if user_id:
            return f"insights:{user_id}"

        import json

        subscriptions_json = json.dumps(subscriptions, sort_keys=True)
        hash_hex = hashlib.md5(subscriptions_json.encode()).hexdigest()
        return f"insights:{hash_hex}"

    async def _call_llm(
        self,
        subscriptions: list[dict[str, Any]],
    ) -> SubscriptionInsights:
        """
        Call CoreLLM for insights generation.

        Uses few-shot prompting with 3 examples.
        Structured output via Pydantic schema.
        """
        import json

        subscriptions_json = json.dumps(subscriptions, indent=2)

        user_prompt = INSIGHTS_GENERATION_USER_PROMPT.format(subscriptions_json=subscriptions_json)

        response = await self.llm.achat(
            provider=self.provider,
            model=self.model_name,
            messages=[
                {"role": "system", "content": INSIGHTS_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            output_schema=SubscriptionInsights,
            output_method="prompt",  # Cross-provider compatibility
            temperature=0.3,  # Slight creativity for recommendations
            max_tokens=500,  # Medium response
        )

        # Extract structured output
        if hasattr(response, "structured") and response.structured:
            return response.structured
        else:
            raise ValueError("LLM returned no structured output for insights")

    def _fallback_insights(
        self,
        subscriptions: list[dict[str, Any]],
    ) -> SubscriptionInsights:
        """
        Fallback to basic insights when LLM unavailable.

        Generates simple summary without recommendations.
        """
        # Calculate total monthly cost
        total_cost = sum(sub.get("amount", 0.0) for sub in subscriptions)

        # Get top 5 by cost
        sorted_subs = sorted(
            subscriptions,
            key=lambda x: x.get("amount", 0.0),
            reverse=True,
        )
        top_subs = sorted_subs[:5]

        # Basic summary
        summary = f"You have {len(subscriptions)} subscription(s) totaling ${total_cost:.2f}/month."

        return SubscriptionInsights(
            summary=summary,
            top_subscriptions=top_subs,
            recommendations=[],
            total_monthly_cost=total_cost,
            potential_savings=None,
        )

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
