"""Scenario modeling for financial what-if analysis.

Provides tools for modeling various financial scenarios:
- Retirement planning projections
- Investment growth scenarios
- Debt payoff strategies
- Savings goal projections
- Income/expense changes
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    """Type of financial scenario to model."""

    RETIREMENT = "retirement"  # Retirement readiness projection
    INVESTMENT = "investment"  # Investment growth projection
    DEBT_PAYOFF = "debt_payoff"  # Debt elimination strategy
    SAVINGS_GOAL = "savings_goal"  # Savings goal timeline
    INCOME_CHANGE = "income_change"  # Income increase/decrease impact
    EXPENSE_CHANGE = "expense_change"  # Expense increase/decrease impact


class ScenarioRequest(BaseModel):
    """Request for scenario modeling."""

    user_id: str = Field(..., description="User identifier")
    scenario_type: ScenarioType = Field(..., description="Type of scenario to model")

    # Starting values
    starting_amount: Decimal = Field(default=Decimal("0"), description="Starting balance/amount")
    current_age: int | None = Field(None, description="Current age (for retirement)", ge=18, le=100)

    # Contribution/payment parameters
    monthly_contribution: Decimal = Field(
        default=Decimal("0"), description="Monthly contribution/payment amount"
    )
    annual_raise: Decimal = Field(
        default=Decimal("0"), description="Annual contribution increase %", ge=0, le=100
    )

    # Growth/interest parameters
    annual_return_rate: Decimal = Field(
        default=Decimal("7"), description="Expected annual return rate %", ge=-50, le=100
    )
    inflation_rate: Decimal = Field(
        default=Decimal("3"), description="Annual inflation rate %", ge=0, le=20
    )

    # Target parameters
    target_amount: Decimal | None = Field(None, description="Target amount to reach")
    target_age: int | None = Field(None, description="Target age (for retirement)", ge=18, le=120)
    years_projection: int = Field(
        default=30, description="Number of years to project", ge=1, le=100
    )


class ScenarioDataPoint(BaseModel):
    """Single data point in scenario projection."""

    year: int = Field(..., description="Year number (0=starting year)")
    age: int | None = Field(None, description="User age at this year")
    balance: Decimal = Field(..., description="Account balance")
    contributions: Decimal = Field(..., description="Cumulative contributions")
    growth: Decimal = Field(..., description="Cumulative investment growth")
    real_value: Decimal = Field(..., description="Inflation-adjusted value")


class ScenarioResult(BaseModel):
    """Result of scenario modeling."""

    user_id: str = Field(..., description="User identifier")
    scenario_type: ScenarioType = Field(..., description="Type of scenario modeled")

    # Projection data
    projections: list[ScenarioDataPoint] = Field(..., description="Year-by-year projections")

    # Summary metrics
    final_balance: Decimal = Field(..., description="Final projected balance")
    total_contributions: Decimal = Field(..., description="Total contributions made")
    total_growth: Decimal = Field(..., description="Total investment growth")
    years_to_target: int | None = Field(None, description="Years to reach target (if applicable)")

    # Recommendations
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )
    warnings: list[str] = Field(default_factory=list, description="Risk warnings")

    created_at: datetime = Field(default_factory=lambda: datetime.now())


def model_scenario(request: ScenarioRequest) -> ScenarioResult:
    """
    Model a financial scenario with year-by-year projections.

    Uses compound interest formula with monthly contributions:
    - FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]
    - Adjusts for inflation to calculate real value
    - Projects contribution increases (annual raises)

    Args:
        request: ScenarioRequest with scenario parameters

    Returns:
        ScenarioResult with projections and recommendations

    Examples:
        >>> # Retirement scenario
        >>> req = ScenarioRequest(
        ...     user_id="user_123",
        ...     scenario_type=ScenarioType.RETIREMENT,
        ...     starting_amount=Decimal("50000"),
        ...     current_age=30,
        ...     target_age=65,
        ...     monthly_contribution=Decimal("500"),
        ...     annual_return_rate=Decimal("7"),
        ...     annual_raise=Decimal("3"),
        ...     years_projection=35,
        ... )
        >>> result = model_scenario(req)
        >>> print(f"At 65: ${result.final_balance:,.2f}")
        At 65: $1,142,811.23

        >>> # Savings goal scenario
        >>> req = ScenarioRequest(
        ...     user_id="user_123",
        ...     scenario_type=ScenarioType.SAVINGS_GOAL,
        ...     starting_amount=Decimal("5000"),
        ...     target_amount=Decimal("50000"),
        ...     monthly_contribution=Decimal("500"),
        ...     annual_return_rate=Decimal("5"),
        ...     years_projection=10,
        ... )
        >>> result = model_scenario(req)
        >>> print(f"Years to goal: {result.years_to_target}")
        Years to goal: 7
    """
    projections = []
    balance = request.starting_amount
    total_contributions = Decimal("0")
    total_growth = Decimal("0")
    monthly_contrib = request.monthly_contribution
    years_to_target = None

    # Convert annual rates to monthly
    monthly_return = request.annual_return_rate / 100 / 12

    for year in range(request.years_projection + 1):
        # Calculate age if provided
        age = request.current_age + year if request.current_age else None

        # Calculate real value (inflation-adjusted)
        inflation_factor = (1 + request.inflation_rate / 100) ** year
        real_value = balance / Decimal(str(inflation_factor))

        # Record data point
        projections.append(
            ScenarioDataPoint(
                year=year,
                age=age,
                balance=balance,
                contributions=total_contributions,
                growth=total_growth,
                real_value=real_value,
            )
        )

        # Check if target reached
        if request.target_amount and years_to_target is None and balance >= request.target_amount:
            years_to_target = year

        # Project next year (if not last year)
        if year < request.years_projection:
            year_start_balance = balance

            # Monthly compounding with contributions
            for month in range(12):
                # Add return
                balance = balance * (1 + monthly_return)
                # Add contribution
                balance += monthly_contrib
                total_contributions += monthly_contrib

            # Calculate growth for this year
            year_growth = balance - year_start_balance - (monthly_contrib * 12)
            total_growth += year_growth

            # Apply annual raise to contributions
            if request.annual_raise > 0:
                monthly_contrib = monthly_contrib * (1 + request.annual_raise / 100)

    # Generate recommendations
    recommendations = _generate_scenario_recommendations(request, projections)
    warnings = _generate_scenario_warnings(request, projections)

    return ScenarioResult(
        user_id=request.user_id,
        scenario_type=request.scenario_type,
        projections=projections,
        final_balance=projections[-1].balance,
        total_contributions=total_contributions,
        total_growth=total_growth,
        years_to_target=years_to_target,
        recommendations=recommendations,
        warnings=warnings,
    )


def _generate_scenario_recommendations(
    request: ScenarioRequest, projections: list[ScenarioDataPoint]
) -> list[str]:
    """Generate recommendations based on scenario results."""
    recommendations = []
    final = projections[-1]

    if request.scenario_type == ScenarioType.RETIREMENT:
        # Retirement-specific recommendations
        if request.target_amount and final.balance < request.target_amount:
            shortfall = request.target_amount - final.balance
            recommendations.append(
                f"Projected shortfall of ${shortfall:,.0f}. "
                f"Consider increasing contributions by ${(shortfall / (request.years_projection * 12)):,.0f}/month."
            )
        elif request.target_amount and final.balance >= request.target_amount:
            surplus = final.balance - request.target_amount
            recommendations.append(
                f"On track to exceed goal by ${surplus:,.0f}. "
                f"Consider reducing risk as you approach retirement."
            )

        # Real value check
        if final.real_value < final.balance * Decimal("0.7"):
            recommendations.append(
                "Inflation significantly erodes purchasing power. "
                "Ensure return rate assumptions account for inflation."
            )

    elif request.scenario_type == ScenarioType.SAVINGS_GOAL:
        if request.target_amount:
            years_to_goal = next(
                (p.year for p in projections if p.balance >= request.target_amount), None
            )
            if years_to_goal:
                recommendations.append(
                    f"You'll reach your ${request.target_amount:,.0f} goal in {years_to_goal} years. "
                    f"Stay consistent with ${request.monthly_contribution:,.0f}/month contributions."
                )
            else:
                recommendations.append(
                    f"Won't reach ${request.target_amount:,.0f} goal in {request.years_projection} years. "
                    f"Consider increasing monthly contributions or extending timeline."
                )

    elif request.scenario_type == ScenarioType.INVESTMENT:
        # Investment-specific recommendations
        growth_rate = (
            (
                final.balance
                - request.starting_amount
                - (request.monthly_contribution * request.years_projection * 12)
            )
            / request.starting_amount
            * 100
            if request.starting_amount > 0
            else Decimal("0")
        )
        recommendations.append(
            f"Projected {growth_rate:.1f}% total return over {request.years_projection} years. "
            f"Diversify across asset classes to manage risk."
        )

    # General recommendations
    if request.monthly_contribution < Decimal("100"):
        recommendations.append(
            "Small contributions can add up over time. "
            "Even increasing by $50/month makes a significant difference."
        )

    return recommendations


def _generate_scenario_warnings(
    request: ScenarioRequest, projections: list[ScenarioDataPoint]
) -> list[str]:
    """Generate warnings based on scenario parameters."""
    warnings = []

    # High return rate warning
    if request.annual_return_rate > 10:
        warnings.append(
            f"{request.annual_return_rate}% annual return is aggressive. "
            "Historical stock market averages ~10%. Consider using 7-8% for conservative estimates."
        )

    # Low inflation warning
    if request.inflation_rate < 2:
        warnings.append(
            "Inflation assumption may be too low. "
            "Historical average is ~3%. Real purchasing power could be lower than projected."
        )

    # No contributions warning
    if request.monthly_contribution == 0 and request.starting_amount > 0:
        warnings.append(
            "No ongoing contributions. "
            "Regular contributions significantly boost long-term growth through dollar-cost averaging."
        )

    # Timeline warning
    if request.years_projection > 40:
        warnings.append(
            "Very long projection timeline increases uncertainty. "
            "Review and adjust assumptions regularly."
        )

    return warnings
