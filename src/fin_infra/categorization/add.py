"""
FastAPI integration for transaction categorization.

Provides REST API endpoints for categorizing transactions.
Uses svc-infra dual routers for consistent behavior.
"""

import time
from typing import Optional

from fastapi import FastAPI, HTTPException

from .ease import easy_categorization
from .engine import CategorizationEngine
from .models import (
    CategorizationRequest,
    CategorizationResponse,
    CategoryStats,
)
from .taxonomy import CategoryGroup, count_categories, get_all_categories
from . import rules


def add_categorization(
    app: FastAPI,
    prefix: str = "/categorization",
    enable_ml: bool = False,
    confidence_threshold: float = 0.75,
    include_in_schema: bool = True,
) -> CategorizationEngine:
    """
    Add transaction categorization endpoints to FastAPI app.

    Uses svc-infra dual routers for consistent trailing slash handling.

    Args:
        app: FastAPI application
        prefix: URL prefix for categorization endpoints
        enable_ml: Enable ML fallback (Layer 3)
        confidence_threshold: Minimum confidence for ML predictions
        include_in_schema: Include in OpenAPI schema

    Returns:
        Configured CategorizationEngine (for programmatic access)

    Example:
        >>> from fastapi import FastAPI
        >>> from fin_infra.categorization.add import add_categorization
        >>>
        >>> app = FastAPI()
        >>> categorizer = add_categorization(app, enable_ml=True)
        >>>
        >>> # API endpoints available:
        >>> # POST /categorization/predict - Categorize a merchant
        >>> # GET /categorization/categories - List all categories
        >>> # GET /categorization/stats - Get categorization statistics

    Endpoints:
        POST /categorization/predict
            Categorize a merchant transaction.
            Request: {"merchant_name": "Starbucks", "include_alternatives": true}
            Response: {"prediction": {...}, "cached": false, "processing_time_ms": 2.5}

        GET /categorization/categories
            List all available categories.
            Query params: ?group=Income (optional)
            Response: [{"name": "Paycheck", "group": "Income", ...}]

        GET /categorization/stats
            Get categorization statistics.
            Response: {"total_categories": 56, "categories_by_group": {...}, ...}
    """
    # Use svc-infra public_router (categorization is a utility function)
    from svc_infra.api.fastapi.dual.public import public_router

    # Create categorization engine
    engine = easy_categorization(
        enable_ml=enable_ml,
        confidence_threshold=confidence_threshold,
    )

    # Store on app state for access in routes
    app.state.categorization_engine = engine

    # Create router
    router = public_router(prefix=prefix, tags=["Transaction Categorization"])

    @router.post("/predict", response_model=CategorizationResponse)
    async def predict_category(request: CategorizationRequest):
        """
        Categorize a merchant transaction.

        Returns the predicted category, confidence score, and method used.
        Optionally includes top-3 alternative predictions.
        """
        start_time = time.perf_counter()

        try:
            prediction = engine.categorize(
                merchant_name=request.merchant_name,
                user_id=request.user_id,
                include_alternatives=request.include_alternatives,
            )

            # Check minimum confidence
            if prediction.confidence < request.min_confidence:
                raise HTTPException(
                    status_code=422,
                    detail=f"Confidence {prediction.confidence:.2f} below minimum {request.min_confidence:.2f}",
                )

            processing_time = (time.perf_counter() - start_time) * 1000

            return CategorizationResponse(
                prediction=prediction,
                cached=False,  # TODO: Integrate with svc-infra.cache
                processing_time_ms=processing_time,
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/categories")
    async def list_categories(group: Optional[CategoryGroup] = None):
        """
        List all available categories.

        Optionally filter by category group.
        """
        from .taxonomy import get_categories_by_group, get_category_metadata

        if group:
            categories = get_categories_by_group(group)
        else:
            categories = get_all_categories()

        # Return category metadata
        return [
            {
                "name": cat.value,
                "group": get_category_metadata(cat).group.value
                if get_category_metadata(cat)
                else None,
                "display_name": get_category_metadata(cat).display_name
                if get_category_metadata(cat)
                else cat.value,
                "description": get_category_metadata(cat).description
                if get_category_metadata(cat)
                else None,
            }
            for cat in categories
        ]

    @router.get("/stats", response_model=CategoryStats)
    async def get_stats():
        """
        Get categorization statistics.

        Returns category counts, rule counts, and performance metrics.
        """
        category_counts = count_categories()
        rule_counts = rules.get_rule_count()
        engine_stats = engine.get_stats()

        # Calculate cache hit rate from engine stats
        total = engine_stats.get("total", 0)
        cache_hit_rate = None
        if total > 0:
            # Exact + Regex = high confidence (cached)
            cache_hits = engine_stats.get("exact_matches", 0) + engine_stats.get("regex_matches", 0)
            cache_hit_rate = cache_hits / total

        return CategoryStats(
            total_categories=len(get_all_categories()),
            categories_by_group=category_counts,
            total_rules=rule_counts["total"],
            cache_hit_rate=cache_hit_rate,
        )

    # Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    # Scoped docs removed (per architectural decision)
    # All categorization endpoints appear in main /docs

    return engine
