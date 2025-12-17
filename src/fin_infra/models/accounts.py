from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    credit = "credit"
    investment = "investment"
    loan = "loan"
    other = "other"


class Account(BaseModel):
    """Financial account model.

    Uses Decimal for balance fields to prevent floating-point precision errors
    in financial calculations (e.g., $0.01 + $0.02 != $0.03 with float).
    """

    id: str
    name: str
    type: AccountType
    mask: Optional[str] = None
    currency: str = "USD"
    institution: Optional[str] = None
    balance_available: Optional[Decimal] = None
    balance_current: Optional[Decimal] = None

    @field_validator("balance_available", "balance_current", mode="before")
    @classmethod
    def _coerce_balance_to_decimal(cls, v):
        """Coerce float/int to Decimal for backwards compatibility."""
        if v is None:
            return v
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
