"""Unit tests for investments FastAPI integration (add.py).

Tests all investment API endpoints with mocked InvestmentProvider.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.investments.add import add_investments
from fin_infra.investments.models import (
    Holding,
    InvestmentTransaction,
    InvestmentAccount,
    AssetAllocation,
    Security,
    SecurityType,
    TransactionType,
)
from fin_infra.investments.providers.base import InvestmentProvider


# Test data fixtures
@pytest.fixture
def mock_security() -> Security:
    """Create a mock Security instance."""
    return Security(
        security_id="sec_123",
        cusip="123456789",
        isin="US1234567890",
        ticker_symbol="AAPL",
        name="Apple Inc.",
        type=SecurityType.equity,
        sector="Technology",
        close_price=Decimal("150.00"),
        currency="USD",
    )


@pytest.fixture
def mock_holding(mock_security: Security) -> Holding:
    """Create a mock Holding instance."""
    return Holding(
        account_id="acc_123",
        security=mock_security,
        quantity=Decimal("10"),
        institution_price=Decimal("150.00"),
        institution_value=Decimal("1500.00"),
        cost_basis=Decimal("1200.00"),
        currency="USD",
    )


@pytest.fixture
def mock_transaction(mock_security: Security) -> InvestmentTransaction:
    """Create a mock InvestmentTransaction instance."""
    return InvestmentTransaction(
        transaction_id="txn_123",
        account_id="acc_123",
        security=mock_security,
        transaction_date=date(2024, 1, 15),
        name="AAPL BUY",
        transaction_type=TransactionType.buy,
        quantity=Decimal("5"),
        price=Decimal("150.00"),
        amount=Decimal("750.00"),
        fees=Decimal("10.00"),
        currency="USD",
    )


@pytest.fixture
def mock_investment_account(mock_holding: Holding) -> InvestmentAccount:
    """Create a mock InvestmentAccount instance."""
    return InvestmentAccount(
        account_id="acc_123",
        name="Brokerage Account",
        type="investment",
        subtype="brokerage",
        balances={"current": Decimal("0"), "available": Decimal("0")},
        holdings=[mock_holding],
    )


@pytest.fixture
def mock_allocation() -> AssetAllocation:
    """Create a mock AssetAllocation instance."""
    return AssetAllocation(
        by_security_type={
            SecurityType.equity: 70.0,
            SecurityType.bond: 20.0,
            SecurityType.cash: 10.0,
        },
        by_sector={"Technology": 40.0, "Healthcare": 30.0},
        cash_percent=10.0,
    )


@pytest.fixture
def mock_provider(
    mock_holding: Holding,
    mock_transaction: InvestmentTransaction,
    mock_investment_account: InvestmentAccount,
    mock_allocation: AssetAllocation,
    mock_security: Security,
) -> InvestmentProvider:
    """Create a mock InvestmentProvider with AsyncMock methods."""
    provider = Mock(spec=InvestmentProvider)

    # Mock async methods
    provider.get_holdings = AsyncMock(return_value=[mock_holding])
    provider.get_transactions = AsyncMock(return_value=[mock_transaction])
    provider.get_investment_accounts = AsyncMock(return_value=[mock_investment_account])
    provider.get_securities = AsyncMock(return_value=[mock_security])

    # Mock helper method (synchronous)
    provider.calculate_allocation = Mock(return_value=mock_allocation)

    return provider


@pytest.fixture
def mock_principal():
    """Create a mock Principal for testing (replaces Identity dependency)."""
    from svc_infra.api.fastapi.auth.security import Principal

    mock_user = Mock()
    mock_user.banking_providers = {}  # No stored tokens - tests provide explicit ones
    return Principal(user=mock_user, scopes=[], via="test")


@pytest.fixture
def app_with_investments(mock_provider: InvestmentProvider, mock_principal) -> FastAPI:
    """Create FastAPI app with investments endpoints mounted.

    Note: Patches user_router with public_router to bypass authentication in tests.
    Production code uses user_router (requires authentication).
    """
    from svc_infra.api.fastapi.dual.public import public_router
    from svc_infra.api.fastapi.auth.security import _current_principal

    app = FastAPI()

    # Patch user_router with public_router to avoid authentication dependencies
    with patch("svc_infra.api.fastapi.dual.protected.user_router", public_router):
        # Mount investments with mocked provider
        add_investments(app, provider=mock_provider)

    # Override the _current_principal dependency to return our mock
    # This bypasses database access in Identity resolution
    app.dependency_overrides[_current_principal] = lambda: mock_principal

    return app


@pytest.fixture
def client(app_with_investments: FastAPI) -> TestClient:
    """Create TestClient for FastAPI app."""
    return TestClient(app_with_investments)


# Test add_investments() function
def test_add_investments_creates_provider_if_none(mock_provider: InvestmentProvider):
    """Test add_investments() creates provider if none provided."""
    app = FastAPI()

    with (
        patch("fin_infra.investments.add.easy_investments", return_value=mock_provider),
        patch("svc_infra.api.fastapi.dual.protected.user_router") as mock_user_router,
    ):
        from svc_infra.api.fastapi.dual.public import public_router

        mock_user_router.side_effect = public_router
        provider = add_investments(app)

    assert provider == mock_provider
    assert app.state.investment_provider == mock_provider


def test_add_investments_uses_provided_provider(mock_provider: InvestmentProvider):
    """Test add_investments() uses provided provider."""
    app = FastAPI()

    with patch("svc_infra.api.fastapi.dual.protected.user_router") as mock_user_router:
        from svc_infra.api.fastapi.dual.public import public_router

        mock_user_router.side_effect = public_router
        provider = add_investments(app, provider=mock_provider)

    assert provider == mock_provider
    assert app.state.investment_provider == mock_provider


def test_add_investments_stores_on_app_state(mock_provider: InvestmentProvider):
    """Test add_investments() stores provider on app.state."""
    app = FastAPI()

    with patch("svc_infra.api.fastapi.dual.protected.user_router") as mock_user_router:
        from svc_infra.api.fastapi.dual.public import public_router

        mock_user_router.side_effect = public_router
        add_investments(app, provider=mock_provider)

    assert hasattr(app.state, "investment_provider")
    assert app.state.investment_provider == mock_provider


def test_add_investments_mounts_router(mock_provider: InvestmentProvider):
    """Test add_investments() mounts router with correct prefix."""
    app = FastAPI()

    with patch("svc_infra.api.fastapi.dual.protected.user_router") as mock_user_router:
        from svc_infra.api.fastapi.dual.public import public_router

        mock_user_router.side_effect = public_router
        add_investments(app, provider=mock_provider, prefix="/investments")

    # Verify routes exist
    routes = [route.path for route in app.routes]
    assert "/investments/holdings" in routes
    assert "/investments/transactions" in routes
    assert "/investments/accounts" in routes
    assert "/investments/allocation" in routes
    assert "/investments/securities" in routes


# Test POST /investments/holdings endpoint
def test_get_holdings_with_plaid_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/holdings with Plaid authentication."""
    response = client.post(
        "/investments/holdings",
        json={
            "access_token": "access-sandbox-token",
            "account_ids": ["acc_123"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["account_id"] == "acc_123"

    # Verify provider called correctly
    mock_provider.get_holdings.assert_called_once_with(
        access_token="access-sandbox-token",
        account_ids=["acc_123"],
    )


def test_get_holdings_with_snaptrade_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/holdings with SnapTrade authentication."""
    response = client.post(
        "/investments/holdings",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
            "account_ids": None,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verify provider called with combined auth
    mock_provider.get_holdings.assert_called_once_with(
        access_token="user_123:secret_456",
        account_ids=None,
    )


def test_get_holdings_missing_credentials(client: TestClient):
    """Test GET /investments/holdings returns 400 if no credentials provided."""
    response = client.post(
        "/investments/holdings",
        json={"account_ids": ["acc_123"]},
    )

    assert response.status_code == 400
    assert "No Plaid connection found" in response.json()["detail"]


def test_get_holdings_invalid_token(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/holdings returns 401 for invalid token."""
    mock_provider.get_holdings.side_effect = ValueError("Invalid access token")

    response = client.post(
        "/investments/holdings",
        json={"access_token": "invalid_token"},
    )

    assert response.status_code == 401
    assert "Invalid access token" in response.json()["detail"]


# Test POST /investments/transactions endpoint
def test_get_transactions_with_plaid_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/transactions with Plaid authentication."""
    response = client.post(
        "/investments/transactions",
        json={
            "access_token": "access-sandbox-token",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "account_ids": ["acc_123"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["transaction_id"] == "txn_123"

    # Verify provider called correctly
    mock_provider.get_transactions.assert_called_once_with(
        access_token="access-sandbox-token",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        account_ids=["acc_123"],
    )


def test_get_transactions_with_snaptrade_auth(
    client: TestClient, mock_provider: InvestmentProvider
):
    """Test GET /investments/transactions with SnapTrade authentication."""
    response = client.post(
        "/investments/transactions",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verify provider called with combined auth
    mock_provider.get_transactions.assert_called_once_with(
        access_token="user_123:secret_456",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        account_ids=None,
    )


def test_get_transactions_invalid_date_range(client: TestClient):
    """Test GET /investments/transactions returns 400 for invalid date range."""
    response = client.post(
        "/investments/transactions",
        json={
            "access_token": "token",
            "start_date": "2024-01-31",
            "end_date": "2024-01-01",  # End before start
        },
    )

    assert response.status_code == 400
    assert "start_date must be before end_date" in response.json()["detail"]


# Test POST /investments/accounts endpoint
def test_get_accounts_with_plaid_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/accounts with Plaid authentication."""
    response = client.post(
        "/investments/accounts",
        json={"access_token": "access-sandbox-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["account_id"] == "acc_123"

    # Verify provider called correctly
    mock_provider.get_investment_accounts.assert_called_once_with(
        access_token="access-sandbox-token",
    )


def test_get_accounts_with_snaptrade_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/accounts with SnapTrade authentication."""
    response = client.post(
        "/investments/accounts",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verify provider called with combined auth
    mock_provider.get_investment_accounts.assert_called_once_with(
        access_token="user_123:secret_456",
    )


# Test POST /investments/allocation endpoint
def test_get_allocation_with_plaid_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/allocation with Plaid authentication."""
    response = client.post(
        "/investments/allocation",
        json={
            "access_token": "access-sandbox-token",
            "account_ids": ["acc_123"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "by_security_type" in data
    assert "by_sector" in data
    assert "cash_percent" in data

    # Verify provider called for holdings then allocation
    mock_provider.get_holdings.assert_called_once_with(
        access_token="access-sandbox-token",
        account_ids=["acc_123"],
    )
    mock_provider.calculate_allocation.assert_called_once()


def test_get_allocation_with_snaptrade_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/allocation with SnapTrade authentication."""
    response = client.post(
        "/investments/allocation",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "by_security_type" in data

    # Verify provider called with combined auth
    mock_provider.get_holdings.assert_called_once_with(
        access_token="user_123:secret_456",
        account_ids=None,
    )


# Test POST /investments/securities endpoint
def test_get_securities_with_plaid_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/securities with Plaid authentication."""
    response = client.post(
        "/investments/securities",
        json={
            "access_token": "access-sandbox-token",
            "security_ids": ["sec_123", "sec_456"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["security_id"] == "sec_123"

    # Verify provider called correctly
    mock_provider.get_securities.assert_called_once_with(
        access_token="access-sandbox-token",
        security_ids=["sec_123", "sec_456"],
    )


def test_get_securities_with_snaptrade_auth(client: TestClient, mock_provider: InvestmentProvider):
    """Test GET /investments/securities with SnapTrade authentication."""
    response = client.post(
        "/investments/securities",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
            "security_ids": ["sec_123"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verify provider called with combined auth
    mock_provider.get_securities.assert_called_once_with(
        access_token="user_123:secret_456",
        security_ids=["sec_123"],
    )


# Test error handling
def test_holdings_generic_error(client: TestClient, mock_provider: InvestmentProvider):
    """Test holdings endpoint handles generic errors."""
    mock_provider.get_holdings.side_effect = Exception("Provider error")

    response = client.post(
        "/investments/holdings",
        json={"access_token": "token"},
    )

    assert response.status_code == 500
    assert "Failed to fetch holdings" in response.json()["detail"]


def test_transactions_generic_error(client: TestClient, mock_provider: InvestmentProvider):
    """Test transactions endpoint handles generic errors."""
    mock_provider.get_transactions.side_effect = Exception("Provider error")

    response = client.post(
        "/investments/transactions",
        json={
            "access_token": "token",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        },
    )

    assert response.status_code == 500
    assert "Failed to fetch transactions" in response.json()["detail"]


def test_accounts_generic_error(client: TestClient, mock_provider: InvestmentProvider):
    """Test accounts endpoint handles generic errors."""
    mock_provider.get_investment_accounts.side_effect = Exception("Provider error")

    response = client.post(
        "/investments/accounts",
        json={"access_token": "token"},
    )

    assert response.status_code == 500
    assert "Failed to fetch accounts" in response.json()["detail"]


def test_allocation_generic_error(client: TestClient, mock_provider: InvestmentProvider):
    """Test allocation endpoint handles generic errors."""
    mock_provider.get_holdings.side_effect = Exception("Provider error")

    response = client.post(
        "/investments/allocation",
        json={"access_token": "token"},
    )

    assert response.status_code == 500
    assert "Failed to fetch allocation" in response.json()["detail"]


def test_securities_generic_error(client: TestClient, mock_provider: InvestmentProvider):
    """Test securities endpoint handles generic errors."""
    mock_provider.get_securities.side_effect = Exception("Provider error")

    response = client.post(
        "/investments/securities",
        json={
            "access_token": "token",
            "security_ids": ["sec_123"],
        },
    )

    assert response.status_code == 500
    assert "Failed to fetch securities" in response.json()["detail"]


# Test OpenAPI documentation
def test_openapi_endpoints_exist(client: TestClient):
    """Test that OpenAPI docs endpoints are accessible."""
    # Check main docs
    response = client.get("/docs")
    assert response.status_code == 200

    # Check OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    # Verify investment endpoints are in schema
    assert "/investments/holdings" in schema["paths"]


# Integration test
def test_full_workflow_plaid(client: TestClient, mock_provider: InvestmentProvider):
    """Test complete workflow with Plaid: accounts -> holdings -> allocation."""
    # 1. Get accounts
    response = client.post(
        "/investments/accounts",
        json={"access_token": "access-sandbox-token"},
    )
    assert response.status_code == 200
    accounts = response.json()
    account_id = accounts[0]["account_id"]

    # 2. Get holdings for account
    response = client.post(
        "/investments/holdings",
        json={
            "access_token": "access-sandbox-token",
            "account_ids": [account_id],
        },
    )
    assert response.status_code == 200
    holdings = response.json()
    assert len(holdings) == 1

    # 3. Get allocation
    response = client.post(
        "/investments/allocation",
        json={
            "access_token": "access-sandbox-token",
            "account_ids": [account_id],
        },
    )
    assert response.status_code == 200
    allocation = response.json()
    assert "by_security_type" in allocation


def test_full_workflow_snaptrade(client: TestClient, mock_provider: InvestmentProvider):
    """Test complete workflow with SnapTrade: accounts -> holdings -> allocation."""
    # 1. Get accounts
    response = client.post(
        "/investments/accounts",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
        },
    )
    assert response.status_code == 200
    accounts = response.json()
    account_id = accounts[0]["account_id"]

    # 2. Get holdings for account
    response = client.post(
        "/investments/holdings",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
            "account_ids": [account_id],
        },
    )
    assert response.status_code == 200
    holdings = response.json()
    assert len(holdings) == 1

    # 3. Get allocation
    response = client.post(
        "/investments/allocation",
        json={
            "user_id": "user_123",
            "user_secret": "secret_456",
            "account_ids": [account_id],
        },
    )
    assert response.status_code == 200
    allocation = response.json()
    assert "by_security_type" in allocation
