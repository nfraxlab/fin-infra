"""Unit tests for goals funding allocation."""

import pytest

from fin_infra.goals.funding import (
    link_account_to_goal,
    get_goal_funding_sources,
    get_account_allocations,
    update_account_allocation,
    remove_account_from_goal,
    clear_funding_store,
)
from fin_infra.goals.management import create_goal, clear_goals_store


@pytest.fixture(autouse=True)
def clear_stores():
    """Clear all stores before each test."""
    clear_goals_store()
    clear_funding_store()
    yield
    clear_goals_store()
    clear_funding_store()


@pytest.fixture
def sample_goal():
    """Create a sample goal for testing."""
    return create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
        current_amount=0.0,
    )


# ============================================================================
# link_account_to_goal tests
# ============================================================================


def test_link_account_to_goal_success(sample_goal):
    """Test linking account to goal with valid allocation."""
    source = link_account_to_goal(
        goal_id=sample_goal["id"],
        account_id="checking_001",
        allocation_percent=50.0,
    )

    assert source.goal_id == sample_goal["id"]
    assert source.account_id == "checking_001"
    assert source.allocation_percent == 50.0


def test_link_multiple_accounts_to_one_goal(sample_goal):
    """Test linking multiple accounts to same goal."""
    source1 = link_account_to_goal(sample_goal["id"], "checking", 50.0)
    source2 = link_account_to_goal(sample_goal["id"], "savings", 30.0)

    assert source1.allocation_percent == 50.0
    assert source2.allocation_percent == 30.0

    # Both should be returned
    sources = get_goal_funding_sources(sample_goal["id"])
    assert len(sources) == 2


def test_link_one_account_to_multiple_goals(sample_goal):
    """Test linking one account to multiple goals."""
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation Fund",
        goal_type="savings",
        target_amount=5000.0,
    )

    source1 = link_account_to_goal(sample_goal["id"], "checking", 50.0)
    source2 = link_account_to_goal(goal2["id"], "checking", 30.0)

    assert source1.allocation_percent == 50.0
    assert source2.allocation_percent == 30.0

    # Check allocations
    allocations = get_account_allocations("checking")
    assert allocations[sample_goal["id"]] == 50.0
    assert allocations[goal2["id"]] == 30.0
    assert sum(allocations.values()) == 80.0


def test_link_account_to_goal_invalid_goal():
    """Test linking account to non-existent goal."""
    with pytest.raises(KeyError):
        link_account_to_goal("invalid_goal", "checking", 50.0)


def test_link_account_to_goal_zero_allocation(sample_goal):
    """Test linking with zero allocation raises ValueError."""
    with pytest.raises(ValueError, match="must be positive"):
        link_account_to_goal(sample_goal["id"], "checking", 0.0)


def test_link_account_to_goal_negative_allocation(sample_goal):
    """Test linking with negative allocation raises ValueError."""
    with pytest.raises(ValueError, match="must be positive"):
        link_account_to_goal(sample_goal["id"], "checking", -10.0)


def test_link_account_to_goal_over_100_allocation(sample_goal):
    """Test linking with >100% allocation raises ValueError."""
    with pytest.raises(ValueError, match="cannot exceed 100%"):
        link_account_to_goal(sample_goal["id"], "checking", 150.0)


def test_link_account_to_goal_exceeds_total_allocation(sample_goal):
    """Test linking when total allocation would exceed 100%."""
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation",
        goal_type="savings",
        target_amount=5000.0,
    )

    # First allocation: 60%
    link_account_to_goal(sample_goal["id"], "checking", 60.0)

    # Second allocation: 30% (total: 90%)
    link_account_to_goal(goal2["id"], "checking", 30.0)

    # Third allocation: 20% would exceed 100%
    goal3 = create_goal(
        user_id="user_123",
        name="Car",
        goal_type="savings",
        target_amount=20000.0,
    )

    with pytest.raises(ValueError, match="would exceed 100%"):
        link_account_to_goal(goal3["id"], "checking", 20.0)


def test_link_account_to_goal_exactly_100_allocation(sample_goal):
    """Test linking with exactly 100% total allocation."""
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation",
        goal_type="savings",
        target_amount=5000.0,
    )

    link_account_to_goal(sample_goal["id"], "checking", 70.0)
    link_account_to_goal(goal2["id"], "checking", 30.0)  # Exactly 100%

    allocations = get_account_allocations("checking")
    assert sum(allocations.values()) == 100.0


def test_link_account_to_goal_update_existing(sample_goal):
    """Test linking account to goal updates existing allocation."""
    # First allocation
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    # Update allocation (not a new link, but same function)
    source = link_account_to_goal(sample_goal["id"], "checking", 70.0)

    assert source.allocation_percent == 70.0

    # Should still be only one funding source
    sources = get_goal_funding_sources(sample_goal["id"])
    assert len(sources) == 1
    assert sources[0].allocation_percent == 70.0


# ============================================================================
# get_goal_funding_sources tests
# ============================================================================


def test_get_goal_funding_sources_success(sample_goal):
    """Test getting funding sources for a goal."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)
    link_account_to_goal(sample_goal["id"], "savings", 30.0)

    sources = get_goal_funding_sources(sample_goal["id"])

    assert len(sources) == 2
    account_ids = {s.account_id for s in sources}
    assert "checking" in account_ids
    assert "savings" in account_ids


def test_get_goal_funding_sources_empty(sample_goal):
    """Test getting funding sources when none exist."""
    sources = get_goal_funding_sources(sample_goal["id"])
    assert sources == []


def test_get_goal_funding_sources_invalid_goal():
    """Test getting funding sources for non-existent goal."""
    with pytest.raises(KeyError):
        get_goal_funding_sources("invalid_goal")


# ============================================================================
# get_account_allocations tests
# ============================================================================


def test_get_account_allocations_success(sample_goal):
    """Test getting all allocations for an account."""
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation",
        goal_type="savings",
        target_amount=5000.0,
    )

    link_account_to_goal(sample_goal["id"], "checking", 50.0)
    link_account_to_goal(goal2["id"], "checking", 30.0)

    allocations = get_account_allocations("checking")

    assert len(allocations) == 2
    assert allocations[sample_goal["id"]] == 50.0
    assert allocations[goal2["id"]] == 30.0
    assert sum(allocations.values()) == 80.0


def test_get_account_allocations_empty():
    """Test getting allocations for account with no allocations."""
    allocations = get_account_allocations("checking")
    assert allocations == {}


def test_get_account_allocations_returns_copy(sample_goal):
    """Test that get_account_allocations returns a copy."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    allocations = get_account_allocations("checking")
    allocations["fake_goal"] = 100.0  # Modify copy

    # Original should be unchanged
    allocations2 = get_account_allocations("checking")
    assert "fake_goal" not in allocations2
    assert len(allocations2) == 1


# ============================================================================
# update_account_allocation tests
# ============================================================================


def test_update_account_allocation_success(sample_goal):
    """Test updating allocation percentage."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    source = update_account_allocation(sample_goal["id"], "checking", 70.0)

    assert source.allocation_percent == 70.0

    # Verify via get_goal_funding_sources
    sources = get_goal_funding_sources(sample_goal["id"])
    assert sources[0].allocation_percent == 70.0


def test_update_account_allocation_respects_total_limit(sample_goal):
    """Test updating allocation respects 100% total limit."""
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation",
        goal_type="savings",
        target_amount=5000.0,
    )

    link_account_to_goal(sample_goal["id"], "checking", 50.0)
    link_account_to_goal(goal2["id"], "checking", 30.0)

    # Try to update first goal to 80% (would exceed 100%)
    with pytest.raises(ValueError, match="would exceed 100%"):
        update_account_allocation(sample_goal["id"], "checking", 80.0)


def test_update_account_allocation_invalid_goal(sample_goal):
    """Test updating allocation for invalid goal."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    with pytest.raises(KeyError):
        update_account_allocation("invalid_goal", "checking", 70.0)


def test_update_account_allocation_invalid_account(sample_goal):
    """Test updating allocation for invalid account."""
    with pytest.raises(KeyError, match="No funding source found"):
        update_account_allocation(sample_goal["id"], "checking", 70.0)


def test_update_account_allocation_zero(sample_goal):
    """Test updating allocation to zero raises ValueError."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    with pytest.raises(ValueError, match="must be positive"):
        update_account_allocation(sample_goal["id"], "checking", 0.0)


def test_update_account_allocation_over_100(sample_goal):
    """Test updating allocation to >100% raises ValueError."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        update_account_allocation(sample_goal["id"], "checking", 150.0)


# ============================================================================
# remove_account_from_goal tests
# ============================================================================


def test_remove_account_from_goal_success(sample_goal):
    """Test removing account from goal."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    remove_account_from_goal(sample_goal["id"], "checking")

    # Should no longer be in funding sources
    sources = get_goal_funding_sources(sample_goal["id"])
    assert len(sources) == 0


def test_remove_account_from_goal_frees_allocation(sample_goal):
    """Test removing account frees up allocation for other goals."""
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation",
        goal_type="savings",
        target_amount=5000.0,
    )

    link_account_to_goal(sample_goal["id"], "checking", 70.0)
    link_account_to_goal(goal2["id"], "checking", 30.0)  # Total: 100%

    # Remove first goal (frees 70%)
    remove_account_from_goal(sample_goal["id"], "checking")

    # Now can add new goal with 70%
    goal3 = create_goal(
        user_id="user_123",
        name="Car",
        goal_type="savings",
        target_amount=20000.0,
    )

    link_account_to_goal(goal3["id"], "checking", 70.0)  # Should succeed

    allocations = get_account_allocations("checking")
    assert sum(allocations.values()) == 100.0


def test_remove_account_from_goal_invalid_goal(sample_goal):
    """Test removing account from invalid goal."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    with pytest.raises(KeyError):
        remove_account_from_goal("invalid_goal", "checking")


def test_remove_account_from_goal_invalid_account(sample_goal):
    """Test removing invalid account from goal."""
    with pytest.raises(KeyError, match="No funding source found"):
        remove_account_from_goal(sample_goal["id"], "checking")


def test_remove_account_from_goal_cleans_up_empty_account(sample_goal):
    """Test removing last allocation cleans up account entry."""
    link_account_to_goal(sample_goal["id"], "checking", 50.0)

    # Remove allocation
    remove_account_from_goal(sample_goal["id"], "checking")

    # Account should no longer exist in store
    allocations = get_account_allocations("checking")
    assert allocations == {}


# ============================================================================
# Integration tests
# ============================================================================


def test_full_funding_lifecycle():
    """Test complete funding lifecycle: create, update, remove."""
    # Create goals
    goal1 = create_goal(
        user_id="user_123",
        name="Emergency Fund",
        goal_type="savings",
        target_amount=10000.0,
    )
    goal2 = create_goal(
        user_id="user_123",
        name="Vacation",
        goal_type="savings",
        target_amount=5000.0,
    )

    # Link accounts
    link_account_to_goal(goal1["id"], "checking", 50.0)
    link_account_to_goal(goal1["id"], "savings", 30.0)
    link_account_to_goal(goal2["id"], "checking", 20.0)

    # Verify allocations
    assert len(get_goal_funding_sources(goal1["id"])) == 2
    assert len(get_goal_funding_sources(goal2["id"])) == 1

    checking_allocations = get_account_allocations("checking")
    assert sum(checking_allocations.values()) == 70.0

    # Update allocation
    update_account_allocation(goal1["id"], "checking", 40.0)
    checking_allocations = get_account_allocations("checking")
    assert sum(checking_allocations.values()) == 60.0

    # Remove allocation
    remove_account_from_goal(goal1["id"], "savings")
    assert len(get_goal_funding_sources(goal1["id"])) == 1

    # Remove all allocations
    remove_account_from_goal(goal1["id"], "checking")
    remove_account_from_goal(goal2["id"], "checking")

    assert len(get_goal_funding_sources(goal1["id"])) == 0
    assert len(get_goal_funding_sources(goal2["id"])) == 0
    assert get_account_allocations("checking") == {}


def test_complex_multi_account_multi_goal_scenario():
    """Test complex scenario with multiple accounts and goals."""
    # Create 4 goals
    goals = [
        create_goal(
            user_id="user_123",
            name=f"Goal {i}",
            goal_type="savings",
            target_amount=10000.0,
        )
        for i in range(1, 5)
    ]

    # Checking: 100% allocated to 3 goals
    link_account_to_goal(goals[0]["id"], "checking", 50.0)
    link_account_to_goal(goals[1]["id"], "checking", 30.0)
    link_account_to_goal(goals[2]["id"], "checking", 20.0)

    # Savings: 80% allocated to 2 goals
    link_account_to_goal(goals[2]["id"], "savings", 50.0)
    link_account_to_goal(goals[3]["id"], "savings", 30.0)

    # Investment: 100% to 1 goal
    link_account_to_goal(goals[3]["id"], "investment", 100.0)

    # Verify totals
    assert sum(get_account_allocations("checking").values()) == 100.0
    assert sum(get_account_allocations("savings").values()) == 80.0
    assert sum(get_account_allocations("investment").values()) == 100.0

    # Verify goal funding counts
    assert len(get_goal_funding_sources(goals[0]["id"])) == 1  # checking only
    assert len(get_goal_funding_sources(goals[1]["id"])) == 1  # checking only
    assert len(get_goal_funding_sources(goals[2]["id"])) == 2  # checking + savings
    assert len(get_goal_funding_sources(goals[3]["id"])) == 2  # savings + investment
