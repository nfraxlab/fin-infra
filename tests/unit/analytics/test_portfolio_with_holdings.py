"""Unit tests for portfolio analytics with real holdings integration.

Tests portfolio_metrics_with_holdings() and calculate_day_change_with_snapshot().
"""

from decimal import Decimal

import pytest

from fin_infra.analytics.portfolio import (
    portfolio_metrics_with_holdings,
    calculate_day_change_with_snapshot,
    _calculate_allocation_from_holdings,
)
from fin_infra.investments.models import Holding, Security, SecurityType


@pytest.fixture
def sample_holdings() -> list[Holding]:
    """Sample holdings for testing."""
    return [
        Holding(
            account_id="acct1",
            security=Security(
                security_id="AAPL",
                name="Apple Inc.",
                ticker_symbol="AAPL",
                type=SecurityType.equity,  # lowercase
            ),
            quantity=Decimal("10"),
            institution_price=Decimal("150.00"),
            institution_value=Decimal("1500.00"),
            cost_basis=Decimal("1200.00"),
            iso_currency_code="USD",
        ),
        Holding(
            account_id="acct1",
            security=Security(
                security_id="GOOGL",
                name="Alphabet Inc.",
                ticker_symbol="GOOGL",
                type=SecurityType.equity,  # lowercase
            ),
            quantity=Decimal("5"),
            institution_price=Decimal("140.00"),
            institution_value=Decimal("700.00"),
            cost_basis=Decimal("650.00"),
            iso_currency_code="USD",
        ),
        Holding(
            account_id="acct2",
            security=Security(
                security_id="BND",
                name="Vanguard Total Bond Market ETF",
                ticker_symbol="BND",
                type=SecurityType.mutual_fund,  # lowercase
            ),
            quantity=Decimal("20"),
            institution_price=Decimal("80.00"),
            institution_value=Decimal("1600.00"),
            cost_basis=Decimal("1580.00"),
            iso_currency_code="USD",
        ),
    ]


@pytest.fixture
def previous_holdings() -> list[Holding]:
    """Previous day holdings for day change testing."""
    return [
        Holding(
            account_id="acct1",
            security=Security(
                security_id="AAPL",
                name="Apple Inc.",
                ticker_symbol="AAPL",
                type=SecurityType.equity,
            ),
            quantity=Decimal("10"),
            institution_price=Decimal("148.00"),  # Was $148, now $150
            institution_value=Decimal("1480.00"),
            cost_basis=Decimal("1200.00"),
            iso_currency_code="USD",
        ),
        Holding(
            account_id="acct1",
            security=Security(
                security_id="GOOGL",
                name="Alphabet Inc.",
                ticker_symbol="GOOGL",
                type=SecurityType.equity,
            ),
            quantity=Decimal("5"),
            institution_price=Decimal("138.00"),  # Was $138, now $140
            institution_value=Decimal("690.00"),
            cost_basis=Decimal("650.00"),
            iso_currency_code="USD",
        ),
        Holding(
            account_id="acct2",
            security=Security(
                security_id="BND",
                name="Vanguard Total Bond Market ETF",
                ticker_symbol="BND",
                type=SecurityType.mutual_fund,
            ),
            quantity=Decimal("20"),
            institution_price=Decimal("79.50"),  # Was $79.50, now $80.00
            institution_value=Decimal("1590.00"),
            cost_basis=Decimal("1580.00"),
            iso_currency_code="USD",
        ),
    ]


class TestPortfolioMetricsWithHoldings:
    """Test portfolio_metrics_with_holdings() function."""

    def test_basic_metrics(self, sample_holdings: list[Holding]) -> None:
        """Test basic portfolio metrics calculation."""
        metrics = portfolio_metrics_with_holdings(sample_holdings)

        # Total value: 1500 + 700 + 1600 = 3800
        assert metrics.total_value == pytest.approx(3800.00)

        # Total return: (1500 - 1200) + (700 - 650) + (1600 - 1580) = 370
        assert metrics.total_return == pytest.approx(370.00)

        # Total return %: 370 / 3430 * 100 ≈ 10.79%
        total_cost = Decimal("1200") + Decimal("650") + Decimal("1580")  # 3430
        expected_percent = float(Decimal("370") / total_cost * 100)
        assert metrics.total_return_percent == pytest.approx(expected_percent, rel=0.01)

    def test_allocation(self, sample_holdings: list[Holding]) -> None:
        """Test asset allocation calculation."""
        metrics = portfolio_metrics_with_holdings(sample_holdings)

        # Stocks (AAPL + GOOGL): 2200 / 3800 ≈ 57.89%
        # Bonds (BND): 1600 / 3800 ≈ 42.11%
        allocation = {a.asset_class: a.percentage for a in metrics.allocation_by_asset_class}

        assert "Stocks" in allocation
        assert "Bonds" in allocation

        stocks_percent = allocation["Stocks"]
        bonds_percent = allocation["Bonds"]

        assert stocks_percent == pytest.approx(57.89, abs=0.1)
        assert bonds_percent == pytest.approx(42.11, abs=0.1)

    def test_empty_holdings(self) -> None:
        """Test with empty holdings list."""
        metrics = portfolio_metrics_with_holdings([])

        assert metrics.total_value == 0.0
        assert metrics.total_return == 0.0
        assert metrics.total_return_percent == 0.0
        assert metrics.allocation_by_asset_class == []

    def test_single_holding(self) -> None:
        """Test with single holding."""
        holdings = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="AAPL",
                    name="Apple Inc.",
                    ticker_symbol="AAPL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("10"),
                institution_price=Decimal("150.00"),
                institution_value=Decimal("1500.00"),
                cost_basis=Decimal("1200.00"),
                iso_currency_code="USD",
            )
        ]

        metrics = portfolio_metrics_with_holdings(holdings)

        assert metrics.total_value == 1500.00
        assert metrics.total_return == 300.00
        assert metrics.total_return_percent == pytest.approx(25.0)
        allocation = {a.asset_class: a.percentage for a in metrics.allocation_by_asset_class}
        assert allocation == {"Stocks": 100.0}

    def test_no_cost_basis(self) -> None:
        """Test holdings without cost basis."""
        holdings = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="AAPL",
                    name="Apple Inc.",
                    ticker_symbol="AAPL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("10"),
                institution_price=Decimal("150.00"),
                institution_value=Decimal("1500.00"),
                cost_basis=None,  # No cost basis
                iso_currency_code="USD",
            )
        ]

        metrics = portfolio_metrics_with_holdings(holdings)

        # Should still calculate total value
        assert metrics.total_value == 1500.00
        # With no cost basis (0), return equals current value
        # (This shows we don't know the true P/L without cost basis)
        assert metrics.total_return == 1500.00  # value - 0 = value
        assert metrics.total_return_percent == 0.0  # Avoid division by zero


class TestCalculateDayChange:
    """Test calculate_day_change_with_snapshot() function."""

    def test_day_change_calculation(
        self, sample_holdings: list[Holding], previous_holdings: list[Holding]
    ) -> None:
        """Test day-over-day change calculation."""
        result = calculate_day_change_with_snapshot(sample_holdings, previous_holdings)

        # AAPL: 1500 - 1480 = +20
        # GOOGL: 700 - 690 = +10
        # BND: 1600 - 1590 = +10
        # Total: +40
        assert result["day_change_dollars"] == pytest.approx(40.0)

        # Previous total: 1480 + 690 + 1590 = 3760
        # Percent: 40 / 3760 * 100 ≈ 1.06%
        assert result["day_change_percent"] == pytest.approx(1.06, abs=0.01)

    def test_negative_day_change(self) -> None:
        """Test negative day change (portfolio decreased)."""
        current = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="AAPL",
                    name="Apple Inc.",
                    ticker_symbol="AAPL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("10"),
                institution_price=Decimal("145.00"),
                institution_value=Decimal("1450.00"),
                cost_basis=Decimal("1200.00"),
                iso_currency_code="USD",
            )
        ]

        previous = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="AAPL",
                    name="Apple Inc.",
                    ticker_symbol="AAPL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("10"),
                institution_price=Decimal("150.00"),
                institution_value=Decimal("1500.00"),
                cost_basis=Decimal("1200.00"),
                iso_currency_code="USD",
            )
        ]

        result = calculate_day_change_with_snapshot(current, previous)

        assert result["day_change_dollars"] == pytest.approx(-50.0)
        assert result["day_change_percent"] == pytest.approx(-3.33, abs=0.01)

    def test_new_holding(self, sample_holdings: list[Holding]) -> None:
        """Test with new holding added today."""
        # Previous day had only 2 holdings, today has 3
        previous = sample_holdings[:2]  # Only AAPL and GOOGL

        result = calculate_day_change_with_snapshot(sample_holdings, previous)

        # Should only compare matching holdings
        # AAPL and GOOGL are same price, so day change is 0
        assert result["day_change_dollars"] == 0.0
        assert result["day_change_percent"] == 0.0

    def test_empty_previous(self, sample_holdings: list[Holding]) -> None:
        """Test with no previous snapshot."""
        result = calculate_day_change_with_snapshot(sample_holdings, [])

        assert result["day_change_dollars"] == 0.0
        assert result["day_change_percent"] == 0.0

    def test_empty_current(self, previous_holdings: list[Holding]) -> None:
        """Test with no current holdings."""
        result = calculate_day_change_with_snapshot([], previous_holdings)

        assert result["day_change_dollars"] == 0.0
        assert result["day_change_percent"] == 0.0


class TestAllocationFromHoldings:
    """Test _calculate_allocation_from_holdings() helper function."""

    def test_mixed_allocation(self, sample_holdings: list[Holding]) -> None:
        """Test allocation with multiple asset types."""
        total_value = float(
            sum(h.institution_value for h in sample_holdings if h.institution_value)
        )
        allocation_list = _calculate_allocation_from_holdings(sample_holdings, total_value)
        allocation = {a.asset_class: a.percentage for a in allocation_list}

        assert "Stocks" in allocation
        assert "Bonds" in allocation

        # Verify percentages sum to 100
        assert sum(allocation.values()) == pytest.approx(100.0)

    def test_single_asset_class(self) -> None:
        """Test allocation with single asset class."""
        holdings = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="AAPL",
                    name="Apple Inc.",
                    ticker_symbol="AAPL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("10"),
                institution_price=Decimal("150.00"),
                institution_value=Decimal("1500.00"),
                cost_basis=Decimal("1200.00"),
                iso_currency_code="USD",
            ),
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="GOOGL",
                    name="Alphabet Inc.",
                    ticker_symbol="GOOGL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("5"),
                institution_price=Decimal("140.00"),
                institution_value=Decimal("700.00"),
                cost_basis=Decimal("650.00"),
                iso_currency_code="USD",
            ),
        ]

        total_value = 2200.0
        allocation_list = _calculate_allocation_from_holdings(holdings, total_value)
        allocation = {a.asset_class: a.percentage for a in allocation_list}

        assert allocation == {"Stocks": 100.0}

    def test_unknown_security_type(self) -> None:
        """Test handling of unknown security types."""
        holdings = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="CRYPTO",
                    name="Bitcoin",
                    ticker_symbol="BTC",
                    type=SecurityType.other,  # Maps to "Other"
                ),
                quantity=Decimal("1"),
                institution_price=Decimal("50000.00"),
                institution_value=Decimal("50000.00"),
                cost_basis=Decimal("40000.00"),
                iso_currency_code="USD",
            )
        ]

        allocation_list = _calculate_allocation_from_holdings(holdings, 50000.0)
        allocation = {a.asset_class: a.percentage for a in allocation_list}

        assert allocation == {"Other": 100.0}

    def test_zero_total_value(self, sample_holdings: list[Holding]) -> None:
        """Test with zero total value."""
        allocation_list = _calculate_allocation_from_holdings(sample_holdings, 0.0)

        assert allocation_list == []

    def test_allocation_rounding(self) -> None:
        """Test allocation percentage rounding."""
        holdings = [
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="AAPL",
                    name="Apple Inc.",
                    ticker_symbol="AAPL",
                    type=SecurityType.equity,
                ),
                quantity=Decimal("1"),
                institution_price=Decimal("100.00"),
                institution_value=Decimal("100.00"),
                cost_basis=Decimal("90.00"),
                iso_currency_code="USD",
            ),
            Holding(
                account_id="acct1",
                security=Security(
                    security_id="BND",
                    name="Bond Fund",
                    ticker_symbol="BND",
                    type=SecurityType.mutual_fund,
                ),
                quantity=Decimal("2"),
                institution_price=Decimal("100.00"),
                institution_value=Decimal("200.00"),
                cost_basis=Decimal("180.00"),
                iso_currency_code="USD",
            ),
        ]

        allocation_list = _calculate_allocation_from_holdings(holdings, 300.0)
        allocation = {a.asset_class: a.percentage for a in allocation_list}

        # 100/300 = 33.33%, 200/300 = 66.67%
        assert allocation["Stocks"] == pytest.approx(33.33, abs=0.01)
        assert allocation["Bonds"] == pytest.approx(66.67, abs=0.01)
