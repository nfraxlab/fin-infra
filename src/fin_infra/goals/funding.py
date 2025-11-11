"""
Funding allocation for financial goals.

Manages how accounts contribute to goals:
- Link accounts to goals with allocation percentages
- Support multiple accounts funding one goal
- Support one account funding multiple goals
- Validate total allocation per account <= 100%

Example:
    >>> # Link checking account to multiple goals
    >>> link_account_to_goal("goal_1", "account_checking", 50.0)  # 50% to emergency fund
    >>> link_account_to_goal("goal_2", "account_checking", 30.0)  # 30% to vacation
    >>> link_account_to_goal("goal_3", "account_checking", 20.0)  # 20% to new car
    >>>
    >>> # Get all funding sources for a goal
    >>> sources = get_goal_funding_sources("goal_1")
    >>> # [FundingSource(account_id="account_checking", allocation_percent=50.0, ...)]
    >>>
    >>> # Update allocation (increases from 50% to 70%)
    >>> update_account_allocation("goal_1", "account_checking", 70.0)
    >>> # Raises ValueError if total allocation > 100%
"""

from typing import Dict, List

from fin_infra.goals.models import FundingSource
from fin_infra.goals.management import get_goal

# In-memory storage for funding allocations
# Structure: {account_id: {goal_id: allocation_percent}}
_FUNDING_STORE: Dict[str, Dict[str, float]] = {}


def link_account_to_goal(
    goal_id: str,
    account_id: str,
    allocation_percent: float,
) -> FundingSource:
    """
    Link an account to a goal with allocation percentage.

    Validates:
    - Goal exists (raises KeyError if not)
    - Allocation is positive (raises ValueError if <= 0)
    - Total allocation for account <= 100% (raises ValueError if over)
    - Allocation is <= 100% (raises ValueError if > 100)

    Args:
        goal_id: Goal identifier
        account_id: Account identifier
        allocation_percent: Percentage of account to allocate (0-100)

    Returns:
        FundingSource with allocation details

    Raises:
        KeyError: Goal not found
        ValueError: Invalid allocation or exceeds 100% total for account

    Example:
        >>> # Allocate 50% of checking to emergency fund
        >>> source = link_account_to_goal("goal_emergency", "checking_001", 50.0)
        >>> source.allocation_percent
        50.0

        >>> # Add another goal with same account
        >>> link_account_to_goal("goal_vacation", "checking_001", 30.0)
        >>> # Now checking_001 has 80% allocated total

        >>> # This would fail (over 100%):
        >>> link_account_to_goal("goal_car", "checking_001", 30.0)
        ValueError: Total allocation for account checking_001 would exceed 100% (current: 80%, adding: 30%)
    """
    # Validate goal exists
    get_goal(goal_id)  # Raises KeyError if not found

    # Validate allocation
    if allocation_percent <= 0:
        raise ValueError(f"Allocation must be positive, got {allocation_percent}")

    if allocation_percent > 100:
        raise ValueError(f"Allocation cannot exceed 100%, got {allocation_percent}")

    # Check total allocation for account
    if account_id not in _FUNDING_STORE:
        _FUNDING_STORE[account_id] = {}

    current_allocations = _FUNDING_STORE[account_id]
    current_total = sum(pct for gid, pct in current_allocations.items() if gid != goal_id)
    new_total = current_total + allocation_percent

    if new_total > 100:
        raise ValueError(
            f"Total allocation for account {account_id} would exceed 100% "
            f"(current: {current_total}%, adding: {allocation_percent}%)"
        )

    # Store allocation
    _FUNDING_STORE[account_id][goal_id] = allocation_percent

    # Create FundingSource
    return FundingSource(
        goal_id=goal_id,
        account_id=account_id,
        allocation_percent=allocation_percent,
        account_name=None,  # Would come from banking provider in real impl
    )


def get_goal_funding_sources(goal_id: str) -> List[FundingSource]:
    """
    Get all accounts funding a specific goal.

    Args:
        goal_id: Goal identifier

    Returns:
        List of FundingSource objects (empty if no funding sources)

    Raises:
        KeyError: Goal not found

    Example:
        >>> # Setup: Link two accounts to goal
        >>> link_account_to_goal("goal_1", "checking", 50.0)
        >>> link_account_to_goal("goal_1", "savings", 30.0)
        >>>
        >>> # Get all funding sources
        >>> sources = get_goal_funding_sources("goal_1")
        >>> len(sources)
        2
        >>> sources[0].account_id
        'checking'
        >>> sources[0].allocation_percent
        50.0
    """
    # Validate goal exists
    get_goal(goal_id)  # Raises KeyError if not found

    # Find all accounts funding this goal
    funding_sources = []
    for account_id, allocations in _FUNDING_STORE.items():
        if goal_id in allocations:
            funding_sources.append(
                FundingSource(
                    goal_id=goal_id,
                    account_id=account_id,
                    allocation_percent=allocations[goal_id],
                    account_name=None,
                )
            )

    return funding_sources


def get_account_allocations(account_id: str) -> Dict[str, float]:
    """
    Get all goal allocations for a specific account.

    Args:
        account_id: Account identifier

    Returns:
        Dictionary mapping goal_id -> allocation_percent

    Example:
        >>> # Setup: Link account to multiple goals
        >>> link_account_to_goal("goal_1", "checking", 50.0)
        >>> link_account_to_goal("goal_2", "checking", 30.0)
        >>>
        >>> # Get all allocations
        >>> allocations = get_account_allocations("checking")
        >>> allocations
        {'goal_1': 50.0, 'goal_2': 30.0}
        >>> sum(allocations.values())
        80.0
    """
    return _FUNDING_STORE.get(account_id, {}).copy()


def update_account_allocation(
    goal_id: str,
    account_id: str,
    new_allocation_percent: float,
) -> FundingSource:
    """
    Update allocation percentage for existing account-goal link.

    Validates same constraints as link_account_to_goal.

    Args:
        goal_id: Goal identifier
        account_id: Account identifier
        new_allocation_percent: New percentage (0-100)

    Returns:
        Updated FundingSource

    Raises:
        KeyError: Goal or funding source not found
        ValueError: Invalid allocation or exceeds 100%

    Example:
        >>> # Setup
        >>> link_account_to_goal("goal_1", "checking", 50.0)
        >>>
        >>> # Update allocation
        >>> source = update_account_allocation("goal_1", "checking", 70.0)
        >>> source.allocation_percent
        70.0
    """
    # Validate goal exists
    get_goal(goal_id)

    # Validate funding source exists
    if account_id not in _FUNDING_STORE or goal_id not in _FUNDING_STORE[account_id]:
        raise KeyError(f"No funding source found for goal {goal_id} from account {account_id}")

    # Validate new allocation
    if new_allocation_percent <= 0:
        raise ValueError(f"Allocation must be positive, got {new_allocation_percent}")

    if new_allocation_percent > 100:
        raise ValueError(f"Allocation cannot exceed 100%, got {new_allocation_percent}")

    # Check total allocation for account (excluding current allocation)
    current_allocations = _FUNDING_STORE[account_id]
    current_total = sum(pct for gid, pct in current_allocations.items() if gid != goal_id)
    new_total = current_total + new_allocation_percent

    if new_total > 100:
        raise ValueError(
            f"Total allocation for account {account_id} would exceed 100% "
            f"(current: {current_total}%, adding: {new_allocation_percent}%)"
        )

    # Update allocation
    _FUNDING_STORE[account_id][goal_id] = new_allocation_percent

    return FundingSource(
        goal_id=goal_id,
        account_id=account_id,
        allocation_percent=new_allocation_percent,
        account_name=None,
    )


def remove_account_from_goal(goal_id: str, account_id: str) -> None:
    """
    Remove account funding from a goal.

    Args:
        goal_id: Goal identifier
        account_id: Account identifier

    Raises:
        KeyError: Goal or funding source not found

    Example:
        >>> # Setup
        >>> link_account_to_goal("goal_1", "checking", 50.0)
        >>>
        >>> # Remove funding
        >>> remove_account_from_goal("goal_1", "checking")
        >>>
        >>> # No longer funded
        >>> sources = get_goal_funding_sources("goal_1")
        >>> len(sources)
        0
    """
    # Validate goal exists
    get_goal(goal_id)

    # Validate funding source exists
    if account_id not in _FUNDING_STORE or goal_id not in _FUNDING_STORE[account_id]:
        raise KeyError(f"No funding source found for goal {goal_id} from account {account_id}")

    # Remove allocation
    del _FUNDING_STORE[account_id][goal_id]

    # Clean up empty account entries
    if not _FUNDING_STORE[account_id]:
        del _FUNDING_STORE[account_id]


def clear_funding_store() -> None:
    """Clear all funding allocations (for testing)."""
    _FUNDING_STORE.clear()


__all__ = [
    "link_account_to_goal",
    "get_goal_funding_sources",
    "get_account_allocations",
    "update_account_allocation",
    "remove_account_from_goal",
    "clear_funding_store",
]
