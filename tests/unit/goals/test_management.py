"""
Unit tests for goal management CRUD operations.

Tests cover:
- create_goal: Validation, defaults, ID generation
- list_goals: Filtering by user_id, type, status
- get_goal: Retrieval, not found errors
- update_goal: Partial updates, validation
- delete_goal: Removal, not found errors
- get_goal_progress: Progress calculations, projections, on-track status
"""

from datetime import datetime, timedelta

import pytest

from fin_infra.goals import (
    create_goal,
    delete_goal,
    get_goal,
    get_goal_progress,
    list_goals,
    update_goal,
)
from fin_infra.goals.management import _GOALS_STORE

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clear_goals_store():
    """Clear the in-memory goals store before each test."""
    _GOALS_STORE.clear()
    yield
    _GOALS_STORE.clear()


@pytest.fixture
def sample_deadline():
    """Sample deadline 2 years from now."""
    return datetime.utcnow() + timedelta(days=730)


# ============================================================================
# create_goal Tests
# ============================================================================


def test_create_goal_minimal(sample_deadline):
    """Test creating a goal with minimal required fields."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    assert goal["id"].startswith("goal_user_123_")
    assert goal["user_id"] == "user_123"
    assert goal["name"] == "Emergency Fund"
    assert goal["type"] == "savings"
    assert goal["status"] == "active"
    assert goal["target_amount"] == 10000.0
    assert goal["current_amount"] == 0.0
    assert goal["deadline"] == sample_deadline
    assert goal["milestones"] == []
    assert goal["funding_sources"] == []
    assert goal["auto_contribute"] is False
    assert goal["tags"] == []
    assert goal["completed_at"] is None


def test_create_goal_with_all_fields(sample_deadline):
    """Test creating a goal with all optional fields."""
    goal = create_goal(
        user_id="user_456",
        name="Down Payment",
        goal_type="savings",  # Valid GoalType value
        target_amount=50000.0,
        deadline=sample_deadline,
        description="Save for house down payment",
        current_amount=5000.0,
        auto_contribute=True,
        tags=["essential", "housing"],
    )

    assert goal["description"] == "Save for house down payment"
    assert goal["current_amount"] == 5000.0
    assert goal["auto_contribute"] is True
    assert goal["tags"] == ["essential", "housing"]


def test_create_goal_validates_target_amount():
    """Test that create_goal validates target_amount > 0."""
    with pytest.raises(ValueError, match="greater than 0"):
        create_goal(
            user_id="user_123",
            name="Invalid Goal",
            goal_type="savings",
            target_amount=0.0,  # Invalid
            deadline=datetime.utcnow() + timedelta(days=365),
        )


def test_create_goal_validates_current_amount():
    """Test that create_goal validates current_amount >= 0."""
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        create_goal(
            user_id="user_123",
            name="Invalid Goal",
            goal_type="savings",
            target_amount=10000.0,
            deadline=datetime.utcnow() + timedelta(days=365),
            current_amount=-100.0,  # Invalid
        )


def test_create_goal_validates_current_vs_target():
    """Test that create_goal validates current_amount <= target_amount."""
    with pytest.raises(ValueError, match="cannot exceed target_amount"):
        create_goal(
            user_id="user_123",
            name="Invalid Goal",
            goal_type="savings",
            target_amount=10000.0,
            deadline=datetime.utcnow() + timedelta(days=365),
            current_amount=15000.0,  # Invalid: exceeds target
        )


def test_create_goal_stores_in_memory():
    """Test that create_goal stores goal in _GOALS_STORE."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=datetime.utcnow() + timedelta(days=365),
    )

    assert goal["id"] in _GOALS_STORE
    assert _GOALS_STORE[goal["id"]] == goal


# ============================================================================
# list_goals Tests
# ============================================================================


def test_list_goals_empty():
    """Test list_goals returns empty list when no goals exist."""
    goals = list_goals(user_id="user_123")
    assert goals == []


def test_list_goals_filters_by_user_id(sample_deadline):
    """Test list_goals filters by user_id."""
    goal1 = create_goal(
        user_id="user_123",
        name="Goal 1",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )
    goal2 = create_goal(
        user_id="user_456",
        name="Goal 2",
        goal_type="savings",
        target_amount=20000.0,
        deadline=sample_deadline,
    )
    goal3 = create_goal(
        user_id="user_123",
        name="Goal 3",
        goal_type="debt",
        target_amount=5000.0,
        deadline=sample_deadline,
    )

    goals = list_goals(user_id="user_123")
    assert len(goals) == 2
    assert goal1 in goals
    assert goal3 in goals
    assert goal2 not in goals


def test_list_goals_filters_by_type(sample_deadline):
    """Test list_goals filters by goal_type."""
    goal1 = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )
    goal2 = create_goal(
        user_id="user_123",
        name="Pay Off Credit Card",
        goal_type="debt",
        target_amount=5000.0,
        deadline=sample_deadline,
    )

    goals = list_goals(user_id="user_123", goal_type="savings")
    assert len(goals) == 1
    assert goal1 in goals
    assert goal2 not in goals


def test_list_goals_filters_by_status(sample_deadline):
    """Test list_goals filters by status."""
    goal1 = create_goal(
        user_id="user_123",
        name="Active Goal",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )
    goal2 = create_goal(
        user_id="user_123",
        name="Paused Goal",
        goal_type="savings",
        target_amount=20000.0,
        deadline=sample_deadline,
    )
    # Update goal2 to paused
    update_goal(goal2["id"], updates={"status": "paused"})

    goals = list_goals(user_id="user_123", status="active")
    assert len(goals) == 1
    assert goals[0]["id"] == goal1["id"]

    goals = list_goals(user_id="user_123", status="paused")
    assert len(goals) == 1
    assert goals[0]["id"] == goal2["id"]


def test_list_goals_filters_by_multiple_criteria(sample_deadline):
    """Test list_goals filters by user_id, type, and status."""
    goal1 = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation Fund",
        goal_type="savings",
        target_amount=5000.0,
        deadline=sample_deadline,
    )
    update_goal(goal2["id"], updates={"status": "paused"})

    create_goal(
        user_id="user_123",
        name="Pay Off Loan",
        goal_type="debt",
        target_amount=15000.0,
        deadline=sample_deadline,
    )

    goals = list_goals(user_id="user_123", goal_type="savings", status="active")
    assert len(goals) == 1
    assert goals[0]["id"] == goal1["id"]


# ============================================================================
# get_goal Tests
# ============================================================================


def test_get_goal_success(sample_deadline):
    """Test get_goal retrieves goal by ID."""
    created = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    retrieved = get_goal(created["id"])
    assert retrieved == created


def test_get_goal_not_found():
    """Test get_goal raises KeyError when goal not found."""
    with pytest.raises(KeyError, match="Goal not found: nonexistent_id"):
        get_goal("nonexistent_id")


# ============================================================================
# update_goal Tests
# ============================================================================


def test_update_goal_single_field(sample_deadline):
    """Test update_goal updates a single field."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    updated = update_goal(goal["id"], updates={"name": "Updated Emergency Fund"})
    assert updated["name"] == "Updated Emergency Fund"
    assert updated["target_amount"] == 10000.0  # Unchanged


def test_update_goal_multiple_fields(sample_deadline):
    """Test update_goal updates multiple fields."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    new_deadline = datetime.utcnow() + timedelta(days=1095)
    updated = update_goal(
        goal["id"],
        updates={
            "target_amount": 15000.0,
            "current_amount": 3000.0,
            "deadline": new_deadline,
        },
    )

    assert updated["target_amount"] == 15000.0
    assert updated["current_amount"] == 3000.0
    assert updated["deadline"] == new_deadline


def test_update_goal_validates_updates(sample_deadline):
    """Test update_goal validates updated values."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    # Try to set current_amount > target_amount
    with pytest.raises(ValueError, match="cannot exceed target_amount"):
        update_goal(goal["id"], updates={"current_amount": 15000.0})


def test_update_goal_not_found():
    """Test update_goal raises KeyError when goal not found."""
    with pytest.raises(KeyError, match="Goal not found: nonexistent_id"):
        update_goal("nonexistent_id", updates={"name": "New Name"})


def test_update_goal_updates_timestamp(sample_deadline):
    """Test update_goal updates updated_at timestamp."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    original_updated_at = goal["updated_at"]

    # Wait a moment to ensure timestamp changes
    import time

    time.sleep(0.01)

    updated = update_goal(goal["id"], updates={"name": "New Name"})
    assert updated["updated_at"] > original_updated_at


# ============================================================================
# delete_goal Tests
# ============================================================================


def test_delete_goal_success(sample_deadline):
    """Test delete_goal removes goal from store."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
    )

    assert goal["id"] in _GOALS_STORE
    delete_goal(goal["id"])
    assert goal["id"] not in _GOALS_STORE


def test_delete_goal_not_found():
    """Test delete_goal raises KeyError when goal not found."""
    with pytest.raises(KeyError, match="Goal not found: nonexistent_id"):
        delete_goal("nonexistent_id")


# ============================================================================
# get_goal_progress Tests
# ============================================================================


def test_get_goal_progress_on_track(sample_deadline):
    """Test get_goal_progress calculates progress for on-track goal."""
    goal = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        deadline=sample_deadline,
        current_amount=3000.0,
    )

    progress = get_goal_progress(goal["id"])

    assert progress["goal_id"] == goal["id"]
    assert progress["current_amount"] == 3000.0
    assert progress["target_amount"] == 10000.0
    assert progress["percent_complete"] == 30.0
    assert progress["monthly_contribution_target"] > 0
    assert progress["projected_completion_date"] is not None
    assert isinstance(progress["on_track"], bool)


def test_get_goal_progress_zero_progress():
    """Test get_goal_progress handles zero current_amount."""
    deadline = datetime.utcnow() + timedelta(days=365)
    goal = create_goal(
        user_id="user_123",
        name="New Goal",
        goal_type="savings",
        target_amount=10000.0,
        deadline=deadline,
        current_amount=0.0,
    )

    progress = get_goal_progress(goal["id"])

    assert progress["percent_complete"] == 0.0
    assert progress["monthly_contribution_target"] > 0


def test_get_goal_progress_complete():
    """Test get_goal_progress handles 100% complete goal."""
    deadline = datetime.utcnow() + timedelta(days=365)
    goal = create_goal(
        user_id="user_123",
        name="Completed Goal",
        goal_type="savings",
        target_amount=10000.0,
        deadline=deadline,
        current_amount=10000.0,
    )

    progress = get_goal_progress(goal["id"])

    assert progress["percent_complete"] == 100.0


def test_get_goal_progress_no_deadline():
    """Test get_goal_progress handles goal without deadline."""
    goal = create_goal(
        user_id="user_123",
        name="No Deadline",
        goal_type="savings",
        target_amount=10000.0,
        deadline=None,
        current_amount=3000.0,
    )

    progress = get_goal_progress(goal["id"])

    assert progress["percent_complete"] == 30.0
    assert progress["monthly_contribution_target"] == 0
    assert progress["projected_completion_date"] is None


def test_get_goal_progress_not_found():
    """Test get_goal_progress raises KeyError when goal not found."""
    with pytest.raises(KeyError, match="Goal not found: nonexistent_id"):
        get_goal_progress("nonexistent_id")


def test_get_goal_progress_date_arithmetic():
    """Test get_goal_progress handles month/year wraparound correctly."""
    # Create goal with deadline 15 months from now
    deadline = datetime.utcnow() + timedelta(days=450)
    goal = create_goal(
        user_id="user_123",
        name="Long Term Goal",
        goal_type="savings",
        target_amount=15000.0,
        deadline=deadline,
        current_amount=1000.0,
    )

    # Should not raise ValueError about month out of range
    progress = get_goal_progress(goal["id"])

    assert progress["projected_completion_date"] is not None
    assert isinstance(progress["projected_completion_date"], datetime)


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_goal_lifecycle(sample_deadline):
    """Test complete CRUD lifecycle: create -> read -> update -> delete."""
    # Create
    goal = create_goal(
        user_id="user_789",
        name="Vacation Fund",
        goal_type="savings",  # Valid GoalType value
        target_amount=5000.0,
        deadline=sample_deadline,
    )
    assert goal["id"] in _GOALS_STORE

    # Read (get)
    retrieved = get_goal(goal["id"])
    assert retrieved["name"] == "Vacation Fund"

    # Read (list)
    goals = list_goals(user_id="user_789")
    assert len(goals) == 1
    assert goals[0]["id"] == goal["id"]

    # Update
    updated = update_goal(goal["id"], updates={"current_amount": 1500.0})
    assert updated["current_amount"] == 1500.0

    # Progress
    progress = get_goal_progress(goal["id"])
    assert progress["percent_complete"] == 30.0

    # Delete
    delete_goal(goal["id"])
    assert goal["id"] not in _GOALS_STORE
    with pytest.raises(KeyError):
        get_goal(goal["id"])
