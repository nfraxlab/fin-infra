"""
Hybrid categorization engine (exact → regex → ML → LLM).

4-layer approach:
1. Layer 1 (Exact Match): O(1) dictionary lookup, 85-90% coverage
2. Layer 2 (Regex): O(n) pattern matching, 5-8% coverage
3. Layer 3 (ML): sklearn Naive Bayes, 3-5% coverage
4. Layer 4 (LLM): ai-infra LLM fallback for low confidence, 2-3% coverage

Expected overall accuracy: 95-97% (V2 with LLM)
"""

import time
import logging
from pathlib import Path
from typing import Optional

from . import rules
from .models import CategorizationMethod, CategoryPrediction
from .taxonomy import Category

# LLM layer (optional, imported only if needed)
try:
    from .llm_layer import LLMCategorizer
except ImportError:
    LLMCategorizer = None

logger = logging.getLogger(__name__)


class CategorizationEngine:
    """
    Hybrid categorization engine.

    Uses 4-layer approach for high accuracy and performance:
    1. Exact match (dictionary)
    2. Regex patterns
    3. Machine learning (sklearn Naive Bayes)
    4. LLM fallback (ai-infra) - V2 feature

    Args:
        enable_ml: Enable ML fallback (Layer 3)
        enable_llm: Enable LLM fallback (Layer 4)
        confidence_threshold: Minimum confidence for ML/LLM trigger (default 0.6)
        model_path: Path to pre-trained ML model
        llm_categorizer: LLMCategorizer instance (Layer 4)
    """

    def __init__(
        self,
        enable_ml: bool = False,
        enable_llm: bool = False,
        confidence_threshold: float = 0.6,
        model_path: Optional[Path] = None,
        llm_categorizer: Optional["LLMCategorizer"] = None,
    ):
        self.enable_ml = enable_ml
        self.enable_llm = enable_llm
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path
        self.llm_categorizer = llm_categorizer

        # ML model (lazy loaded)
        self._ml_model = None
        self._ml_vectorizer = None

        # Statistics
        self.stats = {
            "exact_matches": 0,
            "regex_matches": 0,
            "ml_predictions": 0,
            "llm_predictions": 0,
            "fallback": 0,
        }

        logger.info(
            f"CategorizationEngine initialized: ml={enable_ml}, llm={enable_llm}, "
            f"threshold={confidence_threshold}"
        )

    async def categorize(
        self,
        merchant_name: str,
        user_id: Optional[str] = None,
        include_alternatives: bool = False,
    ) -> CategoryPrediction:
        """
        Categorize a merchant.

        Args:
            merchant_name: Merchant name to categorize
            user_id: User ID for personalized overrides
            include_alternatives: Include top-3 alternative predictions

        Returns:
            CategoryPrediction with category, confidence, and method
        """
        start_time = time.perf_counter()

        # Normalize merchant name
        normalized = self._normalize(merchant_name)

        # Layer 1: Exact match
        category = rules.get_exact_match(normalized)
        if category:
            self.stats["exact_matches"] += 1
            return CategoryPrediction(
                merchant_name=merchant_name,
                normalized_name=normalized,
                category=category,
                confidence=1.0,
                method=CategorizationMethod.EXACT,
                alternatives=[],
            )

        # Layer 2: Regex match
        regex_result = rules.get_regex_match(merchant_name)
        if regex_result:
            category, priority = regex_result
            self.stats["regex_matches"] += 1
            # Higher priority (lower number) = higher confidence
            confidence = max(0.7, 1.0 - (priority / 100))
            return CategoryPrediction(
                merchant_name=merchant_name,
                normalized_name=normalized,
                category=category,
                confidence=confidence,
                method=CategorizationMethod.REGEX,
                alternatives=[],
            )

        # Layer 3: ML prediction (if enabled)
        if self.enable_ml:
            ml_result = self._predict_ml(normalized, include_alternatives)
            if ml_result:
                # Check if confidence is high enough
                if ml_result.confidence >= self.confidence_threshold:
                    self.stats["ml_predictions"] += 1
                    return ml_result

                # Low confidence - try Layer 4 (LLM) if enabled
                if self.enable_llm and self.llm_categorizer:
                    logger.debug(
                        f"sklearn confidence low ({ml_result.confidence:.2f} < {self.confidence_threshold}), "
                        f"trying LLM for '{merchant_name}'"
                    )
                    try:
                        llm_result = await self.llm_categorizer.categorize(
                            merchant_name=merchant_name,
                            user_id=user_id,
                        )

                        # Convert LLM CategoryPrediction to our CategoryPrediction
                        self.stats["llm_predictions"] += 1
                        return CategoryPrediction(
                            merchant_name=merchant_name,
                            normalized_name=normalized,
                            category=Category(llm_result.category),
                            confidence=llm_result.confidence,
                            method=CategorizationMethod.LLM,
                            alternatives=[],
                            reasoning=llm_result.reasoning,
                        )
                    except Exception as e:
                        # LLM failed, fallback to sklearn prediction
                        logger.warning(
                            f"LLM categorization failed for '{merchant_name}': {e}, "
                            f"using sklearn fallback (confidence={ml_result.confidence:.2f})"
                        )
                        self.stats["ml_predictions"] += 1
                        return ml_result
                else:
                    # LLM disabled, use sklearn prediction even if low confidence
                    self.stats["ml_predictions"] += 1
                    return ml_result

        # Fallback: Uncategorized
        self.stats["fallback"] += 1
        return CategoryPrediction(
            merchant_name=merchant_name,
            normalized_name=normalized,
            category=Category.UNCATEGORIZED,
            confidence=0.0,
            method=CategorizationMethod.FALLBACK,
            alternatives=[],
        )

    def _normalize(self, merchant_name: str) -> str:
        """
        Normalize merchant name.

        Uses same normalization as rules module.
        """
        return rules._normalize_merchant(merchant_name)

    def _predict_ml(
        self, merchant_name: str, include_alternatives: bool = False
    ) -> Optional[CategoryPrediction]:
        """
        Predict category using ML model.

        Args:
            merchant_name: Normalized merchant name
            include_alternatives: Include top-3 alternative predictions

        Returns:
            CategoryPrediction if confidence above threshold, None otherwise
        """
        # Lazy load ML model
        if self._ml_model is None:
            self._load_ml_model()

        if self._ml_model is None or self._ml_vectorizer is None:
            return None

        try:
            # Vectorize merchant name
            X = self._ml_vectorizer.transform([merchant_name])

            # Get prediction probabilities
            probabilities = self._ml_model.predict_proba(X)[0]
            classes = self._ml_model.classes_

            # Get top prediction
            top_idx = probabilities.argmax()
            top_category = Category(classes[top_idx])
            top_confidence = float(probabilities[top_idx])

            # Check confidence threshold
            if top_confidence < self.confidence_threshold:
                return None

            # Get alternatives (top 3)
            alternatives = []
            if include_alternatives:
                # Sort by probability (descending)
                sorted_indices = probabilities.argsort()[::-1]
                for idx in sorted_indices[1:4]:  # Top 2-4
                    cat = Category(classes[idx])
                    conf = float(probabilities[idx])
                    if conf > 0.05:  # Only include if > 5% probability
                        alternatives.append((cat, conf))

            return CategoryPrediction(
                merchant_name=merchant_name,
                normalized_name=merchant_name,
                category=top_category,
                confidence=top_confidence,
                method=CategorizationMethod.ML,
                alternatives=alternatives,
            )

        except Exception as e:
            # Log error and return None (will fallback to uncategorized)
            print(f"ML prediction error: {e}")
            return None

    def _load_ml_model(self) -> None:
        """
        Load pre-trained ML model.

        Expected files:
        - model.joblib: sklearn MultinomialNB model
        - vectorizer.joblib: TfidfVectorizer

        These will be created in a separate step.
        """
        if self.model_path is None:
            # Default path: categorization/models/
            self.model_path = Path(__file__).parent / "models"

        model_file = self.model_path / "model.joblib"
        vectorizer_file = self.model_path / "vectorizer.joblib"

        if not model_file.exists() or not vectorizer_file.exists():
            print(f"ML model not found at {self.model_path}")
            print("Run training script to generate model files")
            return

        try:
            import joblib

            self._ml_model = joblib.load(model_file)
            self._ml_vectorizer = joblib.load(vectorizer_file)
            print(f"Loaded ML model from {self.model_path}")
        except ImportError:
            print("scikit-learn not installed. ML predictions disabled.")
            print("Install with: pip install scikit-learn")
        except Exception as e:
            print(f"Error loading ML model: {e}")

    def add_rule(
        self,
        pattern: str,
        category: Category,
        is_regex: bool = False,
    ) -> None:
        """
        Add a custom categorization rule.

        Args:
            pattern: Merchant pattern (exact or regex)
            category: Category to assign
            is_regex: Whether pattern is regex
        """
        rules.add_custom_rule(pattern, category, is_regex)

    def get_stats(self) -> dict:
        """Get categorization statistics."""
        total = sum(self.stats.values())
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "total": total,
            "exact_rate": self.stats["exact_matches"] / total,
            "regex_rate": self.stats["regex_matches"] / total,
            "ml_rate": self.stats["ml_predictions"] / total,
            "fallback_rate": self.stats["fallback"] / total,
        }


# Singleton instance (for easy access)
_default_engine: Optional[CategorizationEngine] = None


def get_engine() -> CategorizationEngine:
    """Get default categorization engine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = CategorizationEngine()
    return _default_engine


def categorize(
    merchant_name: str,
    user_id: Optional[str] = None,
    include_alternatives: bool = False,
) -> CategoryPrediction:
    """
    Categorize a merchant (convenience function).

    Args:
        merchant_name: Merchant name to categorize
        user_id: User ID for personalized overrides (future)
        include_alternatives: Include top-3 alternative predictions

    Returns:
        CategoryPrediction with category, confidence, and method
    """
    engine = get_engine()
    return engine.categorize(merchant_name, user_id, include_alternatives)
