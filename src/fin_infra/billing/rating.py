"""Rating and aggregation helpers for usage-based billing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import AIUsageEvent, BillingPeriodSummary, RatedUsageLine

_USAGE_PLACES = Decimal("0.000001")
_CURRENCY_PLACES = Decimal("0.01")
_TOKENS_PER_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class _TokenRate:
    input_per_million_tokens: Decimal
    output_per_million_tokens: Decimal


_VERIFIED_MODEL_TOKEN_RATES: dict[tuple[str, str], _TokenRate] = {
    ("anthropic", "claude-haiku-4-5"): _TokenRate(Decimal("1.00"), Decimal("5.00")),
    ("anthropic", "claude-sonnet-4"): _TokenRate(Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-sonnet-4-5"): _TokenRate(Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-sonnet-4-6"): _TokenRate(Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-opus-4"): _TokenRate(Decimal("15.00"), Decimal("75.00")),
    ("anthropic", "claude-opus-4-1"): _TokenRate(Decimal("15.00"), Decimal("75.00")),
    ("anthropic", "claude-opus-4-5"): _TokenRate(Decimal("5.00"), Decimal("25.00")),
    ("anthropic", "claude-opus-4-6"): _TokenRate(Decimal("5.00"), Decimal("25.00")),
    ("google", "gemini-2.5-flash-lite"): _TokenRate(Decimal("0.10"), Decimal("0.40")),
    ("google", "gemini-2.5-flash"): _TokenRate(Decimal("0.30"), Decimal("2.50")),
    ("google", "gemini-2.5-pro"): _TokenRate(Decimal("1.25"), Decimal("10.00")),
    ("google", "gemini-3-flash-preview"): _TokenRate(Decimal("0.50"), Decimal("3.00")),
    ("google", "gemini-3.1-flash-lite-preview"): _TokenRate(Decimal("0.25"), Decimal("1.50")),
    ("google", "gemini-3.1-pro-preview"): _TokenRate(Decimal("2.00"), Decimal("12.00")),
    ("openai", "gpt-5.4"): _TokenRate(Decimal("2.50"), Decimal("15.00")),
    ("openai", "gpt-5.4-mini"): _TokenRate(Decimal("0.75"), Decimal("4.50")),
    ("openai", "gpt-5.4-nano"): _TokenRate(Decimal("0.20"), Decimal("1.25")),
}


def _lookup_verified_token_rate(provider: str, model: str) -> _TokenRate | None:
    return _VERIFIED_MODEL_TOKEN_RATES.get((provider.strip().lower(), model.strip().lower()))


def _estimate_provider_cost_from_tokens(event: AIUsageEvent) -> Decimal:
    if event.currency != "USD":
        return Decimal("0")
    rate = _lookup_verified_token_rate(event.provider, event.model)
    if rate is None:
        return Decimal("0")
    input_cost = Decimal(event.input_tokens) * rate.input_per_million_tokens / _TOKENS_PER_MILLION
    output_cost = (
        Decimal(event.output_tokens) * rate.output_per_million_tokens / _TOKENS_PER_MILLION
    )
    return round_usage_amount(input_cost + output_cost)


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

    def resolve_provider_cost(self, event: AIUsageEvent) -> Decimal:
        """Return direct provider cost or a verified model-price estimate when absent."""
        direct_provider_cost = round_usage_amount(event.provider_cost)
        if direct_provider_cost > Decimal("0"):
            return direct_provider_cost
        return _estimate_provider_cost_from_tokens(event)

    def rate_ai_usage(self, event: AIUsageEvent) -> RatedUsageLine:
        """Rate one AI usage event using direct provider cost plus configured markup."""
        provider_cost = self.resolve_provider_cost(event)
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
