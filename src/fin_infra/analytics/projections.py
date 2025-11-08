"""Growth projections and compound interest calculations.

This module provides net worth projection capabilities with multiple scenarios
(conservative, moderate, aggressive) and compound interest calculations.

Typical usage:
    projection = await project_net_worth(user_id="user123", years=30)

    # Custom assumptions
    projection = await project_net_worth(
        user_id="user123",
        years=30,
        assumptions={
            "conservative_return": 0.05,
            "moderate_return": 0.08,
            "aggressive_return": 0.11,
            "inflation": 0.03,
        }
    )
"""

from typing import Optional
import math

from fin_infra.analytics.models import GrowthProjection, Scenario


# ============================================================================
# Public API
# ============================================================================


async def project_net_worth(
    user_id: str,
    *,
    years: int = 30,
    assumptions: Optional[dict] = None,
    net_worth_provider=None,
    cash_flow_provider=None,
) -> GrowthProjection:
    """Project net worth growth over time with multiple scenarios.

    This function creates financial projections showing how net worth could grow
    based on current financial position, expected contributions, and investment
    returns. Generates three scenarios (conservative, moderate, aggressive) with
    confidence intervals.

    Args:
        user_id: User identifier
        years: Projection period (default: 30 years)
        assumptions: Optional dict with custom assumptions:
            - conservative_return: Annual return % (default: 0.05 = 5%)
            - moderate_return: Annual return % (default: 0.08 = 8%)
            - aggressive_return: Annual return % (default: 0.11 = 11%)
            - inflation: Inflation rate (default: 0.03 = 3%)
            - contribution_growth: Annual contribution increase (default: 0.02 = 2%)
        net_worth_provider: Optional net worth data provider (for future integration)
        cash_flow_provider: Optional cash flow data provider (for future integration)

    Returns:
        GrowthProjection with current net worth, scenarios, and confidence intervals

    Examples:
        >>> projection = await project_net_worth("user123", years=20)
        >>> print(f"Conservative: ${projection.scenarios[0].final_value:,.2f}")
        >>> print(f"Moderate: ${projection.scenarios[1].final_value:,.2f}")
        >>> print(f"Aggressive: ${projection.scenarios[2].final_value:,.2f}")

    Generic use cases:
        - Personal finance apps: Show users retirement projections
        - Wealth management: Client portfolio growth forecasts
        - Financial advisors: What-if scenario planning
        - Investment platforms: Goal-based planning
        - Robo-advisors: Automated retirement planning
    """
    # Default assumptions (industry-standard rates)
    default_assumptions = {
        "conservative_return": 0.05,  # 5% - bond-heavy portfolio
        "moderate_return": 0.08,  # 8% - balanced 60/40 portfolio
        "aggressive_return": 0.11,  # 11% - equity-heavy portfolio
        "inflation": 0.03,  # 3% - long-term inflation target
        "contribution_growth": 0.02,  # 2% - annual salary increase
    }

    # Merge with user assumptions
    if assumptions:
        default_assumptions.update(assumptions)

    # TODO: Integrate with real net_worth module (V2)
    # For now, use mock data
    current_net_worth = _get_mock_net_worth(user_id)

    # TODO: Integrate with real cash_flow module (V2)
    # For now, use mock monthly contribution
    monthly_contribution = _get_mock_monthly_contribution(user_id)

    # Generate scenarios
    scenarios = []
    confidence_intervals = {}

    scenario_configs = [
        ("conservative", default_assumptions["conservative_return"]),
        ("moderate", default_assumptions["moderate_return"]),
        ("aggressive", default_assumptions["aggressive_return"]),
    ]

    for scenario_name, return_rate in scenario_configs:
        # Calculate projections year by year
        projected_values = []
        current_value = current_net_worth
        monthly_contrib = monthly_contribution

        for year in range(years + 1):  # Include year 0
            projected_values.append(current_value)

            if year < years:  # Don't grow after last year
                # Calculate next year's value with contributions
                annual_contribution = monthly_contrib * 12

                # Compound interest formula with periodic contributions
                # Year-end value = start_value * (1 + r) + contributions * (1 + r)
                current_value = current_value * (1 + return_rate) + annual_contribution * (
                    1 + return_rate
                )

                # Grow contributions with salary increases
                monthly_contrib *= 1 + default_assumptions["contribution_growth"]

        final_value = projected_values[-1]

        scenario = Scenario(
            name=scenario_name.capitalize(),
            expected_return=return_rate,
            projected_values=projected_values,
            final_value=final_value,
        )
        scenarios.append(scenario)

        # Calculate confidence intervals (±1 standard deviation)
        # Standard deviation of returns ~15% for stocks, 10% for bonds
        volatility = 0.15 if return_rate >= 0.10 else 0.12 if return_rate >= 0.07 else 0.08
        std_dev = final_value * volatility * math.sqrt(years)

        lower_bound = max(current_net_worth, final_value - std_dev)  # Can't go below starting point
        upper_bound = final_value + std_dev

        confidence_intervals[scenario_name] = (lower_bound, upper_bound)

    return GrowthProjection(
        current_net_worth=current_net_worth,
        years=years,
        monthly_contribution=monthly_contribution,
        scenarios=scenarios,
        assumptions=default_assumptions,
        confidence_intervals=confidence_intervals,
    )


def calculate_compound_interest(
    principal: float,
    rate: float,
    periods: int,
    contribution: float = 0,
) -> float:
    """Calculate compound interest with optional periodic contributions.

    This is the core financial calculation for projecting investment growth.
    Uses the compound interest formula with periodic contributions:

    FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]

    Where:
        - FV = Future Value
        - PV = Present Value (principal)
        - r = Interest rate per period
        - n = Number of periods
        - PMT = Periodic payment (contribution)

    Args:
        principal: Initial investment amount
        rate: Interest rate per period (e.g., 0.08 = 8%)
        periods: Number of compounding periods
        contribution: Periodic contribution amount (default: 0)

    Returns:
        Future value after compound interest

    Examples:
        >>> # $10,000 at 8% for 10 years
        >>> calculate_compound_interest(10000, 0.08, 10)
        21589.25

        >>> # $10,000 at 8% for 10 years with $500/period contribution
        >>> calculate_compound_interest(10000, 0.08, 10, 500)
        28973.15

        >>> # Monthly contributions (convert annual rate to monthly)
        >>> calculate_compound_interest(10000, 0.08/12, 10*12, 500)
        100627.89

    Generic use cases:
        - Retirement calculators: Project 401(k) growth
        - Savings goals: How much to save monthly
        - Investment analysis: Compare investment strategies
        - Loan calculators: Calculate loan payoff (negative contributions)
        - Education planning: 529 plan projections
    """
    if periods <= 0:
        return principal

    if rate == 0:
        # Special case: no interest, just contributions
        return principal + (contribution * periods)

    # Compound interest on principal
    future_value = principal * math.pow(1 + rate, periods)

    # Add future value of periodic contributions (annuity formula)
    if contribution != 0:
        contribution_fv = contribution * ((math.pow(1 + rate, periods) - 1) / rate)
        future_value += contribution_fv

    return future_value


# ============================================================================
# Helper Functions
# ============================================================================


def _get_mock_net_worth(user_id: str) -> float:
    """Get current net worth (mock implementation).

    TODO: Integrate with real net_worth module in V2.

    Args:
        user_id: User identifier

    Returns:
        Current net worth
    """
    # Mock: Starting net worth based on user_id hash
    base = 50000
    variation = hash(user_id) % 100000
    return base + variation


def _get_mock_monthly_contribution(user_id: str) -> float:
    """Get average monthly savings contribution (mock implementation).

    TODO: Integrate with real cash_flow module to calculate average monthly surplus.

    Args:
        user_id: User identifier

    Returns:
        Average monthly contribution
    """
    # Mock: Monthly contribution between $500-$2000
    base = 500
    variation = hash(user_id) % 1500
    return base + variation
