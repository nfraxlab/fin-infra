"""Data models for metered billing."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIUsageEvent(BaseModel):
    """Provider-reported AI usage for one billable model call."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(..., min_length=1, description="Stable key for deduplication")
    account_id: str = Field(..., min_length=1, description="Billable account or user identifier")
    provider: str = Field(..., min_length=1, description="AI provider name")
    model: str = Field(..., min_length=1, description="Provider model identifier")
    input_tokens: int = Field(default=0, ge=0, description="Prompt/input token count")
    output_tokens: int = Field(default=0, ge=0, description="Completion/output token count")
    provider_cost: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Provider cost in the event currency",
    )
    currency: str = Field(default="USD", min_length=3, max_length=3)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("provider_cost", mode="before")
    @classmethod
    def _coerce_decimal(cls, value: object) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class RatedUsageLine(BaseModel):
    """Billable amount derived from a raw usage event."""

    model_config = ConfigDict(extra="forbid")

    event: AIUsageEvent
    margin_rate: Decimal
    platform_fee_rate: Decimal
    billable_amount: Decimal


class BillingPeriodSummary(BaseModel):
    """Aggregated usage and charges for a billing period."""

    model_config = ConfigDict(extra="forbid")

    account_id: str
    period_start: datetime
    period_end: datetime
    currency: str = "USD"
    input_tokens: int = 0
    output_tokens: int = 0
    provider_cost: Decimal = Decimal("0")
    platform_fees: Decimal = Decimal("0")
    margin_amount: Decimal = Decimal("0")
    billable_amount: Decimal = Decimal("0")
    event_count: int = 0

    @property
    def amount_due_cents(self) -> int:
        """Return billable amount rounded to whole currency cents."""
        cents = self.billable_amount * Decimal("100")
        return int(cents.quantize(Decimal("1")))
