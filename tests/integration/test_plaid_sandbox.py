"""Integration tests for Plaid banking sandbox.

These tests use Plaid's sandbox environment for testing.
They are skipped by default unless explicitly enabled via:
  - PLAID_CLIENT_ID environment variable
  - PLAID_SECRET environment variable

Plaid sandbox provides test credentials and data without real bank connections.
See: https://plaid.com/docs/sandbox/

Run with: pytest tests/integration/test_plaid_sandbox.py -v
"""

from __future__ import annotations

import os

import pytest

# Skip marker for tests requiring Plaid sandbox credentials
SKIP_NO_PLAID = pytest.mark.skipif(
    not (os.environ.get("PLAID_CLIENT_ID") and os.environ.get("PLAID_SECRET")),
    reason="PLAID_CLIENT_ID and PLAID_SECRET not set",
)


@SKIP_NO_PLAID
@pytest.mark.integration
class TestPlaidSandboxConnection:
    """Integration tests for Plaid sandbox environment."""

    def test_plaid_client_initialization(self):
        """Test that Plaid client can be initialized with sandbox credentials."""
        from fin_infra.clients.plaid import PlaidClient

        client = PlaidClient(
            client_id=os.environ.get("PLAID_CLIENT_ID"),
            secret=os.environ.get("PLAID_SECRET"),
        )
        assert client is not None
        assert client._client_id is not None
        assert client._secret is not None


@pytest.mark.integration
class TestPlaidProviderMock:
    """Integration tests using mock Plaid provider for API structure verification."""

    def test_banking_provider_interface(self):
        """Test that BankingProvider has expected interface."""
        from fin_infra.providers.base import BankingProvider

        # Verify expected methods exist
        expected_methods = [
            "create_link_token",
            "exchange_public_token",
            "accounts",
            "transactions",
        ]

        for method_name in expected_methods:
            assert hasattr(BankingProvider, method_name) or method_name in dir(BankingProvider), (
                f"BankingProvider missing method: {method_name}"
            )

    def test_account_model_structure(self):
        """Test Account model has expected fields."""
        from fin_infra.models import Account, AccountType
        from decimal import Decimal

        # Create sample account using actual model fields
        account = Account(
            id="test_123",
            name="Test Checking",
            type=AccountType.checking,
            mask="1234",
            balance_available=Decimal("1000.00"),
            balance_current=Decimal("1000.00"),
            currency="USD",
        )

        assert account.id == "test_123"
        assert account.name == "Test Checking"
        assert account.type == AccountType.checking
        assert account.balance_available == Decimal("1000.00")
        assert account.currency == "USD"

    def test_transaction_model_structure(self):
        """Test Transaction model has expected fields."""
        from fin_infra.models import Transaction
        from decimal import Decimal
        from datetime import date

        # Create sample transaction using actual model fields
        transaction = Transaction(
            id="txn_123",
            account_id="acc_123",
            amount=Decimal("42.50"),
            date=date(2024, 1, 15),
            description="Coffee Shop",
            category="Food and Drink",
            currency="USD",
        )

        assert transaction.id == "txn_123"
        assert transaction.amount == Decimal("42.50")
        assert transaction.category == "Food and Drink"


@pytest.mark.integration
class TestBankingAPIEndpoints:
    """Integration tests for banking API endpoints with mock provider."""

    @pytest.fixture
    def app_with_mock_banking(self):
        """Create FastAPI app with mock banking provider."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from fin_infra.banking import add_banking
        from fin_infra.providers.base import BankingProvider

        class MockBankingProvider(BankingProvider):
            """Mock provider for testing."""

            def create_link_token(self, user_id: str) -> str:
                return f"link_token_{user_id}"

            def exchange_public_token(self, public_token: str) -> dict:
                return {"access_token": "test_access", "item_id": "test_item"}

            def accounts(self, access_token: str) -> list:
                return [
                    {
                        "account_id": "acc_1",
                        "name": "Checking",
                        "type": "depository",
                        "subtype": "checking",
                        "balances": {"available": 1000.0, "current": 1000.0},
                    }
                ]

            def transactions(
                self,
                access_token: str,
                *,
                start_date: str | None = None,
                end_date: str | None = None,
            ) -> list:
                return [
                    {
                        "transaction_id": "txn_1",
                        "account_id": "acc_1",
                        "amount": 42.50,
                        "date": "2024-01-15",
                        "name": "Coffee Shop",
                    }
                ]

            def balances(self, access_token: str, account_id: str | None = None) -> dict:
                return {
                    "accounts": [
                        {
                            "account_id": "acc_1",
                            "balances": {"available": 1000.0, "current": 1000.0},
                        }
                    ]
                }

            def identity(self, access_token: str) -> dict:
                return {
                    "identity": {
                        "names": ["Test User"],
                        "emails": ["test@example.com"],
                    }
                }

        app = FastAPI(title="Test Banking API")
        add_banking(app, provider=MockBankingProvider())

        return TestClient(app)

    def test_banking_accounts_endpoint_exists(self, app_with_mock_banking):
        """Test that /banking/accounts endpoint exists."""
        client = app_with_mock_banking

        # Check route exists (may require auth token in real implementation)
        response = client.get("/banking/accounts")

        # Should not be 404 (endpoint exists)
        # May be 401/422 depending on auth requirements
        assert response.status_code != 404

    def test_banking_link_token_endpoint_exists(self, app_with_mock_banking):
        """Test that link endpoint exists."""
        client = app_with_mock_banking

        # Check route exists (actual path is /banking/link not /banking/link_token)
        response = client.post("/banking/link", json={"user_id": "test_user"})

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
