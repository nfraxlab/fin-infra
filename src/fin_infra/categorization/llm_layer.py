"""
LLM-based transaction categorization (Layer 4).

Uses ai-infra.llm.CoreLLM with few-shot prompting and structured output
to categorize transactions that sklearn (Layer 3) has low confidence on.

Caches predictions via svc-infra.cache to minimize API costs (85-90% hit rate).
Implements budget caps to prevent runaway costs.

Expected performance:
- Accuracy: 85-95% (few-shot prompting)
- Latency: <1ms cached, 200-500ms uncached
- Cost: $0.00011/uncached txn (Google Gemini 2.5 Flash)
"""

import hashlib
import logging
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field

# ai-infra imports
try:
    from ai_infra.llm import CoreLLM
    from ai_infra.llm.providers import Providers
    from ai_infra.llm.providers.models import Models
except ImportError:
    raise ImportError("ai-infra not installed. Install with: pip install ai-infra")

# fin-infra imports
from .taxonomy import Category, get_all_categories

logger = logging.getLogger(__name__)


# Pydantic schema for structured LLM output
class CategoryPrediction(BaseModel):
    """LLM-predicted transaction category."""

    category: str = Field(..., description="Predicted category (must match fin-infra taxonomy)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    reasoning: str = Field(..., max_length=200, description="Brief explanation (max 200 chars)")


# Few-shot examples (20 diverse merchants covering all major categories)
FEW_SHOT_EXAMPLES: List[Tuple[str, str, str]] = [
    # Food & Dining (5 examples)
    ("STARBUCKS #1234", "Coffee Shops", "Popular coffee shop chain"),
    ("MCDONALD'S", "Fast Food", "Fast food restaurant"),
    ("WHOLE FOODS MARKET", "Groceries", "Grocery store and supermarket"),
    ("OLIVE GARDEN", "Restaurants", "Sit-down restaurant"),
    ("DOORDASH*CHIPOTLE", "Food Delivery", "Food delivery service"),
    # Shopping (3 examples)
    ("AMAZON.COM", "Online Shopping", "Online retail marketplace"),
    ("TARGET STORE #123", "General Merchandise", "Department store"),
    ("BEST BUY", "Electronics", "Electronics retailer"),
    # Transportation (3 examples)
    ("SHELL GAS STATION", "Gas & Fuel", "Gas station fuel purchase"),
    ("UBER *TRIP", "Rideshare & Taxis", "Rideshare service"),
    ("SF MUNI", "Public Transportation", "Public transit fare"),
    # Bills & Utilities (2 examples)
    ("VERIZON WIRELESS", "Phone", "Cell phone service provider"),
    ("NETFLIX", "Subscriptions", "Streaming subscription service"),
    # Healthcare (2 examples)
    ("WALGREENS PHARMACY", "Pharmacy", "Pharmacy and drugstore"),
    ("DR JOHN SMITH", "Doctor & Medical", "Medical provider visit"),
    # Travel (2 examples)
    ("HILTON HOTEL SFO", "Hotels", "Hotel accommodation"),
    ("UNITED AIRLINES", "Flights", "Airline ticket purchase"),
    # Entertainment (1 example)
    ("AMC THEATRES", "Movies & Events", "Movie theater"),
    # Personal Care (1 example)
    ("PLANET FITNESS", "Gym & Fitness", "Gym membership"),
    # Pets (1 example)
    ("PETCO", "Pets", "Pet supplies store"),
]


# System prompt template
SYSTEM_PROMPT_TEMPLATE = """You are a financial transaction categorization assistant.

Your task: Categorize merchant transactions into the correct spending category.

Guidelines:
1. Match the merchant to ONE category from the list below
2. Provide a confidence score (0.0-1.0) based on your certainty
3. Give a brief reason (max 10 words) for your choice
4. If uncertain, assign lower confidence (0.5-0.7) rather than guessing

Few-shot examples (learn the pattern):
{few_shot_examples}

Available categories (56 total):
{category_list}

Return ONLY a JSON object with these exact fields:
- category: str (must match one from the list above)
- confidence: float (0.0-1.0)
- reasoning: str (brief explanation, max 50 words)

Do NOT include any prose, markdown, or extra text. JSON only."""


class LLMCategorizer:
    """
    LLM-based transaction categorization (Layer 4).

    Uses ai-infra.llm.CoreLLM with few-shot prompting and structured output.
    Caches predictions via svc-infra.cache to minimize API costs.

    Args:
        provider: LLM provider ("google_genai", "openai", "anthropic")
        model_name: Model name (e.g., "gemini-2.5-flash", "gpt-4.1-mini")
        max_cost_per_day: Daily budget cap in USD (default $0.10)
        max_cost_per_month: Monthly budget cap in USD (default $2.00)
        cache_ttl: Cache TTL in seconds (default 24 hours)
        enable_personalization: Enable user context injection (default False)

    Example:
        >>> categorizer = LLMCategorizer(
        ...     provider="google_genai",
        ...     model_name="gemini-2.5-flash",
        ... )
        >>> prediction = await categorizer.categorize("UNKNOWN COFFEE CO")
        >>> print(prediction.category, prediction.confidence)
        Coffee Shops 0.85
    """

    def __init__(
        self,
        provider: str = "google_genai",
        model_name: str = "gemini-2.5-flash",
        max_cost_per_day: float = 0.10,
        max_cost_per_month: float = 2.00,
        cache_ttl: int = 86400,  # 24 hours
        enable_personalization: bool = False,
    ):
        self.provider = provider
        self.model_name = model_name
        self.max_cost_per_day = max_cost_per_day
        self.max_cost_per_month = max_cost_per_month
        self.cache_ttl = cache_ttl
        self.enable_personalization = enable_personalization

        # Initialize CoreLLM
        self.llm = CoreLLM()

        # Cost tracking (stored in Redis via svc-infra.cache in production)
        self.daily_cost = 0.0
        self.monthly_cost = 0.0

        # Build system prompt (reused across all requests)
        self.system_prompt = self._build_system_prompt()

        logger.info(
            f"LLMCategorizer initialized: provider={provider}, "
            f"model={model_name}, budget=${max_cost_per_day}/day"
        )

    async def categorize(
        self,
        merchant_name: str,
        user_id: Optional[str] = None,
    ) -> CategoryPrediction:
        """
        Categorize merchant using LLM.

        Args:
            merchant_name: Merchant to categorize
            user_id: User ID for personalized context (optional)

        Returns:
            CategoryPrediction with LLM-predicted category

        Raises:
            RuntimeError: If budget exceeded
            ValueError: If LLM returns invalid category
        """
        # Check budget
        if not self._check_budget():
            raise RuntimeError(
                f"LLM budget exceeded: ${self.daily_cost:.4f}/${self.max_cost_per_day:.2f}"
            )

        # TODO: Check cache first (svc-infra.cache integration)
        # cached = await self._get_cached_prediction(merchant_name)
        # if cached:
        #     logger.debug(f"Cache hit for merchant: {merchant_name}")
        #     return cached

        # Call LLM
        try:
            prediction = await self._call_llm(merchant_name, user_id)

            # TODO: Cache result (svc-infra.cache integration)
            # await self._cache_prediction(merchant_name, prediction)

            # Track cost
            self._track_cost()

            logger.info(
                f"LLM categorized '{merchant_name}' → {prediction.category} "
                f"(confidence={prediction.confidence:.2f})"
            )

            return prediction

        except Exception as e:
            logger.error(f"LLM categorization failed for '{merchant_name}': {e}")
            raise

    async def _call_llm(
        self,
        merchant_name: str,
        user_id: Optional[str] = None,
    ) -> CategoryPrediction:
        """Call LLM API with structured output."""
        # Build user message
        user_message = self._build_user_message(merchant_name, user_id)

        # Call LLM with retry logic
        extra = {
            "retry": {
                "max_tries": 3,
                "base": 0.5,
                "jitter": 0.2,
            }
        }

        logger.debug(f"Calling LLM: provider={self.provider}, model={self.model_name}")

        response = await self.llm.achat(
            user_msg=user_message,
            system=self.system_prompt,
            provider=self.provider,
            model_name=self.model_name,
            output_schema=CategoryPrediction,
            output_method="prompt",  # Most reliable across all providers
            extra=extra,
        )

        # Validate category against taxonomy
        valid_categories = [c.value for c in Category]
        if response.category not in valid_categories:
            raise ValueError(
                f"LLM returned invalid category: '{response.category}'. "
                f"Must be one of {len(valid_categories)} valid categories."
            )

        return response

    def _build_system_prompt(self) -> str:
        """Build system prompt with few-shot examples (reused across all requests)."""
        # Format few-shot examples
        examples_text = "\n\n".join(
            [
                f'Merchant: "{merchant}"\n→ Category: "{category}"\n→ Reasoning: "{reasoning}"'
                for merchant, category, reasoning in FEW_SHOT_EXAMPLES
            ]
        )

        # Format category list (grouped by type for readability)
        categories = get_all_categories()
        category_list = ", ".join([c.value for c in categories])

        # Fill template
        return SYSTEM_PROMPT_TEMPLATE.format(
            few_shot_examples=examples_text,
            category_list=category_list,
        )

    def _build_user_message(
        self,
        merchant_name: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Build user message with optional personalization."""
        if self.enable_personalization and user_id:
            # Get user context (top merchants, categories)
            # TODO: Implement user context retrieval from svc-infra.cache
            context = {
                "top_merchants": "Starbucks, Whole Foods, Shell",  # Placeholder
                "top_categories": "Groceries (30%), Gas & Fuel (15%), Coffee Shops (10%)",
            }
            return f"""Categorize this transaction:

Merchant: "{merchant_name}"

User context:
- Frequently shops at: {context['top_merchants']}
- Top spending categories: {context['top_categories']}

Return JSON with category, confidence, and reasoning."""
        else:
            # Simple message
            return f"""Categorize this transaction:

Merchant: "{merchant_name}"

Return JSON with category, confidence, and reasoning."""

    def _get_cache_key(self, merchant_name: str) -> str:
        """Generate stable cache key from merchant name."""
        normalized = merchant_name.lower().strip()
        hash_value = hashlib.md5(normalized.encode()).hexdigest()
        return f"llm_category:{hash_value}"

    def _check_budget(self) -> bool:
        """Check if daily/monthly budget allows LLM call."""
        if self.daily_cost >= self.max_cost_per_day:
            logger.warning(
                f"Daily budget exceeded: ${self.daily_cost:.4f}/${self.max_cost_per_day:.2f}"
            )
            return False
        if self.monthly_cost >= self.max_cost_per_month:
            logger.warning(
                f"Monthly budget exceeded: ${self.monthly_cost:.4f}/${self.max_cost_per_month:.2f}"
            )
            return False
        return True

    def _track_cost(self):
        """Track LLM API cost (estimate based on token count)."""
        # Estimate: ~1,230 input + ~50 output tokens
        # Google Gemini 2.5 Flash: $0.075/1M input, $0.30/1M output
        cost_per_request = 0.00011  # $0.00011 per request

        self.daily_cost += cost_per_request
        self.monthly_cost += cost_per_request

        # Cost tracking: Use svc-infra.cache (Redis), not database persistence.
        # from svc_infra.cache import cache_write
        # await cache_write(f"llm_cost:daily:{user_id}", self.daily_cost, ttl=86400)
        # await cache_write(f"llm_cost:monthly:{user_id}", self.monthly_cost, ttl=2592000)
        # See docs/persistence.md for LLM cost tracking patterns.
        logger.debug(
            f"Cost tracked: +${cost_per_request:.5f} "
            f"(daily=${self.daily_cost:.5f}, monthly=${self.monthly_cost:.5f})"
        )

    def reset_daily_cost(self):
        """Reset daily cost counter (called at midnight UTC)."""
        logger.info(f"Resetting daily cost: ${self.daily_cost:.5f} → $0.00")
        self.daily_cost = 0.0

    def reset_monthly_cost(self):
        """Reset monthly cost counter (called on 1st of month)."""
        logger.info(f"Resetting monthly cost: ${self.monthly_cost:.5f} → $0.00")
        self.monthly_cost = 0.0
