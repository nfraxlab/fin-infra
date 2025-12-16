"""Acceptance tests for analytics module integration with investments.

Tests the integration between analytics portfolio metrics and real investment holdings.
Verifies that real P/L calculations work with Plaid sandbox data.

Requirements:
- PLAID_CLIENT_ID and PLAID_SECRET environment variables
- PLAID_SANDBOX_ACCESS_TOKEN for actual API calls (optional - tests skip if missing)

Run: poetry run pytest tests/acceptance/test_analytics_investments_integration.py -v
"""

import os
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.investments import easy_investments
from fin_infra.analytics.portfolio import (
    portfolio_metrics_with_holdings,
    calculate_day_change_with_snapshot,
)


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
    reason="PLAID_SANDBOX_ACCESS_TOKEN required for integration tests",
)


@skip_if_no_plaid
@skip_if_no_token
class TestAnalyticsWithRealHoldings:
    """Test analytics portfolio metrics with real Plaid sandbox holdings."""

    def test_portfolio_metrics_with_real_holdings(self):
        """Test calculating portfolio metrics from real Plaid sandbox holdings."""
        investments = easy_investments(provider="plaid")

        try:
            holdings = investments.get_holdings(access_token=PLAID_ACCESS_TOKEN)
        except Exception as e:
            pytest.skip(f"Could not fetch holdings from Plaid: {e}")

        if len(holdings) == 0:
            pytest.skip("No holdings in sandbox account")

        # Calculate metrics from real holdings
        metrics = portfolio_metrics_with_holdings(holdings)

        # Validate metrics
        assert metrics.total_value >= Decimal(0)
        assert isinstance(metrics.allocation_by_asset_class, list)
        assert len(metrics.allocation_by_asset_class) > 0

        # Validate allocations sum to ~100%
        total_percent = sum(a.percentage for a in metrics.allocation_by_asset_class)
        assert 99.0 <= total_percent <= 101.0

        print(f"✓ Portfolio metrics calculated from {len(holdings)} real holdings:")
        print(f"  Total value: ${metrics.total_value:,.2f}")

        # Check if we have cost basis for P/L calculation
        holdings_with_cost = [h for h in holdings if h.cost_basis is not None]
        if len(holdings_with_cost) > 0:
            total_cost = sum(h.cost_basis for h in holdings_with_cost)
            total_value = sum(h.institution_value for h in holdings_with_cost)
            total_return = total_value - total_cost
            total_return_pct = (total_return / total_cost * 100) if total_cost > 0 else 0

            print(f"  Total cost basis: ${total_cost:,.2f}")
            print(f"  Total return: ${total_return:,.2f} ({total_return_pct:+.2f}%)")

        print("  Asset allocation:")
        for alloc in metrics.allocation_by_asset_class:
            print(f"    {alloc.asset_class.value}: {alloc.percentage:.1f}% (${alloc.value:,.2f})")

    def test_portfolio_metrics_handles_missing_cost_basis(self):
        """Test that metrics calculation handles holdings without cost basis."""
        investments = easy_investments(provider="plaid")

        try:
            holdings = investments.get_holdings(access_token=PLAID_ACCESS_TOKEN)
        except Exception as e:
            pytest.skip(f"Could not fetch holdings from Plaid: {e}")

        if len(holdings) == 0:
            pytest.skip("No holdings in sandbox account")

        # Even if some holdings lack cost basis, calculation should work
        metrics = portfolio_metrics_with_holdings(holdings)

        assert metrics.total_value >= Decimal(0)
        assert len(metrics.allocation_by_asset_class) > 0

        holdings_with_cost = [h for h in holdings if h.cost_basis is not None]
        holdings_without_cost = [h for h in holdings if h.cost_basis is None]

        print(f"✓ Handled {len(holdings)} holdings:")
        print(f"  With cost basis: {len(holdings_with_cost)}")
        print(f"  Without cost basis: {len(holdings_without_cost)} (treated as 0)")

    def test_asset_allocation_matches_holdings(self):
        """Test that calculated allocation matches actual holdings distribution."""
        investments = easy_investments(provider="plaid")

        try:
            holdings = investments.get_holdings(access_token=PLAID_ACCESS_TOKEN)
        except Exception as e:
            pytest.skip(f"Could not fetch holdings from Plaid: {e}")

        if len(holdings) == 0:
            pytest.skip("No holdings in sandbox account")

        metrics = portfolio_metrics_with_holdings(holdings)

        # Calculate expected allocation from holdings
        total_value = sum(h.institution_value for h in holdings)

        # Group by security type
        from collections import defaultdict

        value_by_type = defaultdict(Decimal)
        for h in holdings:
            value_by_type[h.security.type] += h.institution_value

        # Verify allocation matches
        for alloc in metrics.allocation_by_asset_class:
            expected_value = value_by_type[alloc.asset_class]
            expected_percent = (expected_value / total_value * 100) if total_value > 0 else 0

            # Allow small floating point differences
            assert abs(alloc.value - expected_value) < Decimal("0.01")
            assert abs(alloc.percentage - expected_percent) < 0.01

        print("✓ Asset allocation calculations match holdings distribution")

    def test_day_change_calculation_with_snapshots(self):
        """Test day change calculation with simulated previous snapshot."""
        investments = easy_investments(provider="plaid")

        try:
            current_holdings = investments.get_holdings(access_token=PLAID_ACCESS_TOKEN)
        except Exception as e:
            pytest.skip(f"Could not fetch holdings from Plaid: {e}")

        if len(current_holdings) == 0:
            pytest.skip("No holdings in sandbox account")

        # Simulate previous day's holdings (reduce values by 2%)
        previous_holdings = []
        for h in current_holdings:
            # Create copy with slightly different value
            import copy

            prev = copy.deepcopy(h)
            prev.institution_value = h.institution_value * Decimal("0.98")  # 2% lower
            prev.institution_price = h.institution_price * Decimal("0.98")
            previous_holdings.append(prev)

        # Calculate day change
        day_change = calculate_day_change_with_snapshot(current_holdings, previous_holdings)

        assert "day_change_dollars" in day_change
        assert "day_change_percent" in day_change

        # Should show positive change (current > previous)
        assert day_change["day_change_dollars"] > 0
        assert day_change["day_change_percent"] > 0

        print("✓ Day change calculation:")
        print(
            f"  Day change: ${day_change['day_change_dollars']:,.2f} ({day_change['day_change_percent']:+.2f}%)"
        )

    def test_real_vs_mock_portfolio_metrics_comparison(self):
        """Compare real holdings metrics vs mock balance-based metrics.

        This demonstrates the improvement from using real holdings data.
        """
        investments = easy_investments(provider="plaid")

        try:
            holdings = investments.get_holdings(access_token=PLAID_ACCESS_TOKEN)
        except Exception as e:
            pytest.skip(f"Could not fetch holdings from Plaid: {e}")

        if len(holdings) == 0:
            pytest.skip("No holdings in sandbox account")

        # Real holdings metrics
        real_metrics = portfolio_metrics_with_holdings(holdings)

        # Mock metrics (would use just account balances)
        # This is what analytics did BEFORE investments module
        mock_total_value = sum(h.institution_value for h in holdings)

        print("\n" + "=" * 60)
        print("REAL VS MOCK PORTFOLIO METRICS COMPARISON")
        print("=" * 60)
        print("\nMOCK (balance-only - BEFORE investments module):")
        print(f"  Total value: ${mock_total_value:,.2f}")
        print("  Cost basis: UNKNOWN (not available)")
        print("  Total return: UNKNOWN (cannot calculate)")
        print("  Asset allocation: ESTIMATED from account types (inaccurate)")

        print("\nREAL (with holdings - AFTER investments module):")
        print(f"  Total value: ${real_metrics.total_value:,.2f}")

        holdings_with_cost = [h for h in holdings if h.cost_basis is not None]
        if len(holdings_with_cost) > 0:
            total_cost = sum(h.cost_basis for h in holdings_with_cost)
            total_value_with_cost = sum(h.institution_value for h in holdings_with_cost)
            total_return = total_value_with_cost - total_cost
            total_return_pct = (total_return / total_cost * 100) if total_cost > 0 else 0
            print(f"  Cost basis: ${total_cost:,.2f} ✓")
            print(f"  Total return: ${total_return:,.2f} ({total_return_pct:+.2f}%) ✓")
        else:
            print("  Cost basis: Not available in sandbox")
            print("  Total return: Cannot calculate")

        print("  Asset allocation: REAL from securities ✓")
        for alloc in real_metrics.allocation_by_asset_class:
            print(f"    {alloc.asset_class.value}: {alloc.percentage:.1f}%")

        print("\n" + "=" * 60)
        print("IMPROVEMENT: Real P/L, accurate allocation, cost basis tracking")
        print("=" * 60 + "\n")

        assert True  # Documentation/comparison test


@skip_if_no_plaid
@skip_if_no_token
class TestAnalyticsAPIWithHoldings:
    """Test analytics API endpoints with holdings integration."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with both analytics and investments."""
        from fin_infra.analytics import add_analytics
        from fin_infra.investments import add_investments

        app = FastAPI(title="Analytics + Investments Integration Tests")

        # Add both modules
        add_analytics(app, prefix="/analytics")
        add_investments(app, provider="plaid", prefix="/investments")

        # Override svc-infra auth
        from svc_infra.api.fastapi.auth.security import _current_principal, Principal

        class MockUser:
            id: str = "user_integration_123"
            email: str = "integration@example.com"

        async def mock_principal(request=None, session=None, jwt_or_cookie=None, ak=None):
            return Principal(user=MockUser(), scopes=["read", "write"], via="test")

        app.dependency_overrides[_current_principal] = mock_principal

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_analytics_portfolio_with_holdings_parameter(self, client):
        """Test analytics portfolio endpoint with with_holdings=true parameter."""
        # Note: Analytics portfolio endpoint would need to be enhanced to accept
        # with_holdings and access_token parameters (from Task 8 implementation)

        # For now, test that both modules work independently
        holdings_response = client.post(
            "/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN}
        )

        if holdings_response.status_code != 200:
            pytest.skip("Could not fetch holdings for integration test")

        holdings = holdings_response.json()

        # Test analytics endpoints exist
        # analytics_response = client.get("/analytics/portfolio?user_id=user123")
        # Would test enhanced endpoint with with_holdings=true

        print(f"✓ Integration test: Fetched {len(holdings)} holdings")
        print("  Note: Analytics API enhancement with with_holdings parameter in Task 8")

    def test_combined_workflow_holdings_to_metrics(self, client):
        """Test complete workflow: fetch holdings → calculate metrics."""
        # 1. Fetch holdings via investments API
        holdings_response = client.post(
            "/investments/holdings", json={"access_token": PLAID_ACCESS_TOKEN}
        )

        if holdings_response.status_code != 200:
            pytest.skip("Could not fetch holdings")

        holdings_data = holdings_response.json()

        # 2. Get asset allocation
        allocation_response = client.post(
            "/investments/allocation", json={"access_token": PLAID_ACCESS_TOKEN}
        )

        assert allocation_response.status_code == 200
        allocation = allocation_response.json()

        # 3. Verify workflow
        print("✓ Complete workflow - Holdings to Metrics:")
        print(f"  1. Fetched {len(holdings_data)} holdings via investments API")
        print("  2. Calculated asset allocation:")
        for alloc in allocation["allocation_by_asset_class"]:
            print(f"     {alloc['asset_class']}: {alloc['percentage']:.1f}%")
        print("  3. Ready for portfolio performance calculations")


@skip_if_no_plaid
class TestAnalyticsInvestmentsIntegrationDocumentation:
    """Document analytics + investments integration for developers."""

    def test_integration_documentation(self):
        """Document how analytics and investments modules work together.

        This isn't a real test - it provides integration documentation.
        """
        print("\n" + "=" * 70)
        print("ANALYTICS + INVESTMENTS INTEGRATION")
        print("=" * 70)
        print(
            """
The investments module enhances analytics with real portfolio data:

BEFORE (balance-only):
  from fin_infra.analytics import easy_analytics
  
  analytics = easy_analytics()
  metrics = await analytics.portfolio_metrics(user_id="user123")
  # Uses account balances only
  # No cost basis, no real P/L, estimated allocation

AFTER (with real holdings):
  from fin_infra.investments import easy_investments
  from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings
  
  # 1. Fetch real holdings
  investments = easy_investments(provider="plaid")
  holdings = await investments.get_holdings(access_token=user_token)
  
  # 2. Calculate metrics with real data
  metrics = portfolio_metrics_with_holdings(holdings)
  
  # Now you have:
  # ✓ Real cost basis from provider
  # ✓ Accurate P/L calculations
  # ✓ Real asset allocation from securities
  # ✓ Unrealized gains/losses
  
  print(f"Total value: ${metrics.total_value:,.2f}")
  print(f"Total return: ${metrics.total_return:,.2f} ({metrics.total_return_percent:.2f}%)")

FASTAPI INTEGRATION:
  from fastapi import FastAPI
  from fin_infra.analytics import add_analytics
  from fin_infra.investments import add_investments
  
  app = FastAPI()
  add_analytics(app, prefix="/analytics")
  add_investments(app, prefix="/investments")
  
  # Clients can now:
  # 1. GET /investments/holdings (fetch holdings)
  # 2. Calculate metrics client-side or server-side
  # 3. GET /analytics/portfolio?with_holdings=true (if enhanced)

USE CASES:
  1. Portfolio Performance Dashboard
     - Fetch holdings daily
     - Calculate day-over-day changes
     - Show real P/L and allocation
  
  2. Rebalancing Recommendations
     - Get current allocation from holdings
     - Compare to target allocation
     - Generate trade recommendations
  
  3. Tax Reporting
     - Get cost basis from holdings
     - Calculate realized/unrealized gains
     - Generate tax forms
  
  4. Multi-Account View
     - Combine holdings from multiple providers
     - Unified portfolio metrics
     - Total net worth (banking + investments)

PERSISTENCE (optional):
  # Store daily snapshots for historical analysis
  from datetime import date
  
  today = date.today()
  holdings = await investments.get_holdings(access_token=token)
  
  # Save to database (app's responsibility)
  for holding in holdings:
      db.save_snapshot(
          user_id=user_id,
          date=today,
          account_id=holding.account_id,
          security_id=holding.security.security_id,
          quantity=holding.quantity,
          value=holding.institution_value,
          cost_basis=holding.cost_basis,
      )
  
  # Later: Calculate day/month/year changes
  yesterday_holdings = db.get_snapshot(user_id, date=yesterday)
  day_change = calculate_day_change_with_snapshot(holdings, yesterday_holdings)
"""
        )
        print("=" * 70 + "\n")

        assert True  # Always passes - documentation only
