from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_validator


class Money(BaseModel):
    amount: Decimal
    currency: str = "USD"

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        # Keep simple ISO-like uppercase normalization; full ISO validation can be added later
        return v.upper()
