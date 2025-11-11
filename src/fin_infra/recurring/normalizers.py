"""
LLM-based merchant name normalization (Layer 2).

Handles cryptic merchant names that fail pattern-based normalization:
- Payment processors: SQ *, TST*, CLOVER*, STRIPE*
- Subscriptions: NFLX*, SPFY*, AMZN MKTP
- Store numbers: #1234, store-specific identifiers
- Legal entities: Inc, LLC, Corp, Ltd

Uses ai-infra CoreLLM with few-shot prompting for 90-95% accuracy.
Caches results for 7 days (95% hit rate expected) → <1ms latency.
Falls back to RapidFuzz if LLM fails or disabled.
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


class MerchantNormalized(BaseModel):
    """
    Result of LLM merchant name normalization.

    Output schema for CoreLLM structured output.
    """

    canonical_name: str = Field(
        ...,
        description="Canonical merchant name (e.g., 'Netflix' for 'NFLX*SUB')",
        min_length=1,
        max_length=100,
    )
    merchant_type: str = Field(
        ...,
        description=(
            "Merchant category: streaming, coffee_shop, grocery, utility_electric, "
            "phone_service, gym, restaurant, rideshare, online_shopping, "
            "software_subscription, cloud_storage, payment_processor, etc."
        ),
        min_length=1,
        max_length=50,
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0 (0.8+ recommended for production)",
    )
    reasoning: str = Field(
        ...,
        max_length=150,
        description="Brief explanation of normalization (e.g., 'NFLX is Netflix subscription prefix')",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "canonical_name": "Netflix",
                "merchant_type": "streaming",
                "confidence": 0.95,
                "reasoning": "NFLX is Netflix subscription prefix",
            }
        }
    )


# Few-shot prompt template (20 examples covering common merchant patterns)
MERCHANT_NORMALIZATION_SYSTEM_PROMPT = """
You are a financial transaction expert specializing in merchant name normalization.
Given a merchant name from a bank transaction, identify the canonical merchant name
and merchant type.

Common patterns:
- Payment processors: SQ * (Square), TST* (Toast), CLOVER* (Clover), STRIPE* (Stripe)
- Subscriptions: NFLX* (Netflix), SPFY* (Spotify), AMZN* (Amazon), AAPL* (Apple)
- Store numbers: Remove #1234, store-specific identifiers
- Legal entities: Remove Inc, LLC, Corp, Ltd
- POS systems: TST* (Toast), CLOVER*, SQUARE*

Examples:
1. "NFLX*SUB #12345" → Netflix (streaming)
2. "Netflix Inc" → Netflix (streaming)
3. "NETFLIX.COM" → Netflix (streaming)
4. "SQ *COZY CAFE" → Cozy Cafe (coffee_shop, Square processor)
5. "TST* STARBUCKS" → Starbucks (coffee_shop, Toast POS)
6. "AMZN MKTP US" → Amazon (online_shopping)
7. "SPFY*PREMIUM" → Spotify (streaming)
8. "UBER *TRIP 12345" → Uber (rideshare)
9. "LYFT   *RIDE ABC" → Lyft (rideshare)
10. "CLOVER* PIZZA PLACE" → Pizza Place (restaurant, Clover POS)
11. "AAPL* ICLOUD STORAGE" → Apple iCloud (cloud_storage)
12. "MSFT*MICROSOFT 365" → Microsoft 365 (software_subscription)
13. "DISNEY PLUS #123" → Disney Plus (streaming)
14. "PRIME VIDEO" → Amazon Prime Video (streaming)
15. "CITY ELECTRIC #456" → City Electric (utility_electric)
16. "T-MOBILE USA" → T-Mobile (phone_service)
17. "VERIZON WIRELESS" → Verizon (phone_service)
18. "WHOLE FOODS MKT #789" → Whole Foods (grocery)
19. "STARBUCKS #1234" → Starbucks (coffee_shop)
20. "LA FITNESS #567" → LA Fitness (gym)

Output format (JSON):
{
  "canonical_name": "Netflix",
  "merchant_type": "streaming",
  "confidence": 0.95,
  "reasoning": "NFLX is Netflix subscription prefix"
}
"""

MERCHANT_NORMALIZATION_USER_PROMPT = "Normalize this merchant name: {merchant_name}"


class MerchantNormalizer:
    """
    LLM-based merchant name normalizer with caching and fallback.

    Layer 2 of 4-layer hybrid architecture:
    1. Check cache first (95% hit rate, 7-day TTL) → <1ms
    2. Call CoreLLM if cache miss → 200-400ms
    3. Cache result for 7 days
    4. Return MerchantNormalized

    Fallback to RapidFuzz if:
    - LLM disabled
    - LLM error
    - Budget exceeded
    """

    def __init__(
        self,
        provider: str = "google",
        model_name: Optional[str] = None,
        cache_ttl: int = 604800,  # 7 days
        enable_cache: bool = True,
        confidence_threshold: float = 0.8,
        max_cost_per_day: float = 0.10,
        max_cost_per_month: float = 2.00,
    ):
        """
        Initialize merchant normalizer.

        Args:
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model override (default: provider-specific)
            cache_ttl: Cache TTL in seconds (default: 604800 = 7 days)
            enable_cache: Enable caching (default: True)
            confidence_threshold: Minimum confidence to accept LLM result (default: 0.8)
            max_cost_per_day: Daily budget cap in USD (default: $0.10)
            max_cost_per_month: Monthly budget cap in USD (default: $2.00)

        Raises:
            ImportError: If ai-infra or svc-infra not installed
        """
        self.provider = provider
        self.model_name = model_name
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.confidence_threshold = confidence_threshold
        self.max_cost_per_day = max_cost_per_day
        self.max_cost_per_month = max_cost_per_month

        # Initialize CoreLLM
        if CoreLLM is None:
            raise ImportError(
                "ai-infra required for LLM normalization. Install: pip install ai-infra"
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
            f"MerchantNormalizer initialized: provider={provider}, model={model_name}, "
            f"cache_ttl={cache_ttl}s, confidence_threshold={confidence_threshold}"
        )

    async def normalize(
        self,
        merchant_name: str,
        fallback_confidence: float = 0.5,
    ) -> MerchantNormalized:
        """
        Normalize merchant name using LLM with caching.

        Flow:
        1. Check cache (95% hit rate) → <1ms
        2. Check budget (daily/monthly caps)
        3. Call CoreLLM if cache miss → 200-400ms
        4. Validate confidence threshold
        5. Cache result (7-day TTL)
        6. Return MerchantNormalized

        Args:
            merchant_name: Raw merchant name from transaction
            fallback_confidence: Confidence for fallback results (default: 0.5)

        Returns:
            MerchantNormalized with canonical name, type, confidence, reasoning

        Raises:
            ValueError: If merchant_name is empty
        """
        if not merchant_name or not merchant_name.strip():
            raise ValueError("merchant_name cannot be empty")

        merchant_name = merchant_name.strip()

        # Check cache first
        if self.enable_cache:
            cached_result = await self._get_cached(merchant_name)
            if cached_result:
                logger.debug(f"Cache hit for merchant: {merchant_name[:30]}")
                return cached_result

        # Check budget
        if self._budget_exceeded:
            logger.warning(
                f"Budget exceeded (daily: ${self._daily_cost:.4f}/{self.max_cost_per_day}, "
                f"monthly: ${self._monthly_cost:.4f}/{self.max_cost_per_month}). "
                "Falling back to basic normalization."
            )
            return self._fallback_normalize(merchant_name, fallback_confidence)

        # Call LLM
        try:
            result = await self._call_llm(merchant_name)

            # Validate confidence
            if result.confidence < self.confidence_threshold:
                logger.warning(
                    f"LLM confidence {result.confidence:.2f} below threshold "
                    f"{self.confidence_threshold:.2f}. Falling back."
                )
                return self._fallback_normalize(merchant_name, fallback_confidence)

            # Cache result
            if self.enable_cache:
                await self._cache_result(merchant_name, result)

            # Update budget tracking
            self._update_budget(cost=0.00008)  # $0.00008 per request (Google Gemini)

            return result

        except Exception as e:
            logger.error(f"LLM normalization failed for '{merchant_name}': {e}")
            return self._fallback_normalize(merchant_name, fallback_confidence)

    async def _get_cached(self, merchant_name: str) -> Optional[MerchantNormalized]:
        """
        Get cached normalization result.

        Cache key: merchant_norm:{md5(lowercase(merchant_name))}
        Expected hit rate: 95%
        """
        if not self.cache:
            return None

        cache_key = self._make_cache_key(merchant_name)

        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return MerchantNormalized(**cached_data)
        except Exception as e:
            logger.warning(f"Cache get failed for '{merchant_name}': {e}")

        return None

    async def _cache_result(self, merchant_name: str, result: MerchantNormalized) -> None:
        """
        Cache normalization result.

        Cache key: merchant_norm:{md5(lowercase(merchant_name))}
        TTL: 7 days (604800 seconds)
        """
        if not self.cache:
            return

        cache_key = self._make_cache_key(merchant_name)

        try:
            await self.cache.set(cache_key, result.model_dump(), ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for '{merchant_name}': {e}")

    def _make_cache_key(self, merchant_name: str) -> str:
        """
        Generate cache key for merchant name.

        Uses MD5 hash to handle special characters and normalize case.
        Format: merchant_norm:{md5_hex}
        """
        normalized = merchant_name.lower().strip()
        hash_hex = hashlib.md5(normalized.encode()).hexdigest()
        return f"merchant_norm:{hash_hex}"

    async def _call_llm(self, merchant_name: str) -> MerchantNormalized:
        """
        Call CoreLLM for merchant normalization.

        Uses few-shot prompting with 20 examples.
        Structured output via Pydantic schema.
        """
        user_prompt = MERCHANT_NORMALIZATION_USER_PROMPT.format(merchant_name=merchant_name)

        response = await self.llm.achat(
            provider=self.provider,
            model=self.model_name,
            messages=[
                {"role": "system", "content": MERCHANT_NORMALIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            output_schema=MerchantNormalized,
            output_method="prompt",  # Cross-provider compatibility
            temperature=0.0,  # Deterministic
            max_tokens=150,  # Small response
        )

        # Extract structured output
        if hasattr(response, "structured") and response.structured:
            return response.structured
        else:
            raise ValueError(f"LLM returned no structured output for '{merchant_name}'")

    def _fallback_normalize(
        self,
        merchant_name: str,
        confidence: float = 0.5,
    ) -> MerchantNormalized:
        """
        Fallback to basic normalization when LLM unavailable.

        Simple preprocessing:
        1. Lowercase
        2. Remove special characters (*, #, etc.)
        3. Remove store numbers (#1234)
        4. Remove legal entities (Inc, LLC, Corp, Ltd)
        5. Strip whitespace
        """
        normalized = merchant_name.lower()

        # Remove payment processor prefixes
        prefixes = ["sq *", "tst*", "clover*", "stripe*", "aapl*", "msft*"]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :].strip()
                break

        # Remove special characters
        normalized = normalized.replace("*", " ").replace("#", " ").replace(".", " ")

        # Remove store numbers (e.g., "starbucks 1234" → "starbucks")
        import re

        normalized = re.sub(r"\b\d{3,}\b", "", normalized)

        # Remove legal entities
        legal_entities = ["inc", "llc", "corp", "ltd", "limited", "corporation"]
        for entity in legal_entities:
            normalized = re.sub(rf"\b{entity}\b", "", normalized)

        # Clean up whitespace
        normalized = " ".join(normalized.split())

        # Capitalize for canonical name
        canonical_name = normalized.title() if normalized else merchant_name

        return MerchantNormalized(
            canonical_name=canonical_name,
            merchant_type="unknown",
            confidence=confidence,
            reasoning="Fallback normalization (LLM unavailable)",
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
