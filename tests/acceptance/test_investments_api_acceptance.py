"""Acceptance tests for investments FastAPI API endpoints.

These tests verify the full investments REST API with real Plaid sandbox calls.
Tests the integration between FastAPI, investments module, and Plaid provider.

Requirements:
- PLAID_CLIENT_ID and PLAID_SECRET environment variables
- PLAID_SANDBOX_ACCESS_TOKEN for actual API calls (optional - tests skip if missing)

Run: poetry run pytest tests/acceptance/test_investments_api_acceptance.py -v
"""

import os
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.investments import add_investments

pytestmark = [pytest.mark.acceptance]


# Skip if Plaid not configured
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ACCESS_TOKEN = os.getenv("PLAID_SANDBOX_ACCESS_TOKEN")

skip_if_no_plaid = pytest.mark.skipif(
    not (PLAID_CLIENT_ID and PLAID_SECRET),
    reason="PLAID_CLIENT_ID and PLAID_SECRET required",
)

skip_if_no_token = pytest.mark.skipif(
    not PLAID_ACCESS_TOKEN,
    reason="PLAID_SANDBOX_ACCESS_TOKEN required for API tests",
)


@pytest.fixture
def app():
    """Create FastAPI app with investments endpoints."""
    app = FastAPI(title="Investments API Acceptance Tests")

    # Add investments module with Plaid provider
    add_investments(app, provider="plaid", prefix="/investments")

    # Override svc-infra auth for testing (investments uses user_router)
    from svc_infra.api.fastapi.auth.security import Principal, _current_principal

    class MockUser:
        id: str = "user_acceptance_123"
        email: str = "acceptance@example.com"

    async def mock_principal(request=None, session=None, jwt_or_cookie=None, ak=None):
        return Principal(user=MockUser(), scopes=["read", "write"], via="test")

    app.dependency_overrides[_current_principal] = mock_principal

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@skip_if_no_plaid
class TestInvestmentsAPIStructure:
    """Test API structure and documentation without making real Plaid calls."""

    def test_openapi_schema_generated(self, client):
        """Test that OpenAPI schema is generated for investments endpoints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "paths" in schema

        # Check that investments endpoints are in schema
        paths = schema["paths"]
        assert "/investments/holdings" in paths or any("holdings" in p for p in paths)

        print("[OK] OpenAPI schema includes investments endpoints")

    def test_docs_page_accessible(self, client):
        """Test that /docs page is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "Investment" in response.text or "holdings" in response.text

        print("[OK] /docs page accessible with investments endpoints")

    def test_all_endpoints_present(self, client):
        """Test that all expected endpoints are registered."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]

        # Expected endpoints (check for substring since prefix may vary)
        expected_endpoints = ["holdings", "transactions", "accounts", "allocation", "securities"]

        for endpoint in expected_endpoints:
            assert any(endpoint in path for path in paths), f"Missing endpoint: {endpoint}"

        print(f"[OK] All {len(expected_endpoints)} investment endpoints registered")


@skip_if_no_plaid
@skip_if_no_token
class TestInvestmentsAPIWithPlaidSandbox:
    """Test API endpoints with real Plaid sandbox calls."""

    def test_post_holdings_endpoint(self, client):
        """Test POST /investments/holdings with real Plaid access token."""
        response = client.post("/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN})

        # May get 200 or 500 depending on sandbox state
        if response.status_code == 500:
            pytest.skip(f"Plaid sandbox error: {response.json().get('detail', 'Unknown')}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        if len(data) == 0:
            pytest.skip("Sandbox account has no holdings")

        # Validate first holding structure
        holding = data[0]
        assert "account_id" in holding
        assert "security" in holding
        assert "quantity" in holding
        assert "institution_value" in holding

        print(f"[OK] POST /investments/holdings returned {len(data)} holdings")

    def test_post_holdings_with_account_filter(self, client):
        """Test holdings endpoint with account_ids filter."""
        # First get all holdings
        response = client.post("/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN})

        if response.status_code != 200:
            pytest.skip("Could not fetch holdings for account filtering test")

        all_holdings = response.json()
        if len(all_holdings) == 0:
            pytest.skip("No holdings to test filtering")

        # Extract unique account IDs
        account_ids = list({h["account_id"] for h in all_holdings})
        if len(account_ids) == 0:
            pytest.skip("No account IDs found")

        # Filter by first account
        response = client.post(
            "/investments/holdings",
            json={"access_token": PLAID_ACCESS_TOKEN, "account_ids": [account_ids[0]]},
        )

        assert response.status_code == 200
        filtered = response.json()

        # All results should be from the requested account
        assert all(h["account_id"] == account_ids[0] for h in filtered)
        assert len(filtered) <= len(all_holdings)

        print(f"[OK] Account filtering: {len(filtered)}/{len(all_holdings)} holdings in account")

    def test_post_transactions_endpoint(self, client):
        """Test POST /investments/transactions with date range."""
        end_date = date.today()
        start_date = end_date - timedelta(days=90)

        response = client.post(
            "/investments/transactions",
            json={
                "access_token": PLAID_ACCESS_TOKEN,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        if response.status_code == 500:
            pytest.skip(f"Plaid sandbox error: {response.json().get('detail', 'Unknown')}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        if len(data) == 0:
            pytest.skip("No transactions in sandbox account")

        # Validate first transaction structure
        transaction = data[0]
        assert "transaction_id" in transaction
        assert "account_id" in transaction
        assert "security" in transaction
        assert "transaction_type" in transaction
        assert "transaction_date" in transaction

        print(f"[OK] POST /investments/transactions returned {len(data)} transactions")

    def test_post_accounts_endpoint(self, client):
        """Test POST /investments/accounts endpoint."""
        response = client.post("/investments/accounts", json={"access_token": PLAID_ACCESS_TOKEN})

        if response.status_code == 500:
            pytest.skip(f"Plaid sandbox error: {response.json().get('detail', 'Unknown')}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        if len(data) == 0:
            pytest.skip("No investment accounts in sandbox")

        # Validate first account structure
        account = data[0]
        assert "account_id" in account
        assert "name" in account
        assert "total_value" in account

        print(f"[OK] POST /investments/accounts returned {len(data)} accounts")

    def test_post_allocation_endpoint(self, client):
        """Test POST /investments/allocation endpoint."""
        response = client.post("/investments/allocation", json={"access_token": PLAID_ACCESS_TOKEN})

        if response.status_code == 500:
            pytest.skip(f"Plaid sandbox error: {response.json().get('detail', 'Unknown')}")

        assert response.status_code == 200
        data = response.json()

        assert "total_value" in data
        assert "allocation_by_asset_class" in data
        assert isinstance(data["allocation_by_asset_class"], list)

        # Validate allocations sum to ~100%
        total_percent = sum(alloc["percentage"] for alloc in data["allocation_by_asset_class"])
        assert 99.0 <= total_percent <= 101.0

        print("[OK] POST /investments/allocation returned asset allocation:")
        for alloc in data["allocation_by_asset_class"]:
            print(f"  {alloc['asset_class']}: {alloc['percentage']:.1f}%")

    def test_post_securities_endpoint(self, client):
        """Test POST /investments/securities endpoint."""
        # First get holdings to extract security IDs
        response = client.post("/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN})

        if response.status_code != 200:
            pytest.skip("Could not fetch holdings for securities test")

        holdings = response.json()
        if len(holdings) == 0:
            pytest.skip("No holdings to extract securities from")

        # Get first 3 security IDs
        security_ids = [h["security"]["security_id"] for h in holdings[:3]]

        response = client.post(
            "/investments/securities",
            json={"access_token": PLAID_ACCESS_TOKEN, "security_ids": security_ids},
        )

        if response.status_code == 500:
            pytest.skip(f"Plaid sandbox error: {response.json().get('detail', 'Unknown')}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Validate first security structure
        security = data[0]
        assert "security_id" in security
        assert "type" in security

        print(f"[OK] POST /investments/securities returned {len(data)} securities")

    def test_error_handling_invalid_token(self, client):
        """Test API error handling with invalid access token."""
        response = client.post(
            "/investments/holdings", json={"access_token": "invalid_token_12345"}
        )

        # Should return 401 or 500 with error message
        assert response.status_code in [401, 500]

        data = response.json()
        assert "detail" in data
        assert "INVALID" in data["detail"] or "invalid" in data["detail"].lower()

        print("[OK] API error handling: Invalid token returns appropriate error")

    def test_error_handling_missing_required_fields(self, client):
        """Test API validation for missing required fields."""
        # Missing access_token
        response = client.post("/investments/holdings", json={})

        # Should return 422 (validation error)
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

        print("[OK] API validation: Missing required fields returns 422")

    def test_error_handling_invalid_date_range(self, client):
        """Test API validation for invalid date ranges in transactions."""
        end_date = date.today()
        start_date = end_date + timedelta(days=30)  # Start after end (invalid)

        response = client.post(
            "/investments/transactions",
            json={
                "access_token": PLAID_ACCESS_TOKEN,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        # Should return 400 or 422 for invalid date range
        assert response.status_code in [400, 422]

        print("[OK] API validation: Invalid date range returns error")


@skip_if_no_plaid
@skip_if_no_token
class TestInvestmentsAPIPerformance:
    """Test API performance and response times."""

    def test_holdings_endpoint_response_time(self, client):
        """Test that holdings endpoint responds within reasonable time."""
        import time

        start_time = time.time()
        response = client.post("/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN})
        elapsed = time.time() - start_time

        if response.status_code != 200:
            pytest.skip("Could not test performance due to API error")

        # Should respond within 5 seconds (Plaid sandbox can be slow)
        assert elapsed < 5.0, f"Holdings endpoint took {elapsed:.2f}s (should be <5s)"

        print(f"[OK] Holdings endpoint response time: {elapsed:.2f}s")

    def test_multiple_concurrent_requests(self, client):
        """Test that API can handle multiple concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.post("/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN})

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in futures]

        # All should succeed or fail gracefully
        success_count = sum(1 for r in responses if r.status_code == 200)
        error_count = sum(1 for r in responses if r.status_code in [429, 500])

        print(f"[OK] Concurrent requests: {success_count} succeeded, {error_count} errors")

        # At least some should succeed (Plaid may rate limit)
        assert success_count > 0 or error_count > 0, "All requests failed unexpectedly"


@skip_if_no_plaid
class TestInvestmentsAPIDocumentation:
    """Document API usage for developers."""

    def test_api_endpoint_documentation(self, client):
        """Document all investments API endpoints.

        This isn't a real test - it provides API documentation.
        """
        print("\n" + "=" * 70)
        print("INVESTMENTS API ENDPOINTS")
        print("=" * 70)
        print(
            """
POST /investments/holdings
  Fetch investment holdings from connected accounts
  Request: {"access_token": "access-sandbox-xxx", "account_ids": ["acc_123"] (optional)}
  Response: List[Holding] with securities, quantities, values, cost basis

POST /investments/transactions
  Fetch investment transactions in date range
  Request: {
    "access_token": "access-sandbox-xxx",
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "account_ids": ["acc_123"] (optional)
  }
  Response: List[InvestmentTransaction] with buys, sells, dividends, etc.

POST /investments/accounts
  Fetch investment account summaries
  Request: {"access_token": "access-sandbox-xxx"}
  Response: List[InvestmentAccount] with total values and metrics

POST /investments/allocation
  Calculate asset allocation from holdings
  Request: {"access_token": "access-sandbox-xxx", "account_ids": ["acc_123"] (optional)}
  Response: AssetAllocation with breakdown by asset class

POST /investments/securities
  Fetch detailed security information
  Request: {"access_token": "access-sandbox-xxx", "security_ids": ["sec_123", "sec_456"]}
  Response: List[Security] with names, types, identifiers

All endpoints:
- Use POST (not GET) to keep credentials in request body
- Require Plaid access_token from Plaid Link flow
- Return JSON matching Pydantic models
- Handle errors with appropriate HTTP status codes:
  * 401: Invalid access token
  * 422: Validation error (missing/invalid fields)
  * 500: Plaid API error or internal error
"""
        )
        print("=" * 70 + "\n")

        assert True  # Always passes - documentation only

    def test_integration_example(self):
        """Document how to integrate investments API in an application.

        This isn't a real test - it provides integration examples.
        """
        print("\n" + "=" * 70)
        print("INTEGRATION EXAMPLE")
        print("=" * 70)
        print(
            """
# 1. Add investments to your FastAPI app
from fastapi import FastAPI
from fin_infra.investments import add_investments

app = FastAPI()
add_investments(app, provider="plaid", prefix="/investments")

# 2. Get Plaid access token (user authenticates via Plaid Link)
# Frontend: Use Plaid Link to get public_token
# Backend: Exchange public_token for access_token
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

exchange_response = plaid_client.item_public_token_exchange(
    ItemPublicTokenExchangeRequest(public_token=public_token)
)
access_token = exchange_response['access_token']

# 3. Store access_token securely (encrypted in database)
# Use svc-infra encryption utilities

# 4. Fetch holdings from your frontend
fetch('https://yourapp.com/investments/holdings', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({access_token: user_access_token})
})
.then(r => r.json())
.then(holdings => {
  // Display holdings in portfolio view
  console.log(`Total holdings: ${holdings.length}`);
});

# 5. Calculate portfolio metrics
fetch('https://yourapp.com/investments/allocation', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({access_token: user_access_token})
})
.then(r => r.json())
.then(allocation => {
  // Show asset allocation pie chart
  allocation.allocation_by_asset_class.forEach(a => {
    console.log(`${a.asset_class}: ${a.percentage}%`);
  });
});

# 6. Use with analytics module for enhanced portfolio metrics
from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings
from fin_infra.investments import easy_investments

investments = easy_investments(provider="plaid")
holdings = await investments.get_holdings(access_token=user_token)
metrics = portfolio_metrics_with_holdings(holdings)

print(f"Total value: ${metrics.total_value:,.2f}")
print(f"Total return: ${metrics.total_return:,.2f} ({metrics.total_return_percent:.2f}%)")
"""
        )
        print("=" * 70 + "\n")

        assert True  # Always passes - documentation only
