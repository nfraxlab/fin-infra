"""
Unit tests for net worth tracking module.

Tests cover:
- Net worth calculation (assets - liabilities)
- Multi-provider aggregation
- Currency normalization
- Asset allocation calculations
- Liability breakdown calculations
- Change detection (amount + percentage)
- Significant change detection (thresholds)
- Easy builder validation
"""

from datetime import datetime

import pytest

from fin_infra.net_worth import (
    AssetCategory,
    AssetDetail,
    LiabilityCategory,
    LiabilityDetail,
    NetWorthAggregator,
    calculate_asset_allocation,
    calculate_change,
    calculate_liability_breakdown,
    calculate_net_worth,
    detect_significant_change,
    easy_net_worth,
    normalize_currency,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_assets():
    """Sample asset accounts for testing."""
    return [
        AssetDetail(
            account_id="acct_cash_1",
            provider="banking",
            account_type=AssetCategory.CASH,
            name="Checking Account",
            balance=10000.0,
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
        AssetDetail(
            account_id="acct_investments_1",
            provider="brokerage",
            account_type=AssetCategory.INVESTMENTS,
            name="Brokerage Account",
            balance=40000.0,
            currency="USD",
            market_value=50000.0,  # $10k unrealized gain
            cost_basis=40000.0,
            gain_loss=10000.0,
            gain_loss_percentage=25.0,
            last_updated=datetime.utcnow(),
        ),
        AssetDetail(
            account_id="acct_crypto_1",
            provider="crypto",
            account_type=AssetCategory.CRYPTO,
            name="Bitcoin Wallet",
            balance=5000.0,
            currency="USD",
            market_value=5000.0,
            last_updated=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def sample_liabilities():
    """Sample liability accounts for testing."""
    return [
        LiabilityDetail(
            account_id="acct_cc_1",
            provider="banking",
            liability_type=LiabilityCategory.CREDIT_CARD,
            name="Credit Card",
            balance=5000.0,
            currency="USD",
            interest_rate=0.18,  # 18% APR
            minimum_payment=150.0,
            last_updated=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def sample_assets_multiple_currencies():
    """Sample assets with multiple currencies."""
    return [
        AssetDetail(
            account_id="acct_usd",
            provider="banking",
            account_type=AssetCategory.CASH,
            name="USD Account",
            balance=10000.0,
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
        AssetDetail(
            account_id="acct_eur",
            provider="banking",
            account_type=AssetCategory.CASH,
            name="EUR Account",
            balance=5000.0,
            currency="EUR",
            last_updated=datetime.utcnow(),
        ),
    ]


# ============================================================================
# Calculator Tests
# ============================================================================


def test_calculate_net_worth_basic(sample_assets, sample_liabilities):
    """Test basic net worth calculation: assets - liabilities."""
    # Expected: $10k cash + $50k stocks (market value) + $5k crypto - $5k credit card
    # = $60k net worth
    net_worth = calculate_net_worth(sample_assets, sample_liabilities)

    assert net_worth == 60000.0, f"Expected $60k, got ${net_worth:,.2f}"


def test_calculate_net_worth_uses_market_value(sample_assets, sample_liabilities):
    """Test that calculation uses market value for investments (not cost basis)."""
    # Brokerage account has $40k cost basis but $50k market value
    # Should use $50k (market value)
    net_worth = calculate_net_worth(sample_assets, sample_liabilities)

    # Verify market value used (not cost basis)
    assert net_worth == 60000.0  # Uses $50k market value, not $40k cost basis


def test_calculate_net_worth_no_liabilities(sample_assets):
    """Test net worth with assets only (no liabilities)."""
    net_worth = calculate_net_worth(sample_assets, [])

    # $10k cash + $50k stocks + $5k crypto = $65k
    assert net_worth == 65000.0


def test_calculate_net_worth_no_assets(sample_liabilities):
    """Test net worth with liabilities only (negative net worth)."""
    net_worth = calculate_net_worth([], sample_liabilities)

    # -$5k credit card = -$5k net worth
    assert net_worth == -5000.0


def test_calculate_net_worth_empty():
    """Test net worth with no accounts."""
    net_worth = calculate_net_worth([], [])

    assert net_worth == 0.0


def test_calculate_net_worth_skips_non_usd(sample_assets_multiple_currencies):
    """Test that non-USD currencies are skipped (for V1)."""
    # Only USD account should be counted
    net_worth = calculate_net_worth(sample_assets_multiple_currencies, [])

    # Should only count USD ($10k), skip EUR
    assert net_worth == 10000.0


# ============================================================================
# Currency Normalization Tests
# ============================================================================


def test_normalize_currency_same_currency():
    """Test currency normalization with same currency (no conversion)."""
    amount = normalize_currency(100.0, "USD", "USD")

    assert amount == 100.0


def test_normalize_currency_with_rate():
    """Test currency normalization with explicit exchange rate."""
    # 100 EUR @ 1.1 rate = 110 USD
    amount = normalize_currency(100.0, "EUR", "USD", exchange_rate=1.1)

    assert abs(amount - 110.0) < 0.01  # Allow floating-point precision tolerance


def test_normalize_currency_without_rate_raises_error():
    """Test that currency conversion without rate raises error (V1 limitation)."""
    with pytest.raises(ValueError, match="Currency conversion.*requires exchange_rate"):
        normalize_currency(100.0, "EUR", "USD")


# ============================================================================
# Asset Allocation Tests
# ============================================================================


def test_calculate_asset_allocation(sample_assets):
    """Test asset allocation calculation by category."""
    allocation = calculate_asset_allocation(sample_assets)

    # Verify amounts
    assert allocation.cash == 10000.0
    assert allocation.investments == 50000.0  # Uses market value
    assert allocation.crypto == 5000.0
    assert allocation.real_estate == 0.0
    assert allocation.vehicles == 0.0
    assert allocation.other_assets == 0.0

    # Verify total
    assert allocation.total_assets == 65000.0

    # Verify percentages (computed fields)
    assert abs(allocation.cash_percentage - 15.38) < 0.1  # ~15.4%
    assert abs(allocation.investments_percentage - 76.92) < 0.1  # ~76.9%
    assert abs(allocation.crypto_percentage - 7.69) < 0.1  # ~7.7%


def test_calculate_asset_allocation_empty():
    """Test asset allocation with no assets."""
    allocation = calculate_asset_allocation([])

    assert allocation.total_assets == 0.0
    assert allocation.cash_percentage == 0.0
    assert allocation.investments_percentage == 0.0


def test_calculate_asset_allocation_percentages_sum_to_100(sample_assets):
    """Test that allocation percentages sum to 100%."""
    allocation = calculate_asset_allocation(sample_assets)

    total_percentage = (
        allocation.cash_percentage
        + allocation.investments_percentage
        + allocation.crypto_percentage
        + allocation.real_estate_percentage
        + allocation.vehicles_percentage
        + allocation.other_percentage
    )

    # Allow small rounding error
    assert abs(total_percentage - 100.0) < 0.01


# ============================================================================
# Liability Breakdown Tests
# ============================================================================


def test_calculate_liability_breakdown(sample_liabilities):
    """Test liability breakdown calculation by category."""
    breakdown = calculate_liability_breakdown(sample_liabilities)

    # Verify amounts
    assert breakdown.credit_cards == 5000.0
    assert breakdown.mortgages == 0.0
    assert breakdown.auto_loans == 0.0
    assert breakdown.student_loans == 0.0
    assert breakdown.personal_loans == 0.0
    assert breakdown.lines_of_credit == 0.0

    # Verify total
    assert breakdown.total_liabilities == 5000.0

    # Verify percentages
    assert breakdown.credit_cards_percentage == 100.0


def test_calculate_liability_breakdown_multiple_types():
    """Test liability breakdown with multiple types."""
    liabilities = [
        LiabilityDetail(
            account_id="cc",
            provider="banking",
            liability_type=LiabilityCategory.CREDIT_CARD,
            name="Credit Card",
            balance=5000.0,
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
        LiabilityDetail(
            account_id="mortgage",
            provider="banking",
            liability_type=LiabilityCategory.MORTGAGE,
            name="Mortgage",
            balance=200000.0,
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
    ]

    breakdown = calculate_liability_breakdown(liabilities)

    assert breakdown.total_liabilities == 205000.0
    assert abs(breakdown.credit_cards_percentage - 2.44) < 0.1  # ~2.4%
    assert abs(breakdown.mortgages_percentage - 97.56) < 0.1  # ~97.6%


def test_calculate_liability_breakdown_empty():
    """Test liability breakdown with no liabilities."""
    breakdown = calculate_liability_breakdown([])

    assert breakdown.total_liabilities == 0.0
    assert breakdown.credit_cards_percentage == 0.0


# ============================================================================
# Change Detection Tests
# ============================================================================


def test_calculate_change_increase():
    """Test change calculation with increase."""
    change_amount, change_percent = calculate_change(64000.0, 60000.0)

    assert change_amount == 4000.0
    assert abs(change_percent - 6.67) < 0.1  # ~6.67%


def test_calculate_change_decrease():
    """Test change calculation with decrease."""
    change_amount, change_percent = calculate_change(56000.0, 60000.0)

    assert change_amount == -4000.0
    assert abs(change_percent - (-6.67)) < 0.1  # ~-6.67%


def test_calculate_change_no_previous():
    """Test change calculation with no previous snapshot (first time)."""
    change_amount, change_percent = calculate_change(60000.0, None)

    assert change_amount is None
    assert change_percent is None


def test_calculate_change_from_zero():
    """Test change calculation from zero net worth."""
    change_amount, change_percent = calculate_change(10000.0, 0.0)

    assert change_amount == 10000.0
    # Should cap at 100% when previous was 0
    assert change_percent == 100.0


def test_calculate_change_to_zero():
    """Test change calculation to zero net worth."""
    change_amount, change_percent = calculate_change(0.0, 10000.0)

    assert change_amount == -10000.0
    assert change_percent == -100.0


# ============================================================================
# Significant Change Detection Tests
# ============================================================================


def test_detect_significant_change_percent_threshold():
    """Test significant change detection with percentage threshold."""
    # 10% increase ($6k on $60k) - exceeds 5% threshold
    is_significant = detect_significant_change(66000.0, 60000.0)

    assert is_significant is True


def test_detect_significant_change_amount_threshold():
    """Test significant change detection with amount threshold."""
    # 3% increase ($15k on $500k) - below 5% but exceeds $10k threshold
    is_significant = detect_significant_change(515000.0, 500000.0)

    assert is_significant is True


def test_detect_significant_change_below_both_thresholds():
    """Test significant change detection below both thresholds."""
    # 2% increase ($1k on $50k) - below both thresholds
    is_significant = detect_significant_change(51000.0, 50000.0)

    assert is_significant is False


def test_detect_significant_change_no_previous():
    """Test significant change detection with no previous (first snapshot)."""
    is_significant = detect_significant_change(60000.0, None)

    # First snapshot is not significant (no baseline)
    assert is_significant is False


def test_detect_significant_change_custom_thresholds():
    """Test significant change detection with custom thresholds."""
    # 4% increase - significant with 3% threshold, not with 5%
    is_significant_3pct = detect_significant_change(
        52000.0, 50000.0, threshold_percent=3.0, threshold_amount=10000.0
    )
    is_significant_5pct = detect_significant_change(
        52000.0, 50000.0, threshold_percent=5.0, threshold_amount=10000.0
    )

    assert is_significant_3pct is True
    assert is_significant_5pct is False


def test_detect_significant_change_negative():
    """Test significant change detection with decrease."""
    # 10% decrease - should be significant (absolute value)
    is_significant = detect_significant_change(54000.0, 60000.0)

    assert is_significant is True


# ============================================================================
# Easy Builder Tests
# ============================================================================


def test_easy_net_worth_requires_provider():
    """Test that easy_net_worth requires at least one provider."""
    with pytest.raises(ValueError, match="At least one provider required"):
        easy_net_worth()


def test_easy_net_worth_with_banking():
    """Test easy_net_worth with banking provider."""

    # Mock banking provider
    class MockBanking:
        pass

    tracker = easy_net_worth(banking=MockBanking())

    assert tracker is not None
    assert tracker.aggregator.banking_provider is not None


def test_easy_net_worth_with_multiple_providers():
    """Test easy_net_worth with multiple providers."""

    # Mock providers
    class MockBanking:
        pass

    class MockBrokerage:
        pass

    tracker = easy_net_worth(
        banking=MockBanking(),
        brokerage=MockBrokerage(),
    )

    assert tracker.aggregator.banking_provider is not None
    assert tracker.aggregator.brokerage_provider is not None


def test_easy_net_worth_default_config():
    """Test easy_net_worth default configuration."""

    class MockBanking:
        pass

    tracker = easy_net_worth(banking=MockBanking())

    # Verify defaults
    assert tracker.aggregator.base_currency == "USD"
    assert tracker.snapshot_schedule == "daily"
    assert tracker.change_threshold_percent == 5.0
    assert tracker.change_threshold_amount == 10000.0


def test_easy_net_worth_custom_config():
    """Test easy_net_worth with custom configuration."""

    class MockBanking:
        pass

    tracker = easy_net_worth(
        banking=MockBanking(),
        base_currency="EUR",
        snapshot_schedule="weekly",
        change_threshold_percent=10.0,
        change_threshold_amount=50000.0,
    )

    # Verify custom config
    assert tracker.aggregator.base_currency == "EUR"
    assert tracker.snapshot_schedule == "weekly"
    assert tracker.change_threshold_percent == 10.0
    assert tracker.change_threshold_amount == 50000.0


# ============================================================================
# Aggregator Tests
# ============================================================================


def test_aggregator_requires_provider():
    """Test that NetWorthAggregator requires at least one provider."""
    with pytest.raises(ValueError, match="At least one provider required"):
        NetWorthAggregator()


def test_aggregator_with_single_provider():
    """Test NetWorthAggregator with single provider."""

    class MockBanking:
        pass

    aggregator = NetWorthAggregator(banking_provider=MockBanking())

    assert aggregator.banking_provider is not None
    assert aggregator.brokerage_provider is None
    assert aggregator.crypto_provider is None


def test_aggregator_with_multiple_providers():
    """Test NetWorthAggregator with multiple providers."""

    class MockBanking:
        pass

    class MockBrokerage:
        pass

    class MockCrypto:
        pass

    aggregator = NetWorthAggregator(
        banking_provider=MockBanking(),
        brokerage_provider=MockBrokerage(),
        crypto_provider=MockCrypto(),
    )

    assert aggregator.banking_provider is not None
    assert aggregator.brokerage_provider is not None
    assert aggregator.crypto_provider is not None


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================


def test_calculate_net_worth_large_numbers():
    """Test net worth calculation with large numbers (millions)."""
    assets = [
        AssetDetail(
            account_id="acct_1",
            provider="banking",
            account_type=AssetCategory.REAL_ESTATE,
            name="Primary Residence",
            balance=1000000.0,  # $1M
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
    ]

    liabilities = [
        LiabilityDetail(
            account_id="acct_2",
            provider="banking",
            liability_type=LiabilityCategory.MORTGAGE,
            name="Mortgage",
            balance=750000.0,  # $750k
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
    ]

    net_worth = calculate_net_worth(assets, liabilities)

    assert net_worth == 250000.0  # $250k equity


def test_calculate_net_worth_negative_net_worth():
    """Test net worth calculation with negative result (more debt than assets)."""
    assets = [
        AssetDetail(
            account_id="acct_1",
            provider="banking",
            account_type=AssetCategory.CASH,
            name="Checking",
            balance=5000.0,
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
    ]

    liabilities = [
        LiabilityDetail(
            account_id="acct_2",
            provider="banking",
            liability_type=LiabilityCategory.STUDENT_LOAN,
            name="Student Loan",
            balance=50000.0,
            currency="USD",
            last_updated=datetime.utcnow(),
        ),
    ]

    net_worth = calculate_net_worth(assets, liabilities)

    assert net_worth == -45000.0  # Negative net worth


def test_detect_significant_change_exactly_at_threshold():
    """Test significant change detection at exact threshold."""
    # Exactly 5% change
    is_significant = detect_significant_change(63000.0, 60000.0, threshold_percent=5.0)

    assert is_significant is True  # >= threshold


def test_detect_significant_change_just_below_threshold():
    """Test significant change detection just below threshold."""
    # 4.99% change (just below 5%)
    is_significant = detect_significant_change(
        62994.0, 60000.0, threshold_percent=5.0, threshold_amount=10000.0
    )

    assert is_significant is False
