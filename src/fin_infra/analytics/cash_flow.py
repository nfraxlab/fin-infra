"""Cash flow analysis functions.

Provides income vs expense analysis, breakdowns by source/category, and forecasting.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from ..models import Transaction
from .models import CashFlowAnalysis


async def calculate_cash_flow(
    user_id: str,
    start_date: str | datetime,
    end_date: str | datetime,
    accounts: Optional[list[str]] = None,
    *,
    banking_provider=None,
    categorization_provider=None,
) -> CashFlowAnalysis:
    """Calculate cash flow analysis for a user.

    Aggregates transactions from banking module, categorizes them, and provides
    income vs expense breakdown with detailed source/category analysis.

    Args:
        user_id: User identifier
        start_date: Analysis period start (ISO string or datetime)
        end_date: Analysis period end (ISO string or datetime)
        accounts: Optional list of account IDs to filter (None = all accounts)
        banking_provider: Optional banking provider instance (for dependency injection)
        categorization_provider: Optional categorization provider (for dependency injection)

    Returns:
        CashFlowAnalysis with income/expense totals and breakdowns

    Raises:
        ValueError: If date range is invalid or user has no accounts

    Example:
        >>> from fin_infra.analytics.cash_flow import calculate_cash_flow
        >>>
        >>> cash_flow = await calculate_cash_flow(
        ...     user_id="user123",
        ...     start_date="2025-01-01",
        ...     end_date="2025-01-31"
        ... )
        >>> print(f"Net: ${cash_flow.net_cash_flow}")
        >>> print(f"Income: ${cash_flow.income_total}")
        >>> print(f"Expenses: ${cash_flow.expense_total}")

    Integration:
        - Fetches transactions from banking module
        - Uses categorization module for expense categories
        - Supports account filtering (all, specific, groups)

    Generic Applicability:
        - Personal finance: Track monthly income/expenses
        - Business accounting: Cash flow statement generation
        - Wealth management: Client cash flow analysis
        - Banking apps: Spending insights and budgeting
    """
    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    # Validate date range
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date")

    # TODO: Fetch transactions from banking provider
    # For now, return mock data structure
    # In real implementation:
    # 1. Get user's accounts (optionally filtered)
    # 2. Fetch transactions for date range
    # 3. Categorize transactions
    # 4. Separate income (positive) from expenses (negative)
    # 5. Group income by source
    # 6. Group expenses by category

    # Mock implementation - replace with real logic
    income_by_source = {
        "Paycheck": 5000.0,
        "Investment": 200.0,
        "Side Hustle": 500.0,
    }

    expenses_by_category = {
        "Groceries": 600.0,
        "Restaurants": 400.0,
        "Transportation": 300.0,
        "Utilities": 200.0,
        "Entertainment": 150.0,
    }

    income_total = sum(income_by_source.values())
    expense_total = sum(expenses_by_category.values())
    net_cash_flow = income_total - expense_total

    return CashFlowAnalysis(
        income_total=income_total,
        expense_total=expense_total,
        net_cash_flow=net_cash_flow,
        income_by_source=income_by_source,
        expenses_by_category=expenses_by_category,
        period_start=start_date,
        period_end=end_date,
    )


async def forecast_cash_flow(
    user_id: str,
    months: int = 6,
    assumptions: Optional[dict[str, Any]] = None,
    *,
    recurring_provider=None,
) -> list[CashFlowAnalysis]:
    """Forecast future cash flow based on recurring patterns.

    Uses recurring detection module to identify predictable income/expenses,
    applies growth rates from assumptions, and generates monthly projections.

    Args:
        user_id: User identifier
        months: Number of months to forecast (default: 6)
        assumptions: Optional assumptions dict with keys:
            - income_growth_rate: Annual income growth rate (default: 0.0)
            - expense_growth_rate: Annual expense growth rate (default: 0.03 for inflation)
            - one_time_income: Dict of {month_index: amount} for one-time income
            - one_time_expenses: Dict of {month_index: amount} for one-time expenses
        recurring_provider: Optional recurring detection provider (for dependency injection)

    Returns:
        List of CashFlowAnalysis, one per month

    Raises:
        ValueError: If months <= 0 or user has no transaction history

    Example:
        >>> from fin_infra.analytics.cash_flow import forecast_cash_flow
        >>>
        >>> forecasts = await forecast_cash_flow(
        ...     user_id="user123",
        ...     months=12,
        ...     assumptions={
        ...         "income_growth_rate": 0.05,  # 5% annual raise
        ...         "expense_growth_rate": 0.03,  # 3% inflation
        ...     }
        ... )
        >>> for i, forecast in enumerate(forecasts, 1):
        ...     print(f"Month {i}: Net ${forecast.net_cash_flow:.2f}")

    Integration:
        - Uses recurring detection for predictable transactions
        - Applies growth rates per assumptions
        - Handles one-time income/expenses

    Generic Applicability:
        - Personal finance: Budget planning and savings goals
        - Wealth management: Client financial planning
        - Business accounting: Cash flow projections
        - Banking apps: Future balance predictions
    """
    if months <= 0:
        raise ValueError("months must be positive")

    assumptions = assumptions or {}
    income_growth_rate = assumptions.get("income_growth_rate", 0.0)
    expense_growth_rate = assumptions.get("expense_growth_rate", 0.03)
    one_time_income = assumptions.get("one_time_income", {})
    one_time_expenses = assumptions.get("one_time_expenses", {})

    # TODO: Get recurring transactions from recurring detection module
    # For now, use mock baseline
    baseline_income = 5700.0
    baseline_expenses = 1650.0

    monthly_income_growth = (1 + income_growth_rate) ** (1 / 12) - 1
    monthly_expense_growth = (1 + expense_growth_rate) ** (1 / 12) - 1

    forecasts = []
    base_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for month_idx in range(months):
        # Calculate period
        period_start = base_date + timedelta(days=30 * month_idx)
        period_end = base_date + timedelta(days=30 * (month_idx + 1))

        # Apply growth
        projected_income = baseline_income * ((1 + monthly_income_growth) ** month_idx)
        projected_expenses = baseline_expenses * ((1 + monthly_expense_growth) ** month_idx)

        # Add one-time amounts
        projected_income += one_time_income.get(month_idx, 0)
        projected_expenses += one_time_expenses.get(month_idx, 0)

        net_cash_flow = projected_income - projected_expenses

        # Create forecast (simplified - would include full breakdowns in real implementation)
        forecast = CashFlowAnalysis(
            income_total=projected_income,
            expense_total=projected_expenses,
            net_cash_flow=net_cash_flow,
            income_by_source={"Projected Income": projected_income},
            expenses_by_category={"Projected Expenses": projected_expenses},
            period_start=period_start,
            period_end=period_end,
        )
        forecasts.append(forecast)

    return forecasts


def _categorize_transactions(
    transactions: list[Transaction],
    categorization_provider=None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Helper to categorize transactions into income sources and expense categories.

    Args:
        transactions: List of Transaction objects
        categorization_provider: Optional categorization provider

    Returns:
        Tuple of (income_by_source, expenses_by_category) dicts
    """
    income_by_source: dict[str, float] = {}
    expenses_by_category: dict[str, float] = {}

    for txn in transactions:
        if txn.amount > 0:
            # Income transaction
            source = _determine_income_source(txn)
            income_by_source[source] = income_by_source.get(source, 0) + txn.amount
        else:
            # Expense transaction
            category = _get_expense_category(txn, categorization_provider)
            amount = abs(txn.amount)
            expenses_by_category[category] = expenses_by_category.get(category, 0) + amount

    return income_by_source, expenses_by_category


def _determine_income_source(transaction: Transaction) -> str:
    """Determine income source from transaction details.

    Args:
        transaction: Transaction object

    Returns:
        Income source name (e.g., "Paycheck", "Investment", "Side Hustle")
    """
    # Simple heuristic - real implementation would use categorization
    description = (transaction.description or "").lower()

    if any(keyword in description for keyword in ["payroll", "salary", "employer"]):
        return "Paycheck"
    elif any(keyword in description for keyword in ["dividend", "interest", "capital gain"]):
        return "Investment"
    elif any(keyword in description for keyword in ["freelance", "upwork", "fiverr"]):
        return "Side Hustle"
    else:
        return "Other Income"


def _get_expense_category(
    transaction: Transaction,
    categorization_provider=None,
) -> str:
    """Get expense category for transaction.

    Args:
        transaction: Transaction object
        categorization_provider: Optional categorization provider

    Returns:
        Category name (e.g., "Groceries", "Restaurants", "Transportation")
    """
    # TODO: Use categorization provider if available
    # For now, return a default category
    return "Uncategorized"
