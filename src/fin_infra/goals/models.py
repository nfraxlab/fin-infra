"""
Enhanced financial goal models with milestone tracking and funding allocation.

Provides comprehensive data models for:
- Goal types (savings, debt, investment, net_worth, income, custom)
- Goal statuses (active, paused, completed, abandoned)
- Milestone tracking with progress monitoring
- Funding source allocation across accounts
- Goal progress calculations and projections
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================


class GoalType(str, Enum):
    """
    Financial goal types.

    Supports multiple fintech use cases:
    - Personal finance: savings, debt payoff
    - Wealth management: investment targets, net worth milestones
    - Business: revenue goals, income targets
    """

    SAVINGS = "savings"  # General savings goal (emergency fund, vacation, etc.)
    DEBT = "debt"  # Debt payoff goal (credit card, student loan, etc.)
    INVESTMENT = "investment"  # Investment target (portfolio growth)
    NET_WORTH = "net_worth"  # Net worth milestone ($1M net worth, etc.)
    INCOME = "income"  # Income goal (salary target, passive income)
    CUSTOM = "custom"  # Custom goal type


class GoalStatus(str, Enum):
    """
    Goal lifecycle status.

    Tracks goal progression:
    - active: In progress, being tracked
    - paused: Temporarily suspended
    - completed: Target achieved
    - abandoned: Goal given up
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ============================================================================
# Supporting Models
# ============================================================================


class Milestone(BaseModel):
    """
    Goal milestone for tracking progress checkpoints.

    Example: For $100K savings goal, milestones at $25K, $50K, $75K.
    """

    amount: float = Field(..., description="Milestone target amount", gt=0)
    target_date: Optional[datetime] = Field(
        None, description="Target date to reach milestone (optional)"
    )
    description: str = Field(
        ..., description="Milestone description (e.g., '25% to emergency fund')", max_length=200
    )
    reached: bool = Field(default=False, description="Whether milestone has been reached")
    reached_date: Optional[datetime] = Field(
        None, description="Date milestone was reached (if reached=True)"
    )

    @field_validator("reached_date")
    @classmethod
    def validate_reached_date(cls, v, info):
        """Ensure reached_date is set only if reached=True."""
        if v is not None and not info.data.get("reached", False):
            raise ValueError("reached_date can only be set if reached=True")
        return v


class FundingSource(BaseModel):
    """
    Account contributing to goal funding.

    Supports split allocation:
    - Multiple accounts can fund one goal (e.g., savings + checking)
    - One account can fund multiple goals (e.g., savings → emergency + vacation)
    - Allocation percentages must sum to ≤100% per account
    """

    goal_id: str = Field(..., description="Goal identifier")
    account_id: str = Field(..., description="Account identifier")
    allocation_percent: float = Field(
        ...,
        description="Percentage of account contributions allocated to this goal",
        ge=0.0,
        le=100.0,
    )
    account_name: Optional[str] = Field(
        None, description="Human-readable account name (e.g., 'Chase Savings')"
    )


# ============================================================================
# Core Goal Model (Enhanced from management.py)
# ============================================================================


class Goal(BaseModel):
    """
    Enhanced financial goal with full tracking capabilities.

    Extends basic goal from management.py with:
    - Type and status enums
    - Milestone tracking
    - Funding source allocation
    - Auto-contribution settings
    - Custom tags for categorization

    Example:
        goal = Goal(
            id="goal_123",
            user_id="user_456",
            name="Emergency Fund",
            type=GoalType.SAVINGS,
            status=GoalStatus.ACTIVE,
            target_amount=50000.0,
            current_amount=15000.0,
            deadline=datetime(2026, 12, 31),
            milestones=[
                Milestone(amount=25000, description="50% to target"),
                Milestone(amount=37500, description="75% to target"),
            ],
            funding_sources=[
                FundingSource(account_id="checking", allocation_percent=60.0),
                FundingSource(account_id="savings", allocation_percent=40.0),
            ],
            auto_contribute=True,
            tags=["essential", "high-priority"]
        )
    """

    id: str = Field(..., description="Unique goal identifier")
    user_id: str = Field(..., description="User who owns this goal")
    name: str = Field(..., description="Goal name", max_length=200)
    description: Optional[str] = Field(
        None, description="Detailed goal description", max_length=1000
    )

    # Goal type and status
    type: GoalType = Field(..., description="Goal type")
    status: GoalStatus = Field(default=GoalStatus.ACTIVE, description="Current goal status")

    # Financial targets
    target_amount: float = Field(..., description="Target amount to achieve", gt=0)
    current_amount: float = Field(default=0.0, description="Current progress toward target", ge=0.0)
    deadline: Optional[datetime] = Field(None, description="Target completion date")

    # Milestone tracking
    milestones: list[Milestone] = Field(default_factory=list, description="Progress milestones")

    # Funding allocation
    funding_sources: list[FundingSource] = Field(
        default_factory=list, description="Accounts contributing to this goal"
    )
    auto_contribute: bool = Field(
        default=False, description="Enable automatic transfers from funding sources"
    )

    # Organization
    tags: list[str] = Field(
        default_factory=list, description="Custom tags for categorization", max_length=10
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Goal creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Completion timestamp (if status=COMPLETED)"
    )

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v, info):
        """Ensure completed_at is set only if status=COMPLETED."""
        if v is not None and info.data.get("status") != GoalStatus.COMPLETED:
            raise ValueError("completed_at can only be set if status=COMPLETED")
        return v

    @field_validator("current_amount")
    @classmethod
    def validate_current_not_exceeds_target(cls, v, info):
        """Ensure current_amount doesn't exceed target (unless debt goal)."""
        target = info.data.get("target_amount")
        goal_type = info.data.get("type")
        if target and v > target and goal_type != GoalType.DEBT:
            raise ValueError(f"current_amount ({v}) cannot exceed target_amount ({target})")
        return v


# ============================================================================
# Goal Progress Model (Enhanced from management.py stub)
# ============================================================================


class GoalProgress(BaseModel):
    """
    Comprehensive goal progress tracking with projections.

    Replaces 501 stub from management.py with full implementation.
    Calculates:
    - Completion percentage
    - Monthly contribution rates (actual vs target)
    - Projected completion date based on current pace
    - On-track status
    - Milestones reached

    Example:
        progress = GoalProgress(
            goal_id="goal_123",
            current_amount=15000.0,
            target_amount=50000.0,
            percent_complete=30.0,
            monthly_contribution_actual=750.0,
            monthly_contribution_target=1000.0,
            projected_completion_date=datetime(2027, 6, 15),
            on_track=False,
            milestones_reached=[
                Milestone(amount=10000, description="20% milestone", reached=True)
            ]
        )
    """

    goal_id: str = Field(..., description="Goal identifier")

    # Current state
    current_amount: float = Field(..., description="Current amount saved/paid", ge=0)
    target_amount: float = Field(..., description="Target amount", gt=0)
    percent_complete: float = Field(
        ..., description="Completion percentage (0-100)", ge=0.0, le=100.0
    )

    # Contribution tracking
    monthly_contribution_actual: float = Field(
        ..., description="Actual average monthly contribution (last 3 months)", ge=0
    )
    monthly_contribution_target: float = Field(
        ..., description="Required monthly contribution to meet deadline", ge=0
    )

    # Projections
    projected_completion_date: Optional[datetime] = Field(
        None, description="Projected completion date at current pace"
    )
    on_track: bool = Field(..., description="Whether on track to meet deadline")

    # Milestone progress
    milestones_reached: list[Milestone] = Field(
        default_factory=list, description="Milestones that have been reached"
    )

    # Metadata
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this progress was calculated"
    )

    @field_validator("percent_complete", mode="before")
    @classmethod
    def calculate_percent_complete(cls, v, info):
        """Auto-calculate percent_complete if not provided."""
        if v is None:
            current = info.data.get("current_amount", 0)
            target = info.data.get("target_amount", 1)
            return (current / target) * 100 if target > 0 else 0
        return v
