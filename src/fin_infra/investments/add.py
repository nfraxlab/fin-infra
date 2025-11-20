"""FastAPI integration for investments module.

This module will be implemented in Task 7.
Placeholder to avoid import errors in __init__.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import FastAPI
    from ..providers.base import InvestmentProvider


def add_investments_impl(
    app: FastAPI,
    *,
    provider: Literal["plaid", "snaptrade"] | None = None,
    prefix: str = "/investments",
    tags: list[str] | None = None,
    **provider_config,
) -> InvestmentProvider:
    """Add investment endpoints to FastAPI app.

    This function will be implemented in Task 7: Create add_investments() FastAPI helper.

    For now, returns a basic provider instance without registering routes.
    """
    from . import easy_investments

    return easy_investments(provider=provider, **provider_config)


__all__ = ["add_investments_impl"]
