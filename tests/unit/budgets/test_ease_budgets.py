"""Unit tests for easy_budgets() builder.

Tests easy_budgets() configuration, validation, and helper functions.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from fin_infra.budgets.ease import (
    easy_budgets,
    shutdown_budgets,
    validate_database_url,
    _get_connect_args,
)
from fin_infra.budgets.tracker import BudgetTracker


class TestEasyBudgets:
    """Test easy_budgets() builder function."""

    @patch("fin_infra.budgets.ease.create_async_engine")
    def test_easy_budgets_with_explicit_url(self, mock_create_engine):
        """Test easy_budgets() with explicit db_url parameter."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        tracker = easy_budgets(db_url="postgresql+asyncpg://localhost/testdb")

        # Verify engine created with correct URL
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql+asyncpg://localhost/testdb"

        # Verify default settings
        assert call_args[1]["pool_size"] == 5
        assert call_args[1]["max_overflow"] == 10
        assert call_args[1]["pool_pre_ping"] is True
        assert call_args[1]["echo"] is False
        assert call_args[1]["pool_recycle"] == 3600

        # Verify tracker created
        assert isinstance(tracker, BudgetTracker)
        assert tracker.db_engine == mock_engine

    @patch("fin_infra.budgets.ease.create_async_engine")
    @patch.dict(os.environ, {"SQL_URL": "postgresql+asyncpg://env/db"})
    def test_easy_budgets_with_env_var(self, mock_create_engine):
        """Test easy_budgets() falls back to SQL_URL env var."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        tracker = easy_budgets()

        # Verify environment variable used
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql+asyncpg://env/db"

        assert isinstance(tracker, BudgetTracker)

    @patch.dict(os.environ, {}, clear=True)
    def test_easy_budgets_no_url_raises_error(self):
        """Test easy_budgets() raises error when no URL provided."""
        with pytest.raises(ValueError, match="Database URL required"):
            easy_budgets()

    @patch("fin_infra.budgets.ease.create_async_engine")
    def test_easy_budgets_with_custom_pool_settings(self, mock_create_engine):
        """Test easy_budgets() with custom pool configuration."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        easy_budgets(
            db_url="postgresql+asyncpg://localhost/db",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=False,
            echo=True,
        )

        call_args = mock_create_engine.call_args
        assert call_args[1]["pool_size"] == 10
        assert call_args[1]["max_overflow"] == 20
        assert call_args[1]["pool_pre_ping"] is False
        assert call_args[1]["echo"] is True

    @patch("fin_infra.budgets.ease.create_async_engine")
    def test_easy_budgets_sqlite(self, mock_create_engine):
        """Test easy_budgets() with SQLite database."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        easy_budgets(db_url="sqlite+aiosqlite:///budget.db")

        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "sqlite+aiosqlite:///budget.db"

        # Verify SQLite-specific connect_args
        assert "check_same_thread" in call_args[1]["connect_args"]
        assert call_args[1]["connect_args"]["check_same_thread"] is False

    @patch("fin_infra.budgets.ease.create_async_engine")
    def test_easy_budgets_mysql(self, mock_create_engine):
        """Test easy_budgets() with MySQL database."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        easy_budgets(db_url="mysql+aiomysql://localhost/db")

        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "mysql+aiomysql://localhost/db"


class TestGetConnectArgs:
    """Test _get_connect_args() helper function."""

    def test_get_connect_args_postgresql(self):
        """Test PostgreSQL connection arguments."""
        args = _get_connect_args("postgresql+asyncpg://localhost/db")

        assert "server_settings" in args
        assert args["server_settings"]["jit"] == "off"

    def test_get_connect_args_asyncpg(self):
        """Test asyncpg (PostgreSQL) connection arguments."""
        args = _get_connect_args("asyncpg://localhost/db")

        assert "server_settings" in args

    def test_get_connect_args_sqlite(self):
        """Test SQLite connection arguments."""
        args = _get_connect_args("sqlite+aiosqlite:///db.sqlite")

        assert "check_same_thread" in args
        assert args["check_same_thread"] is False

    def test_get_connect_args_aiosqlite(self):
        """Test aiosqlite connection arguments."""
        args = _get_connect_args("aiosqlite:///db.sqlite")

        assert "check_same_thread" in args

    def test_get_connect_args_mysql(self):
        """Test MySQL connection arguments (empty)."""
        args = _get_connect_args("mysql+aiomysql://localhost/db")

        assert args == {}

    def test_get_connect_args_unknown(self):
        """Test unknown database returns empty args."""
        args = _get_connect_args("unknown://localhost/db")

        assert args == {}


class TestValidateDatabaseUrl:
    """Test validate_database_url() helper function."""

    def test_validate_postgresql_asyncpg(self):
        """Test valid PostgreSQL with asyncpg."""
        is_valid, msg = validate_database_url("postgresql+asyncpg://localhost/db")

        assert is_valid is True
        assert "Valid" in msg

    def test_validate_sqlite_aiosqlite(self):
        """Test valid SQLite with aiosqlite."""
        is_valid, msg = validate_database_url("sqlite+aiosqlite:///budget.db")

        assert is_valid is True

    def test_validate_mysql_aiomysql(self):
        """Test valid MySQL with aiomysql."""
        is_valid, msg = validate_database_url("mysql+aiomysql://localhost/db")

        assert is_valid is True

    def test_validate_asyncmy(self):
        """Test valid MySQL with asyncmy driver."""
        is_valid, msg = validate_database_url("mysql+asyncmy://localhost/db")

        assert is_valid is True

    def test_validate_sync_driver_fails(self):
        """Test synchronous driver is rejected."""
        is_valid, msg = validate_database_url("postgresql://localhost/db")

        assert is_valid is False
        assert "async driver" in msg

    def test_validate_psycopg2_fails(self):
        """Test psycopg2 (sync) is rejected."""
        is_valid, msg = validate_database_url("postgresql+psycopg2://localhost/db")

        assert is_valid is False
        assert "async driver" in msg

    def test_validate_empty_url(self):
        """Test empty URL is rejected."""
        is_valid, msg = validate_database_url("")

        assert is_valid is False
        assert "Invalid" in msg

    def test_validate_none_url(self):
        """Test None URL is rejected."""
        is_valid, msg = validate_database_url(None)

        assert is_valid is False

    def test_validate_malformed_url(self):
        """Test malformed URL without :// is rejected."""
        is_valid, msg = validate_database_url("notaurl")

        assert is_valid is False
        assert "://" in msg


class TestShutdownBudgets:
    """Test shutdown_budgets() cleanup function."""

    @pytest.mark.asyncio
    async def test_shutdown_disposes_engine(self):
        """Test shutdown_budgets() calls engine.dispose()."""
        mock_engine = MagicMock(spec=AsyncEngine)
        # dispose() can return None or a coroutine depending on implementation
        mock_engine.dispose = MagicMock(return_value=None)

        # Create tracker with mock engine
        tracker = BudgetTracker(db_engine=mock_engine)

        # Shutdown
        await shutdown_budgets(tracker)

        # Verify dispose called
        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_none_tracker(self):
        """Test shutdown_budgets() handles None tracker gracefully."""
        # Should not raise
        await shutdown_budgets(None)

    @pytest.mark.asyncio
    async def test_shutdown_handles_none_engine(self):
        """Test shutdown_budgets() handles tracker with no engine."""
        tracker = MagicMock(spec=BudgetTracker)
        tracker.db_engine = None

        # Should not raise
        await shutdown_budgets(tracker)


class TestEasyBudgetsIntegration:
    """Integration tests for easy_budgets() workflow."""

    @patch("fin_infra.budgets.ease.create_async_engine")
    def test_full_setup_workflow(self, mock_create_engine):
        """Test complete easy_budgets() setup workflow."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        # Step 1: Validate URL
        db_url = "postgresql+asyncpg://localhost/budget_db"
        is_valid, msg = validate_database_url(db_url)
        assert is_valid is True

        # Step 2: Create tracker with validated URL
        tracker = easy_budgets(
            db_url=db_url,
            pool_size=5,
            echo=False,
        )

        # Step 3: Verify tracker ready for use
        assert isinstance(tracker, BudgetTracker)
        assert tracker.db_engine == mock_engine
        assert tracker.session_maker is not None

        # Verify engine configured correctly
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == db_url
        assert call_args[1]["pool_size"] == 5

    @patch("fin_infra.budgets.ease.create_async_engine")
    @patch.dict(os.environ, {"SQL_URL": "sqlite+aiosqlite:///test.db"})
    def test_env_var_workflow(self, mock_create_engine):
        """Test workflow using environment variable."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        # Create tracker without explicit URL (uses env var)
        easy_budgets()

        # Verify environment variable used
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "sqlite+aiosqlite:///test.db"

        # Verify SQLite connect_args applied
        assert "check_same_thread" in call_args[1]["connect_args"]

    @patch("fin_infra.budgets.ease.create_async_engine")
    def test_custom_pool_workflow(self, mock_create_engine):
        """Test workflow with custom pool configuration."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        # Create tracker with custom pool settings for high-traffic app
        easy_budgets(
            db_url="postgresql+asyncpg://localhost/prod_db",
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
        )

        # Verify settings applied
        call_args = mock_create_engine.call_args
        assert call_args[1]["pool_size"] == 20
        assert call_args[1]["max_overflow"] == 30
        assert call_args[1]["pool_pre_ping"] is True

        # Verify PostgreSQL optimizations
        assert "server_settings" in call_args[1]["connect_args"]
        assert call_args[1]["connect_args"]["server_settings"]["jit"] == "off"
