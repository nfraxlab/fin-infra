"""
FastAPI integration for recurring transaction detection.

Provides REST API endpoints for pattern detection, subscription tracking, and predictions.

V2: Adds optional LLM enhancement for merchant normalization, variable detection,
and natural language insights (GET /recurring/insights).
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from .ease import easy_recurring_detection
from .models import (
    BillPrediction,
    DetectionRequest,
    DetectionResponse,
    RecurringPattern,
    SubscriptionStats,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .detector import RecurringDetector


def add_recurring_detection(
    app: FastAPI,
    prefix: str = "/recurring",
    min_occurrences: int = 3,
    amount_tolerance: float = 0.02,
    date_tolerance_days: int = 7,
    enable_llm: bool = False,
    llm_provider: str = "google",
    llm_model: str | None = None,
    include_in_schema: bool = True,
) -> RecurringDetector:
    """
    Add recurring transaction detection endpoints to FastAPI app.

    Mounts 6 endpoints:
    - POST /recurring/detect - Detect patterns in transaction list
    - GET /recurring/subscriptions - List detected subscriptions (cached)
    - GET /recurring/predictions - Predict next bills
    - GET /recurring/stats - Subscription statistics
    - GET /recurring/summary - Comprehensive recurring summary with cancellation opportunities
    - GET /recurring/insights - Natural language insights (V2, LLM-powered)

    Args:
        app: FastAPI application instance
        prefix: URL prefix for endpoints (default: "/recurring")
        min_occurrences: Minimum transactions to detect pattern (default: 3)
        amount_tolerance: Amount variance tolerance (default: 0.02 = 2%)
        date_tolerance_days: Date clustering tolerance (default: 7 days)
        enable_llm: Enable LLM enhancement (V2, default: False)
        llm_provider: LLM provider (V2, default: "google")
        llm_model: LLM model override (V2, default: None)
        include_in_schema: Include endpoints in OpenAPI schema (default: True)

    Returns:
        Configured RecurringDetector instance (stored in app.state)

    Examples:
        >>> from fastapi import FastAPI
        >>> from fin_infra.recurring import add_recurring_detection
        >>>
        >>> app = FastAPI(title="My Finance API")
        >>>
        >>> # V1: Pattern-based detection (fast, $0 cost)
        >>> detector = add_recurring_detection(app)
        >>>
        >>> # V2: LLM-enhanced detection (better accuracy, minimal cost)
        >>> detector = add_recurring_detection(app, enable_llm=True)
        >>>
        >>> # Available endpoints:
        >>> # POST /recurring/detect
        >>> # GET /recurring/subscriptions
        >>> # GET /recurring/predictions
        >>> # GET /recurring/stats
        >>> # GET /recurring/summary
        >>> # GET /recurring/insights (V2 only, requires enable_llm=True)
    """
    # Create detector with V2 parameters
    detector = easy_recurring_detection(
        min_occurrences=min_occurrences,
        amount_tolerance=amount_tolerance,
        date_tolerance_days=date_tolerance_days,
        enable_llm=enable_llm,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

    # Store on app.state
    app.state.recurring_detector = detector

    # Use svc-infra user_router for authentication (recurring detection is user-specific)
    from svc_infra.api.fastapi.dual.protected import user_router

    router = user_router(prefix=prefix, tags=["Recurring Detection"])

    # Route 1: Detect patterns
    @router.post("/detect", response_model=DetectionResponse)
    async def detect_recurring_patterns(request: DetectionRequest):
        """
        Detect recurring patterns in transaction history.

        Analyzes transaction history for recurring subscriptions and bills using
        3-layer hybrid detection (fixed → variable → irregular).

        **Example Request:**
        ```json
        {
          "days": 365,
          "min_confidence": 0.7,
          "include_predictions": true
        }
        ```

        **Returns:**
        - List of detected recurring patterns with confidence scores
        - Optional predictions for next charges
        - Processing time in milliseconds
        """
        start_time = time.time()

        # Persistence: Applications own transaction storage.
        # Transactions typically come from banking providers (Plaid, Teller, etc).
        # Use fin-infra scaffold to generate transaction models if needed.
        # See docs/persistence.md for transaction storage patterns.
        # For now, return empty result with structure.
        # In production: transactions = get_user_transactions(user.id, days=request.days)

        transactions: list[dict[str, Any]] = []  # Placeholder

        # Detect patterns
        patterns = detector.detect_patterns(transactions)

        # Filter by confidence
        patterns = [p for p in patterns if p.confidence >= request.min_confidence]

        # Generate predictions if requested
        predictions = None
        if request.include_predictions:
            predictions = _generate_predictions(patterns)

        processing_time = (time.time() - start_time) * 1000

        return DetectionResponse(
            patterns=patterns,
            count=len(patterns),
            predictions=predictions,
            processing_time_ms=processing_time,
        )

    # Route 2: Get subscriptions (cached)
    @router.get("/subscriptions", response_model=list[RecurringPattern])
    async def get_subscriptions(
        min_confidence: float = 0.7,
        days: int = 365,
    ):
        """
        Get detected subscriptions (cached results).

        Returns cached recurring patterns detected from user's transaction history.

        **Query Parameters:**
        - `min_confidence`: Minimum confidence threshold (0.0-1.0, default: 0.7)
        - `days`: Days of history to analyze (default: 365)

        **Returns:**
        List of recurring patterns sorted by confidence (descending)
        """
        # TODO: Check cache first (svc-infra.cache)
        # cache_key = f"subscriptions:{user_id}:{days}:{min_confidence}"
        # cached = get_from_cache(cache_key)
        # if cached:
        #     return cached

        # Detect patterns (same as /detect endpoint)
        transactions: list[dict[str, Any]] = []  # Placeholder
        patterns = detector.detect_patterns(transactions)
        patterns = [p for p in patterns if p.confidence >= min_confidence]

        # TODO: Cache results (24h TTL)
        # set_cache(cache_key, patterns, ttl=86400)

        return patterns

    # Route 3: Get predictions
    @router.get("/predictions", response_model=list[BillPrediction])
    async def get_bill_predictions(
        days_ahead: int = 30,
        min_confidence: float = 0.7,
    ):
        """
        Predict upcoming bills and subscriptions.

        Predicts future charges based on detected recurring patterns.

        **Query Parameters:**
        - `days_ahead`: Days to predict ahead (default: 30)
        - `min_confidence`: Minimum confidence threshold (default: 0.7)

        **Returns:**
        List of predicted charges with expected dates and amounts
        """
        # Get detected patterns
        transactions: list[dict[str, Any]] = []  # Placeholder
        patterns = detector.detect_patterns(transactions)
        patterns = [p for p in patterns if p.confidence >= min_confidence]

        # Generate predictions for next N days
        predictions = _generate_predictions(patterns, days_ahead=days_ahead)

        return predictions

    # Route 4: Get statistics
    @router.get("/stats", response_model=SubscriptionStats)
    async def get_subscription_stats():
        """
        Get subscription statistics.

        Returns aggregate statistics about detected recurring transactions:
        - Total subscriptions count
        - Estimated monthly total
        - Breakdown by pattern type and cadence
        - Top merchants by amount
        """
        # Get all detected patterns
        transactions: list[dict[str, Any]] = []  # Placeholder
        patterns = detector.detect_patterns(transactions)

        # Calculate stats
        stats = _calculate_stats(patterns)

        return stats

    # Route 5: Get recurring summary
    @router.get("/summary")
    async def get_recurring_summary(
        user_id: str,
        category_map: dict[str, str] | None = None,
    ):
        """
        Get comprehensive recurring transaction summary.

        Aggregates detected recurring patterns into a user-friendly summary with:
        - Total monthly cost (all cadences normalized)
        - Subscriptions vs recurring income
        - Category-based grouping
        - Cancellation opportunities (duplicate services, low-confidence subscriptions)

        **Query Parameters:**
        - `user_id`: User identifier (required)
        - `category_map`: Optional custom category mapping (JSON object)

        **Returns:**
        RecurringSummary with:
        - `total_monthly_cost`: Estimated monthly expense (all cadences normalized)
        - `total_monthly_income`: Estimated monthly recurring income
        - `subscriptions`: List of expense recurring items
        - `recurring_income`: List of income recurring items
        - `by_category`: Monthly cost grouped by category
        - `cancellation_opportunities`: Cost-saving suggestions
        - `generated_at`: Timestamp

        **Example Response:**
        ```json
        {
          "user_id": "user123",
          "total_monthly_cost": 89.97,
          "total_monthly_income": 500.00,
          "subscriptions": [
            {
              "merchant_name": "Netflix",
              "category": "Entertainment",
              "amount": 15.99,
              "cadence": "monthly",
              "monthly_cost": 15.99,
              "is_subscription": true,
              "next_charge_date": "2025-12-15",
              "confidence": 0.95
            }
          ],
          "recurring_income": [
            {
              "merchant_name": "Employer Direct Deposit",
              "category": "Income",
              "amount": 2000.00,
              "cadence": "biweekly",
              "monthly_cost": 4333.33,
              "is_subscription": false,
              "next_charge_date": "2025-12-01",
              "confidence": 0.98
            }
          ],
          "by_category": {
            "Entertainment": 31.98,
            "Fitness": 29.99,
            "Software": 19.99
          },
          "cancellation_opportunities": [
            {
              "merchant_name": "Hulu",
              "reason": "You have multiple streaming services. Consider consolidating.",
              "monthly_savings": 7.99,
              "category": "Entertainment"
            }
          ],
          "generated_at": "2025-11-10T14:30:00Z"
        }
        ```

        **Caching:** Results cached for 24 hours (recommended in production)

        **Performance:** <50ms typical response time with cached patterns
        """
        from .summary import get_recurring_summary

        # Get detected patterns for user
        transactions: list[
            dict[str, Any]
        ] = []  # Placeholder - in production: get_user_transactions(user_id)
        patterns = detector.detect_patterns(transactions)

        # Generate summary
        summary = get_recurring_summary(
            user_id=user_id,
            patterns=patterns,
            category_map=category_map,
        )

        # TODO: Cache results for 24h
        # cache_key = f"recurring_summary:{user_id}"
        # set_cache(cache_key, summary, ttl=86400)

        return summary

    # Route 6: Get insights (V2, LLM-powered)
    if enable_llm and detector.insights_generator:

        @router.get("/insights")
        async def get_subscription_insights():
            """
            Get natural language subscription insights (V2, LLM-powered).

            **Requires:** enable_llm=True when adding detector to app

            Returns personalized insights about user's subscriptions:
            - Monthly spending summary
            - Top 5 subscriptions by cost
            - Cost-saving recommendations (bundle deals, unused subscriptions)
            - Potential monthly savings

            **Example Response:**
            ```json
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
            ```

            **Cache:** Results cached for 24 hours (80% hit rate expected)

            **Cost:** ~$0.0002/generation with Google Gemini, <$0.00004 effective with caching
            """
            # Get detected patterns
            transactions: list[dict[str, Any]] = []  # Placeholder
            patterns = detector.detect_patterns(transactions)

            # Convert patterns to subscription dicts for LLM
            subscriptions = [
                {
                    "merchant": p.merchant_name,
                    "amount": p.amount or 0.0,
                    "cadence": p.cadence.value if hasattr(p.cadence, "value") else str(p.cadence),
                }
                for p in patterns
                if p.amount is not None
            ]

            if not subscriptions:
                # Return empty insights if no subscriptions detected
                from .insights import SubscriptionInsights

                return SubscriptionInsights(
                    summary="No recurring subscriptions detected in your transaction history.",
                    top_subscriptions=[],
                    recommendations=[],
                    total_monthly_cost=0.0,
                    potential_savings=None,
                )

            # Generate insights with LLM
            # TODO: Pass user_id for better caching (currently uses subscriptions hash)
            insights_generator = detector.insights_generator
            if insights_generator is None:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=500,
                    detail="Subscription insights generator not configured (enable_llm=True required).",
                )

            insights = await insights_generator.generate(subscriptions)

            return insights
    else:
        # Endpoint not available when LLM disabled
        @router.get("/insights")
        async def get_subscription_insights_disabled():
            """
            Natural language insights (DISABLED - requires enable_llm=True).

            This endpoint is only available when the detector is initialized with
            `enable_llm=True`. Enable LLM enhancement to access personalized
            subscription insights and recommendations.
            """
            from fastapi import HTTPException

            raise HTTPException(
                status_code=501,
                detail=(
                    "Subscription insights require LLM enhancement. "
                    "Initialize detector with enable_llm=True to enable this endpoint."
                ),
            )

    # Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    return detector


def _generate_predictions(
    patterns: list[RecurringPattern],
    days_ahead: int = 30,
) -> list[BillPrediction]:
    """
    Generate bill predictions from patterns.

    Args:
        patterns: Detected recurring patterns
        days_ahead: Days to predict ahead

    Returns:
        List of BillPrediction objects
    """
    predictions = []
    cutoff_date = datetime.now() + timedelta(days=days_ahead)

    for pattern in patterns:
        # Only predict if next_expected_date is within cutoff
        if pattern.next_expected_date <= cutoff_date:
            prediction = BillPrediction(
                merchant_name=pattern.merchant_name,
                expected_date=pattern.next_expected_date,
                expected_amount=pattern.amount,
                expected_range=pattern.amount_range,
                confidence=pattern.confidence,
                cadence=pattern.cadence,
            )
            predictions.append(prediction)

    # Sort by expected date
    return sorted(predictions, key=lambda x: x.expected_date)


def _calculate_stats(patterns: list[RecurringPattern]) -> SubscriptionStats:
    """
    Calculate subscription statistics.

    Args:
        patterns: Detected recurring patterns

    Returns:
        SubscriptionStats object
    """
    from collections import Counter

    if not patterns:
        return SubscriptionStats(
            total_subscriptions=0,
            monthly_total=0.0,
            by_pattern_type={},
            by_cadence={},
            top_merchants=[],
            confidence_distribution={},
        )

    # Count by pattern type
    by_pattern_type = dict(Counter(p.pattern_type.value for p in patterns))

    # Count by cadence
    by_cadence = dict(Counter(p.cadence.value for p in patterns))

    # Calculate monthly total (estimate)
    monthly_total = 0.0
    for pattern in patterns:
        if pattern.amount:
            # Convert to monthly equivalent
            if pattern.cadence.value == "monthly":
                monthly_total += pattern.amount
            elif pattern.cadence.value == "biweekly":
                monthly_total += pattern.amount * 2
            elif pattern.cadence.value == "quarterly":
                monthly_total += pattern.amount / 3
            elif pattern.cadence.value == "annual":
                monthly_total += pattern.amount / 12

    # Top merchants by amount
    merchants_with_amount = [(p.merchant_name, p.amount) for p in patterns if p.amount is not None]
    top_merchants = sorted(merchants_with_amount, key=lambda x: x[1], reverse=True)[:5]

    # Confidence distribution
    confidence_dist = {
        "high (0.85-1.0)": sum(1 for p in patterns if p.confidence >= 0.85),
        "medium (0.70-0.84)": sum(1 for p in patterns if 0.70 <= p.confidence < 0.85),
        "low (0.60-0.69)": sum(1 for p in patterns if 0.60 <= p.confidence < 0.70),
    }

    return SubscriptionStats(
        total_subscriptions=len(patterns),
        monthly_total=monthly_total,
        by_pattern_type=by_pattern_type,
        by_cadence=by_cadence,
        top_merchants=top_merchants,
        confidence_distribution=confidence_dist,
    )
