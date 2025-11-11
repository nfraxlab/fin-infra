"""Budget tracking and CRUD operations.

Provides BudgetTracker class for creating, reading, updating, and deleting budgets,
as well as tracking spending progress against budgeted amounts.

Generic Design:
- Works with any budget type (personal, household, business, project)
- Integrates with svc-infra SQL for persistence
- Integrates with fin-infra categorization for transaction mapping
- Supports rollover budgets (unused amounts carry over)

Example:
    >>> from fin_infra.budgets import BudgetTracker
    >>> from sqlalchemy.ext.asyncio import create_async_engine
    >>>
    >>> # Create tracker with DB engine
    >>> engine = create_async_engine("postgresql+asyncpg://localhost/db")
    >>> tracker = BudgetTracker(db_engine=engine)
    >>>
    >>> # Create a budget
    >>> budget = await tracker.create_budget(
    ...     user_id="user123",
    ...     name="November Budget",
    ...     type="personal",
    ...     period="monthly",
    ...     categories={"Groceries": 600.00, "Restaurants": 200.00}
    ... )
    >>>
    >>> # Track progress
    >>> progress = await tracker.get_budget_progress(budget.id)
    >>> print(f"Spent: ${progress.total_spent:.2f}")
    >>> print(f"Remaining: ${progress.total_remaining:.2f}")
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.ext.asyncio import async_sessionmaker

from fin_infra.budgets.models import (
    Budget,
    BudgetCategory,
    BudgetPeriod,
    BudgetProgress,
    BudgetType,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


class BudgetTracker:
    """
    Budget CRUD and progress tracking.

    Provides methods for creating, reading, updating, and deleting budgets,
    as well as calculating spending progress against budgeted amounts.

    Generic Design:
    - Works with any budget type (personal, household, business, project)
    - Integrates with svc-infra SQL for persistence
    - Integrates with fin-infra categorization for transaction mapping
    - Supports rollover budgets (unused amounts carry over)

    Integration:
    - Uses svc-infra SQL for budget storage (SqlRepository pattern)
    - Uses fin-infra categorization for transaction category mapping
    - TODO: Uses svc-infra cache for progress calculations (24h TTL)
    - TODO: Uses svc-infra webhooks for budget alerts

    Attributes:
        db_engine: SQLAlchemy async engine
        session_maker: Async session factory

    Example:
        >>> from sqlalchemy.ext.asyncio import create_async_engine
        >>> engine = create_async_engine("postgresql+asyncpg://localhost/db")
        >>> tracker = BudgetTracker(db_engine=engine)
        >>>
        >>> # Create monthly budget
        >>> budget = await tracker.create_budget(
        ...     user_id="user123",
        ...     name="November 2025",
        ...     type="personal",
        ...     period="monthly",
        ...     categories={"Groceries": 600.00, "Dining": 200.00},
        ...     rollover_enabled=True
        ... )
        >>> print(budget.id)  # UUID string
    """

    def __init__(self, db_engine: AsyncEngine):
        """
        Initialize budget tracker with database engine.

        Args:
            db_engine: SQLAlchemy async engine for database operations

        Example:
            >>> from sqlalchemy.ext.asyncio import create_async_engine
            >>> engine = create_async_engine("postgresql+asyncpg://...")
            >>> tracker = BudgetTracker(db_engine=engine)
        """
        self.db_engine = db_engine
        self.session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
        # In-memory storage until SQL persistence is implemented (Task 13)
        self._budgets: dict[str, Budget] = {}

    async def create_budget(
        self,
        user_id: str,
        name: str,
        type: str,  # BudgetType value
        period: str,  # BudgetPeriod value
        categories: dict[str, float],
        start_date: Optional[datetime] = None,
        rollover_enabled: bool = False,
    ) -> Budget:
        """
        Create a new budget.

        Args:
            user_id: User ID who owns the budget
            name: Budget name (e.g., "November 2025")
            type: Budget type (personal, household, business, project, custom)
            period: Budget period (weekly, biweekly, monthly, quarterly, yearly)
            categories: Category allocations (e.g., {"Groceries": 600.00})
            start_date: Budget start date (defaults to now)
            rollover_enabled: Whether unused budget carries over to next period

        Returns:
            Created Budget model

        Raises:
            ValueError: Invalid budget type or period
            ValueError: Empty categories or negative amounts
            HTTPException: Database constraint violation

        Example:
            >>> budget = await tracker.create_budget(
            ...     user_id="user123",
            ...     name="November Budget",
            ...     type="personal",
            ...     period="monthly",
            ...     categories={"Groceries": 600.00, "Restaurants": 200.00},
            ...     rollover_enabled=True
            ... )
            >>> print(budget.id)  # UUID
        """
        # Validate budget type
        try:
            BudgetType(type)
        except ValueError:
            raise ValueError(
                f"Invalid budget type: {type}. " f"Valid types: {[t.value for t in BudgetType]}"
            )

        # Validate budget period
        try:
            BudgetPeriod(period)
        except ValueError:
            raise ValueError(
                f"Invalid budget period: {period}. "
                f"Valid periods: {[p.value for p in BudgetPeriod]}"
            )

        # Validate categories
        if not categories:
            raise ValueError("Budget must have at least one category")
        if any(amount < 0 for amount in categories.values()):
            raise ValueError("Category amounts cannot be negative")

        # Calculate end date based on period
        start = start_date or datetime.now()
        end = self._calculate_end_date(start, period)

        # Create budget
        budget = Budget(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            type=BudgetType(type),
            period=BudgetPeriod(period),
            categories=categories,
            start_date=start,
            end_date=end,
            rollover_enabled=rollover_enabled,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Persistence: Applications own database schema (fin-infra is a stateless library).
        # Generate models/schemas/repository: fin-infra scaffold budgets --dest-dir app/models/
        # Then wire CRUD with svc-infra: add_sql_resources(app, [SqlResource(model=Budget, ...)])
        # See docs/persistence.md for full guide.
        # In-memory storage used here for testing/examples.

        # In-memory storage (Task 13 scope)
        self._budgets[budget.id] = budget

        return budget

    async def get_budgets(
        self,
        user_id: str,
        type: Optional[str] = None,
    ) -> List[Budget]:
        """
        Get all budgets for a user.

        Args:
            user_id: User ID
            type: Optional budget type filter (personal, household, business, etc.)

        Returns:
            List of Budget models (may be empty)

        Example:
            >>> # Get all budgets
            >>> budgets = await tracker.get_budgets("user123")
            >>> print(len(budgets))  # 3
            >>>
            >>> # Get only personal budgets
            >>> personal = await tracker.get_budgets("user123", type="personal")
            >>> print(personal[0].name)  # "November 2025"
        """
        # Persistence: Applications query via scaffolded repository or svc-infra SqlResource.
        # Generate with: fin-infra scaffold budgets --dest-dir app/models/
        # See docs/persistence.md for query patterns.
        # In-memory storage used here for testing/examples.
        #     return list(result.scalars().all())

        # In-memory storage (Task 13 scope)
        budgets = [b for b in self._budgets.values() if b.user_id == user_id]
        if type:
            budgets = [b for b in budgets if b.type.value == type]
        return budgets

    async def get_budget(self, budget_id: str) -> Budget:
        """
        Get a single budget by ID.

        Args:
            budget_id: Budget UUID

        Returns:
            Budget model

        Raises:
            ValueError: Budget not found (404)

        Example:
            >>> budget = await tracker.get_budget("abc-123-def-456")
            >>> print(budget.name)  # "November 2025"
            >>> print(budget.categories)  # {"Groceries": 600.00, ...}
        """
        # Persistence: Applications query via scaffolded repository.get(budget_id).
        # Generate with: fin-infra scaffold budgets --dest-dir app/models/
        # See docs/persistence.md for repository patterns.
        # In-memory storage used here for testing/examples.

        # In-memory storage (Task 13 scope)
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        return budget

    async def update_budget(
        self,
        budget_id: str,
        updates: dict,
    ) -> Budget:
        """
        Update budget fields.

        Args:
            budget_id: Budget UUID
            updates: Fields to update (name, categories, rollover_enabled, etc.)

        Returns:
            Updated Budget model

        Raises:
            ValueError: Budget not found
            ValueError: Invalid updates (e.g., negative amounts)

        Example:
            >>> # Update category allocations
            >>> budget = await tracker.update_budget(
            ...     "abc-123",
            ...     updates={"categories": {"Groceries": 700.00, "Dining": 150.00}}
            ... )
            >>> print(budget.categories["Groceries"])  # 700.00
        """
        # Validate updates
        if "categories" in updates:
            if not updates["categories"]:
                raise ValueError("Budget must have at least one category")
            if any(amount < 0 for amount in updates["categories"].values()):
                raise ValueError("Category amounts cannot be negative")

        # Persistence: Applications update via scaffolded repository.update(budget_id, updates).
        # Generate with: fin-infra scaffold budgets --dest-dir app/models/
        # See docs/persistence.md for update patterns.
        # In-memory storage used here for testing/examples.

        # In-memory storage (Task 13 scope)
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")

        # Update budget fields
        for key, value in updates.items():
            if hasattr(budget, key):
                setattr(budget, key, value)
        budget.updated_at = datetime.now()

        return budget

    async def delete_budget(self, budget_id: str) -> None:
        """
        Delete a budget.

        Args:
            budget_id: Budget UUID

        Returns:
            None

        Raises:
            ValueError: Budget not found

        Example:
            >>> await tracker.delete_budget("abc-123")
            >>> # Budget and related data deleted
        """
        # Persistence: Applications delete via scaffolded repository.delete(budget_id).
        # Generate with: fin-infra scaffold budgets --dest-dir app/models/
        # Supports soft delete if --include-soft-delete flag used during scaffold.
        # See docs/persistence.md for delete patterns.
        # In-memory storage used here for testing/examples.

        # In-memory storage (Task 13 scope)
        if budget_id not in self._budgets:
            raise ValueError(f"Budget not found: {budget_id}")
        del self._budgets[budget_id]

    async def get_budget_progress(
        self,
        budget_id: str,
        period: str = "current",
    ) -> BudgetProgress:
        """
        Calculate budget progress for current or specified period.

        Queries transactions via categorization module to calculate
        spending against budgeted amounts for each category.

        Args:
            budget_id: Budget UUID
            period: Period to calculate ("current", "last", or specific date range)

        Returns:
            BudgetProgress model with spending details

        Raises:
            ValueError: Budget not found
            ValueError: Invalid period

        Example:
            >>> progress = await tracker.get_budget_progress("abc-123")
            >>> print(f"Total budgeted: ${progress.total_budgeted:.2f}")  # $800.00
            >>> print(f"Total spent: ${progress.total_spent:.2f}")  # $510.00
            >>> print(f"Remaining: ${progress.total_remaining:.2f}")  # $290.00
            >>> print(f"Percent used: {progress.percent_used:.1f}%")  # 63.8%
            >>>
            >>> # Check category progress
            >>> for category in progress.categories:
            ...     print(f"{category.category_name}: {category.percent_used:.1f}%")
            Groceries: 70.9%
            Restaurants: 50.0%
        """
        # TODO: Implement full progress calculation (Task 13 scope)
        # 1. Get budget from DB
        # 2. Query transactions for budget period via categorization module
        # 3. Sum spending per category
        # 4. Calculate rollover amounts if enabled
        # 5. Return BudgetProgress

        # For now, return empty progress
        budget = await self.get_budget(budget_id)

        categories = [
            BudgetCategory(
                category_name=name,
                budgeted_amount=amount,
                spent_amount=0.0,
                remaining_amount=amount,
                percent_used=0.0,
            )
            for name, amount in budget.categories.items()
        ]

        total_budgeted = sum(cat.budgeted_amount for cat in categories)
        total_spent = sum(cat.spent_amount for cat in categories)
        total_remaining = sum(cat.remaining_amount for cat in categories)

        # Calculate days elapsed in period
        now = datetime.now()
        days_elapsed = (now - budget.start_date).days
        days_total = (budget.end_date - budget.start_date).days

        return BudgetProgress(
            budget_id=budget_id,
            current_period=f"{budget.start_date.date()} to {budget.end_date.date()}",
            categories=categories,
            total_budgeted=total_budgeted,
            total_spent=total_spent,
            total_remaining=total_remaining,
            percent_used=(total_spent / total_budgeted * 100) if total_budgeted > 0 else 0.0,
            period_days_elapsed=max(0, days_elapsed),
            period_days_total=max(1, days_total),
        )

    def _calculate_end_date(self, start: datetime, period: str) -> datetime:
        """
        Calculate end date based on budget period.

        Args:
            start: Start date
            period: Budget period (weekly, biweekly, monthly, quarterly, yearly)

        Returns:
            End date

        Example:
            >>> start = datetime(2025, 11, 1)
            >>> end = tracker._calculate_end_date(start, "monthly")
            >>> print(end)  # 2025-11-30
        """
        if period == "weekly":
            return start + timedelta(days=7)
        elif period == "biweekly":
            return start + timedelta(days=14)
        elif period == "monthly":
            # Add one month (handle month boundaries)
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1, day=28)
            else:
                return start.replace(month=start.month + 1, day=28)
        elif period == "quarterly":
            # Add 3 months
            month = start.month + 3
            year = start.year
            if month > 12:
                month -= 12
                year += 1
            return start.replace(year=year, month=month, day=28)
        elif period == "yearly":
            return start.replace(year=start.year + 1, day=28)
        else:
            raise ValueError(f"Invalid period: {period}")
