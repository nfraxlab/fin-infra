"""Integration tests for analytics FastAPI endpoints.

Tests add_analytics() helper and all mounted endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.analytics.add import add_analytics


@pytest.fixture
def app():
    """Create FastAPI app with analytics endpoints."""
    app = FastAPI(title="Test Analytics API")
    add_analytics(app)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# Test: add_analytics() helper
def test_add_analytics_helper(app):
    """Test add_analytics() mounts endpoints correctly."""
    # Check analytics engine stored on app state
    assert hasattr(app.state, "analytics_engine")
    assert app.state.analytics_engine is not None

    # Check routes exist
    routes = [route.path for route in app.routes]
    assert "/analytics/cash-flow" in routes or "/analytics/cash-flow/" in routes
    assert "/analytics/savings-rate" in routes or "/analytics/savings-rate/" in routes
    assert "/analytics/spending-insights" in routes or "/analytics/spending-insights/" in routes
    assert "/analytics/spending-advice" in routes or "/analytics/spending-advice/" in routes
    assert "/analytics/portfolio" in routes or "/analytics/portfolio/" in routes
    assert "/analytics/performance" in routes or "/analytics/performance/" in routes
    assert "/analytics/forecast-net-worth" in routes or "/analytics/forecast-net-worth/" in routes


# Test: Cash flow endpoint
def test_cash_flow_endpoint(client):
    """Test GET /analytics/cash-flow endpoint."""
    response = client.get("/analytics/cash-flow?user_id=test_user")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "income_total" in data
    assert "expense_total" in data
    assert "net_cash_flow" in data
    assert "income_by_source" in data
    assert "expenses_by_category" in data  # Fixed: expenses_by_category not expense_by_category
    assert "period_start" in data
    assert "period_end" in data

    # Validate calculations
    assert data["net_cash_flow"] == data["income_total"] - data["expense_total"]


def test_cash_flow_with_custom_period(client):
    """Test cash flow with custom period."""
    start_date = (datetime.now() - timedelta(days=60)).isoformat()
    end_date = datetime.now().isoformat()

    response = client.get(
        f"/analytics/cash-flow?user_id=test_user&start_date={start_date}&end_date={end_date}"
    )

    assert response.status_code == 200
    data = response.json()
    assert "income_total" in data


def test_cash_flow_with_period_days(client):
    """Test cash flow with period_days parameter."""
    response = client.get("/analytics/cash-flow?user_id=test_user&period_days=90")

    assert response.status_code == 200
    data = response.json()
    assert "income_total" in data


# Test: Savings rate endpoint
def test_savings_rate_endpoint(client):
    """Test GET /analytics/savings-rate endpoint."""
    response = client.get("/analytics/savings-rate?user_id=test_user")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "savings_rate" in data
    assert "savings_amount" in data
    assert "income" in data
    assert "expenses" in data
    assert "period" in data
    assert "definition" in data
    assert "trend" in data

    # Validate savings rate is percentage
    assert 0 <= data["savings_rate"] <= 1


def test_savings_rate_with_definition(client):
    """Test savings rate with custom definition."""
    response = client.get(
        "/analytics/savings-rate?user_id=test_user&definition=gross&period=monthly"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["definition"] == "gross"
    assert data["period"] == "monthly"


# Test: Spending insights endpoint
def test_spending_insights_endpoint(client):
    """Test GET /analytics/spending-insights endpoint."""
    response = client.get("/analytics/spending-insights?user_id=test_user")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "top_merchants" in data
    assert "category_breakdown" in data
    assert "spending_trends" in data
    assert "anomalies" in data
    assert "period_days" in data
    assert "total_spending" in data

    # Validate lists and dicts
    assert isinstance(data["top_merchants"], list)
    assert isinstance(data["category_breakdown"], dict)  # category_breakdown is a dict not list


def test_spending_insights_with_custom_period(client):
    """Test spending insights with custom period."""
    response = client.get(
        "/analytics/spending-insights?user_id=test_user&period_days=60&include_trends=false"
    )

    assert response.status_code == 200
    data = response.json()
    assert "top_merchants" in data


# Test: Spending advice endpoint
def test_spending_advice_endpoint(client):
    """Test GET /analytics/spending-advice endpoint."""
    response = client.get("/analytics/spending-advice?user_id=test_user")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "key_observations" in data
    assert "savings_opportunities" in data
    assert "estimated_monthly_savings" in data

    # Validate lists
    assert isinstance(data["key_observations"], list)
    assert isinstance(data["savings_opportunities"], list)


# Test: Portfolio metrics endpoint
def test_portfolio_metrics_endpoint(client):
    """Test GET /analytics/portfolio endpoint."""
    response = client.get("/analytics/portfolio?user_id=test_user")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "total_value" in data
    assert "total_return" in data
    assert "total_return_percent" in data
    assert "ytd_return" in data
    assert "allocation_by_asset_class" in data

    # Validate allocation is list
    assert isinstance(data["allocation_by_asset_class"], list)


def test_portfolio_metrics_with_accounts(client):
    """Test portfolio metrics with specific accounts."""
    response = client.get(
        "/analytics/portfolio?user_id=test_user&accounts=account1&accounts=account2"
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_value" in data


# Test: Benchmark comparison endpoint
def test_benchmark_comparison_endpoint(client):
    """Test GET /analytics/performance endpoint."""
    response = client.get("/analytics/performance?user_id=test_user")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "portfolio_return" in data
    assert "benchmark_return" in data
    assert "benchmark_symbol" in data
    assert "alpha" in data
    assert "beta" in data
    assert "period" in data


def test_benchmark_comparison_with_custom_benchmark(client):
    """Test benchmark comparison with custom benchmark."""
    response = client.get("/analytics/performance?user_id=test_user&benchmark=VTI&period=1y")

    assert response.status_code == 200
    data = response.json()
    assert data["benchmark_symbol"] == "VTI"
    assert data["period"] == "1y"


# Test: Net worth forecast endpoint
def test_forecast_net_worth_endpoint(client):
    """Test POST /analytics/forecast-net-worth endpoint."""
    request_data = {
        "user_id": "test_user",
        "years": 10,
    }

    response = client.post("/analytics/forecast-net-worth", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "current_net_worth" in data
    assert "scenarios" in data
    assert "years" in data  # Fixed: years not projection_years    # Validate scenarios
    assert isinstance(data["scenarios"], list)
    assert len(data["scenarios"]) == 3  # Conservative, Moderate, Aggressive

    # Validate scenario structure
    for scenario in data["scenarios"]:
        assert "name" in scenario
        assert "expected_return" in scenario
        assert "final_value" in scenario
        assert "projected_values" in scenario
        assert isinstance(scenario["projected_values"], list)


def test_forecast_net_worth_with_custom_assumptions(client):
    """Test forecast with custom assumptions."""
    request_data = {
        "user_id": "test_user",
        "years": 20,
        "initial_net_worth": 50000.0,
        "annual_contribution": 10000.0,
        "conservative_return": 0.04,
        "moderate_return": 0.06,
        "aggressive_return": 0.09,
    }

    response = client.post("/analytics/forecast-net-worth", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["years"] == 20  # Fixed: years not projection_years


def test_forecast_net_worth_validation(client):
    """Test forecast validation (years must be 1-50)."""
    # Test years too high
    request_data = {
        "user_id": "test_user",
        "years": 100,  # Invalid: max 50
    }

    response = client.post("/analytics/forecast-net-worth", json=request_data)
    assert response.status_code == 422  # Validation error


# Test: Error handling
def test_missing_user_id(client):
    """Test error when user_id is missing."""
    response = client.get("/analytics/cash-flow")

    # Should return 422 (validation error)
    assert response.status_code == 422


def test_invalid_period(client):
    """Test error with invalid period."""
    response = client.get("/analytics/savings-rate?user_id=test_user&period=invalid")

    # Should handle gracefully (either 200 with default or 400/422)
    assert response.status_code in [200, 400, 422]


# Test: Multiple requests
def test_multiple_concurrent_requests(client):
    """Test multiple concurrent requests to different endpoints."""
    # This tests that the analytics engine can handle concurrent calls
    response1 = client.get("/analytics/cash-flow?user_id=user1")
    response2 = client.get("/analytics/savings-rate?user_id=user2")
    response3 = client.get("/analytics/portfolio?user_id=user3")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 200


# Test: OpenAPI schema
def test_openapi_schema(app):
    """Test that analytics endpoints are in OpenAPI schema."""
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )

    # Check paths exist in schema
    assert "/analytics/cash-flow" in openapi_schema["paths"]
    assert "/analytics/savings-rate" in openapi_schema["paths"]
    assert "/analytics/spending-insights" in openapi_schema["paths"]
    assert "/analytics/spending-advice" in openapi_schema["paths"]
    assert "/analytics/portfolio" in openapi_schema["paths"]
    assert "/analytics/performance" in openapi_schema["paths"]
    assert "/analytics/forecast-net-worth" in openapi_schema["paths"]


# Test: Custom prefix
def test_custom_prefix():
    """Test add_analytics with custom prefix."""
    app = FastAPI()
    add_analytics(app, prefix="/custom-analytics")

    routes = [route.path for route in app.routes]
    assert any("/custom-analytics/cash-flow" in route for route in routes)


# Test: Custom provider
def test_custom_provider():
    """Test add_analytics with pre-configured provider."""
    from fin_infra.analytics.ease import easy_analytics

    app = FastAPI()
    custom_engine = easy_analytics(default_period_days=90)
    returned_engine = add_analytics(app, provider=custom_engine)

    # Should return same instance
    assert returned_engine is custom_engine
    assert app.state.analytics_engine is custom_engine
    assert app.state.analytics_engine.default_period_days == 90
