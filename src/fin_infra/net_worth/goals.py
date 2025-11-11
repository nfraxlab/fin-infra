"""
DEPRECATED: This module has been moved to fin_infra.goals.management

This file provides backward compatibility. Please update imports:
    OLD: from fin_infra.net_worth.goals import FinancialGoalTracker
    NEW: from fin_infra.goals.management import FinancialGoalTracker

This compatibility layer will be removed in v2.0.0.
"""

import warnings

# Import everything from new location
from fin_infra.goals.management import (
    GOAL_PROGRESS_SYSTEM_PROMPT,
    GOAL_VALIDATION_SYSTEM_PROMPT,
    FinancialGoalTracker,
    GoalProgressReport,
    GoalValidation,
    calculate_debt_free_goal,
    calculate_home_purchase_goal,
    calculate_retirement_goal,
    calculate_wealth_milestone,
)

# Issue deprecation warning
warnings.warn(
    "fin_infra.net_worth.goals is deprecated. "
    "Use fin_infra.goals.management instead. "
    "This compatibility layer will be removed in v2.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "GOAL_PROGRESS_SYSTEM_PROMPT",
    "GOAL_VALIDATION_SYSTEM_PROMPT",
    "FinancialGoalTracker",
    "GoalProgressReport",
    "GoalValidation",
    "calculate_debt_free_goal",
    "calculate_home_purchase_goal",
    "calculate_retirement_goal",
    "calculate_wealth_milestone",
]
