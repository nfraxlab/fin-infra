"""
Recurring transaction detection module.

Provides automatic detection of recurring transactions (subscriptions, bills)
using 3-layer hybrid pattern detection.

Quick Start:
    >>> from fin_infra.recurring import easy_recurring_detection
    >>>
    >>> # Create detector
    >>> detector = easy_recurring_detection()
    >>>
    >>> # Detect patterns
    >>> transactions = [
    ...     {"id": "1", "merchant": "Netflix", "amount": 15.99, "date": "2025-01-15"},
    ...     {"id": "2", "merchant": "Netflix", "amount": 15.99, "date": "2025-02-15"},
    ...     {"id": "3", "merchant": "Netflix", "amount": 15.99, "date": "2025-03-15"},
    ... ]
    >>> patterns = detector.detect_patterns(transactions)

FastAPI Integration:
    >>> from fastapi import FastAPI
    >>> from fin_infra.recurring import add_recurring_detection
    >>>
    >>> app = FastAPI()
    >>> detector = add_recurring_detection(app, prefix="/recurring")
    >>>
    >>> # Available endpoints:
    >>> # POST /recurring/detect
    >>> # GET /recurring/subscriptions
    >>> # GET /recurring/predictions
    >>> # GET /recurring/stats
    >>> # GET /recurring/summary
"""

from .add import add_recurring_detection
from .detector import RecurringDetector
from .ease import easy_recurring_detection
from .models import (
    BillPrediction,
    CadenceType,
    DetectionRequest,
    DetectionResponse,
    PatternType,
    RecurringPattern,
    SubscriptionDetection,
    SubscriptionStats,
)
from .summary import (
    CancellationOpportunity,
    RecurringItem,
    RecurringSummary,
    get_recurring_summary,
)
from .normalizer import (
    FuzzyMatcher,
    get_canonical_merchant,
    is_generic_merchant,
    normalize_merchant,
)

__all__ = [
    # Easy builders
    "easy_recurring_detection",
    "add_recurring_detection",
    # Core classes
    "RecurringDetector",
    "FuzzyMatcher",
    # Models
    "RecurringPattern",
    "SubscriptionDetection",
    "BillPrediction",
    "DetectionRequest",
    "DetectionResponse",
    "SubscriptionStats",
    "RecurringSummary",
    "RecurringItem",
    "CancellationOpportunity",
    # Enums
    "CadenceType",
    "PatternType",
    # Functions
    "get_recurring_summary",
    # Utilities
    "normalize_merchant",
    "get_canonical_merchant",
    "is_generic_merchant",
]
