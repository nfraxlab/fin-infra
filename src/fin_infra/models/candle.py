from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_validator


class Candle(BaseModel):
    # Epoch millis timestamp to avoid tz confusion; providers should map to ms since epoch
    ts: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @field_validator("ts")
    @classmethod
    def _non_negative_ts(cls, v: int) -> int:
        if v < 0:
            raise ValueError("ts must be non-negative epoch milliseconds")
        return v
