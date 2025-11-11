"""Pydantic models for unified insights feed."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class InsightPriority(str, Enum):
    """Priority levels for insights."""

    CRITICAL = "critical"  # Immediate action needed (e.g., overspending, missed payment)
    HIGH = "high"  # Important recommendations (e.g., tax-loss harvesting opportunities)
    MEDIUM = "medium"  # Helpful suggestions (e.g., save more this month)
    LOW = "low"  # Informational (e.g., portfolio diversification tip)


class InsightCategory(str, Enum):
    """Categories for insights."""

    NET_WORTH = "net_worth"
    SPENDING = "spending"
    PORTFOLIO = "portfolio"
    TAX = "tax"
    BUDGET = "budget"
    CASH_FLOW = "cash_flow"
    GOAL = "goal"
    RECURRING = "recurring"


class Insight(BaseModel):
    """Single insight with actionable information."""

    id: str = Field(..., description="Unique insight ID")
    user_id: str = Field(..., description="User identifier")
    category: InsightCategory = Field(..., description="Insight category")
    priority: InsightPriority = Field(..., description="Priority level")
    title: str = Field(..., description="Short insight title")
    description: str = Field(..., description="Detailed explanation")
    action: str | None = Field(None, description="Suggested action")
    value: Decimal | None = Field(None, description="Associated monetary value")
    metadata: dict | None = Field(None, description="Additional context data")
    read: bool = Field(default=False, description="Whether user has read this insight")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = Field(None, description="When insight is no longer relevant")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "insight_123",
                "user_id": "user_456",
                "category": "tax",
                "priority": "high",
                "title": "Tax-Loss Harvesting Opportunity",
                "description": "You have $5,000 in unrealized losses that could offset gains",
                "action": "Review positions in your taxable account",
                "value": "750",
                "read": False,
                "created_at": "2025-01-15T10:00:00Z",
            }
        }
    }


class InsightFeed(BaseModel):
    """Aggregated feed of insights for a user."""

    user_id: str = Field(..., description="User identifier")
    insights: list[Insight] = Field(default_factory=list, description="List of insights")
    unread_count: int = Field(default=0, description="Number of unread insights")
    critical_count: int = Field(default=0, description="Number of critical insights")
    generated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_456",
                "insights": [],
                "unread_count": 3,
                "critical_count": 1,
                "generated_at": "2025-01-15T10:00:00Z",
            }
        }
    }
