"""
Easy setup for transaction categorization.

Provides one-line setup with sensible defaults.
"""

from pathlib import Path
from typing import Optional

from .engine import CategorizationEngine


def easy_categorization(
    model: str = "local",
    taxonomy: str = "mx",
    enable_ml: bool = False,
    confidence_threshold: float = 0.75,
    model_path: Optional[Path] = None,
    **config,
) -> CategorizationEngine:
    """
    Easy setup for transaction categorization.

    One-liner to get started:
        categorizer = easy_categorization()
        result = categorizer.categorize("Starbucks")

    With ML enabled:
        categorizer = easy_categorization(enable_ml=True)

    Args:
        model: Model type ("local" for bundled model, "custom" for user-provided)
        taxonomy: Taxonomy to use ("mx" for MX-style 56 categories)
        enable_ml: Enable ML fallback (Layer 3)
        confidence_threshold: Minimum confidence for ML predictions (0-1)
        model_path: Path to custom ML model (for model="custom")
        **config: Additional configuration (future use)

    Returns:
        Configured CategorizationEngine

    Examples:
        >>> # Basic usage (exact + regex only)
        >>> categorizer = easy_categorization()
        >>> result = categorizer.categorize("Starbucks")
        >>> print(result.category)  # "Coffee Shops"

        >>> # With ML fallback
        >>> categorizer = easy_categorization(enable_ml=True)
        >>> result = categorizer.categorize("Unknown Coffee Shop")
        >>> print(result.category)  # "Coffee Shops" (via ML)
        >>> print(result.confidence)  # 0.85

        >>> # Custom ML model
        >>> categorizer = easy_categorization(
        ...     model="custom",
        ...     enable_ml=True,
        ...     model_path=Path("/path/to/model"),
        ... )
    """
    # Validate taxonomy
    if taxonomy != "mx":
        raise ValueError(f"Unsupported taxonomy: {taxonomy}. Only 'mx' is supported currently.")

    # Validate model
    if model not in ["local", "custom"]:
        raise ValueError(f"Unsupported model: {model}. Use 'local' or 'custom'.")

    # For custom models, model_path is required
    if model == "custom" and model_path is None:
        raise ValueError("model_path is required when model='custom'")

    # Create engine
    engine = CategorizationEngine(
        enable_ml=enable_ml,
        confidence_threshold=confidence_threshold,
        model_path=model_path,
    )

    return engine
