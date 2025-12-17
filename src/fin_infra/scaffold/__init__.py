"""Scaffold package for generating persistence layer code from templates.

This package provides functions to generate SQLAlchemy models, Pydantic schemas,
and repository implementations from templates for different financial domains.

Typical usage:
    from fin_infra.scaffold.budgets import scaffold_budgets_core
    from fin_infra.scaffold.goals import scaffold_goals_core

    result = scaffold_budgets_core(
        dest_dir=Path("app/models"),
        include_tenant=True,
        include_soft_delete=True,
    )

    result = scaffold_goals_core(
        dest_dir=Path("app/models/goals"),
        include_tenant=False,
        include_soft_delete=False,
    )
"""

from .budgets import scaffold_budgets_core
from .goals import scaffold_goals_core

__all__ = [
    "scaffold_budgets_core",
    "scaffold_goals_core",
]
