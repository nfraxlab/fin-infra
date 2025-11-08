"""Budget templates for quick setup.

Provides pre-built budget templates for common budgeting strategies:
- 50/30/20: 50% needs, 30% wants, 20% savings (personal finance)
- Zero-based: Every dollar allocated (detailed budgeting)
- Envelope system: Cash-like category limits (spending control)
- Business: Common business expense categories
- Project: Project-specific budget template

Generic Design:
- Templates work for any application type
- Users can create custom templates
- Templates adapt to user's income level
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from fin_infra.budgets.models import Budget, BudgetPeriod, BudgetType

if TYPE_CHECKING:
    from fin_infra.budgets.tracker import BudgetTracker


class BudgetTemplate:
    """Budget template definition.

    Defines category allocations as percentages of total income.
    Templates are generic and adapt to any income level.

    Attributes:
        name: Template name (e.g., "50/30/20 Rule")
        description: Template description
        budget_type: Recommended budget type
        period: Recommended budget period
        categories: Category name to percentage allocation mapping
    """

    def __init__(
        self,
        name: str,
        description: str,
        budget_type: BudgetType,
        period: BudgetPeriod,
        categories: dict[str, float],
    ):
        """Initialize budget template.

        Args:
            name: Template name
            description: Template description
            budget_type: Recommended budget type
            period: Recommended budget period
            categories: Category allocations as percentages (must sum to 100)

        Raises:
            ValueError: If category percentages don't sum to 100
        """
        if not categories:
            raise ValueError("Template must have at least one category")

        total_percent = sum(categories.values())
        if not (99.9 <= total_percent <= 100.1):  # Allow 0.1% float tolerance
            raise ValueError(f"Category percentages must sum to 100, got {total_percent:.2f}")

        self.name = name
        self.description = description
        self.budget_type = budget_type
        self.period = period
        self.categories = categories


# Pre-built budget templates
TEMPLATES: dict[str, BudgetTemplate] = {
    "50_30_20": BudgetTemplate(
        name="50/30/20 Rule",
        description="50% needs, 30% wants, 20% savings - popular personal finance strategy",
        budget_type=BudgetType.PERSONAL,
        period=BudgetPeriod.MONTHLY,
        categories={
            "Housing": 25.0,
            "Groceries": 10.0,
            "Transportation": 8.0,
            "Utilities": 5.0,
            "Insurance": 2.0,
            "Entertainment": 10.0,
            "Restaurants": 8.0,
            "Shopping": 7.0,
            "Personal Care": 5.0,
            "Savings": 15.0,
            "Investments": 5.0,
        },
    ),
    "zero_based": BudgetTemplate(
        name="Zero-Based Budget",
        description="Every dollar allocated to specific categories - detailed budgeting",
        budget_type=BudgetType.PERSONAL,
        period=BudgetPeriod.MONTHLY,
        categories={
            "Mortgage/Rent": 30.0,
            "Groceries": 12.0,
            "Transportation": 10.0,
            "Utilities": 7.0,
            "Insurance": 5.0,
            "Healthcare": 5.0,
            "Debt Payments": 8.0,
            "Clothing": 3.0,
            "Personal Care": 3.0,
            "Entertainment": 5.0,
            "Dining Out": 4.0,
            "Subscriptions": 2.0,
            "Savings": 3.0,
            "Emergency Fund": 3.0,
        },
    ),
    "envelope": BudgetTemplate(
        name="Envelope System",
        description="Cash-like category limits for spending control",
        budget_type=BudgetType.PERSONAL,
        period=BudgetPeriod.BIWEEKLY,
        categories={
            "Groceries": 20.0,
            "Gas": 10.0,
            "Restaurants": 8.0,
            "Entertainment": 7.0,
            "Clothing": 5.0,
            "Personal Care": 5.0,
            "Gifts": 5.0,
            "Household Items": 10.0,
            "Medical": 5.0,
            "Pet Care": 5.0,
            "Miscellaneous": 20.0,
        },
    ),
    "business": BudgetTemplate(
        name="Small Business Budget",
        description="Common business expense categories for small businesses",
        budget_type=BudgetType.BUSINESS,
        period=BudgetPeriod.MONTHLY,
        categories={
            "Payroll": 35.0,
            "Rent": 15.0,
            "Marketing": 10.0,
            "Equipment": 8.0,
            "Software": 5.0,
            "Utilities": 4.0,
            "Insurance": 5.0,
            "Professional Services": 5.0,
            "Office Supplies": 3.0,
            "Travel": 5.0,
            "Contingency": 5.0,
        },
    ),
    "project": BudgetTemplate(
        name="Project Budget",
        description="Project-specific budget template for project management",
        budget_type=BudgetType.PROJECT,
        period=BudgetPeriod.QUARTERLY,
        categories={
            "Personnel": 40.0,
            "Materials": 20.0,
            "Equipment": 15.0,
            "Contractors": 10.0,
            "Software/Tools": 5.0,
            "Travel": 4.0,
            "Training": 3.0,
            "Contingency": 3.0,
        },
    ),
}


async def apply_template(
    user_id: str,
    template_name: str,
    total_income: float,
    tracker: BudgetTracker,
    budget_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    custom_template: Optional[BudgetTemplate] = None,
) -> Budget:
    """Apply a budget template to create a new budget.

    Takes a template (built-in or custom) and user's total income,
    calculates category amounts, and creates a budget via tracker.

    Args:
        user_id: User identifier
        template_name: Template name (e.g., "50_30_20", "zero_based")
        total_income: Total income/budget amount
        tracker: BudgetTracker instance
        budget_name: Optional budget name (defaults to template name + date)
        start_date: Optional start date (defaults to now)
        custom_template: Optional custom template (overrides built-in)

    Returns:
        Created Budget instance

    Raises:
        ValueError: If template not found or total_income <= 0
        Exception: Propagates tracker errors

    Examples:
        >>> # Apply 50/30/20 template with $5000/month income
        >>> budget = await apply_template(
        ...     user_id="user_123",
        ...     template_name="50_30_20",
        ...     total_income=5000.00,
        ...     tracker=tracker,
        ... )
        >>> budget.categories["Housing"]
        1250.0  # 25% of $5000

        >>> # Apply custom template
        >>> custom = BudgetTemplate(
        ...     name="Custom",
        ...     description="My custom budget",
        ...     budget_type=BudgetType.PERSONAL,
        ...     period=BudgetPeriod.MONTHLY,
        ...     categories={"Rent": 50.0, "Food": 30.0, "Other": 20.0},
        ... )
        >>> budget = await apply_template(
        ...     user_id="user_123",
        ...     template_name="custom",
        ...     total_income=3000.00,
        ...     tracker=tracker,
        ...     custom_template=custom,
        ... )

        >>> # Template for business budget
        >>> budget = await apply_template(
        ...     user_id="biz_123",
        ...     template_name="business",
        ...     total_income=50000.00,
        ...     tracker=tracker,
        ...     budget_name="Q4 2025 Operations",
        ... )
    """
    # Validate income
    if total_income <= 0:
        raise ValueError(f"total_income must be positive, got {total_income}")

    # Get template (custom or built-in)
    if custom_template:
        template = custom_template
    else:
        if template_name not in TEMPLATES:
            available = ", ".join(TEMPLATES.keys())
            raise ValueError(
                f"Template '{template_name}' not found. Available templates: {available}"
            )
        template = TEMPLATES[template_name]

    # Calculate category amounts from percentages
    categories = {
        category_name: round(total_income * (percentage / 100), 2)
        for category_name, percentage in template.categories.items()
    }

    # Generate budget name if not provided
    if not budget_name:
        start = start_date or datetime.now()
        budget_name = f"{template.name} - {start.strftime('%B %Y')}"

    # Create budget via tracker
    budget = await tracker.create_budget(
        user_id=user_id,
        name=budget_name,
        type=template.budget_type,
        period=template.period,
        categories=categories,
        start_date=start_date,
    )

    return budget


def list_templates() -> dict[str, dict[str, str | dict[str, float]]]:
    """List all available built-in templates.

    Returns dict mapping template names to metadata (name, description, type, period, categories).

    Returns:
        Dict mapping template_name to template metadata
        Metadata includes: name (str), description (str), type (str), period (str),
        categories (dict[str, float])

    Examples:
        >>> templates = list_templates()
        >>> templates["50_30_20"]["name"]
        '50/30/20 Rule'
        >>> templates["business"]["description"]
        'Common business expense categories for small businesses'
        >>> templates["50_30_20"]["categories"]
        {'Housing': 25.0, 'Groceries': 10.0, ...}
    """
    return {
        template_name: {
            "name": template.name,
            "description": template.description,
            "type": template.budget_type.value,
            "period": template.period.value,
            "categories": template.categories,
        }
        for template_name, template in TEMPLATES.items()
    }


async def save_custom_template(
    user_id: str,
    template: BudgetTemplate,
    tracker: BudgetTracker,
) -> None:
    """Save a custom user template for future use.

    Stores user-defined template for reuse across budgets.
    Implementation requires DB wiring in Task 17.

    Args:
        user_id: User identifier
        template: Custom template to save
        tracker: BudgetTracker instance

    Raises:
        NotImplementedError: Until Task 17 FastAPI wiring

    Examples:
        >>> custom = BudgetTemplate(
        ...     name="My Custom Budget",
        ...     description="Tailored to my needs",
        ...     budget_type=BudgetType.PERSONAL,
        ...     period=BudgetPeriod.MONTHLY,
        ...     categories={"Rent": 40.0, "Food": 30.0, "Savings": 30.0},
        ... )
        >>> await save_custom_template("user_123", custom, tracker)
    """
    # TODO: Implement in Task 17 (requires DB table for custom templates)
    # - Create custom_templates table (user_id, template_name, categories, etc.)
    # - Store template via SqlRepository
    # - Allow retrieval in apply_template()
    raise NotImplementedError("Custom template storage requires Task 17 DB wiring")


async def get_custom_templates(user_id: str, tracker: BudgetTracker) -> list[BudgetTemplate]:
    """Get user's saved custom templates.

    Retrieves all custom templates for a user.
    Implementation requires DB wiring in Task 17.

    Args:
        user_id: User identifier
        tracker: BudgetTracker instance

    Returns:
        List of user's custom templates

    Raises:
        NotImplementedError: Until Task 17 FastAPI wiring

    Examples:
        >>> templates = await get_custom_templates("user_123", tracker)
        >>> len(templates)
        2
        >>> templates[0].name
        'My Custom Budget'
    """
    # TODO: Implement in Task 17 (requires DB table for custom templates)
    # - Query custom_templates table by user_id
    # - Convert DB rows to BudgetTemplate instances
    # - Return list
    raise NotImplementedError("Custom template retrieval requires Task 17 DB wiring")
