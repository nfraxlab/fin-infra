"""Budget management for fintech applications.

Provides comprehensive budget tracking, alerts, and templates for personal finance,
household management, business accounting, and project budgeting.

Generic Applicability:
- Personal finance apps: Track spending against budget categories
- Household management: Shared budgets for families
- Business accounting: Expense budgets for departments/projects
- Project management: Budget tracking for project expenses
- Wealth management: Client budget planning and advisory

Features:
- Multiple budget types: personal, household, business, project, custom
- Multiple periods: weekly, biweekly, monthly, quarterly, yearly
- Budget templates: 50/30/20, zero-based, envelope system, etc.
- Budget alerts: Overspending, approaching limits, unusual spending
- Rollover support: Unused budget carries over to next period
- Real-time tracking: Live progress against budgeted amounts

Integration:
- Uses svc-infra SQL for persistence (budget storage)
- Uses svc-infra webhooks for alerts (overspending notifications)
- Uses fin-infra categorization for transaction mapping
- Uses fin-infra analytics for spending insights

Examples:
    >>> # Create a budget tracker
    >>> from fin_infra.budgets import easy_budgets
    >>> budgets = easy_budgets()

    >>> # Create a monthly budget
    >>> budget = await budgets.create_budget(
    ...     user_id="user123",
    ...     name="November Budget",
    ...     type="personal",
    ...     period="monthly",
    ...     categories={
    ...         "Groceries": 600.00,
    ...         "Restaurants": 200.00,
    ...         "Transportation": 150.00,
    ...     }
    ... )

    >>> # Track progress
    >>> progress = await budgets.get_budget_progress(budget.id)
    >>> print(f"Total spent: ${progress.total_spent:.2f}")
    >>> print(f"Remaining: ${progress.total_remaining:.2f}")

    >>> # Check for alerts
    >>> from fin_infra.budgets import check_budget_alerts
    >>> alerts = await check_budget_alerts(budget.id)
    >>> for alert in alerts:
    ...     print(f"Alert: {alert.message}")

    >>> # FastAPI integration
    >>> from fastapi import FastAPI
    >>> from fin_infra.budgets import add_budgets
    >>>
    >>> app = FastAPI()
    >>> budgets = add_budgets(app)
    >>> # Endpoints: POST /budgets, GET /budgets, GET /budgets/{id}, etc.
"""

from __future__ import annotations

__all__ = [
    # Easy builder
    "easy_budgets",
    # FastAPI integration
    "add_budgets",
    # Models
    "Budget",
    "BudgetType",
    "BudgetPeriod",
    "BudgetCategory",
    "BudgetProgress",
    "BudgetAlert",
    "BudgetTemplate",
    # Core functionality
    "BudgetTracker",
    "check_budget_alerts",
    "apply_template",
]


def __getattr__(name: str):
    """Lazy import for budgets module components."""
    if name == "easy_budgets":
        from fin_infra.budgets.ease import easy_budgets  # type: ignore[attr-defined]

        return easy_budgets
    elif name == "add_budgets":
        from fin_infra.budgets.add import add_budgets  # type: ignore[attr-defined]

        return add_budgets
    elif name in (
        "Budget",
        "BudgetType",
        "BudgetPeriod",
        "BudgetCategory",
        "BudgetProgress",
        "BudgetAlert",
        "BudgetTemplate",
    ):
        from fin_infra.budgets.models import (  # noqa: F401
            Budget,
            BudgetType,
            BudgetPeriod,
            BudgetCategory,
            BudgetProgress,
            BudgetAlert,
            BudgetTemplate,
        )

        return locals()[name]
    elif name == "BudgetTracker":
        from fin_infra.budgets.tracker import BudgetTracker

        return BudgetTracker
    elif name == "check_budget_alerts":
        from fin_infra.budgets.alerts import check_budget_alerts  # type: ignore[attr-defined]

        return check_budget_alerts
    elif name == "apply_template":
        from fin_infra.budgets.templates import apply_template  # type: ignore[attr-defined]

        return apply_template

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
