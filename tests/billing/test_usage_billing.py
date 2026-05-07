from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fin_infra.billing import AIUsageEvent, BillingPriceBook, UsageLedger


def test_rates_ai_usage_with_margin_and_platform_fee() -> None:
    price_book = BillingPriceBook(
        margin_rate=Decimal("0.30"),
        platform_fee_rate=Decimal("0.10"),
    )
    event = AIUsageEvent(
        idempotency_key="usage-1",
        account_id="user-1",
        provider="anthropic",
        model="claude-sonnet",
        input_tokens=1000,
        output_tokens=500,
        provider_cost=Decimal("0.020000"),
        occurred_at=datetime(2026, 5, 6, tzinfo=UTC),
    )

    line = price_book.rate_ai_usage(event)

    assert line.billable_amount == Decimal("0.028000")


def test_ledger_is_idempotent_and_summarizes_period() -> None:
    ledger = UsageLedger(
        BillingPriceBook(margin_rate=Decimal("0.25"), platform_fee_rate=Decimal("0.05"))
    )
    event = AIUsageEvent(
        idempotency_key="usage-1",
        account_id="user-1",
        provider="anthropic",
        model="claude-sonnet",
        input_tokens=100,
        output_tokens=50,
        provider_cost=Decimal("0.010000"),
        occurred_at=datetime(2026, 5, 6, tzinfo=UTC),
    )

    first = ledger.record_ai_usage(event)
    second = ledger.record_ai_usage(event.model_copy(update={"input_tokens": 999}))
    summary = ledger.summarize(
        "user-1",
        datetime(2026, 5, 1, tzinfo=UTC),
        datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert first is second
    assert summary.event_count == 1
    assert summary.input_tokens == 100
    assert summary.output_tokens == 50
    assert summary.provider_cost == Decimal("0.010000")
    assert summary.billable_amount == Decimal("0.01")
    assert summary.amount_due_cents == 1
