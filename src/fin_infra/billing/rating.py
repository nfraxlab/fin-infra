"""Rating and aggregation helpers for usage-based billing."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import AIUsageEvent, BillingPeriodSummary, RatedUsageLine

_USAGE_PLACES = Decimal("0.000001")
_CURRENCY_PLACES = Decimal("0.01")


def round_usage_amount(amount: Decimal) -> Decimal:
    """Round internal usage amounts to six decimal places."""
    return amount.quantize(_USAGE_PLACES, rounding=ROUND_HALF_UP)


def round_currency(amount: Decimal) -> Decimal:
    """Round customer-facing currency amounts to cents."""
    return amount.quantize(_CURRENCY_PLACES, rounding=ROUND_HALF_UP)


class BillingPriceBook(BaseModel):
    """Pricing policy for provider-cost-plus metered billing."""

    model_config = ConfigDict(extra="forbid")

    margin_rate: Decimal = Field(
        default=Decimal("0.35"),
        ge=Decimal("0"),
        description="Markup applied to direct provider cost",
    )
    platform_fee_rate: Decimal = Field(
        default=Decimal("0.05"),
        ge=Decimal("0"),
        description="Additional overhead allocation applied to direct provider cost",
    )

    @field_validator("margin_rate", "platform_fee_rate", mode="before")
    @classmethod
    def _coerce_decimal(cls, value: object) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def rate_ai_usage(self, event: AIUsageEvent) -> RatedUsageLine:
        """Rate one AI usage event using direct provider cost plus configured markup."""
        provider_cost = round_usage_amount(event.provider_cost)
        platform_fee = provider_cost * self.platform_fee_rate
        margin = provider_cost * self.margin_rate
        billable_amount = round_usage_amount(provider_cost + platform_fee + margin)
        return RatedUsageLine(
            event=event.model_copy(update={"provider_cost": provider_cost}),
            margin_rate=self.margin_rate,
            platform_fee_rate=self.platform_fee_rate,
            billable_amount=billable_amount,
        )


class UsageLedger:
    """Small idempotent in-memory ledger useful for tests and service adapters."""

    def __init__(self, price_book: BillingPriceBook | None = None) -> None:
        self._price_book = price_book or BillingPriceBook()
        self._lines: dict[str, RatedUsageLine] = {}

    def record_ai_usage(self, event: AIUsageEvent) -> RatedUsageLine:
        """Record a usage event once and return the rated line."""
        existing = self._lines.get(event.idempotency_key)
        if existing is not None:
            return existing
        line = self._price_book.rate_ai_usage(event)
        self._lines[event.idempotency_key] = line
        return line

    def summarize(
        self,
        account_id: str,
        period_start: datetime,
        period_end: datetime,
        currency: str = "USD",
    ) -> BillingPeriodSummary:
        """Aggregate rated lines for an account and billing period."""
        summary = BillingPeriodSummary(
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            currency=currency.upper(),
        )
        for line in self._lines.values():
            event = line.event
            if event.account_id != account_id:
                continue
            if event.currency != summary.currency:
                continue
            if not (period_start <= event.occurred_at < period_end):
                continue
            provider_cost = line.event.provider_cost
            platform_fee = provider_cost * line.platform_fee_rate
            margin = provider_cost * line.margin_rate
            summary.input_tokens += event.input_tokens
            summary.output_tokens += event.output_tokens
            summary.provider_cost += provider_cost
            summary.platform_fees += platform_fee
            summary.margin_amount += margin
            summary.billable_amount += line.billable_amount
            summary.event_count += 1

        summary.provider_cost = round_usage_amount(summary.provider_cost)
        summary.platform_fees = round_usage_amount(summary.platform_fees)
        summary.margin_amount = round_usage_amount(summary.margin_amount)
        summary.billable_amount = round_currency(summary.billable_amount)
        return summary
