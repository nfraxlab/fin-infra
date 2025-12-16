"""Unit tests for InvestmentProvider base class and helper methods."""

from datetime import date
from decimal import Decimal
from typing import List

import pytest

from fin_infra.investments.models import (
    AssetAllocation,
    Holding,
    InvestmentAccount,
    InvestmentTransaction,
    Security,
    SecurityType,
)
from fin_infra.investments.providers.base import InvestmentProvider


# Test implementation of abstract base class
class MockInvestmentProvider(InvestmentProvider):
    """Mock provider for testing base class functionality."""

    async def get_holdings(
        self, access_token: str, account_ids: List[str] | None = None
    ) -> List[Holding]:
        """Mock implementation."""
        return []

    async def get_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: List[str] | None = None,
    ) -> List[InvestmentTransaction]:
        """Mock implementation."""
        return []

    async def get_securities(self, access_token: str, security_ids: List[str]) -> List[Security]:
        """Mock implementation."""
        return []

    async def get_investment_accounts(self, access_token: str) -> List[InvestmentAccount]:
        """Mock implementation."""
        return []


@pytest.fixture
def provider() -> MockInvestmentProvider:
    """Create a mock provider instance."""
    return MockInvestmentProvider()


@pytest.fixture
def sample_securities() -> List[Security]:
    """Create sample securities for testing."""
    return [
        Security(
            security_id="sec_equity_1",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
            sector="Technology",
            close_price=Decimal("175.50"),
            currency="USD",
        ),
        Security(
            security_id="sec_etf_1",
            ticker_symbol="VOO",
            name="Vanguard S&P 500 ETF",
            type=SecurityType.etf,
            sector="Diversified",
            close_price=Decimal("420.00"),
            currency="USD",
        ),
        Security(
            security_id="sec_bond_1",
            ticker_symbol="BND",
            name="Vanguard Total Bond Market ETF",
            type=SecurityType.bond,
            close_price=Decimal("75.00"),
            currency="USD",
        ),
        Security(
            security_id="sec_cash_1",
            ticker_symbol="USD",
            name="US Dollar",
            type=SecurityType.cash,
            close_price=Decimal("1.00"),
            currency="USD",
        ),
    ]


@pytest.fixture
def sample_holdings(sample_securities: List[Security]) -> List[Holding]:
    """Create sample holdings for testing."""
    return [
        Holding(
            account_id="acc_1",
            security=sample_securities[0],  # AAPL
            quantity=Decimal("10"),
            institution_price=Decimal("175.50"),
            institution_value=Decimal("1755.00"),
            cost_basis=Decimal("1500.00"),
            currency="USD",
        ),
        Holding(
            account_id="acc_1",
            security=sample_securities[1],  # VOO
            quantity=Decimal("5"),
            institution_price=Decimal("420.00"),
            institution_value=Decimal("2100.00"),
            cost_basis=Decimal("2000.00"),
            currency="USD",
        ),
        Holding(
            account_id="acc_1",
            security=sample_securities[2],  # BND
            quantity=Decimal("20"),
            institution_price=Decimal("75.00"),
            institution_value=Decimal("1500.00"),
            cost_basis=Decimal("1550.00"),
            currency="USD",
        ),
        Holding(
            account_id="acc_1",
            security=sample_securities[3],  # Cash
            quantity=Decimal("645.00"),
            institution_price=Decimal("1.00"),
            institution_value=Decimal("645.00"),
            cost_basis=Decimal("645.00"),
            currency="USD",
        ),
    ]


# Tests for calculate_allocation()


class TestCalculateAllocation:
    """Tests for calculate_allocation() helper method."""

    def test_calculate_allocation_basic(
        self, provider: MockInvestmentProvider, sample_holdings: List[Holding]
    ):
        """Test basic asset allocation calculation."""
        allocation = provider.calculate_allocation(sample_holdings)

        assert isinstance(allocation, AssetAllocation)
        assert allocation.by_security_type[SecurityType.equity] == 29.25  # 1755 / 6000
        assert allocation.by_security_type[SecurityType.etf] == 35.0  # 2100 / 6000
        assert allocation.by_security_type[SecurityType.bond] == 25.0  # 1500 / 6000
        assert allocation.cash_percent == 10.75  # 645 / 6000

    def test_calculate_allocation_by_sector(
        self, provider: MockInvestmentProvider, sample_holdings: List[Holding]
    ):
        """Test sector-based allocation calculation."""
        allocation = provider.calculate_allocation(sample_holdings)

        assert "Technology" in allocation.by_sector
        assert allocation.by_sector["Technology"] == 29.25  # AAPL only
        assert "Diversified" in allocation.by_sector
        assert allocation.by_sector["Diversified"] == 35.0  # VOO only

    def test_calculate_allocation_empty_holdings(self, provider: MockInvestmentProvider):
        """Test allocation calculation with empty holdings list."""
        allocation = provider.calculate_allocation([])

        assert allocation.by_security_type == {}
        assert allocation.by_sector == {}
        assert allocation.cash_percent == 0.0

    def test_calculate_allocation_only_cash(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test allocation calculation with only cash holdings."""
        cash_holdings = [
            Holding(
                account_id="acc_1",
                security=sample_securities[3],  # Cash
                quantity=Decimal("1000.00"),
                institution_price=Decimal("1.00"),
                institution_value=Decimal("1000.00"),
                cost_basis=Decimal("1000.00"),
                currency="USD",
            )
        ]

        allocation = provider.calculate_allocation(cash_holdings)

        assert allocation.by_security_type == {}
        assert allocation.by_sector == {}
        assert allocation.cash_percent == 100.0

    def test_calculate_allocation_no_sector_data(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test allocation calculation when securities have no sector information."""
        # Create security without sector
        security_no_sector = Security(
            security_id="sec_no_sector",
            ticker_symbol="TEST",
            name="Test Security",
            type=SecurityType.equity,
            close_price=Decimal("100.00"),
            currency="USD",
        )

        holdings = [
            Holding(
                account_id="acc_1",
                security=security_no_sector,
                quantity=Decimal("10"),
                institution_price=Decimal("100.00"),
                institution_value=Decimal("1000.00"),
                cost_basis=Decimal("900.00"),
                currency="USD",
            )
        ]

        allocation = provider.calculate_allocation(holdings)

        assert allocation.by_security_type[SecurityType.equity] == 100.0
        assert allocation.by_sector == {}  # No sector data
        assert allocation.cash_percent == 0.0

    def test_calculate_allocation_zero_value_holdings(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test allocation calculation when holdings have zero value."""
        zero_holdings = [
            Holding(
                account_id="acc_1",
                security=sample_securities[0],
                quantity=Decimal("0"),
                institution_price=Decimal("175.50"),
                institution_value=Decimal("0.00"),
                cost_basis=Decimal("0.00"),
                currency="USD",
            )
        ]

        allocation = provider.calculate_allocation(zero_holdings)

        assert allocation.by_security_type == {}
        assert allocation.by_sector == {}
        assert allocation.cash_percent == 0.0


# Tests for calculate_portfolio_metrics()


class TestCalculatePortfolioMetrics:
    """Tests for calculate_portfolio_metrics() helper method."""

    def test_calculate_portfolio_metrics_basic(
        self, provider: MockInvestmentProvider, sample_holdings: List[Holding]
    ):
        """Test basic portfolio metrics calculation."""
        metrics = provider.calculate_portfolio_metrics(sample_holdings)

        assert metrics["total_value"] == 6000.0  # 1755 + 2100 + 1500 + 645
        assert metrics["total_cost_basis"] == 5695.0  # 1500 + 2000 + 1550 + 645
        assert metrics["total_unrealized_gain_loss"] == 305.0  # 6000 - 5695
        assert metrics["total_unrealized_gain_loss_percent"] == pytest.approx(
            5.35, rel=0.01
        )  # 305 / 5695 * 100

    def test_calculate_portfolio_metrics_loss(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test portfolio metrics when holdings have unrealized losses."""
        losing_holdings = [
            Holding(
                account_id="acc_1",
                security=sample_securities[0],
                quantity=Decimal("10"),
                institution_price=Decimal("100.00"),
                institution_value=Decimal("1000.00"),
                cost_basis=Decimal("1500.00"),
                currency="USD",
            )
        ]

        metrics = provider.calculate_portfolio_metrics(losing_holdings)

        assert metrics["total_value"] == 1000.0
        assert metrics["total_cost_basis"] == 1500.0
        assert metrics["total_unrealized_gain_loss"] == -500.0
        assert metrics["total_unrealized_gain_loss_percent"] == pytest.approx(-33.33, rel=0.01)

    def test_calculate_portfolio_metrics_empty_holdings(self, provider: MockInvestmentProvider):
        """Test portfolio metrics with empty holdings list."""
        metrics = provider.calculate_portfolio_metrics([])

        assert metrics["total_value"] == 0.0
        assert metrics["total_cost_basis"] == 0.0
        assert metrics["total_unrealized_gain_loss"] == 0.0
        assert metrics["total_unrealized_gain_loss_percent"] == 0.0

    def test_calculate_portfolio_metrics_no_cost_basis(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test portfolio metrics when holdings have no cost basis."""
        no_cost_holdings = [
            Holding(
                account_id="acc_1",
                security=sample_securities[0],
                quantity=Decimal("10"),
                institution_price=Decimal("175.50"),
                institution_value=Decimal("1755.00"),
                currency="USD",
            )
        ]

        metrics = provider.calculate_portfolio_metrics(no_cost_holdings)

        assert metrics["total_value"] == 1755.0
        assert metrics["total_cost_basis"] == 0.0
        assert metrics["total_unrealized_gain_loss"] == 1755.0
        assert metrics["total_unrealized_gain_loss_percent"] == 0.0  # Avoid division by zero

    def test_calculate_portfolio_metrics_precision(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test that metrics are properly rounded to 2 decimal places."""
        holdings = [
            Holding(
                account_id="acc_1",
                security=sample_securities[0],
                quantity=Decimal("3"),
                institution_price=Decimal("33.333333"),
                institution_value=Decimal("99.999999"),
                cost_basis=Decimal("90.123456"),
                currency="USD",
            )
        ]

        metrics = provider.calculate_portfolio_metrics(holdings)

        assert metrics["total_value"] == pytest.approx(100.0, abs=0.01)  # Rounded
        assert metrics["total_cost_basis"] == pytest.approx(90.12, abs=0.01)  # Rounded
        assert metrics["total_unrealized_gain_loss"] == pytest.approx(9.88, abs=0.01)  # Rounded
        # (9.876543 / 90.123456) * 100 = 10.95967... → 10.96
        assert metrics["total_unrealized_gain_loss_percent"] == pytest.approx(10.96, abs=0.01)


# Tests for _normalize_security_type()


class TestNormalizeSecurityType:
    """Tests for _normalize_security_type() helper method."""

    def test_normalize_plaid_types(self, provider: MockInvestmentProvider):
        """Test normalization of Plaid security types."""
        assert provider._normalize_security_type("equity") == SecurityType.equity
        assert provider._normalize_security_type("etf") == SecurityType.etf
        assert provider._normalize_security_type("mutual fund") == SecurityType.mutual_fund
        assert provider._normalize_security_type("bond") == SecurityType.bond
        assert provider._normalize_security_type("cash") == SecurityType.cash
        assert provider._normalize_security_type("derivative") == SecurityType.derivative

    def test_normalize_snaptrade_types(self, provider: MockInvestmentProvider):
        """Test normalization of SnapTrade security types (abbreviations)."""
        assert provider._normalize_security_type("cs") == SecurityType.equity  # common stock
        assert provider._normalize_security_type("mf") == SecurityType.mutual_fund
        assert provider._normalize_security_type("o") == SecurityType.derivative  # option

    def test_normalize_case_insensitive(self, provider: MockInvestmentProvider):
        """Test that normalization is case-insensitive."""
        assert provider._normalize_security_type("EQUITY") == SecurityType.equity
        assert provider._normalize_security_type("Equity") == SecurityType.equity
        assert provider._normalize_security_type("EqUiTy") == SecurityType.equity

    def test_normalize_with_whitespace(self, provider: MockInvestmentProvider):
        """Test that normalization handles whitespace."""
        assert provider._normalize_security_type("  equity  ") == SecurityType.equity
        assert provider._normalize_security_type("mutual fund") == SecurityType.mutual_fund

    def test_normalize_unknown_type(self, provider: MockInvestmentProvider):
        """Test that unknown types default to SecurityType.other."""
        assert provider._normalize_security_type("unknown") == SecurityType.other
        assert provider._normalize_security_type("xyz") == SecurityType.other
        assert provider._normalize_security_type("") == SecurityType.other

    def test_normalize_explicit_other(self, provider: MockInvestmentProvider):
        """Test explicit 'other' type."""
        assert provider._normalize_security_type("other") == SecurityType.other


# Tests for abstract methods (ensure they raise NotImplementedError)


class TestAbstractMethods:
    """Tests to verify abstract methods are properly defined."""

    @pytest.mark.asyncio
    async def test_abstract_methods_not_callable(self):
        """Test that abstract base class cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            InvestmentProvider()  # type: ignore


# Integration test combining multiple helper methods


class TestIntegration:
    """Integration tests using multiple helper methods together."""

    def test_full_portfolio_analysis(
        self, provider: MockInvestmentProvider, sample_holdings: List[Holding]
    ):
        """Test complete portfolio analysis using all helper methods."""
        # Calculate allocation
        allocation = provider.calculate_allocation(sample_holdings)

        # Calculate metrics
        metrics = provider.calculate_portfolio_metrics(sample_holdings)

        # Verify allocation percentages add up correctly
        total_allocation = sum(allocation.by_security_type.values()) + allocation.cash_percent
        assert abs(total_allocation - 100.0) < 0.01  # Allow for rounding

        # Verify metrics are consistent with allocation
        assert metrics["total_value"] == 6000.0
        assert allocation.cash_percent == (645 / 6000) * 100  # 10.75%

    def test_normalize_securities_in_holdings(
        self, provider: MockInvestmentProvider, sample_securities: List[Security]
    ):
        """Test normalizing security types for holdings from different providers."""
        provider_types = ["equity", "EQUITY", "cs", "  equity  "]

        for provider_type in provider_types:
            normalized = provider._normalize_security_type(provider_type)
            assert normalized == SecurityType.equity
