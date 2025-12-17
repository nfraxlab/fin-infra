"""
Unit tests for transaction categorization.

Tests the 3-layer hybrid approach:
- Layer 1: Exact match
- Layer 2: Regex patterns
- Layer 3: ML fallback (when enabled)
"""

import pytest

from fin_infra.categorization import (
    Category,
    CategoryGroup,
    CategorizationEngine,
    CategorizationMethod,
    categorize,
    easy_categorization,
    get_all_categories,
    get_category_group,
)


class TestTaxonomy:
    """Test category taxonomy."""

    @pytest.mark.asyncio
    async def test_category_count(self):
        """Test that we have 56 categories."""
        categories = get_all_categories()
        assert len(categories) == 56

    @pytest.mark.asyncio
    async def test_category_groups(self):
        """Test category group assignments."""
        # Test income
        assert get_category_group(Category.INCOME_PAYCHECK) == CategoryGroup.INCOME

        # Test fixed expenses
        assert get_category_group(Category.FIXED_RENT) == CategoryGroup.FIXED_EXPENSES
        assert get_category_group(Category.FIXED_SUBSCRIPTIONS) == CategoryGroup.FIXED_EXPENSES

        # Test variable expenses
        assert get_category_group(Category.VAR_GROCERIES) == CategoryGroup.VARIABLE_EXPENSES
        assert get_category_group(Category.VAR_COFFEE_SHOPS) == CategoryGroup.VARIABLE_EXPENSES

        # Test savings
        assert get_category_group(Category.SAVINGS_TRANSFER) == CategoryGroup.SAVINGS

        # Test uncategorized
        assert get_category_group(Category.UNCATEGORIZED) == CategoryGroup.UNCATEGORIZED

    @pytest.mark.asyncio
    async def test_all_categories_have_groups(self):
        """Test that all categories are assigned to groups."""
        for category in get_all_categories():
            group = get_category_group(category)
            assert group is not None
            assert isinstance(group, CategoryGroup)


class TestExactMatch:
    """Test Layer 1: Exact match categorization."""

    @pytest.mark.asyncio
    async def test_coffee_shops_exact(self):
        """Test exact match for coffee shops."""
        result = await categorize("Starbucks")
        assert result.category == Category.VAR_COFFEE_SHOPS
        assert result.confidence == 1.0
        assert result.method == CategorizationMethod.EXACT

    @pytest.mark.asyncio
    async def test_fast_food_exact(self):
        """Test exact match for fast food."""
        result = await categorize("McDonalds")
        assert result.category == Category.VAR_FAST_FOOD
        assert result.confidence == 1.0
        assert result.method == CategorizationMethod.EXACT

    @pytest.mark.asyncio
    async def test_groceries_exact(self):
        """Test exact match for groceries."""
        result = await categorize("Whole Foods")
        assert result.category == Category.VAR_GROCERIES
        assert result.confidence == 1.0
        assert result.method == CategorizationMethod.EXACT

    @pytest.mark.asyncio
    async def test_gas_stations_exact(self):
        """Test exact match for gas stations."""
        result = await categorize("Chevron")
        assert result.category == Category.VAR_GAS_FUEL
        assert result.confidence == 1.0
        assert result.method == CategorizationMethod.EXACT

    @pytest.mark.asyncio
    async def test_subscriptions_exact(self):
        """Test exact match for subscriptions."""
        result = await categorize("Netflix")
        assert result.category == Category.FIXED_SUBSCRIPTIONS
        assert result.confidence == 1.0
        assert result.method == CategorizationMethod.EXACT

    @pytest.mark.asyncio
    async def test_rideshare_exact(self):
        """Test exact match for rideshare."""
        result = await categorize("Uber")
        assert result.category == Category.VAR_RIDESHARE
        assert result.confidence == 1.0
        assert result.method == CategorizationMethod.EXACT

    @pytest.mark.asyncio
    async def test_case_insensitive_exact(self):
        """Test that exact matching is case-insensitive."""
        result1 = await categorize("STARBUCKS")
        result2 = await categorize("starbucks")
        result3 = await categorize("Starbucks")

        assert result1.category == result2.category == result3.category
        assert result1.category == Category.VAR_COFFEE_SHOPS


class TestRegexMatch:
    """Test Layer 2: Regex pattern categorization."""

    @pytest.mark.asyncio
    async def test_coffee_shops_regex(self):
        """Test regex match for coffee shops with store numbers."""
        result = await categorize("STARBUCKS #12345")
        assert result.category == Category.VAR_COFFEE_SHOPS
        assert result.confidence >= 0.7
        # Note: May be exact match after normalization (which is fine)
        assert result.method in [CategorizationMethod.EXACT, CategorizationMethod.REGEX]

    @pytest.mark.asyncio
    async def test_gas_station_regex(self):
        """Test regex match for gas stations with store numbers."""
        result = await categorize("CHEVRON #98765")
        assert result.category == Category.VAR_GAS_FUEL
        assert result.confidence >= 0.7
        # Note: May be exact match after normalization (which is fine)
        assert result.method in [CategorizationMethod.EXACT, CategorizationMethod.REGEX]

    @pytest.mark.asyncio
    async def test_subscription_regex(self):
        """Test regex match for subscription variants."""
        result = await categorize("NFLX*SUBSCRIPTION")
        assert result.category == Category.FIXED_SUBSCRIPTIONS
        assert result.confidence >= 0.7
        assert result.method == CategorizationMethod.REGEX

    @pytest.mark.asyncio
    async def test_amazon_variants_regex(self):
        """Test regex match for Amazon variants."""
        result1 = await categorize("AMZN MKTP US")
        result2 = await categorize("AMAZON.COM*1234")

        assert result1.category == Category.VAR_SHOPPING_ONLINE
        assert result2.category == Category.VAR_SHOPPING_ONLINE

    @pytest.mark.asyncio
    async def test_rideshare_variants_regex(self):
        """Test regex match for rideshare variants."""
        result1 = await categorize("UBER TRIP")
        result2 = await categorize("LYFT RIDE")

        assert result1.category == Category.VAR_RIDESHARE
        assert result2.category == Category.VAR_RIDESHARE


class TestNormalization:
    """Test merchant name normalization."""

    @pytest.mark.asyncio
    async def test_remove_store_numbers(self):
        """Test that store numbers are removed."""
        result1 = await categorize("STARBUCKS #12345")
        result2 = await categorize("STARBUCKS #67890")

        # Both should match to same category
        assert result1.category == result2.category == Category.VAR_COFFEE_SHOPS

    @pytest.mark.asyncio
    async def test_remove_special_characters(self):
        """Test that special characters are handled."""
        result1 = await categorize("STARBUCKS*COFFEE")
        result2 = await categorize("STARBUCKS COFFEE")

        # Both should match to same category
        assert result1.category == result2.category

    @pytest.mark.asyncio
    async def test_remove_legal_entities(self):
        """Test that legal entities are removed."""
        # Test with and without "INC"
        result1 = await categorize("STARBUCKS INC")
        result2 = await categorize("STARBUCKS")

        assert result1.category == result2.category == Category.VAR_COFFEE_SHOPS


class TestFallback:
    """Test fallback to uncategorized."""

    @pytest.mark.asyncio
    async def test_unknown_merchant_fallback(self):
        """Test that unknown merchants fall back to uncategorized."""
        result = await categorize("UNKNOWN RANDOM MERCHANT XYZ")
        assert result.category == Category.UNCATEGORIZED
        assert result.confidence == 0.0
        assert result.method == CategorizationMethod.FALLBACK

    @pytest.mark.asyncio
    async def test_random_text_fallback(self):
        """Test that random text falls back to uncategorized."""
        result = await categorize("asdfghjkl qwertyuiop")
        assert result.category == Category.UNCATEGORIZED
        assert result.confidence == 0.0
        assert result.method == CategorizationMethod.FALLBACK


class TestCategorizationEngine:
    """Test CategorizationEngine class."""

    @pytest.mark.asyncio
    async def test_engine_creation(self):
        """Test that engine can be created."""
        engine = CategorizationEngine()
        assert engine is not None

    @pytest.mark.asyncio
    async def test_engine_categorize(self):
        """Test that engine can categorize."""
        engine = CategorizationEngine()
        result = await engine.categorize("Starbucks")
        assert result.category == Category.VAR_COFFEE_SHOPS

    @pytest.mark.asyncio
    async def test_engine_stats(self):
        """Test that engine tracks statistics."""
        engine = CategorizationEngine()

        # Categorize some merchants
        await engine.categorize("Starbucks")  # Exact
        await engine.categorize("STARBUCKS #123")  # Exact (normalized)
        await engine.categorize("Unknown Merchant")  # Fallback

        stats = engine.get_stats()
        # Note: Both "Starbucks" and "STARBUCKS #123" normalize to "starbucks" = exact match
        assert stats["exact_matches"] == 2
        assert stats["fallback"] == 1
        assert stats["total"] == 3

    @pytest.mark.asyncio
    async def test_engine_add_rule(self):
        """Test that custom rules can be added."""
        engine = CategorizationEngine()

        # Add custom rule
        engine.add_rule("MY CUSTOM MERCHANT", Category.VAR_RESTAURANTS)

        # Test custom rule works
        result = await engine.categorize("MY CUSTOM MERCHANT")
        assert result.category == Category.VAR_RESTAURANTS


class TestEasySetup:
    """Test easy_categorization() builder."""

    @pytest.mark.asyncio
    async def test_easy_default(self):
        """Test easy_categorization with defaults."""
        engine = easy_categorization()
        assert engine is not None
        assert isinstance(engine, CategorizationEngine)

    @pytest.mark.asyncio
    async def test_easy_with_ml_disabled(self):
        """Test easy_categorization with ML disabled."""
        engine = easy_categorization(enable_ml=False)
        result = await engine.categorize("Starbucks")
        assert result.category == Category.VAR_COFFEE_SHOPS

    @pytest.mark.asyncio
    async def test_easy_invalid_taxonomy(self):
        """Test that invalid taxonomy raises error."""
        with pytest.raises(ValueError, match="Unsupported taxonomy"):
            easy_categorization(taxonomy="invalid")

    @pytest.mark.asyncio
    async def test_easy_invalid_model(self):
        """Test that invalid model raises error."""
        with pytest.raises(ValueError, match="Unsupported model"):
            easy_categorization(model="invalid")


class TestAccuracy:
    """Test categorization accuracy on common merchants."""

    @pytest.mark.parametrize(
        "merchant,expected_category",
        [
            # Coffee shops
            ("Starbucks", Category.VAR_COFFEE_SHOPS),
            ("STARBUCKS #12345", Category.VAR_COFFEE_SHOPS),
            ("Peet's Coffee", Category.VAR_COFFEE_SHOPS),
            ("Dunkin Donuts", Category.VAR_COFFEE_SHOPS),
            # Fast food
            ("McDonald's", Category.VAR_FAST_FOOD),
            ("Taco Bell", Category.VAR_FAST_FOOD),
            ("Subway", Category.VAR_FAST_FOOD),
            # Groceries
            ("Whole Foods", Category.VAR_GROCERIES),
            ("Trader Joe's", Category.VAR_GROCERIES),
            ("Safeway", Category.VAR_GROCERIES),
            ("Costco", Category.VAR_GROCERIES),
            # Gas stations
            ("Chevron", Category.VAR_GAS_FUEL),
            ("Shell", Category.VAR_GAS_FUEL),
            ("76", Category.VAR_GAS_FUEL),
            # Rideshare
            ("Uber", Category.VAR_RIDESHARE),
            ("Lyft", Category.VAR_RIDESHARE),
            ("UBER TRIP", Category.VAR_RIDESHARE),
            # Subscriptions
            ("Netflix", Category.FIXED_SUBSCRIPTIONS),
            ("Spotify", Category.FIXED_SUBSCRIPTIONS),
            ("Amazon Prime", Category.FIXED_SUBSCRIPTIONS),
            # Online shopping
            ("Amazon", Category.VAR_SHOPPING_ONLINE),
            ("AMZN MKTP US", Category.VAR_SHOPPING_ONLINE),
            # Transfers
            ("Transfer", Category.SAVINGS_TRANSFER),
            ("Savings", Category.SAVINGS_TRANSFER),
        ],
    )
    @pytest.mark.asyncio
    async def test_common_merchants(self, merchant, expected_category):
        """Test categorization of common merchants."""
        result = await categorize(merchant)
        assert result.category == expected_category, (
            f"Failed for {merchant}: expected {expected_category}, got {result.category}"
        )

    @pytest.mark.asyncio
    async def test_accuracy_rate(self):
        """Test overall accuracy rate on known merchants."""
        test_cases = [
            ("Starbucks", Category.VAR_COFFEE_SHOPS),
            ("McDonald's", Category.VAR_FAST_FOOD),
            ("Whole Foods", Category.VAR_GROCERIES),
            ("Chevron", Category.VAR_GAS_FUEL),
            ("Uber", Category.VAR_RIDESHARE),
            ("Netflix", Category.FIXED_SUBSCRIPTIONS),
            ("Amazon", Category.VAR_SHOPPING_ONLINE),
            ("Trader Joe's", Category.VAR_GROCERIES),
            ("Taco Bell", Category.VAR_FAST_FOOD),
            ("Lyft", Category.VAR_RIDESHARE),
        ]

        correct = 0
        for merchant, expected in test_cases:
            result = await categorize(merchant)
            if result.category == expected:
                correct += 1

        accuracy = correct / len(test_cases)
        assert accuracy >= 0.9, f"Accuracy {accuracy:.1%} below 90% target"
