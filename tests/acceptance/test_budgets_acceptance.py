"""Acceptance tests for budgets module.

Tests the full budget lifecycle with real-like scenarios:
- Creating budgets from templates and scratch
- Listing and filtering budgets
- Updating budget allocations
- Tracking budget progress
- Budget validation and error handling

Marked with @pytest.mark.acceptance for selective running.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime

from fin_infra.budgets.ease import easy_budgets
from fin_infra.budgets.add import add_budgets


pytestmark = [pytest.mark.acceptance]


@pytest.fixture
def app():
    """Create FastAPI app with budgets for acceptance testing."""
    app = FastAPI(title="Budgets Acceptance Tests")
    
    # Use in-memory SQLite (BudgetTracker uses dict storage)
    db_url = "sqlite+aiosqlite:///:memory:"
    tracker = easy_budgets(db_url=db_url)
    add_budgets(app, tracker=tracker)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_full_budget_lifecycle(client):
    """Test complete budget lifecycle: create, list, get, update, progress, delete."""
    user_id = "user_acceptance_123"
    
    # 1. CREATE: Create a monthly budget from scratch
    create_response = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "December 2025 Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {
                "Groceries": 600.00,
                "Restaurants": 200.00,
                "Transportation": 150.00,
                "Entertainment": 100.00,
            },
            "rollover_enabled": True,
        },
    )
    assert create_response.status_code == 200
    budget_data = create_response.json()
    budget_id = budget_data["id"]
    
    # Verify budget details
    assert budget_data["name"] == "December 2025 Budget"
    assert budget_data["type"] == "personal"
    assert budget_data["period"] == "monthly"
    assert len(budget_data["categories"]) == 4
    assert budget_data["categories"]["Groceries"] == 600.00
    assert budget_data["rollover_enabled"] is True
    
    # 2. LIST: List user's budgets
    list_response = client.get(f"/budgets?user_id={user_id}")
    assert list_response.status_code == 200
    budgets = list_response.json()
    assert len(budgets) >= 1
    assert any(b["id"] == budget_id for b in budgets)
    
    # 3. GET: Get single budget by ID
    get_response = client.get(f"/budgets/{budget_id}")
    assert get_response.status_code == 200
    budget = get_response.json()
    assert budget["id"] == budget_id
    assert budget["name"] == "December 2025 Budget"
    
    # 4. UPDATE: Update budget allocations
    update_response = client.patch(
        f"/budgets/{budget_id}",
        json={
            "name": "Updated December Budget",
            "categories": {
                "Groceries": 650.00,  # Increased
                "Restaurants": 150.00,  # Decreased
                "Transportation": 150.00,
                "Entertainment": 100.00,
                "Utilities": 200.00,  # New category
            },
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Updated December Budget"
    assert updated["categories"]["Groceries"] == 650.00
    assert updated["categories"]["Restaurants"] == 150.00
    assert updated["categories"]["Utilities"] == 200.00
    
    # 5. PROGRESS: Get budget progress
    progress_response = client.get(f"/budgets/{budget_id}/progress")
    assert progress_response.status_code == 200
    progress = progress_response.json()
    assert progress["budget_id"] == budget_id
    assert "total_budgeted" in progress
    assert "total_spent" in progress
    assert "total_remaining" in progress
    assert "percent_used" in progress
    assert len(progress["categories"]) == 5  # 5 categories after update
    
    # 6. DELETE: Delete budget
    delete_response = client.delete(f"/budgets/{budget_id}")
    assert delete_response.status_code == 204
    
    # Verify budget is deleted
    get_deleted = client.get(f"/budgets/{budget_id}")
    assert get_deleted.status_code == 404


def test_budget_templates(client):
    """Test creating budgets from predefined templates."""
    user_id = "user_templates_123"
    
    # 1. List available templates
    templates_response = client.get("/budgets/templates/list")
    assert templates_response.status_code == 200
    templates = templates_response.json()
    
    # Verify expected templates exist
    assert "50_30_20" in templates
    assert "zero_based" in templates
    assert "envelope" in templates
    
    # 2. Create budget from 50/30/20 template
    create_from_template = client.post(
        "/budgets/from-template",
        json={
            "user_id": user_id,
            "template_name": "50_30_20",
            "total_income": 5000.00,
            "budget_name": "50/30/20 January Budget",
            "period": "monthly",
        },
    )
    assert create_from_template.status_code == 200
    budget = create_from_template.json()
    
    # Verify template applied correctly
    assert budget["name"] == "50/30/20 January Budget"
    assert budget["type"] == "personal"
    assert budget["period"] == "monthly"
    
    # Verify 50/30/20 split (50% needs, 30% wants, 20% savings)
    categories = budget["categories"]
    total = sum(categories.values())
    assert abs(total - 5000.00) < 1.0  # Allow small rounding differences
    
    # 3. Create from zero-based template
    zero_based = client.post(
        "/budgets/from-template",
        json={
            "user_id": user_id,
            "template_name": "zero_based",
            "total_income": 4000.00,
            "budget_name": "Zero-Based Budget",
            "period": "monthly",
        },
    )
    assert zero_based.status_code == 200
    zb_budget = zero_based.json()
    
    # Verify every dollar allocated
    zb_total = sum(zb_budget["categories"].values())
    assert abs(zb_total - 4000.00) < 1.0
    
    # 4. List budgets - should have both template-created budgets
    list_response = client.get(f"/budgets?user_id={user_id}")
    assert list_response.status_code == 200
    budgets = list_response.json()
    assert len(budgets) >= 2


def test_budget_type_filtering(client):
    """Test filtering budgets by type."""
    user_id = "user_filtering_123"
    
    # Create personal budget
    personal = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Personal Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {"Food": 500.00},
        },
    )
    assert personal.status_code == 200
    
    # Create household budget
    household = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Household Budget",
            "type": "household",
            "period": "monthly",
            "categories": {"Utilities": 300.00},
        },
    )
    assert household.status_code == 200
    
    # Create business budget
    business = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Business Budget",
            "type": "business",
            "period": "monthly",
            "categories": {"Office Supplies": 200.00},
        },
    )
    assert business.status_code == 200
    
    # List all budgets
    all_budgets = client.get(f"/budgets?user_id={user_id}")
    assert all_budgets.status_code == 200
    assert len(all_budgets.json()) == 3
    
    # Filter by personal type
    personal_only = client.get(f"/budgets?user_id={user_id}&type=personal")
    assert personal_only.status_code == 200
    personal_budgets = personal_only.json()
    assert len(personal_budgets) == 1
    assert personal_budgets[0]["type"] == "personal"
    
    # Filter by household type
    household_only = client.get(f"/budgets?user_id={user_id}&type=household")
    assert household_only.status_code == 200
    household_budgets = household_only.json()
    assert len(household_budgets) == 1
    assert household_budgets[0]["type"] == "household"
    
    # Filter by business type
    business_only = client.get(f"/budgets?user_id={user_id}&type=business")
    assert business_only.status_code == 200
    business_budgets = business_only.json()
    assert len(business_budgets) == 1
    assert business_budgets[0]["type"] == "business"


def test_budget_validation_errors(client):
    """Test budget validation and error handling."""
    user_id = "user_validation_123"
    
    # 1. Invalid budget type (Pydantic validation returns 422)
    invalid_type = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Invalid Type Budget",
            "type": "invalid_type",
            "period": "monthly",
            "categories": {"Food": 500.00},
        },
    )
    assert invalid_type.status_code == 422  # Pydantic validation error
    
    # 2. Invalid budget period (Pydantic validation returns 422)
    invalid_period = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Invalid Period Budget",
            "type": "personal",
            "period": "invalid_period",
            "categories": {"Food": 500.00},
        },
    )
    assert invalid_period.status_code == 422  # Pydantic validation error
    
    # 3. Empty categories
    empty_categories = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Empty Categories Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {},
        },
    )
    assert empty_categories.status_code == 400
    assert "at least one category" in empty_categories.json()["detail"].lower()
    
    # 4. Negative amount
    negative_amount = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Negative Amount Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {"Food": -100.00},
        },
    )
    assert negative_amount.status_code == 400
    assert "cannot be negative" in negative_amount.json()["detail"].lower()
    
    # 5. Get non-existent budget
    not_found = client.get("/budgets/non-existent-id-12345")
    assert not_found.status_code == 404
    
    # 6. Update non-existent budget
    update_not_found = client.patch(
        "/budgets/non-existent-id-12345",
        json={"name": "Updated"},
    )
    assert update_not_found.status_code == 404
    
    # 7. Delete non-existent budget
    delete_not_found = client.delete("/budgets/non-existent-id-12345")
    assert delete_not_found.status_code == 404
    
    # 8. Progress for non-existent budget
    progress_not_found = client.get("/budgets/non-existent-id-12345/progress")
    assert progress_not_found.status_code == 404
    
    # 9. Invalid template name
    invalid_template = client.post(
        "/budgets/from-template",
        json={
            "user_id": user_id,
            "template_name": "non_existent_template",
            "total_income": 5000.00,
            "budget_name": "Test",
            "period": "monthly",
        },
    )
    assert invalid_template.status_code == 400
    assert "template" in invalid_template.json()["detail"].lower()


def test_budget_progress_calculation(client):
    """Test budget progress calculation with zero spending."""
    user_id = "user_progress_123"
    
    # Create a budget
    create_response = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Progress Test Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {
                "Groceries": 600.00,
                "Entertainment": 200.00,
            },
        },
    )
    assert create_response.status_code == 200
    budget_id = create_response.json()["id"]
    
    # Get progress (should show zero spending initially)
    progress_response = client.get(f"/budgets/{budget_id}/progress")
    assert progress_response.status_code == 200
    progress = progress_response.json()
    
    # Verify progress structure
    assert progress["budget_id"] == budget_id
    assert progress["total_budgeted"] == 800.00
    assert progress["total_spent"] == 0.00
    assert progress["total_remaining"] == 800.00
    assert progress["percent_used"] == 0.0
    
    # Verify category progress
    assert len(progress["categories"]) == 2
    for category in progress["categories"]:
        assert category["spent_amount"] == 0.0
        assert category["percent_used"] == 0.0
        assert category["remaining_amount"] == category["budgeted_amount"]


def test_budget_rollover_feature(client):
    """Test budget rollover configuration."""
    user_id = "user_rollover_123"
    
    # Create budget with rollover enabled
    rollover_enabled = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "Rollover Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {"Savings": 500.00},
            "rollover_enabled": True,
        },
    )
    assert rollover_enabled.status_code == 200
    assert rollover_enabled.json()["rollover_enabled"] is True
    
    # Create budget with rollover disabled
    rollover_disabled = client.post(
        "/budgets",
        json={
            "user_id": user_id,
            "name": "No Rollover Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {"Entertainment": 200.00},
            "rollover_enabled": False,
        },
    )
    assert rollover_disabled.status_code == 200
    assert rollover_disabled.json()["rollover_enabled"] is False
    
    # Update rollover setting
    budget_id = rollover_disabled.json()["id"]
    update_response = client.patch(
        f"/budgets/{budget_id}",
        json={"rollover_enabled": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["rollover_enabled"] is True


def test_multiple_users_isolation(client):
    """Test that budgets are properly isolated between users."""
    user1_id = "user_isolation_1"
    user2_id = "user_isolation_2"
    
    # Create budget for user 1
    user1_budget = client.post(
        "/budgets",
        json={
            "user_id": user1_id,
            "name": "User 1 Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {"Food": 500.00},
        },
    )
    assert user1_budget.status_code == 200
    
    # Create budget for user 2
    user2_budget = client.post(
        "/budgets",
        json={
            "user_id": user2_id,
            "name": "User 2 Budget",
            "type": "personal",
            "period": "monthly",
            "categories": {"Food": 600.00},
        },
    )
    assert user2_budget.status_code == 200
    
    # List user 1 budgets - should only see their own
    user1_list = client.get(f"/budgets?user_id={user1_id}")
    assert user1_list.status_code == 200
    user1_budgets = user1_list.json()
    assert len(user1_budgets) == 1
    assert user1_budgets[0]["user_id"] == user1_id
    
    # List user 2 budgets - should only see their own
    user2_list = client.get(f"/budgets?user_id={user2_id}")
    assert user2_list.status_code == 200
    user2_budgets = user2_list.json()
    assert len(user2_budgets) == 1
    assert user2_budgets[0]["user_id"] == user2_id
