"""Benchmark LLM models for rebalancing speed."""

import asyncio
import time

from ai_infra import LLM

MODELS = [
    ("openai", "gpt-4o-mini"),
    ("openai", "gpt-5-nano"),
    ("google_genai", "gemini-3-flash-preview"),
    ("anthropic", "claude-3-5-haiku-latest"),
    ("xai", "grok-4-1-fast"),
]

PROMPT = """Analyze this portfolio and suggest rebalancing trades as JSON:
Holdings:
- Cash: $12,345 (48.5%)
- SBSI stock: $7,397 (29%) - cost basis $30, unrealized gain $7,367
- CAMYX fund: $1,855 (7.3%)
- BND bonds: $948 (3.7%)

Target: 70% stocks, 30% bonds
Total value: $25,446

Return JSON with: summary, trades (symbol, action, percent, amount, reason)
Prioritize deploying cash before selling positions with gains."""


async def test_model(provider: str, model: str) -> tuple[str, float, bool]:
    """Test a single model and return (name, time, success)."""
    llm = LLM()
    start = time.monotonic()
    try:
        response = await asyncio.wait_for(
            llm.achat(
                user_msg=PROMPT,
                provider=provider,
                model_name=model,
                temperature=0.3,
                max_tokens=1000,
            ),
            timeout=60.0,
        )
        elapsed = time.monotonic() - start
        content = getattr(response, "content", str(response))
        # Check if it suggests buying before selling
        smart = "buy" in content.lower()[:500] or "cash" in content.lower()[:300]
        return f"{provider}/{model}", elapsed, True, smart
    except Exception as e:
        elapsed = time.monotonic() - start
        print(f"    Error: {type(e).__name__}: {e}")
        return f"{provider}/{model}", elapsed, False, False


async def main():
    print("Benchmarking LLM models for rebalancing...")
    print("=" * 60)

    results = []
    for provider, model in MODELS:
        print(f"\nTesting {provider}/{model}...")
        name, elapsed, success, smart = await test_model(provider, model)
        results.append((name, elapsed, success, smart))
        if success:
            print(f"  ✓ {elapsed:.2f}s (smart={smart})")
        else:
            print(f"  ✗ Failed after {elapsed:.2f}s")

    print("\n" + "=" * 60)
    print("RESULTS (sorted by speed):")
    print("=" * 60)

    # Sort by time, successful first
    results.sort(key=lambda x: (not x[2], x[1]))

    for name, elapsed, success, smart in results:
        status = "✓" if success else "✗"
        smart_indicator = "🧠" if smart else "  "
        print(f"{status} {smart_indicator} {name:40} {elapsed:6.2f}s")

    print("\n🧠 = Prioritized deploying cash (smart rebalancing)")


if __name__ == "__main__":
    asyncio.run(main())
