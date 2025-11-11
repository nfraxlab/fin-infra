"""
Pydantic models for transaction categorization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .taxonomy import Category


class CategorizationMethod(str, Enum):
    """Method used for categorization."""

    EXACT = "exact"  # Exact match from dictionary
    REGEX = "regex"  # Regex pattern match
    ML = "ml"  # Machine learning prediction (sklearn)
    LLM = "llm"  # LLM prediction (Layer 4, ai-infra)
    USER_OVERRIDE = "user_override"  # User-defined override
    FALLBACK = "fallback"  # Default fallback


class CategoryPrediction(BaseModel):
    """Result of a category prediction."""

    merchant_name: str = Field(..., description="Original merchant name")
    normalized_name: str = Field(..., description="Normalized merchant name")
    category: Category = Field(..., description="Predicted category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    method: CategorizationMethod = Field(..., description="Method used for categorization")
    alternatives: list[tuple[Category, float]] = Field(
        default_factory=list,
        description="Alternative predictions (category, confidence)",
    )
    reasoning: Optional[str] = Field(None, description="Explanation of prediction (for LLM)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_name": "STARBUCKS #12345",
                "normalized_name": "Starbucks",
                "category": "Coffee Shops",
                "confidence": 0.98,
                "method": "exact",
                "alternatives": [("Restaurants", 0.15), ("Fast Food", 0.10)],
            }
        }
    )


class CategoryRule(BaseModel):
    """A categorization rule."""

    pattern: str = Field(..., description="Merchant name pattern (exact or regex)")
    category: Category = Field(..., description="Category to assign")
    is_regex: bool = Field(default=False, description="Whether pattern is regex")
    priority: int = Field(default=100, description="Rule priority (lower = higher priority)")
    case_sensitive: bool = Field(default=False, description="Case-sensitive matching")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pattern": "STARBUCKS",
                "category": "Coffee Shops",
                "is_regex": False,
                "priority": 100,
                "case_sensitive": False,
            }
        }
    )


class CategoryOverride(BaseModel):
    """User-defined category override."""

    user_id: str = Field(..., description="User ID")
    merchant_name: str = Field(..., description="Merchant name (normalized)")
    category: Category = Field(..., description="User-assigned category")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_123",
                "merchant_name": "Local Coffee Shop",
                "category": "Coffee Shops",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
            }
        }
    )


class CategorizationRequest(BaseModel):
    """Request to categorize a merchant."""

    merchant_name: str = Field(..., description="Merchant name to categorize")
    user_id: Optional[str] = Field(None, description="User ID for personalized overrides")
    include_alternatives: bool = Field(default=False, description="Include alternative predictions")
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "merchant_name": "STARBUCKS #12345",
                "user_id": "user_123",
                "include_alternatives": True,
                "min_confidence": 0.6,
            }
        }
    )


class CategorizationResponse(BaseModel):
    """Response from categorization."""

    prediction: CategoryPrediction
    cached: bool = Field(default=False, description="Whether result was cached")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prediction": {
                    "merchant_name": "STARBUCKS #12345",
                    "normalized_name": "Starbucks",
                    "category": "Coffee Shops",
                    "confidence": 0.98,
                    "method": "exact",
                    "alternatives": [],
                },
                "cached": True,
                "processing_time_ms": 2.5,
            }
        }
    )


class CategoryStats(BaseModel):
    """Statistics about categorization."""

    total_categories: int = Field(..., description="Total number of categories")
    categories_by_group: dict[str, int] = Field(..., description="Category counts by group")
    total_rules: int = Field(..., description="Total number of rules")
    cache_hit_rate: Optional[float] = Field(None, description="Cache hit rate (0-1)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_categories": 56,
                "categories_by_group": {
                    "Income": 5,
                    "Fixed Expenses": 12,
                    "Variable Expenses": 32,
                    "Savings & Investments": 6,
                    "Uncategorized": 1,
                },
                "total_rules": 1500,
                "cache_hit_rate": 0.92,
            }
        }
    )
