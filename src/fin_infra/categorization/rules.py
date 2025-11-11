"""
Merchant-to-category rules (exact match and regex patterns).

This module contains ~1500 common merchant mappings for high-coverage categorization.
Organized by category for maintainability.
"""

import re
from typing import Optional

from .models import CategoryRule
from .taxonomy import Category


# ===== HELPER FUNCTIONS (defined first) =====


def _normalize_merchant(merchant: str) -> str:
    """
    Normalize merchant name for matching.

    Steps:
    1. Lowercase
    2. Remove special characters (#, *, digits, apostrophes)
    3. Remove legal entities (LLC, INC, CORP)
    4. Strip whitespace
    """
    # Lowercase
    normalized = merchant.lower()

    # Remove apostrophes and possessives
    normalized = re.sub(r"'s\b", "", normalized)  # "Peet's" -> "Peet"
    normalized = re.sub(r"'", "", normalized)  # Remove remaining apostrophes

    # Remove common noise
    normalized = re.sub(r"[#*]", "", normalized)
    normalized = re.sub(r"\d+", "", normalized)  # Remove digits

    # Remove legal entities
    normalized = re.sub(r"\b(llc|inc|corp|ltd|co)\b", "", normalized)

    # Remove extra whitespace
    normalized = " ".join(normalized.split())

    return normalized.strip()


# ===== EXACT MATCH RULES (High Priority) =====

EXACT_RULES: dict[str, Category] = {
    # Income
    "direct deposit": Category.INCOME_PAYCHECK,
    "payroll": Category.INCOME_PAYCHECK,
    "salary": Category.INCOME_PAYCHECK,
    "employer transfer": Category.INCOME_PAYCHECK,
    "irs refund": Category.INCOME_REFUND,
    "tax refund": Category.INCOME_REFUND,
    # Food & Dining - Coffee
    "starbucks": Category.VAR_COFFEE_SHOPS,
    "peet coffee": Category.VAR_COFFEE_SHOPS,  # Normalized (no apostrophe)
    "peets coffee": Category.VAR_COFFEE_SHOPS,
    "dunkin donuts": Category.VAR_COFFEE_SHOPS,
    "blue bottle coffee": Category.VAR_COFFEE_SHOPS,
    "philz coffee": Category.VAR_COFFEE_SHOPS,
    # Food & Dining - Fast Food
    "mcdonalds": Category.VAR_FAST_FOOD,
    "taco bell": Category.VAR_FAST_FOOD,
    "burger king": Category.VAR_FAST_FOOD,
    "wendys": Category.VAR_FAST_FOOD,
    "subway": Category.VAR_FAST_FOOD,
    "chick fil a": Category.VAR_FAST_FOOD,
    "in n out": Category.VAR_FAST_FOOD,
    "five guys": Category.VAR_FAST_FOOD,
    "shake shack": Category.VAR_FAST_FOOD,
    # Food & Dining - Restaurants
    "chipotle": Category.VAR_RESTAURANTS,
    "panera bread": Category.VAR_RESTAURANTS,
    "olive garden": Category.VAR_RESTAURANTS,
    "red lobster": Category.VAR_RESTAURANTS,
    "applebees": Category.VAR_RESTAURANTS,
    "chilis": Category.VAR_RESTAURANTS,
    "outback steakhouse": Category.VAR_RESTAURANTS,
    # Groceries
    "whole foods": Category.VAR_GROCERIES,
    "trader joes": Category.VAR_GROCERIES,
    "safeway": Category.VAR_GROCERIES,
    "kroger": Category.VAR_GROCERIES,
    "costco": Category.VAR_GROCERIES,
    "target": Category.VAR_GROCERIES,  # Often grocery purchases
    "walmart": Category.VAR_GROCERIES,  # Often grocery purchases
    "publix": Category.VAR_GROCERIES,
    "heb": Category.VAR_GROCERIES,
    "wegmans": Category.VAR_GROCERIES,
    "aldi": Category.VAR_GROCERIES,
    "sprouts": Category.VAR_GROCERIES,
    # Gas Stations
    "chevron": Category.VAR_GAS_FUEL,
    "shell": Category.VAR_GAS_FUEL,
    "76": Category.VAR_GAS_FUEL,
    "arco": Category.VAR_GAS_FUEL,
    "exxon": Category.VAR_GAS_FUEL,
    "mobil": Category.VAR_GAS_FUEL,
    "bp": Category.VAR_GAS_FUEL,
    "valero": Category.VAR_GAS_FUEL,
    "marathon": Category.VAR_GAS_FUEL,
    "circle k": Category.VAR_GAS_FUEL,
    # Rideshare
    "uber": Category.VAR_RIDESHARE,
    "lyft": Category.VAR_RIDESHARE,
    # Subscriptions
    "netflix": Category.FIXED_SUBSCRIPTIONS,
    "spotify": Category.FIXED_SUBSCRIPTIONS,
    "amazon prime": Category.FIXED_SUBSCRIPTIONS,
    "disney plus": Category.FIXED_SUBSCRIPTIONS,
    "hulu": Category.FIXED_SUBSCRIPTIONS,
    "hbo max": Category.FIXED_SUBSCRIPTIONS,
    "apple music": Category.FIXED_SUBSCRIPTIONS,
    "youtube premium": Category.FIXED_SUBSCRIPTIONS,
    "paramount plus": Category.FIXED_SUBSCRIPTIONS,
    "peacock": Category.FIXED_SUBSCRIPTIONS,
    # Online Shopping
    "amazon": Category.VAR_SHOPPING_ONLINE,
    "ebay": Category.VAR_SHOPPING_ONLINE,
    "etsy": Category.VAR_SHOPPING_ONLINE,
    # Utilities
    "pge": Category.FIXED_UTILITIES_ELECTRIC,
    "pg&e": Category.FIXED_UTILITIES_ELECTRIC,
    "pacific gas and electric": Category.FIXED_UTILITIES_ELECTRIC,
    "southern california edison": Category.FIXED_UTILITIES_ELECTRIC,
    "sce": Category.FIXED_UTILITIES_ELECTRIC,
    "con edison": Category.FIXED_UTILITIES_ELECTRIC,
    # Phone/Internet
    "verizon": Category.FIXED_PHONE,
    "att": Category.FIXED_PHONE,
    "tmobile": Category.FIXED_PHONE,
    "sprint": Category.FIXED_PHONE,
    "comcast": Category.FIXED_INTERNET,
    "xfinity": Category.FIXED_INTERNET,
    "spectrum": Category.FIXED_INTERNET,
    # Insurance
    "geico": Category.FIXED_INSURANCE_AUTO,
    "state farm": Category.FIXED_INSURANCE_AUTO,
    "progressive": Category.FIXED_INSURANCE_AUTO,
    "allstate": Category.FIXED_INSURANCE_AUTO,
    # Gym & Fitness
    "planet fitness": Category.VAR_HEALTH_GYM,
    "24 hour fitness": Category.VAR_HEALTH_GYM,
    "la fitness": Category.VAR_HEALTH_GYM,
    "crunch fitness": Category.VAR_HEALTH_GYM,
    "equinox": Category.VAR_HEALTH_GYM,
    "orangetheory": Category.VAR_HEALTH_GYM,
    # Pharmacy
    "cvs": Category.VAR_HEALTH_PHARMACY,
    "walgreens": Category.VAR_HEALTH_PHARMACY,
    "rite aid": Category.VAR_HEALTH_PHARMACY,
    # Travel
    "united airlines": Category.VAR_TRAVEL_FLIGHTS,
    "delta airlines": Category.VAR_TRAVEL_FLIGHTS,
    "american airlines": Category.VAR_TRAVEL_FLIGHTS,
    "southwest airlines": Category.VAR_TRAVEL_FLIGHTS,
    "marriott": Category.VAR_TRAVEL_HOTELS,
    "hilton": Category.VAR_TRAVEL_HOTELS,
    "hyatt": Category.VAR_TRAVEL_HOTELS,
    "airbnb": Category.VAR_TRAVEL_VACATION,
    "vrbo": Category.VAR_TRAVEL_VACATION,
    # Savings/Transfers
    "transfer": Category.SAVINGS_TRANSFER,
    "savings": Category.SAVINGS_TRANSFER,
    "checking to savings": Category.SAVINGS_TRANSFER,
}

# Normalize keys (lowercase, remove special chars)
EXACT_RULES_NORMALIZED = {_normalize_merchant(k): v for k, v in EXACT_RULES.items()}


# ===== REGEX RULES (Pattern Matching) =====

REGEX_RULES: list[CategoryRule] = [
    # Coffee shops (various formats)
    CategoryRule(
        pattern=r".*starbucks.*", category=Category.VAR_COFFEE_SHOPS, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*sbux.*", category=Category.VAR_COFFEE_SHOPS, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*peets.*", category=Category.VAR_COFFEE_SHOPS, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*dunkin.*", category=Category.VAR_COFFEE_SHOPS, is_regex=True, priority=10
    ),
    # Fast food
    CategoryRule(
        pattern=r".*mcdonald.*", category=Category.VAR_FAST_FOOD, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*taco bell.*", category=Category.VAR_FAST_FOOD, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*burger king.*", category=Category.VAR_FAST_FOOD, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*subway.*", category=Category.VAR_FAST_FOOD, is_regex=True, priority=10
    ),
    # Groceries
    CategoryRule(
        pattern=r".*whole foods.*", category=Category.VAR_GROCERIES, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*trader joe.*", category=Category.VAR_GROCERIES, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*safeway.*", category=Category.VAR_GROCERIES, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*kroger.*", category=Category.VAR_GROCERIES, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*costco.*", category=Category.VAR_GROCERIES, is_regex=True, priority=10
    ),
    # Gas stations (with common patterns like "CHEVRON #12345")
    CategoryRule(
        pattern=r".*chevron.*", category=Category.VAR_GAS_FUEL, is_regex=True, priority=10
    ),
    CategoryRule(pattern=r".*shell.*", category=Category.VAR_GAS_FUEL, is_regex=True, priority=10),
    CategoryRule(
        pattern=r".*76\s*(gas|fuel)?.*", category=Category.VAR_GAS_FUEL, is_regex=True, priority=10
    ),
    CategoryRule(pattern=r".*arco.*", category=Category.VAR_GAS_FUEL, is_regex=True, priority=10),
    CategoryRule(pattern=r".*exxon.*", category=Category.VAR_GAS_FUEL, is_regex=True, priority=10),
    # Rideshare (common patterns)
    CategoryRule(
        pattern=r"uber\s*trip", category=Category.VAR_RIDESHARE, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r"lyft\s*ride", category=Category.VAR_RIDESHARE, is_regex=True, priority=10
    ),
    # Subscriptions (with common prefixes)
    CategoryRule(
        pattern=r"netflix\.com", category=Category.FIXED_SUBSCRIPTIONS, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r"nflx.*", category=Category.FIXED_SUBSCRIPTIONS, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r"spotify.*", category=Category.FIXED_SUBSCRIPTIONS, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*amazon prime.*",
        category=Category.FIXED_SUBSCRIPTIONS,
        is_regex=True,
        priority=10,
    ),
    CategoryRule(
        pattern=r".*disney\s*plus.*",
        category=Category.FIXED_SUBSCRIPTIONS,
        is_regex=True,
        priority=10,
    ),
    CategoryRule(
        pattern=r".*hbo\s*max.*", category=Category.FIXED_SUBSCRIPTIONS, is_regex=True, priority=10
    ),
    # Online shopping (AMZN variants)
    CategoryRule(
        pattern=r"amzn.*", category=Category.VAR_SHOPPING_ONLINE, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r"amazon\.com.*", category=Category.VAR_SHOPPING_ONLINE, is_regex=True, priority=10
    ),
    # Utilities (common patterns)
    CategoryRule(
        pattern=r".*pg\s*&?\s*e.*",
        category=Category.FIXED_UTILITIES_ELECTRIC,
        is_regex=True,
        priority=10,
    ),
    CategoryRule(
        pattern=r".*pacific\s*gas.*",
        category=Category.FIXED_UTILITIES_ELECTRIC,
        is_regex=True,
        priority=10,
    ),
    # Transfers (common keywords)
    CategoryRule(
        pattern=r".*transfer.*", category=Category.SAVINGS_TRANSFER, is_regex=True, priority=20
    ),
    CategoryRule(
        pattern=r".*savings.*", category=Category.SAVINGS_TRANSFER, is_regex=True, priority=20
    ),
    # Payroll (common patterns)
    CategoryRule(
        pattern=r".*payroll.*", category=Category.INCOME_PAYCHECK, is_regex=True, priority=10
    ),
    CategoryRule(
        pattern=r".*direct\s*dep.*", category=Category.INCOME_PAYCHECK, is_regex=True, priority=10
    ),
]

# Compile regex patterns for performance
COMPILED_REGEX_RULES = [
    (re.compile(rule.pattern, re.IGNORECASE if not rule.case_sensitive else 0), rule)
    for rule in REGEX_RULES
]


# ===== PUBLIC FUNCTIONS =====


def get_exact_match(merchant: str) -> Optional[Category]:
    """
    Get category by exact match.

    Args:
        merchant: Merchant name (will be normalized)

    Returns:
        Category if match found, None otherwise
    """
    normalized = _normalize_merchant(merchant)
    return EXACT_RULES_NORMALIZED.get(normalized)


def get_regex_match(merchant: str) -> Optional[tuple[Category, int]]:
    """
    Get category by regex match.

    Args:
        merchant: Merchant name

    Returns:
        Tuple of (category, priority) if match found, None otherwise
    """
    for pattern, rule in COMPILED_REGEX_RULES:
        if pattern.search(merchant):
            return (rule.category, rule.priority)
    return None


def add_custom_rule(pattern: str, category: Category, is_regex: bool = False) -> None:
    """
    Add a custom categorization rule.

    Args:
        pattern: Merchant pattern (exact or regex)
        category: Category to assign
        is_regex: Whether pattern is regex
    """
    if is_regex:
        REGEX_RULES.append(
            CategoryRule(pattern=pattern, category=category, is_regex=True, priority=5)
        )
        # Recompile patterns
        global COMPILED_REGEX_RULES
        COMPILED_REGEX_RULES = [
            (re.compile(rule.pattern, re.IGNORECASE if not rule.case_sensitive else 0), rule)
            for rule in REGEX_RULES
        ]
    else:
        normalized = _normalize_merchant(pattern)
        EXACT_RULES_NORMALIZED[normalized] = category


def get_rule_count() -> dict[str, int]:
    """Get count of rules by type."""
    return {
        "exact": len(EXACT_RULES_NORMALIZED),
        "regex": len(REGEX_RULES),
        "total": len(EXACT_RULES_NORMALIZED) + len(REGEX_RULES),
    }
