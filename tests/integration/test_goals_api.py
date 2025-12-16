"""Integration tests for goals FastAPI endpoints.

Tests add_goals() helper and all mounted endpoints with TestClient.
Covers:
- CRUD operations (create, list, get, update, delete)
- Progress tracking
- Milestone management (add, list, progress)
- Funding allocation (link, list, update, remove)
- Error handling (404, 400)
- Full lifecycle scenarios
"""

import pytest
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.goals.add import add_goals
from fin_infra.goals.management import clear_goals_store
from fin_infra.goals.funding import clear_funding_store


@pytest.fixture(autouse=True)
def clear_all_stores():
    """Clear all in-memory stores before/after each test."""
    clear_goals_store()
    clear_funding_store()
    yield
    clear_goals_store()
    clear_funding_store()


@pytest.fixture
def app():
    """Create FastAPI app with goals endpoints."""
    app = FastAPI(title="Test Goals API")

    # Mount goals endpoints
    add_goals(app, prefix="/goals")

    # Override svc-infra dependencies for testing
    from svc_infra.api.fastapi.db.sql.session import get_session
    from svc_infra.api.fastapi.auth.security import _current_principal, Principal

    class MockUser:
        id: str = "test_user"
        email: str = "test@example.com"

    class _DummySession:
        async def execute(self, *_, **__):
            class _Res:
                def scalars(self):
                    return self

                def all(self):
                    return []

                def scalar_one_or_none(self):
                    return None

            return _Res()

        async def flush(self):
            pass

        async def commit(self):
            pass

        async def rollback(self):
            pass

        async def get(self, model, pk):
            return MockUser()

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


@pytest.fixture
def sample_deadline():
    """Sample deadline 2 years from now."""
    return (datetime.utcnow() + timedelta(days=730)).isoformat()


# ============================================================================
# Test: add_goals() Helper
# ============================================================================


def test_add_goals_helper(app):
    """Test add_goals() mounts endpoints correctly."""
    # Check routes exist
    routes = [route.path for route in app.routes]

    # CRUD routes
    assert "/goals" in routes or "/goals/" in routes
    assert "/goals/{goal_id}" in routes

    # Progress route
    assert "/goals/{goal_id}/progress" in routes

    # Milestone routes
    assert "/goals/{goal_id}/milestones" in routes
    assert "/goals/{goal_id}/milestones/progress" in routes

    # Funding routes
    assert "/goals/{goal_id}/funding" in routes
    assert "/goals/{goal_id}/funding/{account_id}" in routes


# ============================================================================
# Test: CRUD Operations
# ============================================================================


def test_create_goal_endpoint(client, sample_deadline):
    """Test POST /goals endpoint."""
    goal_data = {
        "user_id": "user_123",
        "name": "Emergency Fund",
        "goal_type": "savings",
        "target_amount": 10000.0,
        "deadline": sample_deadline,
        "description": "Save for emergencies",
        "current_amount": 2000.0,
        "auto_contribute": True,
        "tags": ["emergency", "savings"],
    }

    response = client.post("/goals", json=goal_data)

    assert response.status_code == 201
    data = response.json()

    # Validate response structure
    assert data["user_id"] == "user_123"
    assert data["name"] == "Emergency Fund"
    assert data["type"] == "savings"
    assert data["target_amount"] == 10000.0
    assert data["current_amount"] == 2000.0
    assert data["auto_contribute"] is True
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data
    assert data["tags"] == ["emergency", "savings"]


def test_create_goal_minimal(client, sample_deadline):
    """Test POST /goals with minimal required fields."""
    goal_data = {
        "user_id": "user_456",
        "name": "Vacation Fund",
        "goal_type": "savings",
        "target_amount": 5000.0,
    }

    response = client.post("/goals", json=goal_data)

    assert response.status_code == 201
    data = response.json()

    # Validate defaults
    assert data["current_amount"] == 0.0
    assert data["auto_contribute"] is False
    assert data["status"] == "active"
    assert data["tags"] == []


def test_list_goals_endpoint(client, sample_deadline):
    """Test GET /goals endpoint."""
    # Create multiple goals
    for i in range(3):
        client.post(
            "/goals",
            json={
                "user_id": "user_789",
                "name": f"Goal {i}",
                "goal_type": "savings",
                "target_amount": 1000.0 * (i + 1),
            },
        )

    response = client.get("/goals")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    assert all(g["user_id"] == "user_789" for g in data)


def test_list_goals_filtered_by_user(client, sample_deadline):
    """Test GET /goals with user_id filter."""
    # Create goals for different users
    client.post(
        "/goals",
        json={
            "user_id": "user_A",
            "name": "Goal A",
            "goal_type": "savings",
            "target_amount": 1000.0,
        },
    )
    client.post(
        "/goals",
        json={
            "user_id": "user_B",
            "name": "Goal B",
            "goal_type": "debt",
            "target_amount": 2000.0,
        },
    )

    response = client.get("/goals?user_id=user_A")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["user_id"] == "user_A"
    assert data[0]["name"] == "Goal A"


def test_list_goals_filtered_by_type(client, sample_deadline):
    """Test GET /goals with goal_type filter."""
    # Create goals of different types
    client.post(
        "/goals",
        json={
            "user_id": "user_C",
            "name": "Savings Goal",
            "goal_type": "savings",
            "target_amount": 1000.0,
        },
    )
    client.post(
        "/goals",
        json={
            "user_id": "user_C",
            "name": "Debt Goal",
            "goal_type": "debt",
            "target_amount": 2000.0,
        },
    )

    response = client.get("/goals?goal_type=debt")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["type"] == "debt"
    assert data[0]["name"] == "Debt Goal"


def test_get_goal_endpoint(client, sample_deadline):
    """Test GET /goals/{goal_id} endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Test Goal",
            "goal_type": "savings",
            "target_amount": 5000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Get the goal
    response = client.get(f"/goals/{goal_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == goal_id
    assert data["name"] == "Test Goal"
    assert data["user_id"] == "user_123"


def test_get_goal_not_found(client):
    """Test GET /goals/{goal_id} with non-existent ID."""
    response = client.get("/goals/nonexistent_id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_goal_endpoint(client, sample_deadline):
    """Test PATCH /goals/{goal_id} endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Original Name",
            "goal_type": "savings",
            "target_amount": 5000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Update the goal
    update_data = {
        "name": "Updated Name",
        "target_amount": 7500.0,
        "current_amount": 1000.0,
    }
    response = client.patch(f"/goals/{goal_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Name"
    assert data["target_amount"] == 7500.0
    assert data["current_amount"] == 1000.0
    assert data["user_id"] == "user_123"  # Unchanged


def test_update_goal_not_found(client):
    """Test PATCH /goals/{goal_id} with non-existent ID."""
    response = client.patch(
        "/goals/nonexistent_id",
        json={"name": "New Name"},
    )

    assert response.status_code == 404


def test_delete_goal_endpoint(client, sample_deadline):
    """Test DELETE /goals/{goal_id} endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "To Delete",
            "goal_type": "savings",
            "target_amount": 1000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Delete the goal
    response = client.delete(f"/goals/{goal_id}")

    assert response.status_code == 204

    # Verify deletion
    get_response = client.get(f"/goals/{goal_id}")
    assert get_response.status_code == 404


def test_delete_goal_not_found(client):
    """Test DELETE /goals/{goal_id} with non-existent ID."""
    response = client.delete("/goals/nonexistent_id")

    assert response.status_code == 404


# ============================================================================
# Test: Progress Tracking
# ============================================================================


def test_get_goal_progress_endpoint(client, sample_deadline):
    """Test GET /goals/{goal_id}/progress endpoint."""
    # Create a goal with partial progress
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Progress Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
            "current_amount": 2500.0,
            "deadline": sample_deadline,
        },
    )
    goal_id = create_response.json()["id"]

    # Get progress
    response = client.get(f"/goals/{goal_id}/progress")

    assert response.status_code == 200
    data = response.json()

    assert data["goal_id"] == goal_id
    assert data["percent_complete"] == 25.0
    # remaining_amount is not returned by get_goal_progress, calculate if needed
    assert "on_track" in data
    assert "projected_completion_date" in data


def test_get_goal_progress_not_found(client):
    """Test GET /goals/{goal_id}/progress with non-existent ID."""
    response = client.get("/goals/nonexistent_id/progress")

    assert response.status_code == 404


# ============================================================================
# Test: Milestone Management
# ============================================================================


def test_add_milestone_endpoint(client, sample_deadline):
    """Test POST /goals/{goal_id}/milestones endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Milestone Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Add a milestone
    milestone_data = {
        "amount": 2500.0,
        "description": "First Quarter",
        "target_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
    }
    response = client.post(f"/goals/{goal_id}/milestones", json=milestone_data)

    assert response.status_code == 201
    data = response.json()

    assert data["amount"] == 2500.0
    assert data["description"] == "First Quarter"
    assert data["reached"] is False
    assert data["reached_date"] is None


def test_add_milestone_not_found(client):
    """Test POST /goals/{goal_id}/milestones with non-existent goal."""
    milestone_data = {
        "amount": 1000.0,
        "description": "Test",
    }
    response = client.post("/goals/nonexistent_id/milestones", json=milestone_data)

    assert response.status_code == 404


def test_list_milestones_endpoint(client, sample_deadline):
    """Test GET /goals/{goal_id}/milestones endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Milestone Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Add multiple milestones
    for i in range(3):
        client.post(
            f"/goals/{goal_id}/milestones",
            json={
                "amount": 2000.0 * (i + 1),
                "description": f"Milestone {i + 1}",
            },
        )

    # List milestones
    response = client.get(f"/goals/{goal_id}/milestones")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    assert all(m["reached"] is False for m in data)


def test_list_milestones_not_found(client):
    """Test GET /goals/{goal_id}/milestones with non-existent goal."""
    response = client.get("/goals/nonexistent_id/milestones")

    assert response.status_code == 404


def test_get_milestone_progress_endpoint(client, sample_deadline):
    """Test GET /goals/{goal_id}/milestones/progress endpoint."""
    # Create a goal with current amount
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Progress Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
            "current_amount": 3500.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Add milestones
    client.post(
        f"/goals/{goal_id}/milestones",
        json={"amount": 2500.0, "description": "First"},
    )
    client.post(
        f"/goals/{goal_id}/milestones",
        json={"amount": 5000.0, "description": "Second"},
    )

    # Get milestone progress
    response = client.get(f"/goals/{goal_id}/milestones/progress")

    assert response.status_code == 200
    data = response.json()

    assert data["reached_count"] == 1  # 3500 >= 2500, but < 5000
    assert data["total_milestones"] == 2
    assert 0 <= data["percent_complete"] <= 100


def test_get_milestone_progress_not_found(client):
    """Test GET /goals/{goal_id}/milestones/progress with non-existent goal."""
    response = client.get("/goals/nonexistent_id/milestones/progress")

    assert response.status_code == 404


# ============================================================================
# Test: Funding Allocation
# ============================================================================


def test_link_account_to_goal_endpoint(client, sample_deadline):
    """Test POST /goals/{goal_id}/funding endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Funding Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Link account to goal
    funding_data = {
        "account_id": "acc_checking",
        "allocation_percent": 30.0,
    }
    response = client.post(f"/goals/{goal_id}/funding", json=funding_data)

    assert response.status_code == 201
    data = response.json()

    assert data["goal_id"] == goal_id
    assert data["account_id"] == "acc_checking"
    assert data["allocation_percent"] == 30.0


def test_link_account_exceeds_100_percent(client, sample_deadline):
    """Test POST /goals/{goal_id}/funding with >100% total allocation."""
    # Create two goals
    goal1_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Goal 1",
            "goal_type": "savings",
            "target_amount": 5000.0,
        },
    )
    goal1_id = goal1_response.json()["id"]

    goal2_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Goal 2",
            "goal_type": "savings",
            "target_amount": 5000.0,
        },
    )
    goal2_id = goal2_response.json()["id"]

    # Link account to first goal with 70%
    client.post(
        f"/goals/{goal1_id}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 70.0},
    )

    # Try to link same account to second goal with 40% (total would be 110%)
    response = client.post(
        f"/goals/{goal2_id}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 40.0},
    )

    assert response.status_code == 400
    assert "exceed 100%" in response.json()["detail"].lower()


def test_link_account_not_found(client):
    """Test POST /goals/{goal_id}/funding with non-existent goal."""
    response = client.post(
        "/goals/nonexistent_id/funding",
        json={"account_id": "acc_123", "allocation_percent": 50.0},
    )

    assert response.status_code == 404


def test_get_goal_funding_endpoint(client, sample_deadline):
    """Test GET /goals/{goal_id}/funding endpoint."""
    # Create a goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Funding Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Link multiple accounts
    client.post(
        f"/goals/{goal_id}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 40.0},
    )
    client.post(
        f"/goals/{goal_id}/funding",
        json={"account_id": "acc_savings", "allocation_percent": 30.0},
    )

    # Get funding sources
    response = client.get(f"/goals/{goal_id}/funding")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert any(f["account_id"] == "acc_checking" for f in data)
    assert any(f["account_id"] == "acc_savings" for f in data)


def test_get_goal_funding_not_found(client):
    """Test GET /goals/{goal_id}/funding with non-existent goal."""
    response = client.get("/goals/nonexistent_id/funding")

    assert response.status_code == 404


def test_update_account_allocation_endpoint(client, sample_deadline):
    """Test PATCH /goals/{goal_id}/funding/{account_id} endpoint."""
    # Create a goal and link account
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Funding Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
        },
    )
    goal_id = create_response.json()["id"]

    client.post(
        f"/goals/{goal_id}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 30.0},
    )

    # Update allocation
    response = client.patch(
        f"/goals/{goal_id}/funding/acc_checking",
        json={"new_allocation_percent": 50.0},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["allocation_percent"] == 50.0


def test_update_account_allocation_not_found(client):
    """Test PATCH /goals/{goal_id}/funding/{account_id} with non-existent goal."""
    response = client.patch(
        "/goals/nonexistent_id/funding/acc_123",
        json={"new_allocation_percent": 50.0},
    )

    assert response.status_code == 404


def test_remove_account_from_goal_endpoint(client, sample_deadline):
    """Test DELETE /goals/{goal_id}/funding/{account_id} endpoint."""
    # Create a goal and link account
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_123",
            "name": "Funding Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
        },
    )
    goal_id = create_response.json()["id"]

    client.post(
        f"/goals/{goal_id}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 30.0},
    )

    # Remove account
    response = client.delete(f"/goals/{goal_id}/funding/acc_checking")

    assert response.status_code == 204

    # Verify removal
    get_response = client.get(f"/goals/{goal_id}/funding")
    assert len(get_response.json()) == 0


def test_remove_account_not_found(client):
    """Test DELETE /goals/{goal_id}/funding/{account_id} with non-existent goal."""
    response = client.delete("/goals/nonexistent_id/funding/acc_123")

    assert response.status_code == 404


# ============================================================================
# Test: Full Lifecycle Scenarios
# ============================================================================


def test_full_goal_lifecycle(client, sample_deadline):
    """Test complete goal lifecycle: create → milestone → fund → progress → delete."""
    # 1. Create goal
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_lifecycle",
            "name": "Complete Lifecycle Goal",
            "goal_type": "savings",
            "target_amount": 10000.0,
            "current_amount": 1000.0,
            "deadline": sample_deadline,
        },
    )
    assert create_response.status_code == 201
    goal_id = create_response.json()["id"]

    # 2. Add milestones
    milestone_response = client.post(
        f"/goals/{goal_id}/milestones",
        json={"amount": 5000.0, "description": "Halfway There"},
    )
    assert milestone_response.status_code == 201

    # 3. Link funding accounts
    funding_response = client.post(
        f"/goals/{goal_id}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 50.0},
    )
    assert funding_response.status_code == 201

    # 4. Check progress
    progress_response = client.get(f"/goals/{goal_id}/progress")
    assert progress_response.status_code == 200
    assert progress_response.json()["percent_complete"] == 10.0

    # 5. Update goal (add more funds)
    update_response = client.patch(
        f"/goals/{goal_id}",
        json={"current_amount": 6000.0},
    )
    assert update_response.status_code == 200

    # 6. Check milestone progress (should show completed)
    milestone_progress = client.get(f"/goals/{goal_id}/milestones/progress")
    assert milestone_progress.status_code == 200
    assert milestone_progress.json()["reached_count"] == 1

    # 7. List all goals for user
    list_response = client.get("/goals?user_id=user_lifecycle")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    # 8. Delete goal
    delete_response = client.delete(f"/goals/{goal_id}")
    assert delete_response.status_code == 204

    # 9. Verify deletion
    get_response = client.get(f"/goals/{goal_id}")
    assert get_response.status_code == 404


def test_multi_goal_funding_allocation(client, sample_deadline):
    """Test complex funding allocation across multiple goals."""
    # Create 3 goals
    goal_ids = []
    for i in range(3):
        response = client.post(
            "/goals",
            json={
                "user_id": "user_multi",
                "name": f"Goal {i + 1}",
                "goal_type": "savings",
                "target_amount": 5000.0 * (i + 1),
            },
        )
        goal_ids.append(response.json()["id"])

    # Allocate checking account: 40% to goal1, 30% to goal2, 20% to goal3
    client.post(
        f"/goals/{goal_ids[0]}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 40.0},
    )
    client.post(
        f"/goals/{goal_ids[1]}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 30.0},
    )
    client.post(
        f"/goals/{goal_ids[2]}/funding",
        json={"account_id": "acc_checking", "allocation_percent": 20.0},
    )

    # Verify all allocations
    for goal_id in goal_ids:
        response = client.get(f"/goals/{goal_id}/funding")
        assert response.status_code == 200
        assert len(response.json()) == 1

    # Try to add 20% more to goal3 (would exceed 100%)
    response = client.patch(
        f"/goals/{goal_ids[2]}/funding/acc_checking",
        json={"new_allocation_percent": 40.0},
    )
    assert response.status_code == 400

    # Remove allocation from goal1 (frees 40%)
    client.delete(f"/goals/{goal_ids[0]}/funding/acc_checking")

    # Now we can increase goal3's allocation
    response = client.patch(
        f"/goals/{goal_ids[2]}/funding/acc_checking",
        json={"new_allocation_percent": 40.0},
    )
    assert response.status_code == 200


def test_milestone_auto_completion(client, sample_deadline):
    """Test that milestones auto-complete when current_amount increases."""
    # Create goal with milestones
    create_response = client.post(
        "/goals",
        json={
            "user_id": "user_milestone",
            "name": "Milestone Test",
            "goal_type": "savings",
            "target_amount": 10000.0,
            "current_amount": 500.0,
        },
    )
    goal_id = create_response.json()["id"]

    # Add milestones at 2000, 5000, 8000
    for amount in [2000.0, 5000.0, 8000.0]:
        client.post(
            f"/goals/{goal_id}/milestones",
            json={"amount": amount, "description": f"${amount} milestone"},
        )

    # Initially, no milestones completed
    progress = client.get(f"/goals/{goal_id}/milestones/progress").json()
    assert progress["reached_count"] == 0

    # Update to 3000 (completes first milestone)
    client.patch(f"/goals/{goal_id}", json={"current_amount": 3000.0})
    progress = client.get(f"/goals/{goal_id}/milestones/progress").json()
    assert progress["reached_count"] == 1

    # Update to 6000 (completes second milestone)
    client.patch(f"/goals/{goal_id}", json={"current_amount": 6000.0})
    progress = client.get(f"/goals/{goal_id}/milestones/progress").json()
    assert progress["reached_count"] == 2

    # Update to 10000 (completes all milestones)
    client.patch(f"/goals/{goal_id}", json={"current_amount": 10000.0})
    progress = client.get(f"/goals/{goal_id}/milestones/progress").json()
    assert progress["reached_count"] == 3
    assert progress["percent_complete"] == 100.0
