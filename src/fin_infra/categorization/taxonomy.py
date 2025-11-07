"""
Transaction category taxonomy (MX-style, 50-60 categories).

Hierarchy:
- Income (5 categories)
- Fixed Expenses (12 categories)
- Variable Expenses (32 categories)
- Savings & Investments (6 categories)
- Uncategorized (1 category)

Total: 56 leaf categories
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class CategoryGroup(str, Enum):
    """Top-level category groups."""

    INCOME = "Income"
    FIXED_EXPENSES = "Fixed Expenses"
    VARIABLE_EXPENSES = "Variable Expenses"
    SAVINGS = "Savings & Investments"
    UNCATEGORIZED = "Uncategorized"


class Category(str, Enum):
    """Transaction categories (56 total)."""

    # ===== INCOME (5) =====
    INCOME_PAYCHECK = "Paycheck"
    INCOME_INVESTMENT = "Investment Income"
    INCOME_REFUND = "Refunds & Reimbursements"
    INCOME_SIDE_HUSTLE = "Side Income"
    INCOME_OTHER = "Other Income"

    # ===== FIXED EXPENSES (12) =====
    FIXED_RENT = "Rent"
    FIXED_MORTGAGE = "Mortgage"
    FIXED_INSURANCE_HOME = "Home Insurance"
    FIXED_INSURANCE_AUTO = "Auto Insurance"
    FIXED_INSURANCE_HEALTH = "Health Insurance"
    FIXED_INSURANCE_LIFE = "Life Insurance"
    FIXED_UTILITIES_ELECTRIC = "Electric"
    FIXED_UTILITIES_GAS = "Gas"
    FIXED_UTILITIES_WATER = "Water"
    FIXED_INTERNET = "Internet & Cable"
    FIXED_PHONE = "Phone"
    FIXED_SUBSCRIPTIONS = "Subscriptions"  # Netflix, Spotify, etc.

    # ===== VARIABLE EXPENSES (32) =====
    # Food & Dining (6)
    VAR_GROCERIES = "Groceries"
    VAR_RESTAURANTS = "Restaurants"
    VAR_COFFEE_SHOPS = "Coffee Shops"
    VAR_BARS = "Bars & Nightlife"
    VAR_FAST_FOOD = "Fast Food"
    VAR_FOOD_DELIVERY = "Food Delivery"

    # Transportation (4)
    VAR_GAS_FUEL = "Gas & Fuel"
    VAR_PARKING = "Parking"
    VAR_RIDESHARE = "Rideshare & Taxis"
    VAR_PUBLIC_TRANSIT = "Public Transportation"

    # Shopping (6)
    VAR_SHOPPING_GENERAL = "General Merchandise"
    VAR_SHOPPING_CLOTHING = "Clothing & Shoes"
    VAR_SHOPPING_ELECTRONICS = "Electronics"
    VAR_SHOPPING_HOME = "Home & Garden"
    VAR_SHOPPING_BOOKS = "Books & Media"
    VAR_SHOPPING_ONLINE = "Online Shopping"

    # Entertainment (5)
    VAR_ENTERTAINMENT_MOVIES = "Movies & Events"
    VAR_ENTERTAINMENT_SPORTS = "Sports & Recreation"
    VAR_ENTERTAINMENT_HOBBIES = "Hobbies"
    VAR_ENTERTAINMENT_MUSIC = "Music & Concerts"
    VAR_ENTERTAINMENT_STREAMING = "Streaming Services"

    # Health & Wellness (4)
    VAR_HEALTH_PHARMACY = "Pharmacy"
    VAR_HEALTH_DOCTOR = "Doctor & Medical"
    VAR_HEALTH_GYM = "Gym & Fitness"
    VAR_HEALTH_PERSONAL_CARE = "Personal Care"

    # Travel (3)
    VAR_TRAVEL_FLIGHTS = "Flights"
    VAR_TRAVEL_HOTELS = "Hotels"
    VAR_TRAVEL_VACATION = "Vacation & Travel"

    # Other Variable (4)
    VAR_EDUCATION = "Education"
    VAR_GIFTS = "Gifts & Donations"
    VAR_PETS = "Pets"
    VAR_OTHER = "Other Expenses"

    # ===== SAVINGS & INVESTMENTS (6) =====
    SAVINGS_EMERGENCY = "Emergency Fund"
    SAVINGS_RETIREMENT = "Retirement"
    SAVINGS_INVESTMENT = "Investments"
    SAVINGS_TRANSFER = "Transfers"
    SAVINGS_GOAL = "Savings Goals"
    SAVINGS_OTHER = "Other Savings"

    # ===== UNCATEGORIZED (1) =====
    UNCATEGORIZED = "Uncategorized"


class CategoryMetadata(BaseModel):
    """Metadata for a category."""

    name: Category
    group: CategoryGroup
    display_name: str
    description: str
    keywords: list[str]
    examples: list[str]


# Category hierarchy mapping
CATEGORY_GROUPS: dict[Category, CategoryGroup] = {
    # Income
    Category.INCOME_PAYCHECK: CategoryGroup.INCOME,
    Category.INCOME_INVESTMENT: CategoryGroup.INCOME,
    Category.INCOME_REFUND: CategoryGroup.INCOME,
    Category.INCOME_SIDE_HUSTLE: CategoryGroup.INCOME,
    Category.INCOME_OTHER: CategoryGroup.INCOME,
    # Fixed Expenses
    Category.FIXED_RENT: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_MORTGAGE: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_INSURANCE_HOME: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_INSURANCE_AUTO: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_INSURANCE_HEALTH: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_INSURANCE_LIFE: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_UTILITIES_ELECTRIC: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_UTILITIES_GAS: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_UTILITIES_WATER: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_INTERNET: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_PHONE: CategoryGroup.FIXED_EXPENSES,
    Category.FIXED_SUBSCRIPTIONS: CategoryGroup.FIXED_EXPENSES,
    # Variable Expenses
    Category.VAR_GROCERIES: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_RESTAURANTS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_COFFEE_SHOPS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_BARS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_FAST_FOOD: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_FOOD_DELIVERY: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_GAS_FUEL: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_PARKING: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_RIDESHARE: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_PUBLIC_TRANSIT: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_SHOPPING_GENERAL: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_SHOPPING_CLOTHING: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_SHOPPING_ELECTRONICS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_SHOPPING_HOME: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_SHOPPING_BOOKS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_SHOPPING_ONLINE: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_ENTERTAINMENT_MOVIES: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_ENTERTAINMENT_SPORTS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_ENTERTAINMENT_HOBBIES: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_ENTERTAINMENT_MUSIC: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_ENTERTAINMENT_STREAMING: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_HEALTH_PHARMACY: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_HEALTH_DOCTOR: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_HEALTH_GYM: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_HEALTH_PERSONAL_CARE: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_TRAVEL_FLIGHTS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_TRAVEL_HOTELS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_TRAVEL_VACATION: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_EDUCATION: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_GIFTS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_PETS: CategoryGroup.VARIABLE_EXPENSES,
    Category.VAR_OTHER: CategoryGroup.VARIABLE_EXPENSES,
    # Savings & Investments
    Category.SAVINGS_EMERGENCY: CategoryGroup.SAVINGS,
    Category.SAVINGS_RETIREMENT: CategoryGroup.SAVINGS,
    Category.SAVINGS_INVESTMENT: CategoryGroup.SAVINGS,
    Category.SAVINGS_TRANSFER: CategoryGroup.SAVINGS,
    Category.SAVINGS_GOAL: CategoryGroup.SAVINGS,
    Category.SAVINGS_OTHER: CategoryGroup.SAVINGS,
    # Uncategorized
    Category.UNCATEGORIZED: CategoryGroup.UNCATEGORIZED,
}


# Category metadata (for display and matching)
CATEGORY_METADATA: dict[Category, CategoryMetadata] = {
    # Income
    Category.INCOME_PAYCHECK: CategoryMetadata(
        name=Category.INCOME_PAYCHECK,
        group=CategoryGroup.INCOME,
        display_name="Paycheck",
        description="Salary, wages, and employment income",
        keywords=["payroll", "salary", "wages", "direct deposit", "employer"],
        examples=["ACME CORP PAYROLL", "Direct Deposit", "Employer Transfer"],
    ),
    Category.INCOME_INVESTMENT: CategoryMetadata(
        name=Category.INCOME_INVESTMENT,
        group=CategoryGroup.INCOME,
        display_name="Investment Income",
        description="Dividends, interest, and capital gains",
        keywords=["dividend", "interest", "capital gains", "investment"],
        examples=["Vanguard Dividend", "Interest Payment", "Stock Sale"],
    ),
    Category.INCOME_REFUND: CategoryMetadata(
        name=Category.INCOME_REFUND,
        group=CategoryGroup.INCOME,
        display_name="Refunds & Reimbursements",
        description="Tax refunds, rebates, and reimbursements",
        keywords=["refund", "rebate", "reimbursement", "return"],
        examples=["IRS Refund", "Insurance Reimbursement", "Product Return"],
    ),
    # Fixed Expenses
    Category.FIXED_RENT: CategoryMetadata(
        name=Category.FIXED_RENT,
        group=CategoryGroup.FIXED_EXPENSES,
        display_name="Rent",
        description="Monthly rent payments",
        keywords=["rent", "apartment", "landlord"],
        examples=["ABC Property Management", "Monthly Rent", "Landlord Payment"],
    ),
    Category.FIXED_SUBSCRIPTIONS: CategoryMetadata(
        name=Category.FIXED_SUBSCRIPTIONS,
        group=CategoryGroup.FIXED_EXPENSES,
        display_name="Subscriptions",
        description="Recurring subscription services",
        keywords=["subscription", "membership", "recurring"],
        examples=["Netflix", "Spotify", "Amazon Prime", "Disney+"],
    ),
    # Variable Expenses - Food & Dining
    Category.VAR_GROCERIES: CategoryMetadata(
        name=Category.VAR_GROCERIES,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Groceries",
        description="Grocery stores and supermarkets",
        keywords=["grocery", "supermarket", "food market"],
        examples=["Whole Foods", "Safeway", "Trader Joe's", "Costco"],
    ),
    Category.VAR_RESTAURANTS: CategoryMetadata(
        name=Category.VAR_RESTAURANTS,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Restaurants",
        description="Sit-down restaurants and dining",
        keywords=["restaurant", "dining", "bistro", "cafe"],
        examples=["Chipotle", "Olive Garden", "Local Restaurant"],
    ),
    Category.VAR_COFFEE_SHOPS: CategoryMetadata(
        name=Category.VAR_COFFEE_SHOPS,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Coffee Shops",
        description="Coffee shops and cafes",
        keywords=["coffee", "cafe", "espresso", "latte"],
        examples=["Starbucks", "Peet's Coffee", "Local Cafe"],
    ),
    Category.VAR_FAST_FOOD: CategoryMetadata(
        name=Category.VAR_FAST_FOOD,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Fast Food",
        description="Fast food and quick service restaurants",
        keywords=["fast food", "quick service", "drive thru"],
        examples=["McDonald's", "Taco Bell", "Subway", "Wendy's"],
    ),
    # Variable Expenses - Transportation
    Category.VAR_GAS_FUEL: CategoryMetadata(
        name=Category.VAR_GAS_FUEL,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Gas & Fuel",
        description="Gas stations and fuel",
        keywords=["gas", "fuel", "gasoline", "chevron", "shell"],
        examples=["Chevron", "Shell", "76 Gas", "Arco"],
    ),
    Category.VAR_RIDESHARE: CategoryMetadata(
        name=Category.VAR_RIDESHARE,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Rideshare & Taxis",
        description="Uber, Lyft, and taxi services",
        keywords=["uber", "lyft", "taxi", "rideshare"],
        examples=["Uber", "Lyft", "Yellow Cab"],
    ),
    # Variable Expenses - Shopping
    Category.VAR_SHOPPING_ONLINE: CategoryMetadata(
        name=Category.VAR_SHOPPING_ONLINE,
        group=CategoryGroup.VARIABLE_EXPENSES,
        display_name="Online Shopping",
        description="Online retailers and e-commerce",
        keywords=["amazon", "online", "ecommerce", "internet"],
        examples=["Amazon", "eBay", "Target.com"],
    ),
    # Savings
    Category.SAVINGS_TRANSFER: CategoryMetadata(
        name=Category.SAVINGS_TRANSFER,
        group=CategoryGroup.SAVINGS,
        display_name="Transfers",
        description="Account transfers and savings",
        keywords=["transfer", "savings", "move money"],
        examples=["Transfer to Savings", "Account Transfer"],
    ),
    # Uncategorized
    Category.UNCATEGORIZED: CategoryMetadata(
        name=Category.UNCATEGORIZED,
        group=CategoryGroup.UNCATEGORIZED,
        display_name="Uncategorized",
        description="Transactions that don't fit other categories",
        keywords=["unknown", "misc", "other"],
        examples=["Unknown Merchant", "Unrecognized Transaction"],
    ),
}


def get_category_group(category: Category) -> CategoryGroup:
    """Get the group for a category."""
    return CATEGORY_GROUPS.get(category, CategoryGroup.UNCATEGORIZED)


def get_category_metadata(category: Category) -> Optional[CategoryMetadata]:
    """Get metadata for a category."""
    return CATEGORY_METADATA.get(category)


def get_all_categories() -> list[Category]:
    """Get all categories."""
    return list(Category)


def get_categories_by_group(group: CategoryGroup) -> list[Category]:
    """Get all categories in a group."""
    return [cat for cat, grp in CATEGORY_GROUPS.items() if grp == group]


def count_categories() -> dict[str, int]:
    """Count categories by group."""
    counts = {group.value: 0 for group in CategoryGroup}
    for category, group in CATEGORY_GROUPS.items():
        counts[group.value] += 1
    return counts
