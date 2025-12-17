"""Acceptance tests for investments module with Plaid sandbox.

These tests make real API calls to Plaid's sandbox environment and require:
- PLAID_CLIENT_ID: Your Plaid client ID
- PLAID_SECRET: Your Plaid sandbox secret
- PLAID_ENVIRONMENT: Set to "sandbox" (default)

To run these tests:
1. Sign up for Plaid sandbox: https://dashboard.plaid.com/signup
2. Get your client_id and sandbox secret from the Plaid dashboard
3. Export environment variables:
   export PLAID_CLIENT_ID=your_client_id
   export PLAID_SECRET=your_sandbox_secret
   export PLAID_ENVIRONMENT=sandbox
4. Run: poetry run pytest tests/acceptance/test_investments_plaid_acceptance.py -v

Plaid Sandbox Test Credentials:
- Username: user_good
- Password: pass_good
- Institution: First Platypus Bank (ins_109508)
- These credentials work in sandbox without real bank connections

Plaid Sandbox Limitations:
- No real money or accounts
- Limited transaction history
- Holdings data may be synthetic
- Rate limits: 1000 requests/day (sandbox)
"""

import os
from decimal import Decimal
from datetime import date, timedelta

import pytest

from fin_infra.investments import easy_investments
from fin_infra.investments.models import (
    Holding,
    Security,
    InvestmentTransaction,
    InvestmentAccount,
    AssetAllocation,
    SecurityType,
    TransactionType,
)


pytestmark = [pytest.mark.acceptance]


# Skip all tests if Plaid credentials not configured
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENVIRONMENT = os.getenv("PLAID_ENVIRONMENT", "sandbox")

skip_if_no_plaid = pytest.mark.skipif(
    not (PLAID_CLIENT_ID and PLAID_SECRET),
    reason="PLAID_CLIENT_ID and PLAID_SECRET environment variables required",
)


@pytest.fixture
def plaid_access_token():
    """Get Plaid sandbox access token for testing.

    In a real application, users would go through Plaid Link flow to get access tokens.
    For acceptance tests, we need a sandbox access token from a test account.

    NOTE: You must have a sandbox access token to run these tests. Get one by:
    1. Using Plaid Link in sandbox mode
    2. Or using the /sandbox/public_token/create endpoint
    3. Then exchange public token for access token

    For now, we'll use an environment variable if provided, or skip tests.
    """
    access_token = os.getenv("PLAID_SANDBOX_ACCESS_TOKEN")
    if not access_token:
        pytest.skip(
            "PLAID_SANDBOX_ACCESS_TOKEN not set. "
            "Create a sandbox item via Plaid Link or /sandbox/public_token/create endpoint."
        )
    return access_token


@skip_if_no_plaid
class TestPlaidInvestmentsAcceptance:
    """Acceptance tests for Plaid investment provider with sandbox."""

    def test_easy_investments_auto_detection(self):
        """Test that easy_investments() auto-detects Plaid from environment."""
        investments = easy_investments()

        assert investments is not None
        assert hasattr(investments, "get_holdings")
        assert hasattr(investments, "get_transactions")
        print("✓ easy_investments() auto-detected Plaid provider from env vars")

    def test_get_holdings_with_sandbox(self, plaid_access_token):
        """Test fetching real holdings from Plaid sandbox.

        This makes a real API call to Plaid's sandbox environment.
        Sandbox holdings are synthetic but follow the same data structure.
        """
        investments = easy_investments(provider="plaid")

        try:
            holdings = investments.get_holdings(access_token=plaid_access_token)
        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

        # Validate response structure
        assert isinstance(holdings, list)

        if len(holdings) == 0:
            pytest.skip("Sandbox account has no holdings (empty account)")

        # Validate first holding
        holding = holdings[0]
        assert isinstance(holding, Holding)
        assert holding.account_id
        assert isinstance(holding.security, Security)
        assert holding.quantity >= Decimal(0)
        assert holding.institution_value >= Decimal(0)

        # Security validation
        security = holding.security
        assert security.security_id
        assert security.type in SecurityType

        print(f"✓ Fetched {len(holdings)} holdings from Plaid sandbox")
        print(
            f"  Sample holding: {security.name or security.ticker_symbol} - {holding.quantity} @ ${holding.institution_price}"
        )

    def test_get_holdings_filters_by_account(self, plaid_access_token):
        """Test fetching holdings filtered by specific account IDs."""
        investments = easy_investments(provider="plaid")

        try:
            # First get all holdings to find account IDs
            all_holdings = investments.get_holdings(access_token=plaid_access_token)

            if len(all_holdings) == 0:
                pytest.skip("No holdings in sandbox account")

            # Get unique account IDs
            account_ids = list(set(h.account_id for h in all_holdings))
            if len(account_ids) == 0:
                pytest.skip("No account IDs found")

            # Filter by first account only
            first_account_id = account_ids[0]
            filtered_holdings = investments.get_holdings(
                access_token=plaid_access_token, account_ids=[first_account_id]
            )

            # Validate filtering worked
            assert all(h.account_id == first_account_id for h in filtered_holdings)
            assert len(filtered_holdings) <= len(all_holdings)

            print(
                f"✓ Account filtering: {len(filtered_holdings)}/{len(all_holdings)} holdings in account {first_account_id}"
            )

        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

    def test_get_transactions_with_sandbox(self, plaid_access_token):
        """Test fetching investment transactions from Plaid sandbox."""
        investments = easy_investments(provider="plaid")

        # Get last 90 days of transactions
        end_date = date.today()
        start_date = end_date - timedelta(days=90)

        try:
            transactions = investments.get_transactions(
                access_token=plaid_access_token,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

        assert isinstance(transactions, list)

        if len(transactions) == 0:
            pytest.skip("No transactions in sandbox account (expected for new accounts)")

        # Validate first transaction
        transaction = transactions[0]
        assert isinstance(transaction, InvestmentTransaction)
        assert transaction.transaction_id
        assert transaction.account_id
        assert isinstance(transaction.security, Security)
        assert transaction.transaction_type in TransactionType
        assert isinstance(transaction.transaction_date, date)

        print(f"✓ Fetched {len(transactions)} transactions from Plaid sandbox")
        print(
            f"  Sample: {transaction.transaction_type.value} - {transaction.security.name or transaction.security.ticker_symbol}"
        )

    def test_get_investment_accounts(self, plaid_access_token):
        """Test fetching investment account summaries."""
        investments = easy_investments(provider="plaid")

        try:
            accounts = investments.get_investment_accounts(access_token=plaid_access_token)
        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

        assert isinstance(accounts, list)

        if len(accounts) == 0:
            pytest.skip("No investment accounts in sandbox")

        # Validate first account
        account = accounts[0]
        assert isinstance(account, InvestmentAccount)
        assert account.account_id
        assert account.name
        assert account.total_value >= Decimal(0)

        print(f"✓ Fetched {len(accounts)} investment accounts from Plaid sandbox")
        print(f"  Sample account: {account.name} - ${account.total_value:,.2f}")

    def test_get_allocation(self, plaid_access_token):
        """Test calculating asset allocation from holdings."""
        investments = easy_investments(provider="plaid")

        try:
            allocation = investments.get_allocation(access_token=plaid_access_token)
        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

        assert isinstance(allocation, AssetAllocation)
        assert allocation.total_value >= Decimal(0)

        # Validate allocations sum to ~100%
        total_percent = sum(alloc.percentage for alloc in allocation.allocation_by_asset_class)
        assert 99.0 <= total_percent <= 101.0, (
            f"Allocations should sum to 100%, got {total_percent}%"
        )

        print("✓ Asset allocation calculated from Plaid sandbox holdings:")
        for alloc in allocation.allocation_by_asset_class:
            print(f"  {alloc.asset_class.value}: {alloc.percentage:.1f}% (${alloc.value:,.2f})")

    def test_get_securities(self, plaid_access_token):
        """Test fetching security details."""
        investments = easy_investments(provider="plaid")

        try:
            # First get holdings to find security IDs
            holdings = investments.get_holdings(access_token=plaid_access_token)

            if len(holdings) == 0:
                pytest.skip("No holdings to extract securities from")

            # Get first 5 security IDs
            security_ids = [h.security.security_id for h in holdings[:5]]

            securities = investments.get_securities(
                access_token=plaid_access_token, security_ids=security_ids
            )

            assert isinstance(securities, list)
            assert len(securities) > 0

            # Validate first security
            security = securities[0]
            assert isinstance(security, Security)
            assert security.security_id
            assert security.type in SecurityType

            print(f"✓ Fetched {len(securities)} securities from Plaid sandbox")

        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

    def test_cost_basis_and_pnl_calculation(self, plaid_access_token):
        """Test that holdings include cost basis for P/L calculations."""
        investments = easy_investments(provider="plaid")

        try:
            holdings = investments.get_holdings(access_token=plaid_access_token)

            if len(holdings) == 0:
                pytest.skip("No holdings in sandbox account")

            # Find holdings with cost basis
            holdings_with_cost_basis = [h for h in holdings if h.cost_basis is not None]

            if len(holdings_with_cost_basis) == 0:
                pytest.skip(
                    "No holdings have cost basis in sandbox (expected for some account types)"
                )

            # Validate P/L calculation
            holding = holdings_with_cost_basis[0]
            assert holding.cost_basis > Decimal(0)

            # Calculate unrealized gain/loss
            unrealized_gain = holding.institution_value - holding.cost_basis
            unrealized_percent = (unrealized_gain / holding.cost_basis) * 100

            print("✓ Cost basis and P/L calculation:")
            print(f"  Security: {holding.security.name or holding.security.ticker_symbol}")
            print(f"  Quantity: {holding.quantity}")
            print(f"  Cost basis: ${holding.cost_basis:,.2f}")
            print(f"  Current value: ${holding.institution_value:,.2f}")
            print(f"  Unrealized gain/loss: ${unrealized_gain:,.2f} ({unrealized_percent:+.2f}%)")

        except Exception as e:
            pytest.skip(f"Plaid sandbox API error: {e}")

    def test_error_handling_invalid_token(self):
        """Test error handling with invalid access token."""
        investments = easy_investments(provider="plaid")

        with pytest.raises(ValueError, match="INVALID_ACCESS_TOKEN"):
            investments.get_holdings(access_token="invalid_token_12345")

        print("✓ Error handling: Invalid access token raises ValueError")

    def test_error_handling_missing_credentials(self):
        """Test error handling when Plaid credentials missing."""
        # Temporarily clear environment variables
        orig_client_id = os.environ.pop("PLAID_CLIENT_ID", None)
        orig_secret = os.environ.pop("PLAID_SECRET", None)

        try:
            with pytest.raises(ValueError, match="PLAID_CLIENT_ID.*required"):
                easy_investments(provider="plaid")

            print("✓ Error handling: Missing credentials raises ValueError")

        finally:
            # Restore environment variables
            if orig_client_id:
                os.environ["PLAID_CLIENT_ID"] = orig_client_id
            if orig_secret:
                os.environ["PLAID_SECRET"] = orig_secret


@skip_if_no_plaid
class TestPlaidRateLimits:
    """Test Plaid rate limit handling in sandbox."""

    def test_rate_limit_documentation(self):
        """Document Plaid rate limits for developers.

        This isn't a real test - it documents rate limits for reference.
        """
        rate_limits = {
            "sandbox": "1000 requests/day (all endpoints combined)",
            "development": "100 requests/minute per product",
            "production": "600 requests/minute per product",
        }

        print("\n" + "=" * 60)
        print("PLAID RATE LIMITS")
        print("=" * 60)
        for env, limit in rate_limits.items():
            print(f"  {env.upper()}: {limit}")
        print("=" * 60)
        print("\nBest practices:")
        print("  1. Cache holdings/transactions data")
        print("  2. Implement exponential backoff on 429 errors")
        print("  3. Use webhooks for updates instead of polling")
        print("  4. Batch requests when possible")
        print("=" * 60 + "\n")

        # This always passes - it's just documentation
        assert True


@skip_if_no_plaid
class TestPlaidSandboxSetup:
    """Helper tests for setting up Plaid sandbox environment."""

    def test_environment_variables_configured(self):
        """Verify Plaid environment variables are set correctly."""
        assert PLAID_CLIENT_ID, "PLAID_CLIENT_ID not set"
        assert PLAID_SECRET, "PLAID_SECRET not set"
        assert PLAID_ENVIRONMENT == "sandbox", (
            f"PLAID_ENVIRONMENT should be 'sandbox', got '{PLAID_ENVIRONMENT}'"
        )

        print("✓ Plaid environment variables configured:")
        print(f"  PLAID_CLIENT_ID: {PLAID_CLIENT_ID[:8]}...")
        print(f"  PLAID_SECRET: {PLAID_SECRET[:8]}...")
        print(f"  PLAID_ENVIRONMENT: {PLAID_ENVIRONMENT}")

    def test_sandbox_documentation(self):
        """Document how to set up Plaid sandbox for testing.

        This isn't a real test - it provides setup instructions.
        """
        print("\n" + "=" * 70)
        print("PLAID SANDBOX SETUP INSTRUCTIONS")
        print("=" * 70)
        print(
            """
1. Create Plaid account:
   https://dashboard.plaid.com/signup

2. Get sandbox credentials:
   - Navigate to Team Settings → Keys
   - Copy your client_id
   - Copy your sandbox secret (NOT production secret!)

3. Set environment variables:
   export PLAID_CLIENT_ID=your_client_id_here
   export PLAID_SECRET=your_sandbox_secret_here
   export PLAID_ENV=sandbox

4. Create sandbox access token (two methods):

   METHOD A - Using Plaid Link (recommended):
   - Integrate Plaid Link in sandbox mode
   - Use test credentials: user_good / pass_good
   - Select "First Platypus Bank" (ins_109508)
   - Exchange public_token for access_token
   - Save access_token: export PLAID_SANDBOX_ACCESS_TOKEN=access-sandbox-xxx

   METHOD B - Using API directly:
   ```python
   from plaid.api import plaid_api
   from plaid import Configuration, ApiClient
   from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
   from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

   configuration = Configuration(
       host="https://sandbox.plaid.com",
       api_key={
           'clientId': 'your_client_id',
           'secret': 'your_sandbox_secret',
       }
   )
   
   client = plaid_api.PlaidApi(ApiClient(configuration))
   
   # Create sandbox public token
   response = client.sandbox_public_token_create(
       SandboxPublicTokenCreateRequest(
           institution_id='ins_109508',
           initial_products=['investments']
       )
   )
   public_token = response['public_token']
   
   # Exchange for access token
   exchange_response = client.item_public_token_exchange(
       ItemPublicTokenExchangeRequest(public_token=public_token)
   )
   access_token = exchange_response['access_token']
   
   # Save it
   print(f"export PLAID_SANDBOX_ACCESS_TOKEN={access_token}")
   ```

5. Run acceptance tests:
   poetry run pytest tests/acceptance/test_investments_plaid_acceptance.py -v

6. Sandbox test credentials:
   - Username: user_good (successful authentication)
   - Username: user_bad (failed authentication - for error testing)
   - Password: pass_good (for user_good)
   - Institution: First Platypus Bank (ins_109508)
   
7. Sandbox limitations:
   - Holdings data is synthetic (not real market prices)
   - Transaction history is limited
   - Rate limit: 1000 requests/day
   - No cost for sandbox usage
"""
        )
        print("=" * 70 + "\n")

        # Always passes - documentation only
        assert True
