"""Savings rate analysis.

Provides savings rate calculations with multiple definitions and period support.

Generic Applicability:
- Personal finance: Track monthly savings goals
- Wealth management: Client savings rate benchmarking
- Budgeting tools: Savings progress monitoring
- Banking apps: Savings insights and recommendations
- Business accounting: Profit retention analysis

Examples:
    >>> # Calculate monthly net savings rate
    >>> result = await calculate_savings_rate("user123", period="monthly", definition="net")
    >>> print(f"Savings rate: {result.savings_rate:.1%}")

    >>> # Calculate gross savings rate (pre-tax)
    >>> result = await calculate_savings_rate("user123", period="monthly", definition="gross")

    >>> # Calculate discretionary savings (after necessities)
    >>> result = await calculate_savings_rate("user123", period="monthly", definition="discretionary")
"""

from fin_infra.analytics.models import (
    Period,
    SavingsDefinition,
    SavingsRateData,
    TrendDirection,
)


async def calculate_savings_rate(
    user_id: str,
    *,
    period: str = "monthly",
    definition: str = "net",
    historical_months: int = 6,
    banking_provider=None,
    categorization_provider=None,
) -> SavingsRateData:
    """Calculate savings rate for a user.

    Supports multiple calculation definitions:
    - GROSS: (Income - Expenses) / Gross Income
    - NET: (Income - Expenses) / Net Income (after tax)
    - DISCRETIONARY: (Income - Expenses) / Discretionary Income (after necessities)

    Args:
        user_id: User identifier
        period: Period type (weekly/monthly/quarterly/yearly)
        definition: Savings definition (gross/net/discretionary)
        historical_months: Number of past months for trend analysis
        banking_provider: Banking data provider (optional, for DI)
        categorization_provider: Categorization provider (optional, for DI)

    Returns:
        SavingsRateData with savings rate, amount, and trend

    Raises:
        ValueError: If period or definition invalid

    Examples:
        >>> # Monthly net savings rate
        >>> result = await calculate_savings_rate("user123", period="monthly")
        >>> result.savings_rate
        0.25  # 25% savings rate

        >>> # Quarterly gross savings
        >>> result = await calculate_savings_rate(
        ...     "user123",
        ...     period="quarterly",
        ...     definition="gross"
        ... )
    """
    # Validate inputs
    try:
        period_enum = Period(period)
    except ValueError:
        raise ValueError(
            f"Invalid period '{period}'. Must be one of: " f"{', '.join([p.value for p in Period])}"
        )

    try:
        definition_enum = SavingsDefinition(definition)
    except ValueError:
        raise ValueError(
            f"Invalid definition '{definition}'. Must be one of: "
            f"{', '.join([d.value for d in SavingsDefinition])}"
        )

    # Calculate period date range (TODO: Use for banking provider integration)
    # end_date = datetime.now()
    # Calculate start_date but commented until banking provider integration
    # if period_enum == Period.WEEKLY:
    #     start_date = end_date - timedelta(days=7)
    # elif period_enum == Period.MONTHLY:
    #     start_date = end_date - timedelta(days=30)
    # elif period_enum == Period.QUARTERLY:
    #     start_date = end_date - timedelta(days=90)
    # else:  # YEARLY
    #     start_date = end_date - timedelta(days=365)

    # TODO: Fetch transactions from banking provider
    # transactions = await banking_provider.get_transactions(
    #     user_id=user_id,
    #     start_date=start_date,
    #     end_date=end_date,
    # )

    # TODO: Calculate income and expenses from real transactions
    # For now, mock data based on definition
    if definition_enum == SavingsDefinition.GROSS:
        # Gross income (before tax)
        gross_income = 6000.0
        expenses = 3500.0
        savings_amount = gross_income - expenses
        savings_rate = savings_amount / gross_income if gross_income > 0 else 0.0
        income_for_calculation = gross_income

    elif definition_enum == SavingsDefinition.NET:
        # Net income (after tax)
        gross_income = 6000.0
        tax = 1200.0
        net_income = gross_income - tax
        expenses = 3500.0
        savings_amount = net_income - expenses
        savings_rate = savings_amount / net_income if net_income > 0 else 0.0
        income_for_calculation = net_income

    else:  # DISCRETIONARY
        # Discretionary income (after necessities like rent, utilities)
        gross_income = 6000.0
        tax = 1200.0
        net_income = gross_income - tax
        necessities = 2000.0  # Rent, utilities, insurance
        discretionary_income = net_income - necessities
        discretionary_expenses = 1500.0  # Non-necessity spending
        savings_amount = discretionary_income - discretionary_expenses
        savings_rate = savings_amount / discretionary_income if discretionary_income > 0 else 0.0
        income_for_calculation = discretionary_income
        expenses = discretionary_expenses

    # TODO: Calculate trend from historical data
    # historical_rates = await _get_historical_savings_rates(
    #     user_id, historical_months, period_enum, definition_enum
    # )
    # trend = _calculate_trend(historical_rates)

    # Mock trend for now
    trend = TrendDirection.STABLE

    return SavingsRateData(
        savings_rate=max(0.0, min(1.0, savings_rate)),  # Clamp to [0, 1]
        savings_amount=savings_amount,
        income=income_for_calculation,
        expenses=expenses,
        period=period_enum,
        definition=definition_enum,
        trend=trend,
    )


async def _get_historical_savings_rates(
    user_id: str,
    months: int,
    period: Period,
    definition: SavingsDefinition,
) -> list[float]:
    """Get historical savings rates for trend analysis.

    Args:
        user_id: User identifier
        months: Number of historical months
        period: Period type
        definition: Savings definition

    Returns:
        List of historical savings rates (newest first)
    """
    # TODO: Fetch historical cash flow data
    # TODO: Calculate savings rate for each period
    # TODO: Return list of rates for trend analysis

    # Mock historical data for now
    return [0.25, 0.23, 0.24, 0.26, 0.22, 0.25]


def _calculate_trend(historical_rates: list[float]) -> TrendDirection:
    """Calculate trend direction from historical rates.

    Uses simple linear regression on recent data points.

    Args:
        historical_rates: List of historical savings rates (newest first)

    Returns:
        Trend direction (INCREASING, DECREASING, or STABLE)
    """
    if not historical_rates or len(historical_rates) < 3:
        return TrendDirection.STABLE

    # Take most recent rates (up to 6)
    recent_rates = historical_rates[:6]

    # Calculate simple moving average difference
    first_half_avg = sum(recent_rates[: len(recent_rates) // 2]) / (len(recent_rates) // 2)
    second_half_avg = sum(recent_rates[len(recent_rates) // 2 :]) / (
        len(recent_rates) - len(recent_rates) // 2
    )

    change = first_half_avg - second_half_avg  # Positive if improving (recent > older)

    # Define threshold for "stable" (within 2 percentage points)
    threshold = 0.02

    if abs(change) < threshold:
        return TrendDirection.STABLE
    elif change > 0:
        return TrendDirection.INCREASING
    else:
        return TrendDirection.DECREASING
