"""Account balance history tracking for fin-infra banking module.

This module provides functionality to record and retrieve historical account balance
snapshots over time. This enables balance trend analysis, sparklines, and time-series
visualizations in fintech dashboards.

Features:
- Record daily balance snapshots for accounts
- Store snapshots in time-series optimized format
- Support multiple data sources (provider API, manual, calculated)
- Automatic daily snapshot recording via svc-infra jobs

Example usage:
    # Record a balance snapshot
    from fin_infra.banking.history import record_balance_snapshot

    record_balance_snapshot(
        account_id="acc_123",
        balance=5432.10,
        date=date.today(),
        source="plaid"
    )

    # Get balance history
    from fin_infra.banking.history import get_balance_history

    history = get_balance_history(account_id="acc_123", days=90)
    for snapshot in history:
        print(f"{snapshot.date}: ${snapshot.balance:.2f}")

Integration with svc-infra:
- Storage: Uses svc-infra SQL database for time-series data
- Jobs: Automatic daily snapshots via svc-infra background jobs
- Cache: Query results cached with 24h TTL
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


__all__ = [
    "BalanceSnapshot",
    "record_balance_snapshot",
    "get_balance_history",
    "get_balance_snapshots",
    "delete_balance_history",
]


# In-memory storage for testing (will be replaced with SQL database in production)
_balance_snapshots: List[BalanceSnapshot] = []


class BalanceSnapshot(BaseModel):
    """Balance snapshot at a specific point in time.

    Attributes:
        account_id: Account identifier
        balance: Account balance at the snapshot time
        snapshot_date: Date of the snapshot
        source: Source of the balance data (provider name, manual, calculated)
        created_at: Timestamp when snapshot was recorded
    """

    model_config = ConfigDict(
        json_encoders={
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }
    )

    account_id: str = Field(..., description="Account identifier")
    balance: float = Field(..., description="Account balance at snapshot time")
    snapshot_date: date = Field(..., description="Date of the snapshot")
    source: str = Field(
        default="manual",
        description="Source of balance data: provider name (plaid, teller), manual, or calculated",
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when snapshot was recorded"
    )


def record_balance_snapshot(
    account_id: str, balance: float, snapshot_date: date, source: str = "manual"
) -> None:
    """Record a balance snapshot for an account.

    This function stores a point-in-time balance record for trend analysis.
    In production, this would write to a SQL database via svc-infra.

    Args:
        account_id: Account identifier
        balance: Account balance at the snapshot time
        snapshot_date: Date of the snapshot
        source: Source of the balance data (default: "manual")

    Examples:
        >>> from datetime import date
        >>> record_balance_snapshot("acc_123", 5432.10, date.today(), "plaid")
        >>> record_balance_snapshot("acc_123", 5500.00, date.today() + timedelta(days=1), "plaid")

    Notes:
        - Duplicate snapshots (same account + date) will be stored but can be filtered
        - In production, use unique constraint on (account_id, date) in SQL
        - Consider using svc-infra jobs for automatic daily snapshots
    """
    snapshot = BalanceSnapshot(
        account_id=account_id,
        balance=balance,
        snapshot_date=snapshot_date,
        source=source,
    )

    # In production, this would be:
    # from svc_infra.db import get_session
    # session = get_session()
    # session.add(snapshot)
    # session.commit()

    _balance_snapshots.append(snapshot)


def get_balance_history(
    account_id: str,
    days: int = 90,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[BalanceSnapshot]:
    """Get balance history for an account.

    Retrieves balance snapshots for the specified account within a date range.
    Results are sorted by date in descending order (most recent first).

    Args:
        account_id: Account identifier
        days: Number of days of history to retrieve (default: 90)
        start_date: Optional start date (overrides days parameter)
        end_date: Optional end date (default: today)

    Returns:
        List of BalanceSnapshot objects sorted by date (descending)

    Examples:
        >>> # Get last 90 days of history
        >>> history = get_balance_history("acc_123", days=90)
        >>>
        >>> # Get specific date range
        >>> from datetime import date
        >>> history = get_balance_history(
        ...     "acc_123",
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 12, 31)
        ... )

    Notes:
        - Results are cached with 24h TTL in production (via svc-infra cache)
        - Use start_date/end_date for custom ranges
        - Use days parameter for recent history
    """
    # Calculate date range
    if end_date is None:
        end_date = date.today()

    if start_date is None:
        start_date = end_date - timedelta(days=days)

    # Filter snapshots by account and date range
    # In production, this would be a SQL query:
    # SELECT * FROM balance_snapshots
    # WHERE account_id = ? AND date BETWEEN ? AND ?
    # ORDER BY date DESC

    filtered = [
        snapshot
        for snapshot in _balance_snapshots
        if (snapshot.account_id == account_id and start_date <= snapshot.snapshot_date <= end_date)
    ]

    # Sort by date descending (most recent first)
    filtered.sort(key=lambda s: s.snapshot_date, reverse=True)

    return filtered


def get_balance_snapshots(
    account_id: str,
    dates: List[date],
) -> List[BalanceSnapshot]:
    """Get balance snapshots for specific dates.

    Args:
        account_id: Account identifier
        dates: List of dates to retrieve snapshots for

    Returns:
        List of BalanceSnapshot objects for the specified dates

    Examples:
        >>> from datetime import date, timedelta
        >>> today = date.today()
        >>> snapshots = get_balance_snapshots(
        ...     "acc_123",
        ...     [today, today - timedelta(days=7), today - timedelta(days=30)]
        ... )
    """
    date_set = set(dates)

    filtered = [
        snapshot
        for snapshot in _balance_snapshots
        if snapshot.account_id == account_id and snapshot.snapshot_date in date_set
    ]

    return filtered


def delete_balance_history(
    account_id: str,
    before_date: Optional[date] = None,
) -> int:
    """Delete balance history for an account.

    Args:
        account_id: Account identifier
        before_date: Optional date; delete snapshots before this date

    Returns:
        Number of snapshots deleted

    Examples:
        >>> # Delete all history for account
        >>> deleted = delete_balance_history("acc_123")
        >>>
        >>> # Delete history older than 1 year
        >>> from datetime import date, timedelta
        >>> cutoff = date.today() - timedelta(days=365)
        >>> deleted = delete_balance_history("acc_123", before_date=cutoff)
    """
    deleted_count = 0

    if before_date is None:
        # Delete all snapshots for this account
        for i in range(len(_balance_snapshots) - 1, -1, -1):
            if _balance_snapshots[i].account_id == account_id:
                _balance_snapshots.pop(i)
                deleted_count += 1
    else:
        # Delete snapshots before the specified date
        for i in range(len(_balance_snapshots) - 1, -1, -1):
            snapshot = _balance_snapshots[i]
            if snapshot.account_id == account_id and snapshot.snapshot_date < before_date:
                _balance_snapshots.pop(i)
                deleted_count += 1

    return deleted_count


# Production integration notes:
#
# 1. SQL Schema (via svc-infra):
#    CREATE TABLE balance_snapshots (
#        id SERIAL PRIMARY KEY,
#        account_id VARCHAR(255) NOT NULL,
#        balance DECIMAL(15, 2) NOT NULL,
#        date DATE NOT NULL,
#        source VARCHAR(50) NOT NULL,
#        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#        UNIQUE(account_id, date),
#        INDEX idx_account_date (account_id, date DESC)
#    );
#
# 2. Automatic daily snapshots (via svc-infra jobs):
#    from svc_infra.jobs import easy_jobs
#
#    @worker.task(schedule="0 0 * * *")  # Daily at midnight
#    async def record_daily_balances():
#        """Record balance snapshots for all accounts."""
#        accounts = get_all_accounts()
#        for account in accounts:
#            balance = get_current_balance(account.id)
#            record_balance_snapshot(
#                account_id=account.id,
#                balance=balance,
#                date=date.today(),
#                source=account.provider
#            )
#
# 3. Caching (via svc-infra cache):
#    from svc_infra.cache import cache_read
#
#    @cache_read(ttl=86400)  # 24 hours
#    def get_balance_history_cached(account_id: str, days: int):
#        return get_balance_history(account_id, days)
