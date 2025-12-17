from __future__ import annotations

from datetime import date  # noqa: F401 - used in type annotation
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class Transaction(BaseModel):
    """Financial transaction model.

    Uses Decimal for amount to prevent floating-point precision errors
    in financial calculations (e.g., $0.01 + $0.02 != $0.03 with float).
    """

    id: str
    account_id: str
    date: date
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    category: Optional[str] = None

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount_to_decimal(cls, v):
        """Coerce float/int to Decimal for backwards compatibility."""
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
