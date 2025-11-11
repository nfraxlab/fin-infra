"""Unit tests for banking balance history tracking."""

import pytest
from datetime import date, timedelta, datetime

from fin_infra.banking.history import (
    BalanceSnapshot,
    record_balance_snapshot,
    get_balance_history,
    get_balance_snapshots,
    delete_balance_history,
    _balance_snapshots,
)


@pytest.fixture(autouse=True)
def clear_snapshots():
    """Clear in-memory snapshots before and after each test."""
    import fin_infra.banking.history as history_module

    history_module._balance_snapshots.clear()
    yield
    history_module._balance_snapshots.clear()


class TestBalanceSnapshot:
    """Test BalanceSnapshot model."""

    def test_minimal_snapshot(self):
        """Test creating a snapshot with minimal fields."""
        snapshot = BalanceSnapshot(
            account_id="acc_123",
            balance=5432.10,
            snapshot_date=date(2024, 1, 15),
        )

        assert snapshot.account_id == "acc_123"
        assert snapshot.balance == 5432.10
        assert snapshot.snapshot_date == date(2024, 1, 15)
        assert snapshot.source == "manual"  # default
        assert isinstance(snapshot.created_at, datetime)

    def test_full_snapshot(self):
        """Test creating a snapshot with all fields."""
        now = datetime.now()
        snapshot = BalanceSnapshot(
            account_id="acc_123",
            balance=5432.10,
            snapshot_date=date(2024, 1, 15),
            source="plaid",
            created_at=now,
        )

        assert snapshot.account_id == "acc_123"
        assert snapshot.balance == 5432.10
        assert snapshot.snapshot_date == date(2024, 1, 15)
        assert snapshot.source == "plaid"
        assert snapshot.created_at == now

    def test_negative_balance(self):
        """Test snapshot with negative balance."""
        snapshot = BalanceSnapshot(
            account_id="acc_123",
            balance=-150.50,
            snapshot_date=date.today(),
        )

        assert snapshot.balance == -150.50

    def test_zero_balance(self):
        """Test snapshot with zero balance."""
        snapshot = BalanceSnapshot(
            account_id="acc_123",
            balance=0.0,
            snapshot_date=date.today(),
        )

        assert snapshot.balance == 0.0

    def test_json_serialization(self):
        """Test that snapshot can be serialized to JSON."""
        snapshot = BalanceSnapshot(
            account_id="acc_123",
            balance=5432.10,
            snapshot_date=date(2024, 1, 15),
            source="plaid",
        )

        json_data = snapshot.model_dump(mode="json")

        assert json_data["account_id"] == "acc_123"
        assert json_data["balance"] == 5432.10
        assert json_data["snapshot_date"] == "2024-01-15"  # JSON serialized date
        assert json_data["source"] == "plaid"
        assert "created_at" in json_data


class TestRecordBalanceSnapshot:
    """Test record_balance_snapshot function."""

    def test_record_single_snapshot(self):
        """Test recording a single balance snapshot."""
        record_balance_snapshot(
            account_id="acc_123",
            balance=5432.10,
            snapshot_date=date(2024, 1, 15),
            source="plaid",
        )

        assert len(_balance_snapshots) == 1
        snapshot = _balance_snapshots[0]
        assert snapshot.account_id == "acc_123"
        assert snapshot.balance == 5432.10
        assert snapshot.snapshot_date == date(2024, 1, 15)
        assert snapshot.source == "plaid"

    def test_record_multiple_snapshots(self):
        """Test recording multiple balance snapshots."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=2), "plaid")
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=1), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today, "plaid")

        assert len(_balance_snapshots) == 3
        assert _balance_snapshots[0].balance == 5000.00
        assert _balance_snapshots[1].balance == 5100.00
        assert _balance_snapshots[2].balance == 5200.00

    def test_record_default_source(self):
        """Test that default source is 'manual'."""
        record_balance_snapshot(
            account_id="acc_123",
            balance=5432.10,
            snapshot_date=date.today(),
        )

        assert _balance_snapshots[0].source == "manual"

    def test_record_different_accounts(self):
        """Test recording snapshots for different accounts."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today, "plaid")
        record_balance_snapshot("acc_456", 10000.00, today, "teller")

        assert len(_balance_snapshots) == 2
        assert _balance_snapshots[0].account_id == "acc_123"
        assert _balance_snapshots[1].account_id == "acc_456"

    def test_record_duplicate_date(self):
        """Test that duplicate dates are allowed (to be filtered later)."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today, "plaid")
        record_balance_snapshot("acc_123", 5100.00, today, "manual")

        assert len(_balance_snapshots) == 2


class TestGetBalanceHistory:
    """Test get_balance_history function."""

    def test_get_history_empty(self):
        """Test getting history when no snapshots exist."""
        history = get_balance_history("acc_123", days=90)

        assert history == []

    def test_get_history_single_account(self):
        """Test getting history for a single account."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=30), "plaid")
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=15), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today, "plaid")

        history = get_balance_history("acc_123", days=90)

        assert len(history) == 3
        # Should be sorted by date descending
        assert history[0].snapshot_date == today
        assert history[1].snapshot_date == today - timedelta(days=15)
        assert history[2].snapshot_date == today - timedelta(days=30)

    def test_get_history_filters_by_account(self):
        """Test that history is filtered by account_id."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today, "plaid")
        record_balance_snapshot("acc_456", 10000.00, today, "teller")

        history = get_balance_history("acc_123", days=90)

        assert len(history) == 1
        assert history[0].account_id == "acc_123"

    def test_get_history_filters_by_days(self):
        """Test that history is filtered by days parameter."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=100), "plaid")
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=50), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today - timedelta(days=10), "plaid")
        record_balance_snapshot("acc_123", 5300.00, today, "plaid")

        history = get_balance_history("acc_123", days=60)

        # Should only include last 60 days
        assert len(history) == 3
        assert all(snapshot.snapshot_date >= today - timedelta(days=60) for snapshot in history)

    def test_get_history_with_date_range(self):
        """Test getting history with explicit date range."""
        today = date.today()
        start = today - timedelta(days=30)
        end = today - timedelta(days=10)

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=40), "plaid")
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=20), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today - timedelta(days=5), "plaid")

        history = get_balance_history("acc_123", start_date=start, end_date=end)

        # Should only include snapshots between start and end
        assert len(history) == 1
        assert history[0].snapshot_date == today - timedelta(days=20)

    def test_get_history_sorted_descending(self):
        """Test that history is sorted by date descending."""
        today = date.today()

        # Add in random order
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=15), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today, "plaid")
        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=30), "plaid")

        history = get_balance_history("acc_123", days=90)

        # Should be sorted descending (most recent first)
        assert history[0].snapshot_date == today
        assert history[1].snapshot_date == today - timedelta(days=15)
        assert history[2].snapshot_date == today - timedelta(days=30)


class TestGetBalanceSnapshots:
    """Test get_balance_snapshots function."""

    def test_get_snapshots_specific_dates(self):
        """Test getting snapshots for specific dates."""
        today = date.today()
        date1 = today - timedelta(days=30)
        date2 = today - timedelta(days=15)
        date3 = today

        record_balance_snapshot("acc_123", 5000.00, date1, "plaid")
        record_balance_snapshot("acc_123", 5100.00, date2, "plaid")
        record_balance_snapshot("acc_123", 5200.00, date3, "plaid")
        record_balance_snapshot("acc_123", 5150.00, today - timedelta(days=7), "plaid")

        snapshots = get_balance_snapshots("acc_123", [date1, date3])

        assert len(snapshots) == 2
        dates = [s.snapshot_date for s in snapshots]
        assert date1 in dates
        assert date3 in dates
        assert date2 not in dates

    def test_get_snapshots_empty(self):
        """Test getting snapshots when none exist for specified dates."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=10), "plaid")

        snapshots = get_balance_snapshots("acc_123", [today, today - timedelta(days=5)])

        assert snapshots == []

    def test_get_snapshots_filters_by_account(self):
        """Test that snapshots are filtered by account_id."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today, "plaid")
        record_balance_snapshot("acc_456", 10000.00, today, "teller")

        snapshots = get_balance_snapshots("acc_123", [today])

        assert len(snapshots) == 1
        assert snapshots[0].account_id == "acc_123"


class TestDeleteBalanceHistory:
    """Test delete_balance_history function."""

    def test_delete_all_history(self):
        """Test deleting all history for an account."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=30), "plaid")
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=15), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today, "plaid")
        record_balance_snapshot("acc_456", 10000.00, today, "teller")

        deleted = delete_balance_history("acc_123")

        assert deleted == 3
        assert len(_balance_snapshots) == 1
        assert _balance_snapshots[0].account_id == "acc_456"

    def test_delete_history_before_date(self):
        """Test deleting history before a specific date."""
        today = date.today()
        cutoff = today - timedelta(days=20)

        record_balance_snapshot("acc_123", 5000.00, today - timedelta(days=30), "plaid")
        record_balance_snapshot("acc_123", 5100.00, today - timedelta(days=15), "plaid")
        record_balance_snapshot("acc_123", 5200.00, today, "plaid")

        deleted = delete_balance_history("acc_123", before_date=cutoff)

        assert deleted == 1
        assert len(_balance_snapshots) == 2
        # Should keep snapshots on or after cutoff
        assert all(s.snapshot_date >= cutoff for s in _balance_snapshots)

    def test_delete_no_matching_snapshots(self):
        """Test deleting when no snapshots match criteria."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today, "plaid")

        deleted = delete_balance_history("acc_456")

        assert deleted == 0
        assert len(_balance_snapshots) == 1

    def test_delete_history_filters_by_account(self):
        """Test that delete only affects specified account."""
        today = date.today()

        record_balance_snapshot("acc_123", 5000.00, today, "plaid")
        record_balance_snapshot("acc_456", 10000.00, today, "teller")

        deleted = delete_balance_history("acc_123")

        assert deleted == 1
        assert len(_balance_snapshots) == 1
        assert _balance_snapshots[0].account_id == "acc_456"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_daily_snapshot_workflow(self):
        """Test recording daily snapshots over time."""
        account_id = "acc_123"
        start_balance = 5000.00
        daily_change = 10.00

        # Record 30 days of snapshots
        today = date.today()
        for i in range(30):
            snapshot_date = today - timedelta(days=29 - i)
            balance = start_balance + (i * daily_change)
            record_balance_snapshot(account_id, balance, snapshot_date, "plaid")

        # Get history
        history = get_balance_history(account_id, days=30)

        assert len(history) == 30
        # Should be increasing over time (but descending order)
        assert history[0].balance > history[-1].balance

    def test_multiple_accounts_tracking(self):
        """Test tracking multiple accounts simultaneously."""
        today = date.today()

        # Record snapshots for 3 accounts
        for i in range(10):
            snapshot_date = today - timedelta(days=9 - i)
            record_balance_snapshot("acc_1", 5000 + i * 10, snapshot_date, "plaid")
            record_balance_snapshot("acc_2", 10000 + i * 20, snapshot_date, "plaid")
            record_balance_snapshot("acc_3", 15000 + i * 30, snapshot_date, "teller")

        # Get history for each account
        history_1 = get_balance_history("acc_1", days=10)
        history_2 = get_balance_history("acc_2", days=10)
        history_3 = get_balance_history("acc_3", days=10)

        assert len(history_1) == 10
        assert len(history_2) == 10
        assert len(history_3) == 10

        # Verify balances are account-specific
        assert history_1[0].balance != history_2[0].balance
        assert history_2[0].balance != history_3[0].balance

    def test_retention_policy(self):
        """Test implementing a retention policy (keep last 90 days)."""
        today = date.today()
        retention_days = 90

        # Record 120 days of snapshots
        for i in range(120):
            snapshot_date = today - timedelta(days=119 - i)
            record_balance_snapshot("acc_123", 5000 + i, snapshot_date, "plaid")

        # Delete snapshots older than retention period
        cutoff = today - timedelta(days=retention_days)
        deleted = delete_balance_history("acc_123", before_date=cutoff)

        # Should delete 29 snapshots (day 119 to day 91, exclusive of day 90)
        # Days: today-119 to today-91 = 29 days
        # Days: today-90 to today = 91 days (inclusive)
        assert deleted == 29

        # Verify only recent snapshots remain
        history = get_balance_history("acc_123", days=120)
        assert len(history) == 91
        assert all(s.snapshot_date >= cutoff for s in history)
