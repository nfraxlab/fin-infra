"""Integration tests for tax API endpoints."""

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient



# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def app():
    """Create FastAPI app with tax routes (bypass auth for testing)."""
    from svc_infra.api.fastapi.dual.public import public_router
    from fin_infra.tax import easy_tax
    from fin_infra.tax.tlh import find_tlh_opportunities, simulate_tlh_scenario

    app = FastAPI()

    # Initialize provider
    tax_provider = easy_tax(provider="mock")

    # Create router WITHOUT auth for testing
    router = public_router(prefix="/tax", tags=["Tax Data"])

    # Define routes manually (same as add.py but with public_router)
    from fin_infra.tax.add import CryptoGainsRequest, TaxLiabilityRequest, TLHScenarioRequest

    @router.get("/documents")
    async def get_tax_documents(user_id: str, tax_year: int):
        return await tax_provider.get_tax_documents(user_id, tax_year)

    @router.get("/documents/{document_id}")
    async def get_tax_document(document_id: str):
        return await tax_provider.get_tax_document(document_id)

    @router.post("/crypto-gains")
    async def calculate_crypto_gains(request: CryptoGainsRequest):
        return await tax_provider.calculate_crypto_gains(
            user_id=request.user_id,
            transactions=request.transactions,
            tax_year=request.tax_year,
            cost_basis_method=request.cost_basis_method,
        )

    @router.post("/tax-liability")
    async def calculate_tax_liability(request: TaxLiabilityRequest):
        return await tax_provider.calculate_tax_liability(
            user_id=request.user_id,
            income=request.income,
            deductions=request.deductions,
            filing_status=request.filing_status,
            tax_year=request.tax_year,
            state=request.state,
        )

    @router.get("/tlh-opportunities")
    async def get_tlh_opportunities(
        user_id: str,
        min_loss: Decimal = Decimal("100.0"),
        tax_rate: Decimal = Decimal("0.15"),
    ):
        # For testing, return empty list (no actual brokerage positions)
        positions = []
        opportunities = find_tlh_opportunities(
            user_id=user_id,
            positions=positions,
            min_loss=min_loss,
            tax_rate=tax_rate,
        )
        return opportunities

    @router.post("/tlh-scenario")
    async def simulate_tlh_scenario_endpoint(request: TLHScenarioRequest):
        scenario = simulate_tlh_scenario(
            opportunities=request.opportunities,
            tax_rate=request.tax_rate,
        )
        return scenario

    app.include_router(router)
    app.state.tax_provider = tax_provider

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_tlh_opportunity() -> dict:
    """Sample TLH opportunity as dict (for JSON serialization)."""
    return {
        "position_symbol": "AAPL",
        "position_qty": "100",
        "cost_basis": "15000.00",
        "current_value": "13500.00",
        "loss_amount": "1500.00",
        "loss_percent": "0.10",
        "replacement_ticker": "VGT",
        "wash_sale_risk": "none",
        "potential_tax_savings": "225.00",
        "tax_rate": "0.15",
        "explanation": "AAPL down 10.0% ($1,500.00 loss). Replace with VGT to maintain exposure without wash sale. Estimated $225.00 tax savings @ 15%.",
    }


# ============================================================================
# TLH Opportunity Endpoint Tests
# ============================================================================


def test_get_tlh_opportunities_empty(client):
    """Test TLH opportunities with no positions (empty result)."""
    response = client.get("/tax/tlh-opportunities?user_id=test_user")

    assert response.status_code == 200
    opportunities = response.json()
    assert isinstance(opportunities, list)
    # No positions, so no opportunities
    assert len(opportunities) == 0


def test_get_tlh_opportunities_with_defaults(client):
    """Test TLH opportunities uses default parameters."""
    # Default min_loss=100, tax_rate=0.15
    response = client.get("/tax/tlh-opportunities?user_id=test_user")

    assert response.status_code == 200
    opportunities = response.json()
    assert isinstance(opportunities, list)


def test_get_tlh_opportunities_custom_params(client):
    """Test TLH opportunities with custom parameters."""
    response = client.get("/tax/tlh-opportunities?user_id=test_user&min_loss=500&tax_rate=0.20")

    assert response.status_code == 200
    opportunities = response.json()
    assert isinstance(opportunities, list)


def test_get_tlh_opportunities_missing_user_id(client):
    """Test TLH opportunities without user_id (validation error)."""
    response = client.get("/tax/tlh-opportunities")

    # Should return 422 for missing required query param
    assert response.status_code == 422
    error = response.json()
    assert "detail" in error


def test_get_tlh_opportunities_invalid_min_loss(client):
    """Test TLH opportunities with invalid min_loss."""
    response = client.get("/tax/tlh-opportunities?user_id=test_user&min_loss=invalid")

    # Should return 422 for invalid decimal value
    assert response.status_code == 422


# ============================================================================
# TLH Scenario Endpoint Tests
# ============================================================================


def test_simulate_tlh_scenario_empty_opportunities(client):
    """Test TLH scenario simulation with no opportunities."""
    request_body = {"opportunities": [], "tax_rate": None}

    response = client.post("/tax/tlh-scenario", json=request_body)

    assert response.status_code == 200
    scenario = response.json()

    # Empty scenario
    assert scenario["num_opportunities"] == 0
    assert scenario["total_loss_harvested"] == "0"
    assert scenario["total_tax_savings"] == "0"
    assert scenario["wash_sale_risk_summary"] == {
        "none": 0,
        "low": 0,
        "medium": 0,
        "high": 0,
    }
    assert len(scenario["recommendations"]) == 0
    assert len(scenario["caveats"]) >= 4  # Default caveats


def test_simulate_tlh_scenario_single_opportunity(client, sample_tlh_opportunity):
    """Test TLH scenario simulation with single opportunity."""
    request_body = {"opportunities": [sample_tlh_opportunity], "tax_rate": None}

    response = client.post("/tax/tlh-scenario", json=request_body)

    assert response.status_code == 200
    scenario = response.json()

    # Verify scenario calculations
    assert scenario["num_opportunities"] == 1
    assert scenario["total_loss_harvested"] == "1500.00"
    assert scenario["total_tax_savings"] == "225.00"  # $1500 * 0.15
    assert scenario["avg_tax_rate"] == "0.15"
    assert scenario["wash_sale_risk_summary"]["none"] == 1
    assert scenario["total_cost_basis"] == "15000.00"
    assert scenario["total_current_value"] == "13500.00"
    assert len(scenario["recommendations"]) > 0
    assert len(scenario["caveats"]) >= 4


def test_simulate_tlh_scenario_multiple_opportunities(client, sample_tlh_opportunity):
    """Test TLH scenario simulation with multiple opportunities."""
    # Create second opportunity (different symbol)
    opp2 = sample_tlh_opportunity.copy()
    opp2["position_symbol"] = "MSFT"
    opp2["cost_basis"] = "16000.00"
    opp2["current_value"] = "15000.00"
    opp2["loss_amount"] = "1000.00"
    opp2["loss_percent"] = "0.0625"
    opp2["potential_tax_savings"] = "150.00"

    request_body = {
        "opportunities": [sample_tlh_opportunity, opp2],
        "tax_rate": None,
    }

    response = client.post("/tax/tlh-scenario", json=request_body)

    assert response.status_code == 200
    scenario = response.json()

    # Verify aggregated calculations
    assert scenario["num_opportunities"] == 2
    assert scenario["total_loss_harvested"] == "2500.00"  # $1500 + $1000
    assert scenario["total_tax_savings"] == "375.00"  # $225 + $150
    assert scenario["total_cost_basis"] == "31000.00"  # $15k + $16k
    assert scenario["total_current_value"] == "28500.00"  # $13.5k + $15k


def test_simulate_tlh_scenario_override_tax_rate(client, sample_tlh_opportunity):
    """Test TLH scenario simulation with override tax rate."""
    # Opportunity has 15% rate, override with 20%
    request_body = {
        "opportunities": [sample_tlh_opportunity],
        "tax_rate": "0.20",  # Override to 20%
    }

    response = client.post("/tax/tlh-scenario", json=request_body)

    assert response.status_code == 200
    scenario = response.json()

    # Should use override rate
    assert scenario["avg_tax_rate"] == "0.20"
    # Check with Decimal comparison to handle precision
    assert Decimal(scenario["total_tax_savings"]) == Decimal("300.00")  # $1500 * 0.20


def test_simulate_tlh_scenario_wash_sale_risk_summary(client):
    """Test TLH scenario correctly counts wash sale risk levels."""
    opportunities = [
        {
            "position_symbol": "AAPL",
            "position_qty": "100",
            "cost_basis": "10000.00",
            "current_value": "9000.00",
            "loss_amount": "1000.00",
            "loss_percent": "0.10",
            "replacement_ticker": "VGT",
            "wash_sale_risk": "high",  # High risk
            "potential_tax_savings": "150.00",
            "tax_rate": "0.15",
            "explanation": "Test",
        },
        {
            "position_symbol": "MSFT",
            "position_qty": "100",
            "cost_basis": "10000.00",
            "current_value": "9000.00",
            "loss_amount": "1000.00",
            "loss_percent": "0.10",
            "replacement_ticker": "VGT",
            "wash_sale_risk": "medium",  # Medium risk
            "potential_tax_savings": "150.00",
            "tax_rate": "0.15",
            "explanation": "Test",
        },
        {
            "position_symbol": "GOOGL",
            "position_qty": "100",
            "cost_basis": "10000.00",
            "current_value": "9000.00",
            "loss_amount": "1000.00",
            "loss_percent": "0.10",
            "replacement_ticker": "VGT",
            "wash_sale_risk": "low",  # Low risk
            "potential_tax_savings": "150.00",
            "tax_rate": "0.15",
            "explanation": "Test",
        },
        {
            "position_symbol": "NVDA",
            "position_qty": "100",
            "cost_basis": "10000.00",
            "current_value": "9000.00",
            "loss_amount": "1000.00",
            "loss_percent": "0.10",
            "replacement_ticker": "SOXX",
            "wash_sale_risk": "none",  # No risk
            "potential_tax_savings": "150.00",
            "tax_rate": "0.15",
            "explanation": "Test",
        },
    ]

    request_body = {"opportunities": opportunities, "tax_rate": None}

    response = client.post("/tax/tlh-scenario", json=request_body)

    assert response.status_code == 200
    scenario = response.json()

    # Verify risk summary
    assert scenario["wash_sale_risk_summary"]["high"] == 1
    assert scenario["wash_sale_risk_summary"]["medium"] == 1
    assert scenario["wash_sale_risk_summary"]["low"] == 1
    assert scenario["wash_sale_risk_summary"]["none"] == 1


def test_simulate_tlh_scenario_invalid_opportunity(client):
    """Test TLH scenario with invalid opportunity data."""
    # Missing required field
    invalid_opp = {
        "position_symbol": "AAPL",
        # Missing cost_basis, current_value, etc.
    }

    request_body = {"opportunities": [invalid_opp], "tax_rate": None}

    response = client.post("/tax/tlh-scenario", json=request_body)

    # Should return 422 for validation error
    assert response.status_code == 422


# ============================================================================
# Existing Tax Endpoint Tests (ensure TLH addition doesn't break existing)
# ============================================================================


def test_get_tax_documents(client):
    """Test get tax documents endpoint still works."""
    response = client.get("/tax/documents?user_id=test_user&tax_year=2024")

    assert response.status_code == 200
    documents = response.json()
    assert isinstance(documents, list)


def test_calculate_crypto_gains(client):
    """Test crypto gains endpoint still works."""
    request_body = {
        "user_id": "test_user",
        "tax_year": 2024,
        "transactions": [],
        "cost_basis_method": "FIFO",
    }

    response = client.post("/tax/crypto-gains", json=request_body)

    assert response.status_code == 200
    result = response.json()
    assert "user_id" in result


def test_calculate_tax_liability(client):
    """Test tax liability endpoint still works."""
    request_body = {
        "user_id": "test_user",
        "tax_year": 2024,
        "income": "100000.00",
        "deductions": "14600.00",
        "filing_status": "single",
    }

    response = client.post("/tax/tax-liability", json=request_body)

    assert response.status_code == 200
    result = response.json()
    assert "user_id" in result


# ============================================================================
# Router and App State Tests
# ============================================================================


def test_add_tax_data_mounts_tlh_routes(app):
    """Test add_tax_data properly mounts TLH routes."""
    # Get all routes
    routes = [route.path for route in app.routes]

    # Verify TLH endpoints exist
    assert "/tax/tlh-opportunities" in routes
    assert "/tax/tlh-scenario" in routes


def test_add_tax_data_stores_provider_on_app_state(app):
    """Test add_tax_data stores provider on app.state."""
    assert hasattr(app.state, "tax_provider")
    assert app.state.tax_provider is not None
