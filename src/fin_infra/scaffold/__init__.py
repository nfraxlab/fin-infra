"""Scaffold package for generating persistence layer code from templates.

This package provides functions to generate SQLAlchemy models, Pydantic schemas,
and repository implementations from templates for different financial domains.

Typical usage:
    from fin_infra.scaffold.budgets import scaffold_budgets_core

    result = scaffold_budgets_core(
        dest_dir=Path("app/models"),
        include_tenant=True,
        include_soft_delete=True,
    )
"""

from .budgets import scaffold_budgets_core

__all__ = [
    "scaffold_budgets_core",
]
