"""
Transaction categorization module.

Provides ML-based categorization of merchant transactions into 56 categories
using a hybrid approach (exact match → regex → sklearn Naive Bayes → LLM).

Basic usage:
    from fin_infra.categorization import categorize

    result = await categorize("STARBUCKS #12345")
    print(result.category)  # "Coffee Shops"
    print(result.confidence)  # 0.98
    print(result.method)  # "exact"

Advanced usage with engine:
    from fin_infra.categorization import CategorizationEngine

    engine = CategorizationEngine(enable_ml=True, enable_llm=True, confidence_threshold=0.6)
    result = await engine.categorize("Unknown Merchant")

Easy setup with LLM:
    from fin_infra.categorization import easy_categorization

    # Hybrid (sklearn + LLM fallback)
    categorizer = easy_categorization(model="hybrid", enable_ml=True, llm_provider="google")
    result = await categorizer.categorize("Unknown Coffee Shop")
"""

from .add import add_categorization
from .ease import easy_categorization
from .engine import CategorizationEngine, categorize, get_engine
from .models import (
    CategorizationMethod,
    CategorizationRequest,
    CategorizationResponse,
    CategoryOverride,
    CategoryPrediction,
    CategoryRule,
    CategoryStats,
)
from .taxonomy import Category, CategoryGroup, get_all_categories, get_category_group

# LLM layer (optional import)
try:
    from .llm_layer import LLMCategorizer
except ImportError:
    LLMCategorizer = None

__all__ = [
    # Easy setup
    "easy_categorization",
    "add_categorization",
    # Engine
    "CategorizationEngine",
    "categorize",
    "get_engine",
    # LLM layer (V2)
    "LLMCategorizer",
    # Models
    "CategoryPrediction",
    "CategoryRule",
    "CategoryOverride",
    "CategorizationRequest",
    "CategorizationResponse",
    "CategoryStats",
    "CategorizationMethod",
    # Taxonomy
    "Category",
    "CategoryGroup",
    "get_all_categories",
    "get_category_group",
]
