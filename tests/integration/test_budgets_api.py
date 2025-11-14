"""Integration tests for budgets FastAPI endpoints.

Tests add_budgets() helper and all mounted endpoints with TestClient.
"""

import pytest
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.budgets.add import add_budgets


@pytest.fixture
def app():
    """Create FastAPI app with budgets endpoints."""
    from fin_infra.budgets.ease import easy_budgets

    app = FastAPI(title="Test Budgets API")

    # Create tracker with in-memory SQLite
    # BudgetTracker uses internal dict storage (_budgets) so no actual DB needed
    db_url = "sqlite+aiosqlite:///:memory:"

    # Add budgets with explicit tracker creation
    tracker = easy_budgets(db_url=db_url)

    # Mount endpoints
    add_budgets(app, tracker=tracker)
    
    # Override svc-infra dependencies for testing
    from svc_infra.api.fastapi.db.sql.session import get_session
    from svc_infra.api.fastapi.auth.security import _current_principal, Principal
    
    class MockUser:
        id: str = "test_user"
        email: str = "test@example.com"
    
    class _DummySession:
        async def execute(self, *_, **__):
            class _Res:
                def scalars(self): return self
                def all(self): return []
                def scalar_one_or_none(self): return None
            return _Res()
        async def flush(self): pass
        async def commit(self): pass
        async def rollback(self): pass
        async def get(self, model, pk): return MockUser()
    
    async def _mock_session():
        return _DummySession()
    
    async def mock_principal(request=None, session=None, jwt_or_cookie=None, ak=None):
        return Principal(user=MockUser(), scopes=["read", "write"], via="test")
    
    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[_current_principal] = mock_principal

    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# Test: add_budgets() helper
def test_add_budgets_helper(app):
    """Test add_budgets() mounts endpoints correctly."""
    # Check tracker stored on app state
    assert hasattr(app.state, "budget_tracker")
    assert app.state.budget_tracker is not None

    # Check routes exist
    routes = [route.path for route in app.routes]
    assert "/budgets" in routes or "/budgets/" in routes
    assert "/budgets/{budget_id}" in routes
    assert "/budgets/{budget_id}/progress" in routes
    assert "/budgets/templates/list" in routes
    assert "/budgets/from-template" in routes


# Test: Create budget endpoint
def test_create_budget_endpoint(client):
    """Test POST /budgets endpoint."""
    budget_data = {
        "user_id": "user_123",
        "name": "November Budget",
        "type": "personal",
        "period": "monthly",
        "categories": {
            "Groceries": 600.00,
            "Restaurants": 200.00,
            "Transportation": 150.00,
        },
        "start_date": datetime.now().isoformat(),
        "rollover_enabled": False,
    }

    response = client.post("/budgets", json=budget_data)

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["user_id"] == "user_123"
    assert data["name"] == "November Budget"
    assert data["type"] == "personal"
    assert data["period"] == "monthly"
    assert "id" in data
    # Budget IDs are UUIDs, not prefixed
    assert len(data["id"]) > 0  # Has an ID
    assert "end_date" in data
    assert data["rollover_enabled"] is False


# Test: List budgets endpoint
def test_list_budgets_endpoint(client):
    """Test GET /budgets endpoint."""
    # Create a budget first
    budget_data = {
        "user_id": "user_456",
        "name": "Test Budget",
        "type": "personal",
        "period": "monthly",
        "categories": {"Food": 500.00},
        "start_date": datetime.now().isoformat(),
    }
    client.post("/budgets", json=budget_data)

    # List budgets for this user
    response = client.get("/budgets?user_id=user_456")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["user_id"] == "user_456"


def test_list_budgets_with_type_filter(client):
    """Test GET /budgets with type filter."""
    # Create budgets of different types
    personal_budget = {
        "user_id": "user_789",
        "name": "Personal Budget",
        "type": "personal",
        "period": "monthly",
        "categories": {"Food": 500.00},
        "start_date": datetime.now().isoformat(),
    }
    business_budget = {
        "user_id": "user_789",
        "name": "Business Budget",
        "type": "business",
        "period": "monthly",
        "categories": {"Operating": 5000.00},
        "start_date": datetime.now().isoformat(),
    }

    client.post("/budgets", json=personal_budget)
    client.post("/budgets", json=business_budget)

    # Filter by type
    response = client.get("/budgets?user_id=user_789&type=personal")

    assert response.status_code == 200
    data = response.json()
    assert all(b["type"] == "personal" for b in data)


# Test: Get single budget endpoint
def test_get_budget_endpoint(client):
    """Test GET /budgets/{budget_id} endpoint."""
    # Create a budget first
    budget_data = {
        "user_id": "user_111",
        "name": "Test Get Budget",
        "type": "personal",
        "period": "monthly",
        "categories": {"Groceries": 600.00},
        "start_date": datetime.now().isoformat(),
    }
    create_response = client.post("/budgets", json=budget_data)
    budget_id = create_response.json()["id"]

    # Get the budget
    response = client.get(f"/budgets/{budget_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == budget_id
    assert data["name"] == "Test Get Budget"


def test_get_budget_not_found(client):
    """Test GET /budgets/{budget_id} with non-existent ID."""
    response = client.get("/budgets/bud_nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# Test: Update budget endpoint
def test_update_budget_endpoint(client):
    """Test PATCH /budgets/{budget_id} endpoint."""
    # Create a budget first
    budget_data = {
        "user_id": "user_222",
        "name": "Original Name",
        "type": "personal",
        "period": "monthly",
        "categories": {"Food": 500.00},
        "start_date": datetime.now().isoformat(),
    }
    create_response = client.post("/budgets", json=budget_data)
    budget_id = create_response.json()["id"]

    # Update the budget
    updates = {
        "name": "Updated Name",
        "categories": {"Food": 600.00, "Transport": 200.00},
    }
    response = client.patch(f"/budgets/{budget_id}", json=updates)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["categories"]["Food"] == 600.00
    assert "Transport" in data["categories"]


def test_update_budget_not_found(client):
    """Test PATCH /budgets/{budget_id} with non-existent ID."""
    response = client.patch("/budgets/bud_nonexistent", json={"name": "New Name"})

    assert response.status_code == 404


def test_update_budget_no_updates(client):
    """Test PATCH /budgets/{budget_id} with no updates."""
    response = client.patch("/budgets/bud_123", json={})

    assert response.status_code == 400
    assert "no updates" in response.json()["detail"].lower()


# Test: Delete budget endpoint
def test_delete_budget_endpoint(client):
    """Test DELETE /budgets/{budget_id} endpoint."""
    # Create a budget first
    budget_data = {
        "user_id": "user_333",
        "name": "To Be Deleted",
        "type": "personal",
        "period": "monthly",
        "categories": {"Food": 500.00},
        "start_date": datetime.now().isoformat(),
    }
    create_response = client.post("/budgets", json=budget_data)
    budget_id = create_response.json()["id"]

    # Delete the budget
    response = client.delete(f"/budgets/{budget_id}")

    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/budgets/{budget_id}")
    assert get_response.status_code == 404


def test_delete_budget_not_found(client):
    """Test DELETE /budgets/{budget_id} with non-existent ID."""
    response = client.delete("/budgets/bud_nonexistent")

    assert response.status_code == 404


# Test: Get budget progress endpoint
def test_get_budget_progress_endpoint(client):
    """Test GET /budgets/{budget_id}/progress endpoint."""
    # Create a budget first
    budget_data = {
        "user_id": "user_444",
        "name": "Progress Test",
        "type": "personal",
        "period": "monthly",
        "categories": {
            "Groceries": 600.00,
            "Restaurants": 200.00,
        },
        "start_date": datetime.now().isoformat(),
    }
    create_response = client.post("/budgets", json=budget_data)
    budget_id = create_response.json()["id"]

    # Get progress
    response = client.get(f"/budgets/{budget_id}/progress")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["budget_id"] == budget_id
    assert "current_period" in data
    assert "categories" in data
    assert "total_budgeted" in data
    assert "total_spent" in data
    assert "total_remaining" in data
    assert "percent_used" in data
    assert "period_days_elapsed" in data
    assert "period_days_total" in data

    # Validate categories
    assert len(data["categories"]) == 2
    category_names = [c["category_name"] for c in data["categories"]]
    assert "Groceries" in category_names
    assert "Restaurants" in category_names


def test_get_budget_progress_not_found(client):
    """Test GET /budgets/{budget_id}/progress with non-existent ID."""
    response = client.get("/budgets/bud_nonexistent/progress")

    assert response.status_code == 404


# Test: List templates endpoint
def test_list_templates_endpoint(client):
    """Test GET /budgets/templates/list endpoint."""
    response = client.get("/budgets/templates/list")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert isinstance(data, dict)
    assert len(data) >= 5  # At least 5 templates

    # Check specific templates exist (keys use underscores, not slashes/dashes)
    assert "50_30_20" in data
    assert "zero_based" in data
    assert "envelope" in data
    # Note: Actual template keys may differ from expected names
    # Check for at least some valid templates

    # Validate template structure (use actual key from data)
    template = data["50_30_20"]
    assert "name" in template
    assert "description" in template
    assert "categories" in template
    assert "type" in template
    assert "period" in template


# Test: Create from template endpoint
def test_create_from_template_endpoint(client):
    """Test POST /budgets/from-template endpoint."""
    template_data = {
        "user_id": "user_555",
        "template_name": "50_30_20",  # Use underscore format
        "total_income": 5000.00,
        "budget_name": "My 50/30/20 Budget",
        "start_date": datetime.now().isoformat(),
    }

    response = client.post("/budgets/from-template", json=template_data)

    assert response.status_code == 200
    data = response.json()

    # Validate response
    assert data["user_id"] == "user_555"
    assert data["name"] == "My 50/30/20 Budget"
    assert data["type"] == "personal"
    assert "categories" in data

    # Validate allocations (50/30/20 rule)
    categories = data["categories"]
    total_allocated = sum(categories.values())
    assert abs(total_allocated - 5000.00) < 1.0  # Allow small rounding differences


def test_create_from_template_invalid_name(client):
    """Test POST /budgets/from-template with invalid template name."""
    template_data = {
        "user_id": "user_666",
        "template_name": "nonexistent-template",
        "total_income": 5000.00,
    }

    response = client.post("/budgets/from-template", json=template_data)

    assert response.status_code == 400
    # Error message contains template name and "not found"
    detail = response.json()["detail"].lower()
    assert "not found" in detail
    assert "nonexistent-template" in detail


# Test: Full workflow integration
def test_full_budget_workflow(client):
    """Test complete budget lifecycle: create → list → get → update → progress → delete."""
    user_id = "user_workflow"

    # 1. Create budget
    budget_data = {
        "user_id": user_id,
        "name": "Workflow Test Budget",
        "type": "personal",
        "period": "monthly",
        "categories": {
            "Groceries": 600.00,
            "Restaurants": 200.00,
            "Transportation": 150.00,
        },
        "start_date": datetime.now().isoformat(),
        "rollover_enabled": True,
    }
    create_response = client.post("/budgets", json=budget_data)
    assert create_response.status_code == 200
    budget_id = create_response.json()["id"]

    # 2. List budgets
    list_response = client.get(f"/budgets?user_id={user_id}")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    # 3. Get single budget
    get_response = client.get(f"/budgets/{budget_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Workflow Test Budget"

    # 4. Update budget
    update_response = client.patch(
        f"/budgets/{budget_id}", json={"name": "Updated Workflow Budget"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Workflow Budget"

    # 5. Get progress
    progress_response = client.get(f"/budgets/{budget_id}/progress")
    assert progress_response.status_code == 200
    assert progress_response.json()["budget_id"] == budget_id

    # 6. Delete budget
    delete_response = client.delete(f"/budgets/{budget_id}")
    assert delete_response.status_code == 204

    # 7. Verify deletion
    final_get = client.get(f"/budgets/{budget_id}")
    assert final_get.status_code == 404
