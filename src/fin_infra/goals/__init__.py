"""
Goals module for financial goal tracking and management.

Provides comprehensive goal management with milestone tracking,
funding allocation, and progress monitoring.
"""

from fin_infra.goals.management import (
    FinancialGoalTracker,
    GoalProgressReport,
    GoalValidation,
    calculate_debt_free_goal,
    calculate_home_purchase_goal,
    calculate_retirement_goal,
    calculate_wealth_milestone,
    create_goal,
    delete_goal,
    get_goal,
    get_goal_progress,
    list_goals,
    update_goal,
)
from fin_infra.goals.milestones import (
    add_milestone,
    check_milestones,
    get_celebration_message,
    get_milestone_progress,
    get_next_milestone,
    trigger_milestone_notification,
)
from fin_infra.goals.funding import (
    link_account_to_goal,
    get_goal_funding_sources,
    get_account_allocations,
    update_account_allocation,
    remove_account_from_goal,
)
from fin_infra.goals.add import add_goals
from fin_infra.goals.models import (
    FundingSource,
    Goal,
    GoalProgress,
    GoalStatus,
    GoalType,
    Milestone,
)

__all__ = [
    # Tracker and validation (from management.py)
    "FinancialGoalTracker",
    "GoalProgressReport",
    "GoalValidation",
    "calculate_debt_free_goal",
    "calculate_home_purchase_goal",
    "calculate_retirement_goal",
    "calculate_wealth_milestone",
    # CRUD operations (from management.py)
    "create_goal",
    "delete_goal",
    "get_goal",
    "get_goal_progress",
    "list_goals",
    "update_goal",
    # Milestone tracking (from milestones.py)
    "add_milestone",
    "check_milestones",
    "get_celebration_message",
    "get_milestone_progress",
    "get_next_milestone",
    "trigger_milestone_notification",
    # Funding allocation (from funding.py)
    "link_account_to_goal",
    "get_goal_funding_sources",
    "get_account_allocations",
    "update_account_allocation",
    "remove_account_from_goal",
    # FastAPI integration (from add.py)
    "add_goals",
    # Enhanced models (from models.py)
    "FundingSource",
    "Goal",
    "GoalProgress",
    "GoalStatus",
    "GoalType",
    "Milestone",
]
