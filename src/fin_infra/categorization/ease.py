"""
Easy setup for transaction categorization.

Provides one-line setup with sensible defaults.
"""

from pathlib import Path
from typing import Literal, Optional

from .engine import CategorizationEngine

# LLM layer (optional import)
try:
    from .llm_layer import LLMCategorizer
except ImportError:
    LLMCategorizer = None


def easy_categorization(
    model: Literal["local", "llm", "hybrid"] = "hybrid",
    taxonomy: str = "mx",
    enable_ml: bool = False,
    confidence_threshold: float = 0.6,
    model_path: Optional[Path] = None,
    # LLM-specific parameters (V2)
    llm_provider: Literal["google", "openai", "anthropic", "none"] = "google",
    llm_model: Optional[str] = None,
    llm_confidence_threshold: float = 0.6,
    llm_cache_ttl: int = 86400,  # 24 hours
    llm_max_cost_per_day: float = 0.10,  # $0.10/day
    llm_max_cost_per_month: float = 2.00,  # $2/month
    enable_personalization: bool = False,
    **config,
) -> CategorizationEngine:
    """
    Easy setup for transaction categorization.

    One-liner to get started:
        categorizer = easy_categorization()
        result = await categorizer.categorize("Starbucks")

    With hybrid (sklearn + LLM) fallback:
        categorizer = easy_categorization(model="hybrid", enable_ml=True)

    With LLM only:
        categorizer = easy_categorization(model="llm", llm_provider="google")

    Args:
        model: Model architecture
            - "local": Exact + Regex only (no ML/LLM)
            - "llm": Exact + Regex + LLM (skip sklearn)
            - "hybrid": Exact + Regex + sklearn + LLM (default, best accuracy)
        taxonomy: Taxonomy to use ("mx" for MX-style 56 categories)
        enable_ml: Enable sklearn ML fallback (Layer 3)
        confidence_threshold: Minimum sklearn confidence before trying LLM (0-1)
        model_path: Path to custom sklearn model

        llm_provider: LLM provider ("google", "openai", "anthropic", "none")
        llm_model: Model name override (default varies by provider)
        llm_confidence_threshold: Minimum LLM confidence (0-1)
        llm_cache_ttl: Cache TTL in seconds (default 24h)
        llm_max_cost_per_day: Daily budget cap in USD (default $0.10)
        llm_max_cost_per_month: Monthly budget cap in USD (default $2.00)
        enable_personalization: Enable user-specific category learning
        **config: Additional configuration (future use)

    Returns:
        Configured CategorizationEngine

    Examples:
        >>> # Basic usage (exact + regex only)
        >>> categorizer = easy_categorization(model="local")
        >>> result = await categorizer.categorize("Starbucks")
        >>> print(result.category)  # "Coffee Shops"

        >>> # Hybrid (sklearn + LLM fallback for low confidence)
        >>> categorizer = easy_categorization(
        ...     model="hybrid",
        ...     enable_ml=True,
        ...     llm_provider="google"
        ... )
        >>> result = await categorizer.categorize("Unknown Coffee Shop")
        >>> print(result.category)  # "Coffee Shops" (via LLM if sklearn < 0.6)
        >>> print(result.method)  # "llm" or "ml"

        >>> # LLM-only (skip sklearn)
        >>> categorizer = easy_categorization(
        ...     model="llm",
        ...     llm_provider="openai",
        ...     llm_model="gpt-4o-mini"
        ... )

        >>> # Cost-conscious setup
        >>> categorizer = easy_categorization(
        ...     model="hybrid",
        ...     enable_ml=True,
        ...     llm_max_cost_per_day=0.05,  # $0.05/day
        ...     llm_cache_ttl=172800,  # 48 hours
        ... )
    """
    # Validate taxonomy
    if taxonomy != "mx":
        raise ValueError(f"Unsupported taxonomy: {taxonomy}. Only 'mx' is supported currently.")

    # Validate model
    if model not in ["local", "llm", "hybrid"]:
        raise ValueError(f"Unsupported model: {model}. Use 'local', 'llm', or 'hybrid'.")

    # Initialize LLM categorizer if needed
    llm_categorizer = None
    enable_llm = model in ["llm", "hybrid"] and llm_provider != "none"

    if enable_llm:
        if LLMCategorizer is None:
            raise ImportError(
                "LLM support requires ai-infra package. " "Install with: pip install ai-infra"
            )

        # Map provider names to ai-infra provider format
        provider_map = {
            "google": "google_genai",
            "openai": "openai",
            "anthropic": "anthropic",
        }
        ai_infra_provider = provider_map.get(llm_provider)
        if not ai_infra_provider:
            raise ValueError(
                f"Unsupported LLM provider: {llm_provider}. "
                f"Use 'google', 'openai', or 'anthropic'."
            )

        # Default models per provider
        default_models = {
            "google": "gemini-2.0-flash-exp",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
        }
        model_name = llm_model or default_models[llm_provider]

        llm_categorizer = LLMCategorizer(
            provider=ai_infra_provider,
            model_name=model_name,
            max_cost_per_day=llm_max_cost_per_day,
            max_cost_per_month=llm_max_cost_per_month,
            enable_personalization=enable_personalization,
        )

    # For "llm" model, always enable LLM but optionally enable ML too
    # For "hybrid", enable both if enable_ml=True
    # For "local", disable both
    effective_enable_ml = enable_ml if model == "hybrid" else False
    effective_enable_llm = enable_llm

    # Create engine
    engine = CategorizationEngine(
        enable_ml=effective_enable_ml,
        enable_llm=effective_enable_llm,
        confidence_threshold=confidence_threshold,
        model_path=model_path,
        llm_categorizer=llm_categorizer,
    )

    return engine
