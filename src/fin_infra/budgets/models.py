"""Pydantic models for budget management.

This module defines the data models for budgets, categories, progress tracking,
alerts, and templates. All models are generic and application-agnostic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BudgetType(str, Enum):
    """Budget type classification.

    Generic across applications:
    - personal: Individual budget (personal finance apps)
    - household: Shared family budget (household management)
    - business: Company/department budget (business accounting)
    - project: Project-specific budget (project management)
    - custom: User-defined budget type
    """

    PERSONAL = "personal"
    HOUSEHOLD = "household"
    BUSINESS = "business"
    PROJECT = "project"
    CUSTOM = "custom"


class BudgetPeriod(str, Enum):
    """Budget period for tracking cycles.

    Supports various budgeting frequencies:
    - weekly: 7 days (short-term tracking)
    - biweekly: 14 days (paycheck cycles)
    - monthly: 30 days (most common)
    - quarterly: 90 days (business planning)
    - yearly: 365 days (annual budgets)
    """

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AlertType(str, Enum):
    """Budget alert type classification.

    Alert types for budget monitoring:
    - overspending: Spent amount exceeds budgeted amount
    - approaching_limit: Spent > threshold% of budgeted (default 80%)
    - unusual_spending: Spending spike detected (>25% above historical average)
    """

    OVERSPENDING = "overspending"
    APPROACHING_LIMIT = "approaching_limit"
    UNUSUAL_SPENDING = "unusual_spending"


class AlertSeverity(str, Enum):
    """Alert severity levels for prioritization."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Budget(BaseModel):
    """Budget model for tracking planned vs actual spending.

    Generic across applications:
    - Personal finance: Individual monthly budgets
    - Household: Family shared budgets
    - Business: Department/company budgets
    - Project: Project-specific expense budgets

    Attributes:
        id: Unique budget identifier
        user_id: User/owner identifier
        name: Budget name (e.g., "November 2025", "Q4 Marketing")
        type: Budget type (personal, household, business, project, custom)
        period: Budget period (weekly, biweekly, monthly, quarterly, yearly)
        categories: Dict mapping category names to budgeted amounts
        start_date: Budget period start date
        end_date: Budget period end date
        rollover_enabled: Whether unused budget carries over to next period
        created_at: Budget creation timestamp
        updated_at: Last update timestamp

    Examples:
        >>> budget = Budget(
        ...     id="bud_123",
        ...     user_id="user_123",
        ...     name="November 2025",
        ...     type=BudgetType.PERSONAL,
        ...     period=BudgetPeriod.MONTHLY,
        ...     categories={
        ...         "Groceries": 600.00,
        ...         "Restaurants": 200.00,
        ...         "Transportation": 150.00,
        ...     },
        ...     start_date=datetime(2025, 11, 1),
        ...     end_date=datetime(2025, 11, 30),
        ...     rollover_enabled=True,
        ... )
    """

    id: str = Field(..., description="Unique budget identifier")
    user_id: str = Field(..., description="User/owner identifier")
    name: str = Field(..., description="Budget name", min_length=1, max_length=200)
    type: BudgetType = Field(..., description="Budget type classification")
    period: BudgetPeriod = Field(..., description="Budget tracking period")
    categories: dict[str, float] = Field(
        ..., description="Category name to budgeted amount mapping"
    )
    start_date: datetime = Field(..., description="Budget period start date")
    end_date: datetime = Field(..., description="Budget period end date")
    rollover_enabled: bool = Field(default=False, description="Whether unused budget carries over")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "bud_123",
                "user_id": "user_123",
                "name": "November 2025",
                "type": "personal",
                "period": "monthly",
                "categories": {
                    "Groceries": 600.00,
                    "Restaurants": 200.00,
                    "Transportation": 150.00,
                },
                "start_date": "2025-11-01T00:00:00",
                "end_date": "2025-11-30T23:59:59",
                "rollover_enabled": True,
                "created_at": "2025-11-01T00:00:00",
                "updated_at": "2025-11-01T00:00:00",
            }
        }
    )


class BudgetCategory(BaseModel):
    """Budget category with spending tracking.

    Tracks budgeted vs actual spending for a single category.

    Attributes:
        category_name: Category name (e.g., "Groceries", "Marketing")
        budgeted_amount: Planned spending amount
        spent_amount: Actual spending amount
        remaining_amount: Budget remaining (budgeted - spent)
        percent_used: Percentage of budget used (spent / budgeted * 100)

    Examples:
        >>> category = BudgetCategory(
        ...     category_name="Groceries",
        ...     budgeted_amount=600.00,
        ...     spent_amount=425.50,
        ...     remaining_amount=174.50,
        ...     percent_used=70.92,
        ... )
    """

    category_name: str = Field(..., description="Category name")
    budgeted_amount: float = Field(..., description="Planned spending amount", ge=0)
    spent_amount: float = Field(..., description="Actual spending amount", ge=0)
    remaining_amount: float = Field(..., description="Budget remaining")
    percent_used: float = Field(..., description="Percentage of budget used", ge=0, le=200)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_name": "Groceries",
                "budgeted_amount": 600.00,
                "spent_amount": 425.50,
                "remaining_amount": 174.50,
                "percent_used": 70.92,
            }
        }
    )


class BudgetProgress(BaseModel):
    """Budget progress tracking for current period.

    Provides real-time view of budget performance across all categories.

    Attributes:
        budget_id: Budget identifier
        current_period: Period being tracked (e.g., "November 2025", "Q4 2025")
        categories: List of category progress details
        total_budgeted: Sum of all budgeted amounts
        total_spent: Sum of all spent amounts
        total_remaining: Total budget remaining
        percent_used: Overall budget usage percentage
        period_days_elapsed: Days elapsed in current period
        period_days_total: Total days in period

    Examples:
        >>> progress = BudgetProgress(
        ...     budget_id="bud_123",
        ...     current_period="November 2025",
        ...     categories=[
        ...         BudgetCategory(
        ...             category_name="Groceries",
        ...             budgeted_amount=600.00,
        ...             spent_amount=425.50,
        ...             remaining_amount=174.50,
        ...             percent_used=70.92,
        ...         ),
        ...     ],
        ...     total_budgeted=950.00,
        ...     total_spent=605.75,
        ...     total_remaining=344.25,
        ...     percent_used=63.76,
        ...     period_days_elapsed=15,
        ...     period_days_total=30,
        ... )
    """

    budget_id: str = Field(..., description="Budget identifier")
    current_period: str = Field(..., description="Period being tracked")
    categories: list[BudgetCategory] = Field(..., description="Category progress details")
    total_budgeted: float = Field(..., description="Sum of all budgeted amounts", ge=0)
    total_spent: float = Field(..., description="Sum of all spent amounts", ge=0)
    total_remaining: float = Field(..., description="Total budget remaining")
    percent_used: float = Field(..., description="Overall budget usage percentage", ge=0, le=200)
    period_days_elapsed: int = Field(..., description="Days elapsed in current period", ge=0)
    period_days_total: int = Field(..., description="Total days in period", ge=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "budget_id": "bud_123",
                "current_period": "November 2025",
                "categories": [
                    {
                        "category_name": "Groceries",
                        "budgeted_amount": 600.00,
                        "spent_amount": 425.50,
                        "remaining_amount": 174.50,
                        "percent_used": 70.92,
                    },
                    {
                        "category_name": "Restaurants",
                        "budgeted_amount": 200.00,
                        "spent_amount": 180.25,
                        "remaining_amount": 19.75,
                        "percent_used": 90.13,
                    },
                ],
                "total_budgeted": 950.00,
                "total_spent": 605.75,
                "total_remaining": 344.25,
                "percent_used": 63.76,
                "period_days_elapsed": 15,
                "period_days_total": 30,
            }
        }
    )


class BudgetAlert(BaseModel):
    """Budget alert for overspending or unusual patterns.

    Alerts users when budget thresholds are exceeded or unusual spending detected.

    Attributes:
        budget_id: Budget identifier
        category: Category triggering alert (None for budget-level alerts)
        alert_type: Type of alert (overspending, approaching_limit, unusual_spending)
        threshold: Threshold that triggered alert (percentage or absolute amount)
        message: Human-readable alert message
        triggered_at: Timestamp when alert was triggered
        severity: Alert severity level (info, warning, critical)

    Examples:
        >>> alert = BudgetAlert(
        ...     budget_id="bud_123",
        ...     category="Restaurants",
        ...     alert_type=AlertType.APPROACHING_LIMIT,
        ...     threshold=80.0,
        ...     message="Restaurants spending is at 90% of budget (80% threshold)",
        ...     triggered_at=datetime.now(),
        ...     severity=AlertSeverity.WARNING,
        ... )
    """

    budget_id: str = Field(..., description="Budget identifier")
    category: Optional[str] = Field(None, description="Category triggering alert")
    alert_type: AlertType = Field(..., description="Type of alert")
    threshold: float = Field(..., description="Threshold that triggered alert")
    message: str = Field(..., description="Human-readable alert message")
    triggered_at: datetime = Field(..., description="Timestamp when alert was triggered")
    severity: AlertSeverity = Field(..., description="Alert severity level")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "budget_id": "bud_123",
                "category": "Restaurants",
                "alert_type": "approaching_limit",
                "threshold": 80.0,
                "message": "Restaurants spending is at 90% of budget (80% threshold)",
                "triggered_at": "2025-11-07T23:30:00",
                "severity": "warning",
            }
        }
    )


class BudgetTemplate(BaseModel):
    """Budget template for quick budget creation.

    Pre-built or custom templates for common budgeting strategies.

    Built-in templates:
    - 50/30/20: 50% needs, 30% wants, 20% savings (personal finance)
    - Zero-based: Every dollar allocated (detailed budgeting)
    - Envelope: Cash-like category limits (spending control)
    - Business: Common business expense categories
    - Project: Project-specific budget template

    Attributes:
        name: Template name (e.g., "50/30/20", "Zero-based")
        type: Budget type this template applies to
        categories: Dict mapping category names to percentage/amount allocations
        description: Template description and use case
        is_custom: Whether this is a user-created custom template

    Examples:
        >>> template = BudgetTemplate(
        ...     name="50/30/20",
        ...     type=BudgetType.PERSONAL,
        ...     categories={
        ...         "Housing": 0.25,
        ...         "Groceries": 0.15,
        ...         "Transportation": 0.10,
        ...         "Dining Out": 0.10,
        ...         "Entertainment": 0.10,
        ...         "Shopping": 0.10,
        ...         "Savings": 0.20,
        ...     },
        ...     description="50% needs, 30% wants, 20% savings",
        ...     is_custom=False,
        ... )
    """

    name: str = Field(..., description="Template name", min_length=1, max_length=100)
    type: BudgetType = Field(..., description="Budget type this template applies to")
    categories: dict[str, float] = Field(
        ..., description="Category name to percentage/amount allocation"
    )
    description: str = Field(..., description="Template description and use case")
    is_custom: bool = Field(default=False, description="Whether this is a custom template")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "50/30/20",
                "type": "personal",
                "categories": {
                    "Housing": 0.25,
                    "Groceries": 0.15,
                    "Transportation": 0.10,
                    "Dining Out": 0.10,
                    "Entertainment": 0.10,
                    "Shopping": 0.10,
                    "Savings": 0.20,
                },
                "description": "50% needs, 30% wants, 20% savings",
                "is_custom": False,
            }
        }
    )
