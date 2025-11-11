"""
Pydantic models for recurring transaction detection.

This module defines data models for:
- Recurring patterns (subscriptions, bills)
- Detection results
- Bill predictions
- API request/response models
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CadenceType(str, Enum):
    """Transaction recurrence cadence."""

    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class PatternType(str, Enum):
    """Type of recurring pattern detected."""

    FIXED = "fixed"  # Fixed amount (Netflix, Spotify)
    VARIABLE = "variable"  # Variable amount (utilities, phone)
    IRREGULAR = "irregular"  # Irregular/annual (insurance, memberships)


class RecurringPattern(BaseModel):
    """Detected recurring transaction pattern."""

    merchant_name: str = Field(..., description="Original merchant name")
    normalized_merchant: str = Field(..., description="Normalized merchant name for grouping")
    pattern_type: PatternType = Field(..., description="Pattern type (fixed/variable/irregular)")
    cadence: CadenceType = Field(..., description="Recurrence cadence")

    # Amount information
    amount: float | None = Field(None, description="Fixed amount (for fixed patterns)")
    amount_range: tuple[float, float] | None = Field(
        None, description="Amount range (for variable patterns)"
    )
    amount_variance_pct: float = Field(..., description="Amount variance percentage (0.0-1.0)")

    # Date information
    occurrence_count: int = Field(..., description="Number of occurrences detected", ge=2)
    first_date: datetime = Field(..., description="First occurrence date")
    last_date: datetime = Field(..., description="Last occurrence date")
    next_expected_date: datetime = Field(..., description="Next expected charge date")
    date_std_dev: float = Field(..., description="Standard deviation of days between charges")

    # Confidence and reasoning
    confidence: float = Field(..., description="Detection confidence (0.0-1.0)", ge=0.0, le=1.0)
    reasoning: str | None = Field(None, description="Human-readable detection reasoning")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_name": "NETFLIX.COM",
                "normalized_merchant": "netflix",
                "pattern_type": "fixed",
                "cadence": "monthly",
                "amount": 15.99,
                "amount_range": None,
                "amount_variance_pct": 0.0,
                "occurrence_count": 12,
                "first_date": "2024-01-15T00:00:00Z",
                "last_date": "2024-12-15T00:00:00Z",
                "next_expected_date": "2025-01-15T00:00:00Z",
                "date_std_dev": 0.5,
                "confidence": 0.98,
                "reasoning": "Fixed amount $15.99 charged monthly on 15th (±0 days variance)",
            }
        }
    )


class SubscriptionDetection(BaseModel):
    """User-facing subscription detection result."""

    pattern: RecurringPattern = Field(..., description="Detected recurring pattern")
    historical_transactions: list[str] = Field(
        ..., description="Transaction IDs that match this pattern"
    )
    detected_at: datetime = Field(..., description="When pattern was detected")
    user_confirmed: bool = Field(False, description="User confirmed this subscription")
    user_id: str | None = Field(None, description="User ID (for multi-tenant systems)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pattern": {
                    "merchant_name": "Spotify Premium",
                    "normalized_merchant": "spotify",
                    "pattern_type": "fixed",
                    "cadence": "monthly",
                    "amount": 9.99,
                    "amount_variance_pct": 0.0,
                    "occurrence_count": 6,
                    "confidence": 0.95,
                },
                "historical_transactions": ["txn_001", "txn_002", "txn_003"],
                "detected_at": "2025-11-06T12:00:00Z",
                "user_confirmed": False,
                "user_id": "user_123",
            }
        }
    )


class BillPrediction(BaseModel):
    """Predicted future bill/subscription charge."""

    merchant_name: str = Field(..., description="Merchant name")
    expected_date: datetime = Field(..., description="Expected charge date")
    expected_amount: float | None = Field(None, description="Expected amount (for fixed patterns)")
    expected_range: tuple[float, float] | None = Field(
        None, description="Expected amount range (for variable patterns)"
    )
    confidence: float = Field(..., description="Prediction confidence (0.0-1.0)", ge=0.0, le=1.0)
    cadence: CadenceType = Field(..., description="Recurrence cadence")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_name": "Netflix",
                "expected_date": "2025-12-15T00:00:00Z",
                "expected_amount": 15.99,
                "expected_range": None,
                "confidence": 0.98,
                "cadence": "monthly",
            }
        }
    )


# API Models


class DetectionRequest(BaseModel):
    """Request to detect recurring patterns in transactions."""

    days: int = Field(365, description="Days of transaction history to analyze", ge=30, le=730)
    min_confidence: float = Field(
        0.7, description="Minimum confidence threshold (0.0-1.0)", ge=0.0, le=1.0
    )
    include_predictions: bool = Field(False, description="Include predictions for next charges")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "days": 365,
                "min_confidence": 0.7,
                "include_predictions": True,
            }
        }
    )


class DetectionResponse(BaseModel):
    """Response with detected recurring patterns."""

    patterns: list[RecurringPattern] = Field(..., description="Detected recurring patterns")
    count: int = Field(..., description="Number of patterns detected")
    predictions: list[BillPrediction] | None = Field(
        None, description="Predicted future charges (if requested)"
    )
    processing_time_ms: float | None = Field(None, description="Processing time in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patterns": [
                    {
                        "merchant_name": "Netflix",
                        "normalized_merchant": "netflix",
                        "pattern_type": "fixed",
                        "cadence": "monthly",
                        "amount": 15.99,
                        "confidence": 0.98,
                    }
                ],
                "count": 1,
                "predictions": [
                    {
                        "merchant_name": "Netflix",
                        "expected_date": "2025-12-15T00:00:00Z",
                        "expected_amount": 15.99,
                        "confidence": 0.98,
                        "cadence": "monthly",
                    }
                ],
                "processing_time_ms": 45.2,
            }
        }
    )


class SubscriptionStats(BaseModel):
    """Statistics about detected subscriptions."""

    total_subscriptions: int = Field(..., description="Total number of subscriptions detected")
    monthly_total: float = Field(..., description="Estimated total monthly recurring cost")
    by_pattern_type: dict[str, int] = Field(
        ..., description="Counts by pattern type (fixed/variable/irregular)"
    )
    by_cadence: dict[str, int] = Field(
        ..., description="Counts by cadence (monthly/biweekly/quarterly/annual)"
    )
    top_merchants: list[tuple[str, float]] = Field(
        ..., description="Top merchants by amount [(name, amount), ...]"
    )
    confidence_distribution: dict[str, int] = Field(
        ..., description="Distribution of confidence scores"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_subscriptions": 15,
                "monthly_total": 245.50,
                "by_pattern_type": {"fixed": 12, "variable": 2, "irregular": 1},
                "by_cadence": {"monthly": 13, "quarterly": 1, "annual": 1},
                "top_merchants": [
                    ("Netflix", 15.99),
                    ("Spotify", 9.99),
                    ("Amazon Prime", 14.99),
                ],
                "confidence_distribution": {
                    "high (0.85-1.0)": 12,
                    "medium (0.70-0.84)": 2,
                    "low (0.60-0.69)": 1,
                },
            }
        }
    )
