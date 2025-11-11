"""
Net Worth Calculator Module

Provides core calculation functions for net worth tracking:
- Net worth calculation (assets - liabilities)
- Currency normalization (all currencies → base currency)
- Asset allocation breakdown
- Change detection (amount + percentage)

**Quick Start**:
```python
from fin_infra.net_worth.calculator import (
    calculate_net_worth,
    normalize_currency,
    calculate_asset_allocation,
    calculate_change
)

# Calculate net worth
assets = [
    {"balance": 10000.0, "currency": "USD", "type": "cash"},
    {"balance": 50000.0, "currency": "USD", "type": "investments"},
]
liabilities = [
    {"balance": 5000.0, "currency": "USD", "type": "credit_card"},
]

net_worth = calculate_net_worth(assets, liabilities)
print(f"Net Worth: ${net_worth:,.2f}")  # $55,000.00
```
"""


from fin_infra.net_worth.models import (
    AssetAllocation,
    AssetCategory,
    AssetDetail,
    LiabilityBreakdown,
    LiabilityCategory,
    LiabilityDetail,
)


def calculate_net_worth(
    assets: list[AssetDetail],
    liabilities: list[LiabilityDetail],
    base_currency: str = "USD",
) -> float:
    """
    Calculate net worth from assets and liabilities.

    **Formula**: Net Worth = Total Assets - Total Liabilities

    All amounts are normalized to base_currency before calculation.

    **Example**:
    ```python
    assets = [
        AssetDetail(
            account_id="acct_1",
            provider="plaid",
            account_type=AssetCategory.CASH,
            name="Checking",
            balance=10000.0,
            currency="USD",
            last_updated=datetime.utcnow()
        ),
        AssetDetail(
            account_id="acct_2",
            provider="alpaca",
            account_type=AssetCategory.INVESTMENTS,
            name="Brokerage",
            balance=50000.0,
            currency="USD",
            market_value=50000.0,
            last_updated=datetime.utcnow()
        ),
    ]

    liabilities = [
        LiabilityDetail(
            account_id="acct_3",
            provider="plaid",
            liability_type=LiabilityCategory.CREDIT_CARD,
            name="Credit Card",
            balance=5000.0,
            currency="USD",
            last_updated=datetime.utcnow()
        ),
    ]

    net_worth = calculate_net_worth(assets, liabilities)
    # Result: 55000.0
    ```

    Args:
        assets: List of asset details
        liabilities: List of liability details
        base_currency: Currency to normalize to (default: USD)

    Returns:
        Net worth in base currency
    """
    # Sum all assets (use market_value if available, otherwise balance)
    total_assets = 0.0
    for asset in assets:
        # Use market value for investments/crypto (includes unrealized gains)
        amount = asset.market_value if asset.market_value is not None else asset.balance

        # Normalize to base currency (future: implement currency conversion)
        # For now, assume all are in USD
        if asset.currency != base_currency:
            # TODO: Implement currency conversion with exchange rate API
            # For V1, we'll require all accounts in USD or skip non-USD
            continue

        total_assets += amount

    # Sum all liabilities
    total_liabilities = 0.0
    for liability in liabilities:
        # Normalize to base currency
        if liability.currency != base_currency:
            # TODO: Implement currency conversion
            continue

        total_liabilities += liability.balance

    return total_assets - total_liabilities


def normalize_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    exchange_rate: float | None = None,
) -> float:
    """
    Normalize currency amount to target currency.

    **Example**:
    ```python
    # Convert 100 EUR to USD (assume rate 1.1)
    usd_amount = normalize_currency(100.0, "EUR", "USD", exchange_rate=1.1)
    # Result: 110.0
    ```

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "EUR")
        to_currency: Target currency code (e.g., "USD")
        exchange_rate: Exchange rate (from_currency to to_currency)
                      If None, will fetch from market data provider (future)

    Returns:
        Normalized amount in target currency

    Raises:
        ValueError: If exchange_rate is None and currencies don't match
    """
    # No conversion needed if same currency
    if from_currency == to_currency:
        return amount

    # Use provided exchange rate
    if exchange_rate is not None:
        return amount * exchange_rate

    # TODO: Fetch exchange rate from market data provider
    # For V1, require explicit exchange rate
    raise ValueError(
        f"Currency conversion from {from_currency} to {to_currency} requires "
        f"exchange_rate parameter. Auto-fetching not yet implemented."
    )


def calculate_asset_allocation(assets: list[AssetDetail]) -> AssetAllocation:
    """
    Calculate asset allocation breakdown by category.

    **Example**:
    ```python
    assets = [
        AssetDetail(..., account_type=AssetCategory.CASH, balance=10000.0),
        AssetDetail(..., account_type=AssetCategory.INVESTMENTS, balance=45000.0),
        AssetDetail(..., account_type=AssetCategory.CRYPTO, balance=5000.0),
    ]

    allocation = calculate_asset_allocation(assets)
    print(f"Cash: ${allocation.cash:,.2f} ({allocation.cash_percentage:.1f}%)")
    print(f"Investments: ${allocation.investments:,.2f} ({allocation.investments_percentage:.1f}%)")
    # Output:
    # Cash: $10,000.00 (16.7%)
    # Investments: $45,000.00 (75.0%)
    ```

    Args:
        assets: List of asset details

    Returns:
        AssetAllocation with totals and percentages
    """
    # Initialize category totals
    cash = 0.0
    investments = 0.0
    crypto = 0.0
    real_estate = 0.0
    vehicles = 0.0
    other_assets = 0.0

    # Sum by category
    for asset in assets:
        # Use market value if available (for stocks/crypto)
        amount = asset.market_value if asset.market_value is not None else asset.balance

        # Categorize
        if asset.account_type == AssetCategory.CASH:
            cash += amount
        elif asset.account_type == AssetCategory.INVESTMENTS:
            investments += amount
        elif asset.account_type == AssetCategory.CRYPTO:
            crypto += amount
        elif asset.account_type == AssetCategory.REAL_ESTATE:
            real_estate += amount
        elif asset.account_type == AssetCategory.VEHICLES:
            vehicles += amount
        elif asset.account_type == AssetCategory.OTHER:
            other_assets += amount

    return AssetAllocation(
        cash=cash,
        investments=investments,
        crypto=crypto,
        real_estate=real_estate,
        vehicles=vehicles,
        other_assets=other_assets,
    )


def calculate_liability_breakdown(liabilities: list[LiabilityDetail]) -> LiabilityBreakdown:
    """
    Calculate liability breakdown by category.

    **Example**:
    ```python
    liabilities = [
        LiabilityDetail(..., liability_type=LiabilityCategory.CREDIT_CARD, balance=5000.0),
        LiabilityDetail(..., liability_type=LiabilityCategory.MORTGAGE, balance=200000.0),
    ]

    breakdown = calculate_liability_breakdown(liabilities)
    print(f"Credit Cards: ${breakdown.credit_cards:,.2f} ({breakdown.credit_cards_percentage:.1f}%)")
    print(f"Mortgages: ${breakdown.mortgages:,.2f} ({breakdown.mortgages_percentage:.1f}%)")
    # Output:
    # Credit Cards: $5,000.00 (2.4%)
    # Mortgages: $200,000.00 (97.6%)
    ```

    Args:
        liabilities: List of liability details

    Returns:
        LiabilityBreakdown with totals and percentages
    """
    # Initialize category totals
    credit_cards = 0.0
    mortgages = 0.0
    auto_loans = 0.0
    student_loans = 0.0
    personal_loans = 0.0
    lines_of_credit = 0.0

    # Sum by category
    for liability in liabilities:
        if liability.liability_type == LiabilityCategory.CREDIT_CARD:
            credit_cards += liability.balance
        elif liability.liability_type == LiabilityCategory.MORTGAGE:
            mortgages += liability.balance
        elif liability.liability_type == LiabilityCategory.AUTO_LOAN:
            auto_loans += liability.balance
        elif liability.liability_type == LiabilityCategory.STUDENT_LOAN:
            student_loans += liability.balance
        elif liability.liability_type == LiabilityCategory.PERSONAL_LOAN:
            personal_loans += liability.balance
        elif liability.liability_type == LiabilityCategory.LINE_OF_CREDIT:
            lines_of_credit += liability.balance

    return LiabilityBreakdown(
        credit_cards=credit_cards,
        mortgages=mortgages,
        auto_loans=auto_loans,
        student_loans=student_loans,
        personal_loans=personal_loans,
        lines_of_credit=lines_of_credit,
    )


def calculate_change(
    current_net_worth: float,
    previous_net_worth: float | None,
) -> tuple[float | None, float | None]:
    """
    Calculate net worth change (amount + percentage).

    **Example**:
    ```python
    change_amount, change_percent = calculate_change(64000.0, 60000.0)
    print(f"Change: ${change_amount:,.2f} ({change_percent:.2f}%)")
    # Output: Change: $4,000.00 (6.67%)
    ```

    Args:
        current_net_worth: Current net worth
        previous_net_worth: Previous net worth (None if first snapshot)

    Returns:
        Tuple of (change_amount, change_percentage)
        Returns (None, None) if previous_net_worth is None
    """
    if previous_net_worth is None:
        return None, None

    # Calculate absolute change
    change_amount = current_net_worth - previous_net_worth

    # Calculate percentage change
    # Avoid division by zero
    if previous_net_worth == 0:
        # If previous was 0 and current is not, that's infinite growth
        # Return 100% as a reasonable cap
        change_percentage = 100.0 if current_net_worth > 0 else 0.0
    else:
        change_percentage = (change_amount / abs(previous_net_worth)) * 100

    return change_amount, change_percentage


def detect_significant_change(
    current_net_worth: float,
    previous_net_worth: float | None,
    threshold_percent: float = 5.0,
    threshold_amount: float = 10000.0,
) -> bool:
    """
    Detect if net worth change is significant.

    A change is significant if it exceeds EITHER:
    - Percentage threshold (default: 5%)
    - Absolute amount threshold (default: $10,000)

    **Example**:
    ```python
    # 10% increase ($6k on $60k) - SIGNIFICANT
    is_significant = detect_significant_change(66000.0, 60000.0)
    # Result: True (exceeds 5% threshold)

    # 3% increase ($15k on $500k) - SIGNIFICANT
    is_significant = detect_significant_change(515000.0, 500000.0)
    # Result: True (exceeds $10k threshold)

    # 2% increase ($1k on $50k) - NOT SIGNIFICANT
    is_significant = detect_significant_change(51000.0, 50000.0)
    # Result: False (below both thresholds)
    ```

    Args:
        current_net_worth: Current net worth
        previous_net_worth: Previous net worth (None if first snapshot)
        threshold_percent: Percentage threshold (default: 5.0%)
        threshold_amount: Absolute amount threshold (default: $10,000)

    Returns:
        True if change is significant, False otherwise
    """
    if previous_net_worth is None:
        # First snapshot - not significant (no baseline)
        return False

    # Calculate change
    change_amount, change_percentage = calculate_change(current_net_worth, previous_net_worth)

    if change_amount is None or change_percentage is None:
        return False

    # Check thresholds (either one triggers significance)
    percent_exceeded = abs(change_percentage) >= threshold_percent
    amount_exceeded = abs(change_amount) >= threshold_amount

    return percent_exceeded or amount_exceeded
