"""
Acceptance tests for LLM-based categorization (Layer 4).

These tests make REAL API calls to LLM providers. They are skipped by default
and only run when:
1. Marked with @pytest.mark.acceptance
2. LLM API keys are set in environment variables

Required environment variables:
- GOOGLE_API_KEY: For Google Gemini tests
- OPENAI_API_KEY: For OpenAI GPT-4o-mini tests
- ANTHROPIC_API_KEY: For Anthropic Claude tests

Run with: pytest -m acceptance tests/acceptance/test_categorization_llm_acceptance.py
"""

import os
import pytest
from fin_infra.categorization import Category, easy_categorization

# Check for API keys
HAS_GOOGLE_KEY = bool(os.getenv("GOOGLE_API_KEY"))
HAS_OPENAI_KEY = bool(os.getenv("OPENAI_API_KEY"))
HAS_ANTHROPIC_KEY = bool(os.getenv("ANTHROPIC_API_KEY"))

# Test merchants with expected categories
TEST_MERCHANTS = [
    # Coffee shops
    ("Starbucks", Category.VAR_COFFEE_SHOPS),
    ("Dunkin Donuts", Category.VAR_COFFEE_SHOPS),
    ("Peet's Coffee", Category.VAR_COFFEE_SHOPS),
    # Groceries
    ("Whole Foods", Category.VAR_GROCERIES),
    ("Trader Joe's", Category.VAR_GROCERIES),
    ("Safeway", Category.VAR_GROCERIES),
    # Restaurants
    ("Chipotle", Category.VAR_RESTAURANTS),
    ("Olive Garden", Category.VAR_RESTAURANTS),
    # Fast food
    ("McDonald's", Category.VAR_FAST_FOOD),
    ("Taco Bell", Category.VAR_FAST_FOOD),
    # Gas stations
    ("Shell", Category.VAR_GAS_FUEL),
    ("Chevron", Category.VAR_GAS_FUEL),
    # Online shopping
    ("Amazon", Category.VAR_SHOPPING_ONLINE),
    ("eBay", Category.VAR_SHOPPING_ONLINE),
    # Rideshare
    ("Uber", Category.VAR_RIDESHARE),
    ("Lyft", Category.VAR_RIDESHARE),
    # Travel/Flights
    ("United Airlines", Category.VAR_TRAVEL_FLIGHTS),
    ("Delta Air Lines", Category.VAR_TRAVEL_FLIGHTS),
    # Subscriptions
    ("Netflix", Category.FIXED_SUBSCRIPTIONS),
    ("Spotify", Category.FIXED_SUBSCRIPTIONS),
]


@pytest.mark.acceptance
@pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="GOOGLE_API_KEY not set")
class TestGoogleGeminiLLM:
    """Test LLM categorization with Google Gemini 2.0 Flash."""

    @pytest.mark.asyncio
    async def test_google_gemini_basic(self):
        """Test basic categorization with Google Gemini."""
        categorizer = easy_categorization(
            model="llm",  # LLM only, skip rules/regex/sklearn
            llm_provider="google",
            llm_model="gemini-2.0-flash-exp",
        )

        result = await categorizer.categorize("Starbucks Coffee Shop")

        # Verify response structure
        assert result.category is not None
        assert result.confidence > 0
        assert result.method.value == "llm"

        # Verify correct category
        assert result.category == Category.VAR_COFFEE_SHOPS

        print(
            f"✅ Google Gemini: {result.merchant_name} → {result.category} (confidence: {result.confidence:.2f})"
        )

    @pytest.mark.asyncio
    async def test_google_gemini_accuracy(self):
        """Test accuracy across 20 test merchants with Google Gemini."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="google",
            llm_model="gemini-2.0-flash-exp",
        )

        correct = 0
        total = len(TEST_MERCHANTS)

        for merchant, expected_category in TEST_MERCHANTS:
            result = await categorizer.categorize(merchant)
            if result.category == expected_category:
                correct += 1
                print(f"✅ {merchant} → {result.category} (expected: {expected_category})")
            else:
                print(f"❌ {merchant} → {result.category} (expected: {expected_category})")

        accuracy = correct / total
        print(f"\n📊 Google Gemini Accuracy: {accuracy:.1%} ({correct}/{total})")

        # Target: >90% accuracy
        assert accuracy >= 0.90, f"Accuracy {accuracy:.1%} below 90% threshold"

    @pytest.mark.asyncio
    async def test_google_gemini_cost_tracking(self):
        """Test that costs are tracked correctly."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="google",
            llm_model="gemini-2.0-flash-exp",
            llm_max_cost_per_day=1.00,  # High limit for testing
        )

        # Initial costs should be zero
        assert categorizer.llm_categorizer.daily_cost == 0
        assert categorizer.llm_categorizer.monthly_cost == 0

        # Categorize a merchant
        await categorizer.categorize("Target")

        # Costs should be tracked
        assert categorizer.llm_categorizer.daily_cost > 0
        assert categorizer.llm_categorizer.monthly_cost > 0

        # Cost should be reasonable (< $0.001 per transaction)
        cost_per_txn = categorizer.llm_categorizer.daily_cost
        assert cost_per_txn < 0.001, f"Cost per transaction too high: ${cost_per_txn}"

        print(f"💰 Google Gemini cost: ${cost_per_txn:.6f} per transaction")


@pytest.mark.acceptance
@pytest.mark.skipif(not HAS_OPENAI_KEY, reason="OPENAI_API_KEY not set")
class TestOpenAIGPT4oMini:
    """Test LLM categorization with OpenAI GPT-4o-mini."""

    @pytest.mark.asyncio
    async def test_openai_gpt4o_mini_basic(self):
        """Test basic categorization with OpenAI GPT-4o-mini."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )

        result = await categorizer.categorize("Whole Foods Market")

        # Verify response structure
        assert result.category is not None
        assert result.confidence > 0
        assert result.method.value == "llm"

        # Verify correct category
        assert result.category == Category.VAR_GROCERIES

        print(
            f"✅ OpenAI GPT-4o-mini: {result.merchant_name} → {result.category} (confidence: {result.confidence:.2f})"
        )

    @pytest.mark.asyncio
    async def test_openai_gpt4o_mini_accuracy(self):
        """Test accuracy across 20 test merchants with OpenAI."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )

        correct = 0
        total = len(TEST_MERCHANTS)

        for merchant, expected_category in TEST_MERCHANTS:
            result = await categorizer.categorize(merchant)
            if result.category == expected_category:
                correct += 1
                print(f"✅ {merchant} → {result.category}")
            else:
                print(f"❌ {merchant} → {result.category} (expected: {expected_category})")

        accuracy = correct / total
        print(f"\n📊 OpenAI GPT-4o-mini Accuracy: {accuracy:.1%} ({correct}/{total})")

        # Target: >90% accuracy
        assert accuracy >= 0.90, f"Accuracy {accuracy:.1%} below 90% threshold"

    @pytest.mark.asyncio
    async def test_openai_cost_tracking(self):
        """Test cost tracking for OpenAI."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            llm_max_cost_per_day=1.00,
        )

        await categorizer.categorize("Walmart")

        cost_per_txn = categorizer.llm_categorizer.daily_cost
        assert cost_per_txn > 0
        assert cost_per_txn < 0.001, f"Cost per transaction too high: ${cost_per_txn}"

        print(f"💰 OpenAI GPT-4o-mini cost: ${cost_per_txn:.6f} per transaction")


@pytest.mark.acceptance
@pytest.mark.skipif(not HAS_ANTHROPIC_KEY, reason="ANTHROPIC_API_KEY not set")
class TestAnthropicClaude:
    """Test LLM categorization with Anthropic Claude 3.5 Haiku."""

    @pytest.mark.asyncio
    async def test_anthropic_claude_basic(self):
        """Test basic categorization with Anthropic Claude."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="anthropic",
            llm_model="claude-3-5-haiku-20241022",
        )

        result = await categorizer.categorize("Netflix Subscription")

        # Verify response structure
        assert result.category is not None
        assert result.confidence > 0
        assert result.method.value == "llm"

        # Verify correct category
        assert result.category == Category.FIXED_SUBSCRIPTIONS

        print(
            f"✅ Anthropic Claude: {result.merchant_name} → {result.category} (confidence: {result.confidence:.2f})"
        )

    @pytest.mark.asyncio
    async def test_anthropic_accuracy(self):
        """Test accuracy across 20 test merchants with Claude."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="anthropic",
            llm_model="claude-3-5-haiku-20241022",
        )

        correct = 0
        total = len(TEST_MERCHANTS)

        for merchant, expected_category in TEST_MERCHANTS:
            result = await categorizer.categorize(merchant)
            if result.category == expected_category:
                correct += 1
                print(f"✅ {merchant} → {result.category}")
            else:
                print(f"❌ {merchant} → {result.category} (expected: {expected_category})")

        accuracy = correct / total
        print(f"\n📊 Anthropic Claude Accuracy: {accuracy:.1%} ({correct}/{total})")

        # Target: >90% accuracy
        assert accuracy >= 0.90, f"Accuracy {accuracy:.1%} below 90% threshold"

    @pytest.mark.asyncio
    async def test_anthropic_cost_tracking(self):
        """Test cost tracking for Anthropic."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="anthropic",
            llm_model="claude-3-5-haiku-20241022",
            llm_max_cost_per_day=1.00,
        )

        await categorizer.categorize("Costco")

        cost_per_txn = categorizer.llm_categorizer.daily_cost
        assert cost_per_txn > 0
        assert cost_per_txn < 0.001, f"Cost per transaction too high: ${cost_per_txn}"

        print(f"💰 Anthropic Claude cost: ${cost_per_txn:.6f} per transaction")


@pytest.mark.acceptance
@pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="GOOGLE_API_KEY not set")
class TestHybridWithLLM:
    """Test hybrid categorization (rules + regex + sklearn + LLM)."""

    @pytest.mark.asyncio
    async def test_hybrid_flow(self):
        """Test full hybrid flow: exact → regex → sklearn → LLM."""
        categorizer = easy_categorization(
            model="hybrid",
            enable_ml=True,
            llm_provider="google",
            llm_confidence_threshold=0.6,
        )

        # Test exact match (should skip LLM)
        result1 = await categorizer.categorize("Starbucks")
        assert result1.method.value == "exact"
        assert result1.category == Category.VAR_COFFEE_SHOPS

        # Test regex match (should skip LLM)
        result2 = await categorizer.categorize("UBER TRIP #12345")
        assert result2.method.value == "regex"

        # Test unknown merchant (should use LLM if sklearn confidence < 0.6)
        result3 = await categorizer.categorize("Unknown Coffee Roasters")
        # Method could be "ml" or "llm" depending on sklearn confidence
        assert result3.method.value in ["ml", "llm"]

        print("✅ Hybrid flow test passed:")
        print(f"  - Exact: {result1.merchant_name} → {result1.category} ({result1.method.value})")
        print(f"  - Regex: {result2.merchant_name} → {result2.category} ({result2.method.value})")
        print(f"  - Unknown: {result3.merchant_name} → {result3.category} ({result3.method.value})")

    @pytest.mark.asyncio
    async def test_hybrid_stats(self):
        """Test that stats track all layer usage."""
        categorizer = easy_categorization(
            model="hybrid",
            enable_ml=True,
            llm_provider="google",
        )

        # Categorize various merchants
        await categorizer.categorize("Starbucks")  # Exact
        await categorizer.categorize("UBER")  # Exact
        await categorizer.categorize("Unknown Place 123")  # ML or LLM

        stats = categorizer.get_stats()

        # Should have exact matches
        assert stats["exact_matches"] >= 2

        # Total should match number of calls
        total = sum(stats.values())
        assert total == 3

        print(f"📊 Hybrid stats: {stats}")

    @pytest.mark.asyncio
    async def test_hybrid_accuracy(self):
        """Test hybrid accuracy is better than sklearn-only."""
        # Hybrid with LLM
        hybrid = easy_categorization(
            model="hybrid",
            enable_ml=True,
            llm_provider="google",
        )

        # Local only (no LLM)
        local_only = easy_categorization(
            model="local",
            enable_ml=True,
        )

        hybrid_correct = 0
        local_correct = 0
        total = len(TEST_MERCHANTS)

        for merchant, expected_category in TEST_MERCHANTS:
            hybrid_result = await hybrid.categorize(merchant)
            local_result = await local_only.categorize(merchant)

            if hybrid_result.category == expected_category:
                hybrid_correct += 1

            if local_result.category == expected_category:
                local_correct += 1

        hybrid_accuracy = hybrid_correct / total
        local_accuracy = local_correct / total
        improvement = hybrid_accuracy - local_accuracy

        print("\n📊 Accuracy Comparison:")
        print(f"  - Hybrid (with LLM): {hybrid_accuracy:.1%} ({hybrid_correct}/{total})")
        print(f"  - Local only: {local_accuracy:.1%} ({local_correct}/{total})")
        print(f"  - Improvement: {improvement:+.1%}")

        # Target: Hybrid should be at least as good as local, ideally 5%+ better
        assert hybrid_accuracy >= local_accuracy, "Hybrid should not be worse than local"


@pytest.mark.acceptance
@pytest.mark.skipif(not HAS_GOOGLE_KEY, reason="GOOGLE_API_KEY not set")
class TestBudgetEnforcement:
    """Test budget caps work correctly with real API calls."""

    @pytest.mark.asyncio
    async def test_daily_budget_cap(self):
        """Test that daily budget cap prevents excessive spending."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="google",
            llm_max_cost_per_day=0.0001,  # Very low budget
        )

        # First request should succeed
        result1 = await categorizer.categorize("Starbucks")
        assert result1 is not None

        # Manually exceed budget
        categorizer.llm_categorizer.daily_cost = 0.0002

        # Second request should fail
        with pytest.raises(RuntimeError, match="budget exceeded"):
            await categorizer.categorize("Another Merchant")

        print("✅ Daily budget cap enforced")

    @pytest.mark.asyncio
    async def test_cost_per_transaction(self):
        """Measure actual cost per transaction."""
        categorizer = easy_categorization(
            model="llm",
            llm_provider="google",
            llm_max_cost_per_day=1.00,
        )

        # Test 5 transactions
        merchants = ["Starbucks", "Walmart", "Target", "Whole Foods", "Amazon"]

        for merchant in merchants:
            await categorizer.categorize(merchant)

        total_cost = categorizer.llm_categorizer.daily_cost
        cost_per_txn = total_cost / len(merchants)

        print("\n💰 Cost Analysis (5 transactions):")
        print(f"  - Total cost: ${total_cost:.6f}")
        print(f"  - Cost per transaction: ${cost_per_txn:.6f}")

        # Target: <$0.0002 per transaction (research said $0.00011 for Gemini)
        assert cost_per_txn < 0.0002, f"Cost per txn too high: ${cost_per_txn}"
