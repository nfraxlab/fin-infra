"""Test fin-infra rebalancing directly."""

import asyncio
import time
from decimal import Decimal

from fin_infra.analytics.rebalancing_llm import RebalancingInsightsGenerator
from fin_infra.models.brokerage import Position


async def test():
    print("Creating generator with google_genai/gemini-3-flash-preview...")
    generator = RebalancingInsightsGenerator(
        provider="google_genai", model_name="gemini-3-flash-preview"
    )

    # Create test positions similar to real ones
    positions = [
        Position(
            symbol="AAPL",
            qty=Decimal("10"),
            side="long",
            avg_entry_price=Decimal("150"),
            current_price=Decimal("170"),
            market_value=Decimal("5000"),
            cost_basis=Decimal("4500"),
            unrealized_pl=Decimal("500"),
            unrealized_plpc=Decimal("0.11"),
            asset_class="stocks",
        ),
        Position(
            symbol="MSFT",
            qty=Decimal("5"),
            side="long",
            avg_entry_price=Decimal("300"),
            current_price=Decimal("320"),
            market_value=Decimal("3000"),
            cost_basis=Decimal("2800"),
            unrealized_pl=Decimal("200"),
            unrealized_plpc=Decimal("0.07"),
            asset_class="stocks",
        ),
        Position(
            symbol="CASH",
            qty=Decimal("1"),
            side="long",
            avg_entry_price=Decimal("0"),
            current_price=Decimal("0"),
            market_value=Decimal("12000"),
            cost_basis=Decimal("12000"),
            unrealized_pl=Decimal("0"),
            unrealized_plpc=Decimal("0"),
            asset_class="cash",
        ),
    ]

    start = time.time()
    try:
        result = await asyncio.wait_for(generator.generate(positions), timeout=70.0)
        elapsed = time.time() - start
        print(f"Time: {elapsed:.2f}s")
        print(f"Summary: {result.summary[:100]}")
        print(f"Trades: {len(result.trades)}")
    except Exception as e:
        import traceback

        print(f"Error after {time.time() - start:.2f}s: {e}")
        traceback.print_exc()


asyncio.run(test())
