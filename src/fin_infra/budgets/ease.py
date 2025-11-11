"""Easy builder for budget tracker.

Provides easy_budgets() function for quick BudgetTracker setup with sensible defaults.

Generic Design:
- Configures svc-infra SQL for persistence
- Configures svc-infra webhooks for alerts
- Defaults to monthly budgets with rollover enabled
- Works with any database backend (via svc-infra)
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine

from fin_infra.budgets.tracker import BudgetTracker


def easy_budgets(
    db_url: Optional[str] = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> BudgetTracker:
    """Easy setup for BudgetTracker with sensible defaults.

    One-line function to configure database and return BudgetTracker instance.
    Uses svc-infra patterns for database configuration.

    Args:
        db_url: Database URL (defaults to SQL_URL env var)
            Examples:
            - PostgreSQL: "postgresql+asyncpg://user:pass@localhost/db"
            - SQLite: "sqlite+aiosqlite:///budget.db"
            - MySQL: "mysql+aiomysql://user:pass@localhost/db"
        pool_size: Connection pool size (default: 5)
        max_overflow: Max overflow connections beyond pool_size (default: 10)
        pool_pre_ping: Test connections before use (default: True, recommended)
        echo: Echo SQL queries to logs (default: False, set True for debugging)

    Returns:
        Configured BudgetTracker instance ready for use

    Raises:
        ValueError: If db_url not provided and SQL_URL env var not set
        Exception: If database connection fails

    Examples:
        >>> # Basic usage with env var SQL_URL
        >>> tracker = easy_budgets()

        >>> # With explicit database URL
        >>> tracker = easy_budgets(db_url="postgresql+asyncpg://localhost/mydb")

        >>> # With custom pool settings
        >>> tracker = easy_budgets(
        ...     db_url="postgresql+asyncpg://localhost/mydb",
        ...     pool_size=10,
        ...     max_overflow=20,
        ... )

        >>> # SQLite for development
        >>> tracker = easy_budgets(db_url="sqlite+aiosqlite:///budget.db")

        >>> # Enable SQL logging for debugging
        >>> tracker = easy_budgets(echo=True)

        >>> # Use tracker immediately
        >>> budget = await tracker.create_budget(
        ...     user_id="user_123",
        ...     name="November 2025",
        ...     type=BudgetType.PERSONAL,
        ...     period=BudgetPeriod.MONTHLY,
        ...     categories={"Food": 500.0, "Rent": 1500.0},
        ... )

        >>> # Full application setup
        >>> from fin_infra.budgets import easy_budgets
        >>> from fin_infra.budgets.templates import apply_template
        >>>
        >>> # Initialize tracker
        >>> tracker = easy_budgets()
        >>>
        >>> # Apply template
        >>> budget = await apply_template(
        ...     user_id="user_123",
        ...     template_name="50_30_20",
        ...     total_income=5000.00,
        ...     tracker=tracker,
        ... )
    """
    # Get database URL from parameter or environment
    database_url = db_url or os.getenv("SQL_URL")

    if not database_url:
        raise ValueError(
            "Database URL required: provide db_url parameter or set SQL_URL environment variable"
        )

    # Build engine kwargs (SQLite doesn't support max_overflow)
    engine_kwargs = {
        "pool_pre_ping": pool_pre_ping,
        "echo": echo,
        "connect_args": _get_connect_args(database_url),
    }

    # Only add pool settings for non-SQLite databases
    if "sqlite" not in database_url.lower():
        engine_kwargs["pool_size"] = pool_size
        engine_kwargs["max_overflow"] = max_overflow
        engine_kwargs["pool_recycle"] = 3600  # Recycle connections after 1 hour

    # Create async engine with sensible defaults
    engine = create_async_engine(database_url, **engine_kwargs)

    # Create and return tracker
    return BudgetTracker(db_engine=engine)


def _get_connect_args(database_url: str) -> dict:
    """Get database-specific connection arguments.

    Provides optimal connection settings per database backend.

    Args:
        database_url: Database connection URL

    Returns:
        Dict of connection arguments for SQLAlchemy

    Examples:
        >>> _get_connect_args("postgresql+asyncpg://localhost/db")
        {'server_settings': {'jit': 'off'}}
        >>> _get_connect_args("sqlite+aiosqlite:///db.sqlite")
        {'check_same_thread': False}
        >>> _get_connect_args("mysql+aiomysql://localhost/db")
        {}
    """
    # PostgreSQL optimizations
    if "postgresql" in database_url or "asyncpg" in database_url:
        return {
            "server_settings": {
                "jit": "off",  # Disable JIT for faster short queries
            }
        }

    # SQLite settings for async
    if "sqlite" in database_url or "aiosqlite" in database_url:
        return {
            "check_same_thread": False,  # Required for async SQLite
        }

    # MySQL/MariaDB (if needed in future)
    if "mysql" in database_url or "aiomysql" in database_url:
        return {}

    # Default: no special args
    return {}


async def shutdown_budgets(tracker: BudgetTracker) -> None:
    """Gracefully shutdown BudgetTracker and close database connections.

    Should be called during application shutdown to ensure clean resource cleanup.

    Args:
        tracker: BudgetTracker instance to shutdown

    Examples:
        >>> # FastAPI lifespan
        >>> from contextlib import asynccontextmanager
        >>> from fastapi import FastAPI
        >>>
        >>> tracker = None
        >>>
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     global tracker
        ...     tracker = easy_budgets()
        ...     yield
        ...     await shutdown_budgets(tracker)
        >>>
        >>> app = FastAPI(lifespan=lifespan)

        >>> # Manual shutdown
        >>> tracker = easy_budgets()
        >>> try:
        ...     # Use tracker
        ...     pass
        ... finally:
        ...     await shutdown_budgets(tracker)
    """
    if tracker and tracker.db_engine:
        # dispose() returns None in most cases, but handle as coroutine if needed
        result = tracker.db_engine.dispose()
        # Check if it's a coroutine
        import inspect

        if inspect.iscoroutine(result):
            await result


def validate_database_url(url: str) -> tuple[bool, str]:
    """Validate database URL format and check if driver is async.

    Helps catch configuration errors early.

    Args:
        url: Database connection URL to validate

    Returns:
        Tuple of (is_valid: bool, message: str)
        - (True, "Valid async database URL") if valid
        - (False, "Error message") if invalid

    Examples:
        >>> validate_database_url("postgresql+asyncpg://localhost/db")
        (True, 'Valid async database URL')

        >>> validate_database_url("postgresql://localhost/db")
        (False, 'Database URL must use async driver (asyncpg, aiosqlite, aiomysql)')

        >>> validate_database_url("invalid")
        (False, 'Invalid database URL format (missing ://)')

        >>> # Use in easy_budgets() with validation
        >>> db_url = "postgresql+asyncpg://localhost/db"
        >>> is_valid, msg = validate_database_url(db_url)
        >>> if not is_valid:
        ...     raise ValueError(msg)
        >>> tracker = easy_budgets(db_url=db_url)
    """
    if not url or not isinstance(url, str):
        return False, "Invalid database URL format"

    # Check basic URL structure first
    if "://" not in url:
        return False, "Invalid database URL format (missing ://)"

    # Check for async drivers
    async_drivers = ["asyncpg", "aiosqlite", "aiomysql", "asyncmy"]
    has_async_driver = any(driver in url for driver in async_drivers)

    if not has_async_driver:
        return (
            False,
            f"Database URL must use async driver ({', '.join(async_drivers)})",
        )

    return True, "Valid async database URL"
