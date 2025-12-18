from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class Quote(BaseModel):
    symbol: str
    price: Decimal
    as_of: datetime
    currency: str = "USD"

    @field_validator("as_of")
    @classmethod
    def _ensure_tzaware(cls, v: datetime) -> datetime:
        # Normalize to timezone-aware (UTC) for consistency
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)
