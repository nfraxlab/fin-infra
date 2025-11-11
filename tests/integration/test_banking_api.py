"""Integration tests for banking API endpoints with filtering."""

from datetime import date
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pytest

from fin_infra.banking import add_banking
from fin_infra.providers.base import BankingProvider


class MockBankingProvider(BankingProvider):
    """Mock banking provider for testing."""

    def __init__(self):
        """Initialize mock provider with test data."""
        self.test_transactions = [
            {
                "id": "txn_1",
                "date": "2024-11-01",
                "merchant_name": "Starbucks",
                "amount": 5.50,
                "category": "food",
                "account_id": "acc_1",
                "is_recurring": False,
                "tags": ["coffee", "morning"],
            },
            {
                "id": "txn_2",
                "date": "2024-11-02",
                "merchant_name": "Amazon",
                "amount": 149.99,
                "category": "shopping",
                "account_id": "acc_1",
                "is_recurring": False,
                "tags": ["online"],
            },
            {
                "id": "txn_3",
                "date": "2024-11-03",
                "merchant_name": "Netflix",
                "amount": 15.99,
                "category": "entertainment",
                "account_id": "acc_2",
                "is_recurring": True,
                "tags": ["subscription", "streaming"],
            },
            {
                "id": "txn_4",
                "date": "2024-11-04",
                "merchant_name": "Whole Foods",
                "amount": 87.32,
                "category": "food",
                "account_id": "acc_1",
                "is_recurring": False,
                "tags": ["groceries"],
            },
            {
                "id": "txn_5",
                "date": "2024-11-05",
                "merchant_name": "Spotify",
                "amount": 9.99,
                "category": "entertainment",
                "account_id": "acc_2",
                "is_recurring": True,
                "tags": ["subscription", "music"],
            },
            {
                "id": "txn_6",
                "date": "2024-11-06",
                "merchant_name": "Starbucks",
                "amount": 6.25,
                "category": "food",
                "account_id": "acc_1",
                "is_recurring": False,
                "tags": ["coffee", "afternoon"],
            },
            {
                "id": "txn_7",
                "date": "2024-11-07",
                "merchant_name": "Shell Gas Station",
                "amount": 45.00,
                "category": "transportation",
                "account_id": "acc_1",
                "is_recurring": False,
                "tags": ["gas", "car"],
            },
        ]

    def create_link_token(self, user_id: str) -> str:
        """Mock create link token."""
        return f"link_token_{user_id}"

    def exchange_public_token(self, public_token: str) -> dict:
        """Mock exchange public token."""
        return {"access_token": "test_access_token", "item_id": "test_item"}

    def accounts(self, access_token: str) -> list:
        """Mock accounts."""
        return [
            {"id": "acc_1", "name": "Checking", "balance": 5000.00},
            {"id": "acc_2", "name": "Savings", "balance": 10000.00},
        ]

    def transactions(self, access_token: str, start_date=None, end_date=None) -> list:
        """Mock transactions with date filtering."""
        results = self.test_transactions.copy()

        if start_date:
            results = [t for t in results if t["date"] >= str(start_date)]

        if end_date:
            results = [t for t in results if t["date"] <= str(end_date)]

        return results

    def balances(self, access_token: str, account_id=None) -> dict:
        """Mock balances."""
        return {"current": 5000.00, "available": 4800.00}

    def identity(self, access_token: str) -> dict:
        """Mock identity."""
        return {"name": "Test User", "email": "test@example.com"}


@pytest.fixture
def app():
    """Create FastAPI app with banking endpoints."""
    app = FastAPI()
    mock_provider = MockBankingProvider()
    add_banking(app, provider=mock_provider)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestBankingTransactionFiltering:
    """Test transaction filtering functionality."""

    def test_get_all_transactions(self, client):
        """Test getting all transactions without filters."""
        response = client.get(
            "/banking/transactions", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert data["meta"]["total"] == 7
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 50
        assert len(data["data"]) == 7

    def test_filter_by_merchant(self, client):
        """Test filtering by merchant name (partial match)."""
        response = client.get(
            "/banking/transactions?merchant=starbucks",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 2
        assert all("Starbucks" in t["merchant_name"] for t in data["data"])

    def test_filter_by_category(self, client):
        """Test filtering by category."""
        response = client.get(
            "/banking/transactions?category=food", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 3
        assert all(t["category"] == "food" for t in data["data"])

    def test_filter_by_multiple_categories(self, client):
        """Test filtering by multiple categories."""
        response = client.get(
            "/banking/transactions?category=food,entertainment",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 5
        categories = {t["category"] for t in data["data"]}
        assert categories == {"food", "entertainment"}

    def test_filter_by_amount_range(self, client):
        """Test filtering by min and max amount."""
        response = client.get(
            "/banking/transactions?min_amount=10&max_amount=50",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 2  # Netflix ($15.99) and Shell ($45.00)
        for txn in data["data"]:
            assert 10 <= txn["amount"] <= 50

    def test_filter_by_min_amount_only(self, client):
        """Test filtering by min amount only."""
        response = client.get(
            "/banking/transactions?min_amount=50", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 2
        for txn in data["data"]:
            assert txn["amount"] >= 50

    def test_filter_by_max_amount_only(self, client):
        """Test filtering by max amount only."""
        response = client.get(
            "/banking/transactions?max_amount=10", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 3
        for txn in data["data"]:
            assert txn["amount"] <= 10

    def test_filter_by_tags(self, client):
        """Test filtering by tags."""
        response = client.get(
            "/banking/transactions?tags=subscription",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 2
        for txn in data["data"]:
            assert "subscription" in txn["tags"]

    def test_filter_by_multiple_tags(self, client):
        """Test filtering by multiple tags (AND logic)."""
        response = client.get(
            "/banking/transactions?tags=subscription,streaming",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 1
        assert data["data"][0]["merchant_name"] == "Netflix"

    def test_filter_by_account_id(self, client):
        """Test filtering by account ID."""
        response = client.get(
            "/banking/transactions?account_id=acc_1", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 5
        assert all(t["account_id"] == "acc_1" for t in data["data"])

    def test_filter_by_recurring_status(self, client):
        """Test filtering by recurring status."""
        response = client.get(
            "/banking/transactions?is_recurring=true",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 2
        assert all(t["is_recurring"] for t in data["data"])

    def test_filter_by_non_recurring(self, client):
        """Test filtering by non-recurring status."""
        response = client.get(
            "/banking/transactions?is_recurring=false",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 5
        assert all(not t["is_recurring"] for t in data["data"])

    def test_sort_by_amount_asc(self, client):
        """Test sorting by amount ascending."""
        response = client.get(
            "/banking/transactions?sort_by=amount&order=asc",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        amounts = [t["amount"] for t in data["data"]]
        assert amounts == sorted(amounts)

    def test_sort_by_amount_desc(self, client):
        """Test sorting by amount descending."""
        response = client.get(
            "/banking/transactions?sort_by=amount&order=desc",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        amounts = [t["amount"] for t in data["data"]]
        assert amounts == sorted(amounts, reverse=True)

    def test_sort_by_merchant(self, client):
        """Test sorting by merchant name."""
        response = client.get(
            "/banking/transactions?sort_by=merchant&order=asc",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        merchants = [t["merchant_name"] for t in data["data"]]
        assert merchants == sorted(merchants)

    def test_sort_by_date_desc_default(self, client):
        """Test default sorting by date descending."""
        response = client.get(
            "/banking/transactions", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 200
        data = response.json()

        dates = [t["date"] for t in data["data"]]
        assert dates == sorted(dates, reverse=True)

    def test_pagination_first_page(self, client):
        """Test pagination - first page."""
        response = client.get(
            "/banking/transactions?page=1&per_page=3",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 7
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 3
        assert data["meta"]["total_pages"] == 3
        assert len(data["data"]) == 3

    def test_pagination_second_page(self, client):
        """Test pagination - second page."""
        response = client.get(
            "/banking/transactions?page=2&per_page=3",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["page"] == 2
        assert len(data["data"]) == 3

    def test_pagination_last_page(self, client):
        """Test pagination - last page with partial results."""
        response = client.get(
            "/banking/transactions?page=3&per_page=3",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["page"] == 3
        assert len(data["data"]) == 1  # Only 1 item on last page

    def test_pagination_beyond_last_page(self, client):
        """Test pagination - page beyond data."""
        response = client.get(
            "/banking/transactions?page=10&per_page=3",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["page"] == 10
        assert len(data["data"]) == 0  # No data on this page

    def test_combined_filters(self, client):
        """Test multiple filters combined."""
        response = client.get(
            "/banking/transactions?category=food&min_amount=5&max_amount=10&sort_by=amount&order=asc",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 2
        # All should be food category
        assert all(t["category"] == "food" for t in data["data"])
        # All should be in amount range
        for txn in data["data"]:
            assert 5 <= txn["amount"] <= 10
        # Should be sorted by amount ascending
        amounts = [t["amount"] for t in data["data"]]
        assert amounts == sorted(amounts)

    def test_filter_no_results(self, client):
        """Test filter that returns no results."""
        response = client.get(
            "/banking/transactions?merchant=nonexistent",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["total"] == 0
        assert len(data["data"]) == 0

    def test_invalid_per_page_above_max(self, client):
        """Test that per_page is capped at 200."""
        response = client.get(
            "/banking/transactions?per_page=500", headers={"Authorization": "Bearer test_token"}
        )
        # FastAPI should reject this with 422 validation error
        assert response.status_code == 422

    def test_invalid_page_below_min(self, client):
        """Test that page must be >= 1."""
        response = client.get(
            "/banking/transactions?page=0", headers={"Authorization": "Bearer test_token"}
        )
        # FastAPI should reject this with 422 validation error
        assert response.status_code == 422


class TestBalanceHistoryEndpoint:
    """Test balance history endpoint with trend calculations."""

    @pytest.fixture
    def client(self):
        """Create test client with mock banking provider."""
        from datetime import timedelta
        from fin_infra.banking.history import record_balance_snapshot, _balance_snapshots

        # Clear any existing snapshots
        _balance_snapshots.clear()

        # Record 30 days of increasing balance snapshots
        today = date.today()
        for i in range(30):
            snapshot_date = today - timedelta(days=29 - i)
            balance = 5000.0 + (i * 50.0)  # Increases by $50/day
            record_balance_snapshot(
                account_id="acc_1", balance=balance, snapshot_date=snapshot_date, source="plaid"
            )

        # Record 30 days of decreasing balance snapshots for another account
        for i in range(30):
            snapshot_date = today - timedelta(days=29 - i)
            balance = 10000.0 - (i * 30.0)  # Decreases by $30/day
            record_balance_snapshot(
                account_id="acc_2", balance=balance, snapshot_date=snapshot_date, source="teller"
            )

        # Record 30 days of stable balance for a third account
        for i in range(30):
            snapshot_date = today - timedelta(days=29 - i)
            balance = 3000.0  # Stable
            record_balance_snapshot(
                account_id="acc_3", balance=balance, snapshot_date=snapshot_date, source="plaid"
            )

        app = FastAPI()
        mock_provider = MockBankingProvider()
        add_banking(app, provider=mock_provider)

        yield TestClient(app)

        # Cleanup
        _balance_snapshots.clear()

    def test_get_history_increasing_trend(self, client):
        """Test getting balance history with increasing trend."""
        response = client.get("/banking/accounts/acc_1/history?days=30")
        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        assert "account_id" in data
        assert "snapshots" in data
        assert "stats" in data

        assert data["account_id"] == "acc_1"
        assert len(data["snapshots"]) == 30

        # Verify stats
        stats = data["stats"]
        assert stats["trend"] == "increasing"
        assert stats["average"] == pytest.approx(5725.0, rel=1e-2)  # Midpoint of 5000 to 6450
        assert stats["minimum"] == 5000.0
        assert stats["maximum"] == 6450.0
        assert stats["change_amount"] == pytest.approx(1450.0, rel=1e-2)
        assert stats["change_percent"] == pytest.approx(29.0, rel=1e-2)

    def test_get_history_decreasing_trend(self, client):
        """Test getting balance history with decreasing trend."""
        response = client.get("/banking/accounts/acc_2/history?days=30")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        assert stats["trend"] == "decreasing"
        assert stats["average"] == pytest.approx(9565.0, rel=1e-2)
        assert stats["minimum"] == 9130.0
        assert stats["maximum"] == 10000.0
        assert stats["change_amount"] == pytest.approx(-870.0, rel=1e-2)
        assert stats["change_percent"] == pytest.approx(-8.7, rel=1e-2)

    def test_get_history_stable_trend(self, client):
        """Test getting balance history with stable trend."""
        response = client.get("/banking/accounts/acc_3/history?days=30")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        assert stats["trend"] == "stable"
        assert stats["average"] == 3000.0
        assert stats["minimum"] == 3000.0
        assert stats["maximum"] == 3000.0
        assert stats["change_amount"] == 0.0
        assert stats["change_percent"] == 0.0

    def test_get_history_custom_days(self, client):
        """Test getting history with custom days parameter."""
        response = client.get("/banking/accounts/acc_1/history?days=7")
        assert response.status_code == 200

        data = response.json()

        # Should only return last 7 days (inclusive of both endpoints = 8 snapshots)
        # days=7 means from today-7 to today (inclusive) = 8 snapshots
        assert len(data["snapshots"]) == 8

    def test_get_history_empty_account(self, client):
        """Test getting history for account with no snapshots."""
        response = client.get("/banking/accounts/acc_nonexistent/history?days=30")
        assert response.status_code == 200

        data = response.json()

        assert data["account_id"] == "acc_nonexistent"
        assert len(data["snapshots"]) == 0

        # Should return zeroed stats
        stats = data["stats"]
        assert stats["trend"] == "stable"
        assert stats["average"] == 0.0
        assert stats["minimum"] == 0.0
        assert stats["maximum"] == 0.0
        assert stats["change_amount"] == 0.0
        assert stats["change_percent"] == 0.0

    def test_get_history_snapshots_format(self, client):
        """Test that snapshots are properly formatted."""
        response = client.get("/banking/accounts/acc_1/history?days=30")
        assert response.status_code == 200

        data = response.json()
        snapshots = data["snapshots"]

        # Check first snapshot has all required fields
        snapshot = snapshots[0]
        assert "account_id" in snapshot
        assert "balance" in snapshot
        assert "date" in snapshot
        assert "source" in snapshot
        assert "created_at" in snapshot

        assert snapshot["account_id"] == "acc_1"
        assert isinstance(snapshot["balance"], (int, float))
        assert isinstance(snapshot["date"], str)
        assert snapshot["source"] == "plaid"

    def test_get_history_sorted_descending(self, client):
        """Test that snapshots are sorted by date descending."""
        response = client.get("/banking/accounts/acc_1/history?days=30")
        assert response.status_code == 200

        data = response.json()
        snapshots = data["snapshots"]

        # Verify snapshots are in descending order (most recent first)
        dates = [s["date"] for s in snapshots]
        assert dates == sorted(dates, reverse=True)

    def test_get_history_days_validation(self, client):
        """Test that days parameter is validated."""
        # Test below minimum
        response = client.get("/banking/accounts/acc_1/history?days=0")
        assert response.status_code == 422  # Validation error

        # Test above maximum
        response = client.get("/banking/accounts/acc_1/history?days=400")
        assert response.status_code == 422  # Validation error

    def test_get_history_trend_threshold(self, client):
        """Test that trend detection uses 5% threshold for stable."""
        from datetime import timedelta
        from fin_infra.banking.history import record_balance_snapshot, _balance_snapshots

        # Clear and add snapshots with 4% increase (should be stable)
        _balance_snapshots.clear()
        today = date.today()

        for i in range(10):
            snapshot_date = today - timedelta(days=9 - i)
            # 4% total increase over 10 days
            balance = 5000.0 + (i * 2.0)
            record_balance_snapshot(
                account_id="acc_threshold",
                balance=balance,
                snapshot_date=snapshot_date,
                source="test",
            )

        response = client.get("/banking/accounts/acc_threshold/history?days=10")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        # 4% change should be classified as stable
        assert stats["trend"] == "stable"
        assert stats["change_percent"] < 5.0
