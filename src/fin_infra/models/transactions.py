from __future__ import annotations

from datetime import date
from decimal import Decimal

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
    description: str | None = None
    category: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount_to_decimal(cls, v):
        """Coerce float/int to Decimal for backwards compatibility."""
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
