"""
LLM-validated financial goal tracking with progress monitoring (Section 17 V2).

Provides 4 goal types with validation and progress tracking:
1. Retirement Goal: Calculate required savings for target age/amount
2. Home Purchase Goal: Validate down payment timeline
3. Debt-Free Goal: Debt payoff schedule with APR calculations
4. Wealth Milestone: Project growth to target net worth

Uses ai-infra CoreLLM for validation + local math for calculations.
Weekly progress check-ins via svc-infra.jobs scheduler ($0.0036/user/month).

Example:
    from ai_infra.llm import CoreLLM
    from fin_infra.goals.management import FinancialGoalTracker

    llm = CoreLLM()
    tracker = FinancialGoalTracker(
        llm=llm,
        provider="google",
        model_name="gemini-2.0-flash-exp"
    )

    # Validate retirement goal
    goal = {
        "type": "retirement",
        "target_amount": 2000000.0,
        "target_age": 65,
        "current_age": 40,
        "current_savings": 300000.0,
        "monthly_contribution": 1500.0
    }

    validation = await tracker.validate_goal(goal)
    print(validation.feasibility)  # "feasible"
    print(validation.required_monthly_savings)  # 1500.0

    # Track progress
    progress = await tracker.track_progress(goal, current_net_worth=575000.0)
    print(progress.status)  # "on_track" | "ahead" | "behind" | "off_track"
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas (Structured Output)
# ============================================================================


class GoalValidation(BaseModel):
    """
    LLM validation result for a financial goal.

    Assesses feasibility and provides required monthly savings.
    """

    goal_id: str = Field(..., description="Unique goal identifier")
    goal_type: str = Field(..., description="retirement|home_purchase|debt_free|wealth_milestone")
    feasibility: str = Field(..., description="feasible|challenging|unrealistic")
    required_monthly_savings: float = Field(
        ..., description="Monthly savings needed to achieve goal"
    )
    projected_completion_date: str = Field(
        ..., description="Projected completion date (ISO format)"
    )
    current_progress: float = Field(
        ..., ge=0.0, le=1.0, description="Current progress toward goal (0.0-1.0)"
    )
    alternative_paths: list[str] = Field(
        ..., max_length=3, description="Alternative approaches to achieve goal"
    )
    recommendations: list[str] = Field(..., max_length=5, description="Actionable recommendations")
    confidence: float = Field(..., ge=0.0, le=1.0)


class GoalProgressReport(BaseModel):
    """
    Weekly progress report for a financial goal.

    Compares actual vs target trajectory and suggests course corrections.
    """

    goal_id: str = Field(..., description="Goal identifier")
    status: str = Field(..., description="on_track|ahead|behind|off_track")
    current_progress: float = Field(..., ge=0.0, le=1.0, description="Current progress (0.0-1.0)")
    projected_completion_date: str = Field(
        ..., description="Projected completion date based on current trajectory"
    )
    variance_from_target_days: int = Field(
        ..., description="Days ahead (positive) or behind (negative) target"
    )
    course_corrections: list[str] = Field(
        ..., max_length=5, description="Recommended adjustments if behind"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================================
# System Prompts (Few-Shot Examples)
# ============================================================================

GOAL_VALIDATION_SYSTEM_PROMPT = """You are a financial planner validating goals.

Given a financial goal, you must:
1. Assess feasibility (feasible|challenging|unrealistic)
2. Calculate required monthly savings
3. Suggest 2-3 alternative paths
4. Provide specific recommendations

IMPORTANT: The system will provide you with CALCULATED values (required savings, projected date).
Your job is to provide CONTEXT and ADVICE around these calculations, not redo the math.

Example 1 (Retirement Goal):
Calculated values: Required $1,500/month, projected completion 2050-01-01, feasibility: feasible
Your response: {
  "goal_id": "retire_2050",
  "goal_type": "retirement",
  "feasibility": "feasible",
  "required_monthly_savings": 1500.0,
  "projected_completion_date": "2050-01-01",
  "current_progress": 0.15,
  "alternative_paths": [
    "Increase returns from 7% to 9% (riskier portfolio) to reduce monthly savings to $1,200",
    "Delay retirement by 2 years to age 67 to reduce monthly savings to $1,100",
    "Reduce target from $2M to $1.5M to reduce monthly savings to $1,100"
  ],
  "recommendations": [
    "Maximize 401k contributions ($23k/year limit)",
    "Maintain 7% returns with diversified 70/30 stocks/bonds portfolio",
    "Review progress annually and adjust if behind",
    "Consider catch-up contributions ($7.5k extra) after age 50"
  ],
  "confidence": 0.89
}

Example 2 (Home Purchase Goal):
Calculated values: Required $2,000/month, projected completion 2027-06-01, feasibility: feasible
Your response: {
  "goal_id": "home_2027",
  "goal_type": "home_purchase",
  "feasibility": "feasible",
  "required_monthly_savings": 2000.0,
  "projected_completion_date": "2027-06-01",
  "current_progress": 0.50,
  "alternative_paths": [
    "Reduce down payment from 20% to 10% (requires PMI ~$200/month)",
    "Look for FHA loan with 3.5% down payment ($17.5k vs $100k)",
    "Extend timeline to 2028 to reduce monthly savings to $1,500"
  ],
  "recommendations": [
    "Keep 20% down payment to avoid PMI",
    "Factor in closing costs (~3% of home price = $15k)",
    "Get pre-approved 6 months before target date",
    "Keep emergency fund separate (6 months expenses)"
  ],
  "confidence": 0.91
}

Example 3 (Debt-Free Goal - Unrealistic):
Calculated values: Required $1,800/month, projected completion 2030-06-01, feasibility: unrealistic
Your response: {
  "goal_id": "debt_free_2028",
  "goal_type": "debt_free",
  "feasibility": "unrealistic",
  "required_monthly_savings": 1800.0,
  "projected_completion_date": "2030-06-01",
  "current_progress": 0.20,
  "alternative_paths": [
    "Extend target date to 2030 (currently paying off by 2028 is unrealistic)",
    "Negotiate lower interest rates or consolidate debt to reduce monthly payment",
    "Focus on high-interest debt first (avalanche method) to reduce total interest"
  ],
  "recommendations": [
    "With current $1,200/month payment, debt-free by mid-2030 (not 2028)",
    "Increase payment to $1,400/month to hit 2029 target",
    "Prioritize credit card (22% APR) before student loans (4% APR)",
    "Consider balance transfer to 0% APR card if available"
  ],
  "confidence": 0.94
}

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""

GOAL_PROGRESS_SYSTEM_PROMPT = """You are a financial advisor reviewing goal progress.

Given current vs target progress, you must:
1. Assess status (on_track|ahead|behind|off_track)
2. Calculate variance from target (days ahead/behind)
3. Suggest course corrections if needed

The system provides CALCULATED values. Provide CONTEXT and ADVICE.

Example 1 (On Track):
Calculated: Current progress 0.40, target 0.38, variance +90 days
Your response: {
  "goal_id": "retire_2050",
  "status": "on_track",
  "current_progress": 0.40,
  "projected_completion_date": "2049-09-01",
  "variance_from_target_days": 90,
  "course_corrections": [
    "You're 3 months ahead! Maintain current savings rate of $1,500/month",
    "Consider increasing 401k by 1% to accelerate further",
    "Review allocation annually to maintain 7% returns"
  ],
  "confidence": 0.91
}

Example 2 (Behind):
Calculated: Current progress 0.25, target 0.35, variance -180 days
Your response: {
  "goal_id": "home_2027",
  "status": "behind",
  "current_progress": 0.25,
  "projected_completion_date": "2027-12-01",
  "variance_from_target_days": -180,
  "course_corrections": [
    "You're 6 months behind target. Need to save extra $400/month to catch up",
    "Cut discretionary spending: reduce dining out by $200/month",
    "Increase income: take on freelance work for $200/month",
    "Alternative: extend target date to 2028 and keep current savings rate"
  ],
  "confidence": 0.88
}

Example 3 (Off Track):
Calculated: Current progress 0.15, target 0.40, variance -365 days
Your response: {
  "goal_id": "debt_free_2028",
  "status": "off_track",
  "status": "off_track",
  "current_progress": 0.15,
  "projected_completion_date": "2029-06-01",
  "variance_from_target_days": -365,
  "course_corrections": [
    "⚠️ 12 months behind! Current $1,000/month payment needs to increase to $1,500/month",
    "Emergency: reduce expenses by $500/month (cancel subscriptions, cut entertainment)",
    "Contact debt counselor for consolidation or negotiation options",
    "Consider side income: gig work, selling unused items ($500/month target)",
    "Alternative: extend target to 2029 and focus on highest APR debt first"
  ],
  "confidence": 0.95
}

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""


# ============================================================================
# Financial Calculations (Local Math - Don't Trust LLM)
# ============================================================================


def calculate_retirement_goal(
    target_amount: float,
    target_age: int,
    current_age: int,
    current_savings: float,
    monthly_contribution: float,
    annual_return: float = 0.07,
) -> dict[str, Any]:
    """
    Calculate retirement goal feasibility.

    Formula: FV = PV × (1+r)^n + PMT × (((1+r)^n - 1) / r)

    Args:
        target_amount: Target retirement savings
        target_age: Age to retire
        current_age: Current age
        current_savings: Current retirement savings
        monthly_contribution: Monthly contribution
        annual_return: Expected annual return (default 7%)

    Returns:
        Dict with feasibility, projected_amount, required_monthly
    """
    years = target_age - current_age
    months = years * 12
    monthly_rate = annual_return / 12

    # Future value calculation
    fv_current = current_savings * ((1 + monthly_rate) ** months)
    fv_contributions = monthly_contribution * ((((1 + monthly_rate) ** months) - 1) / monthly_rate)
    projected_amount = fv_current + fv_contributions

    # Calculate required monthly contribution
    required_monthly = (
        (target_amount - fv_current) * monthly_rate / (((1 + monthly_rate) ** months) - 1)
    )

    feasibility = "feasible" if projected_amount >= target_amount else "challenging"
    if projected_amount < target_amount * 0.8:
        feasibility = "unrealistic"

    return {
        "feasibility": feasibility,
        "projected_amount": projected_amount,
        "required_monthly": required_monthly,
        "current_progress": current_savings / target_amount,
    }


def calculate_home_purchase_goal(
    home_price: float,
    down_payment_percent: float,
    target_date: str,
    current_savings: float,
    monthly_savings: float,
) -> dict[str, Any]:
    """
    Calculate home purchase goal feasibility.

    Args:
        home_price: Target home price
        down_payment_percent: Down payment % (e.g., 0.20 = 20%)
        target_date: Target purchase date (ISO format)
        current_savings: Current down payment savings
        monthly_savings: Monthly savings rate

    Returns:
        Dict with feasibility, projected_savings, required_monthly
    """
    down_payment_needed = home_price * down_payment_percent
    closing_costs = home_price * 0.03  # Estimate 3%
    total_needed = down_payment_needed + closing_costs

    # Calculate months to target
    target = datetime.fromisoformat(target_date.split("T")[0])
    now = datetime.utcnow()
    months = (target.year - now.year) * 12 + (target.month - now.month)

    projected_savings = current_savings + (monthly_savings * months)
    required_monthly = (total_needed - current_savings) / months if months > 0 else 0

    feasibility = "feasible" if projected_savings >= total_needed else "challenging"
    if projected_savings < total_needed * 0.85:
        feasibility = "unrealistic"

    return {
        "feasibility": feasibility,
        "projected_savings": projected_savings,
        "required_monthly": required_monthly,
        "current_progress": current_savings / total_needed,
        "total_needed": total_needed,
    }


def calculate_debt_free_goal(
    total_debt: float,
    target_date: str,
    monthly_payment: float,
    weighted_avg_apr: float,
) -> dict[str, Any]:
    """
    Calculate debt-free goal feasibility.

    Args:
        total_debt: Total debt across all accounts
        target_date: Target debt-free date (ISO format)
        monthly_payment: Monthly debt payment
        weighted_avg_apr: Weighted average APR

    Returns:
        Dict with feasibility, projected_payoff_date, required_monthly
    """
    monthly_rate = weighted_avg_apr / 12

    # Calculate months to payoff with current payment
    if monthly_rate > 0:
        months_to_payoff = -1 * (
            (total_debt * monthly_rate - monthly_payment) / (monthly_payment * monthly_rate)
        )
        months_to_payoff = int(months_to_payoff)
    else:
        months_to_payoff = int(total_debt / monthly_payment) if monthly_payment > 0 else 999

    # Calculate target months
    target = datetime.fromisoformat(target_date.split("T")[0])
    now = datetime.utcnow()
    target_months = (target.year - now.year) * 12 + (target.month - now.month)

    # Calculate required monthly payment
    if monthly_rate > 0 and target_months > 0:
        required_monthly = (total_debt * monthly_rate) / (
            1 - ((1 + monthly_rate) ** (-target_months))
        )
    else:
        required_monthly = total_debt / target_months if target_months > 0 else 0

    feasibility = "feasible" if months_to_payoff <= target_months else "challenging"
    if months_to_payoff > target_months * 1.2:
        feasibility = "unrealistic"

    # Projected payoff date
    projected_date = datetime(now.year, now.month, now.day)
    projected_date = projected_date.replace(
        year=projected_date.year + (months_to_payoff // 12),
        month=((projected_date.month + months_to_payoff % 12 - 1) % 12) + 1,
    )

    return {
        "feasibility": feasibility,
        "projected_payoff_date": projected_date.isoformat(),
        "required_monthly": required_monthly,
        "current_progress": 0.0,  # Start at 0% (debt not reduced yet)
        "months_to_payoff": months_to_payoff,
    }


def calculate_wealth_milestone(
    target_net_worth: float,
    target_date: str,
    current_net_worth: float,
    historical_growth_rate: float = 0.15,
) -> dict[str, Any]:
    """
    Calculate wealth milestone goal feasibility.

    Args:
        target_net_worth: Target net worth
        target_date: Target achievement date (ISO format)
        current_net_worth: Current net worth
        historical_growth_rate: Historical annual growth rate (default 15%)

    Returns:
        Dict with feasibility, projected_net_worth, required_growth_rate
    """
    # Calculate years to target
    target = datetime.fromisoformat(target_date.split("T")[0])
    now = datetime.utcnow()
    years = (target.year - now.year) + (target.month - now.month) / 12

    # Project net worth with historical growth
    projected_net_worth = current_net_worth * ((1 + historical_growth_rate) ** years)

    # Calculate required growth rate
    if current_net_worth > 0 and years > 0:
        required_growth_rate = ((target_net_worth / current_net_worth) ** (1 / years)) - 1
    else:
        required_growth_rate = 0.0

    feasibility = "feasible" if projected_net_worth >= target_net_worth else "challenging"
    if required_growth_rate > 0.25:  # >25% annual growth unrealistic
        feasibility = "unrealistic"

    return {
        "feasibility": feasibility,
        "projected_net_worth": projected_net_worth,
        "required_growth_rate": required_growth_rate,
        "current_progress": current_net_worth / target_net_worth,
    }


# ============================================================================
# FinancialGoalTracker
# ============================================================================


class FinancialGoalTracker:
    """
    LLM-validated financial goal tracking with progress monitoring.

    Features:
    - 4 goal types (retirement, home purchase, debt-free, wealth milestone)
    - Local math calculations (don't trust LLM for arithmetic)
    - LLM provides context and advice around calculations
    - Weekly progress tracking with course corrections

    Cost: ~$0.0009/validation, ~$0.0009/week for progress ($0.0036/user/month)

    Example:
        from ai_infra.llm import CoreLLM

        llm = CoreLLM()
        tracker = FinancialGoalTracker(llm=llm, provider="google")

        # Validate goal
        goal = {
            "type": "retirement",
            "target_amount": 2000000.0,
            "target_age": 65,
            "current_age": 40,
            "current_savings": 300000.0,
            "monthly_contribution": 1500.0
        }

        validation = await tracker.validate_goal(goal)
    """

    def __init__(
        self,
        llm: Any,
        provider: str = "google",
        model_name: str = "gemini-2.0-flash-exp",
    ):
        """
        Initialize goal tracker.

        Args:
            llm: ai-infra CoreLLM instance
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model name (default: gemini-2.0-flash-exp)
        """
        self.llm = llm
        self.provider = provider
        self.model_name = model_name

    async def validate_goal(
        self,
        goal: dict[str, Any],
        goal_id: str | None = None,
    ) -> GoalValidation:
        """
        Validate financial goal with LLM context around local calculations.

        Args:
            goal: Goal data with type-specific fields:
                  Retirement: target_amount, target_age, current_age, current_savings, monthly_contribution
                  Home Purchase: home_price, down_payment_percent, target_date, current_savings, monthly_savings
                  Debt-Free: total_debt, target_date, monthly_payment, weighted_avg_apr
                  Wealth Milestone: target_net_worth, target_date, current_net_worth, historical_growth_rate
            goal_id: Optional goal identifier (generated if not provided)

        Returns:
            GoalValidation with feasibility, required savings, alternatives, recommendations

        Cost: ~$0.0009/call
        """
        goal_type = goal.get("type", "unknown")
        goal_id = goal_id or f"{goal_type}_{datetime.utcnow().timestamp()}"

        # Calculate locally (don't trust LLM for math)
        if goal_type == "retirement":
            calc = calculate_retirement_goal(
                target_amount=goal["target_amount"],
                target_age=goal["target_age"],
                current_age=goal["current_age"],
                current_savings=goal["current_savings"],
                monthly_contribution=goal["monthly_contribution"],
                annual_return=goal.get("annual_return", 0.07),
            )
            projected_date = (
                datetime.utcnow()
                .replace(year=goal["target_age"] - goal["current_age"] + datetime.utcnow().year)
                .isoformat()
            )

        elif goal_type == "home_purchase":
            calc = calculate_home_purchase_goal(
                home_price=goal["home_price"],
                down_payment_percent=goal["down_payment_percent"],
                target_date=goal["target_date"],
                current_savings=goal["current_savings"],
                monthly_savings=goal["monthly_savings"],
            )
            projected_date = goal["target_date"]

        elif goal_type == "debt_free":
            calc = calculate_debt_free_goal(
                total_debt=goal["total_debt"],
                target_date=goal["target_date"],
                monthly_payment=goal["monthly_payment"],
                weighted_avg_apr=goal["weighted_avg_apr"],
            )
            projected_date = calc["projected_payoff_date"]

        elif goal_type == "wealth_milestone":
            calc = calculate_wealth_milestone(
                target_net_worth=goal["target_net_worth"],
                target_date=goal["target_date"],
                current_net_worth=goal["current_net_worth"],
                historical_growth_rate=goal.get("historical_growth_rate", 0.15),
            )
            projected_date = goal["target_date"]

        else:
            raise ValueError(f"Unknown goal type: {goal_type}")

        # Build structured output
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=GoalValidation,
            method="json_mode",
        )

        # Build prompt with calculated values
        user_prompt = f"""Validate financial goal:

Goal type: {goal_type}
Goal data: {goal}

CALCULATED VALUES (use these exactly, don't recalculate):
- Feasibility: {calc['feasibility']}
- Required monthly: ${calc['required_monthly']:,.0f}
- Projected completion: {projected_date}
- Current progress: {calc['current_progress']:.1%}

Provide context and advice around these calculations. Suggest 2-3 alternative paths and 3-5 specific recommendations."""

        # Call LLM
        messages = [
            {"role": "system", "content": GOAL_VALIDATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result: GoalValidation = await structured.ainvoke(messages)
        return result

    async def track_progress(
        self,
        goal: dict[str, Any],
        current_net_worth: float,
        goal_id: str | None = None,
    ) -> GoalProgressReport:
        """
        Track goal progress and suggest course corrections.

        Args:
            goal: Goal data (same as validate_goal)
            current_net_worth: Current net worth for progress calculation
            goal_id: Goal identifier (generated if not provided)

        Returns:
            GoalProgressReport with status, variance, course corrections

        Cost: ~$0.0009/call (weekly check-ins via svc-infra.jobs)
        """
        goal_type = goal.get("type", "unknown")
        goal_id = goal_id or f"{goal_type}_{datetime.utcnow().timestamp()}"

        # Calculate current vs target progress
        # (Simplified - in production, compare actual vs planned trajectory)
        validation = await self.validate_goal(goal, goal_id)

        # Determine status based on progress
        if validation.current_progress >= 0.9:
            status = "on_track"
            variance_days = 0
        elif validation.current_progress >= 0.8:
            status = "ahead"
            variance_days = 90
        elif validation.current_progress >= 0.6:
            status = "on_track"
            variance_days = 0
        elif validation.current_progress >= 0.4:
            status = "behind"
            variance_days = -90
        else:
            status = "off_track"
            variance_days = -180

        # Build structured output
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=GoalProgressReport,
            method="json_mode",
        )

        # Build prompt
        user_prompt = f"""Track goal progress:

Goal: {goal}
Current progress: {validation.current_progress:.1%}
Status: {status}
Variance: {variance_days} days

Provide course corrections if behind."""

        # Call LLM
        messages = [
            {"role": "system", "content": GOAL_PROGRESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result: GoalProgressReport = await structured.ainvoke(messages)
        return result


# ============================================================================
# Goal CRUD Operations (In-Memory Storage)
# ============================================================================

# In-memory goal storage for testing/examples
# Applications should use svc-infra DB (SQL/Mongo) for persistence
_GOALS_STORE: dict[str, Any] = {}


def create_goal(
    user_id: str,
    name: str,
    goal_type: str,
    target_amount: float,
    deadline: datetime | None = None,
    description: str | None = None,
    current_amount: float = 0.0,
    milestones: list[dict[str, Any]] | None = None,
    funding_sources: list[dict[str, Any]] | None = None,
    auto_contribute: bool = False,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a new financial goal.

    Args:
        user_id: User identifier
        name: Goal name
        goal_type: Goal type (savings, debt, investment, net_worth, income, custom)
        target_amount: Target amount to achieve
        deadline: Optional target completion date
        description: Optional detailed description
        current_amount: Initial progress amount (default 0.0)
        milestones: Optional list of milestone dicts
        funding_sources: Optional list of funding source dicts
        auto_contribute: Enable automatic transfers (default False)
        tags: Optional list of tags for categorization

    Returns:
        Goal dict with generated ID and timestamps

    Example:
        from fin_infra.goals.management import create_goal
        from datetime import datetime

        goal = create_goal(
            user_id="user_123",
            name="Emergency Fund",
            goal_type="savings",
            target_amount=50000.0,
            deadline=datetime(2026, 12, 31),
            tags=["essential", "high-priority"]
        )

    Note:
        Uses in-memory storage for testing. Applications should use
        svc-infra DB (SQL/Mongo) for persistence. See docs/persistence.md.
    """
    from fin_infra.goals.models import Goal, GoalStatus, GoalType

    goal_id = f"goal_{user_id}_{datetime.utcnow().timestamp()}"

    # Create Goal model instance for validation
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        name=name,
        description=description,
        type=GoalType(goal_type),
        status=GoalStatus.ACTIVE,
        target_amount=target_amount,
        current_amount=current_amount,
        deadline=deadline,
        milestones=[],  # Will be added via milestone tracking
        funding_sources=[],  # Will be added via funding allocation
        auto_contribute=auto_contribute,
        tags=tags or [],
        completed_at=None,  # Not completed yet
    )

    # Store as dict
    goal_dict = goal.model_dump()
    _GOALS_STORE[goal_id] = goal_dict

    return goal_dict


def list_goals(
    user_id: str,
    goal_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """
    List all goals for a user with optional filtering.

    Args:
        user_id: User identifier
        goal_type: Optional filter by goal type
        status: Optional filter by status

    Returns:
        List of goal dicts matching filters

    Example:
        from fin_infra.goals.management import list_goals

        # Get all active savings goals
        goals = list_goals(
            user_id="user_123",
            goal_type="savings",
            status="active"
        )
    """
    results = []

    for goal in _GOALS_STORE.values():
        # Filter by user
        if goal["user_id"] != user_id:
            continue

        # Filter by type if specified
        if goal_type and goal["type"] != goal_type:
            continue

        # Filter by status if specified
        if status and goal["status"] != status:
            continue

        results.append(goal)

    return results


def get_goal(goal_id: str) -> dict[str, Any]:
    """
    Get a goal by ID.

    Args:
        goal_id: Goal identifier

    Returns:
        Goal dict

    Raises:
        KeyError: If goal not found

    Example:
        from fin_infra.goals.management import get_goal

        goal = get_goal("goal_123")
        print(goal["name"])
    """
    if goal_id not in _GOALS_STORE:
        raise KeyError(f"Goal not found: {goal_id}")

    return _GOALS_STORE[goal_id]


def update_goal(
    goal_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a goal with partial updates.

    Args:
        goal_id: Goal identifier
        updates: Dict of fields to update

    Returns:
        Updated goal dict

    Raises:
        KeyError: If goal not found

    Example:
        from fin_infra.goals.management import update_goal

        goal = update_goal(
            "goal_123",
            {"current_amount": 15000.0, "status": "active"}
        )
    """
    if goal_id not in _GOALS_STORE:
        raise KeyError(f"Goal not found: {goal_id}")

    goal = _GOALS_STORE[goal_id]

    # Update fields
    for key, value in updates.items():
        if key in goal and key not in ["id", "user_id", "created_at"]:
            goal[key] = value

    # Update timestamp
    goal["updated_at"] = datetime.utcnow()

    # Validate updated goal
    from fin_infra.goals.models import Goal

    Goal(**goal)  # Will raise ValidationError if invalid

    return goal


def delete_goal(goal_id: str) -> None:
    """
    Delete a goal.

    Args:
        goal_id: Goal identifier

    Raises:
        KeyError: If goal not found

    Example:
        from fin_infra.goals.management import delete_goal

        delete_goal("goal_123")
    """
    if goal_id not in _GOALS_STORE:
        raise KeyError(f"Goal not found: {goal_id}")

    del _GOALS_STORE[goal_id]


def get_goal_progress(goal_id: str) -> dict[str, Any]:
    """
    Calculate comprehensive goal progress with projections.

    Replaces 501 stub. Calculates:
    - Current progress percentage
    - Monthly contributions (actual vs target)
    - Projected completion date
    - On-track status
    - Milestones reached

    Args:
        goal_id: Goal identifier

    Returns:
        GoalProgress dict with calculations

    Raises:
        KeyError: If goal not found

    Example:
        from fin_infra.goals.management import get_goal_progress

        progress = get_goal_progress("goal_123")
        print(f"Progress: {progress['percent_complete']:.1f}%")
        print(f"On track: {progress['on_track']}")

    Note:
        In production, this should integrate with:
        - Banking/brokerage accounts for current_amount
        - Transaction history for actual contribution calculation
        - svc-infra.cache for expensive calculations (24h TTL)
    """
    from fin_infra.goals.models import GoalProgress, Milestone

    goal = get_goal(goal_id)

    # Calculate percent complete
    current = goal["current_amount"]
    target = goal["target_amount"]
    percent_complete = (current / target * 100) if target > 0 else 0

    # Calculate monthly contributions
    # Simplified: In production, query transaction history
    deadline = goal.get("deadline")
    if deadline:
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))

        months_remaining = max(
            (
                (deadline.year - datetime.utcnow().year) * 12
                + (deadline.month - datetime.utcnow().month)
            ),
            1,
        )
        remaining_amount = target - current
        monthly_target = remaining_amount / months_remaining if months_remaining > 0 else 0
    else:
        monthly_target = 0

    # Simplified actual contribution (in production, calculate from transactions)
    monthly_actual = monthly_target * 0.8  # Assume 80% of target for demo

    # Project completion date
    if monthly_actual > 0:
        months_needed = (target - current) / monthly_actual
        now = datetime.utcnow()
        total_months = now.year * 12 + now.month + int(months_needed)
        projected_year = total_months // 12
        projected_month = (total_months % 12) or 12
        if projected_month == 12:
            projected_year -= 1
        projected_date = now.replace(year=projected_year, month=projected_month, day=1)
    else:
        projected_date = None

    # Determine if on track
    on_track = monthly_actual >= monthly_target if monthly_target > 0 else True

    # Check milestones reached
    milestones_reached = []
    for milestone_dict in goal.get("milestones", []):
        milestone = Milestone(**milestone_dict)
        if current >= milestone.amount and not milestone.reached:
            milestone.reached = True
            milestone.reached_date = datetime.utcnow()
            milestones_reached.append(milestone)

    # Create progress model
    progress = GoalProgress(
        goal_id=goal_id,
        current_amount=current,
        target_amount=target,
        percent_complete=percent_complete,
        monthly_contribution_actual=monthly_actual,
        monthly_contribution_target=monthly_target,
        projected_completion_date=projected_date,
        on_track=on_track,
        milestones_reached=milestones_reached,
    )

    return progress.model_dump()


def clear_goals_store() -> None:
    """Clear all goals from storage (for testing)."""
    _GOALS_STORE.clear()
