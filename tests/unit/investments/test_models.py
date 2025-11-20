"""Unit tests for investment models."""

import pytest
from datetime import date
from decimal import Decimal

from fin_infra.investments.models import (
    AssetAllocation,
    Holding,
    InvestmentAccount,
    InvestmentTransaction,
    Security,
    SecurityType,
    TransactionType,
)


class TestSecurityType:
    """Test SecurityType enum."""

    def test_security_type_values(self):
        """Test all security type enum values."""
        assert SecurityType.equity.value == "equity"
        assert SecurityType.etf.value == "etf"
        assert SecurityType.mutual_fund.value == "mutual_fund"
        assert SecurityType.bond.value == "bond"
        assert SecurityType.cash.value == "cash"
        assert SecurityType.derivative.value == "derivative"
        assert SecurityType.other.value == "other"

    def test_security_type_string_conversion(self):
        """Test SecurityType can be compared as string."""
        assert SecurityType.equity == "equity"
        assert SecurityType.equity.value == "equity"


class TestTransactionType:
    """Test TransactionType enum."""

    def test_transaction_type_values(self):
        """Test all transaction type enum values."""
        assert TransactionType.buy.value == "buy"
        assert TransactionType.sell.value == "sell"
        assert TransactionType.dividend.value == "dividend"
        assert TransactionType.interest.value == "interest"
        assert TransactionType.fee.value == "fee"
        assert TransactionType.tax.value == "tax"
        assert TransactionType.transfer.value == "transfer"
        assert TransactionType.split.value == "split"
        assert TransactionType.merger.value == "merger"
        assert TransactionType.cancel.value == "cancel"
        assert TransactionType.other.value == "other"


class TestSecurity:
    """Test Security model."""

    def test_security_creation(self):
        """Test creating a security with all fields."""
        security = Security(
            security_id="sec_123",
            cusip="037833100",
            isin="US0378331005",
            sedol="2046251",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
            sector="Technology",
            close_price=Decimal("150.25"),
            close_price_as_of=date(2025, 11, 19),
            exchange="NASDAQ",
            currency="USD",
        )

        assert security.security_id == "sec_123"
        assert security.cusip == "037833100"
        assert security.isin == "US0378331005"
        assert security.ticker_symbol == "AAPL"
        assert security.name == "Apple Inc."
        assert security.type == SecurityType.equity
        assert security.sector == "Technology"
        assert security.close_price == Decimal("150.25")
        assert security.close_price_as_of == date(2025, 11, 19)
        assert security.exchange == "NASDAQ"
        assert security.currency == "USD"

    def test_security_minimal_fields(self):
        """Test creating security with minimal required fields."""
        security = Security(
            security_id="sec_456",
            name="Tesla Inc.",
            type=SecurityType.equity,
        )

        assert security.security_id == "sec_456"
        assert security.name == "Tesla Inc."
        assert security.type == SecurityType.equity
        assert security.cusip is None
        assert security.ticker_symbol is None
        assert security.currency == "USD"  # Default

    def test_security_negative_price_validation(self):
        """Test that negative prices are rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            Security(
                security_id="sec_789",
                name="Invalid Security",
                type=SecurityType.equity,
                close_price=Decimal("-10.00"),
            )


class TestHolding:
    """Test Holding model."""

    @pytest.fixture
    def sample_security(self):
        """Sample security for testing."""
        return Security(
            security_id="sec_123",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
            close_price=Decimal("150.25"),
            currency="USD",
        )

    def test_holding_creation(self, sample_security):
        """Test creating a holding with all fields."""
        holding = Holding(
            account_id="acct_123",
            security=sample_security,
            quantity=Decimal("10.5"),
            institution_price=Decimal("150.25"),
            institution_value=Decimal("1577.63"),
            cost_basis=Decimal("1522.50"),
            currency="USD",
            as_of_date=date(2025, 11, 19),
        )

        assert holding.account_id == "acct_123"
        assert holding.security.ticker_symbol == "AAPL"
        assert holding.quantity == Decimal("10.5")
        assert holding.institution_price == Decimal("150.25")
        assert holding.institution_value == Decimal("1577.63")
        assert holding.cost_basis == Decimal("1522.50")

    def test_holding_unrealized_gain_loss(self, sample_security):
        """Test unrealized gain/loss calculation."""
        holding = Holding(
            account_id="acct_123",
            security=sample_security,
            quantity=Decimal("10"),
            institution_price=Decimal("150.00"),
            institution_value=Decimal("1500.00"),
            cost_basis=Decimal("1400.00"),
            currency="USD",
        )

        assert holding.unrealized_gain_loss == Decimal("100.00")
        assert holding.unrealized_gain_loss_percent == Decimal("7.14")

    def test_holding_unrealized_loss(self, sample_security):
        """Test unrealized loss calculation."""
        holding = Holding(
            account_id="acct_123",
            security=sample_security,
            quantity=Decimal("10"),
            institution_price=Decimal("140.00"),
            institution_value=Decimal("1400.00"),
            cost_basis=Decimal("1500.00"),
            currency="USD",
        )

        assert holding.unrealized_gain_loss == Decimal("-100.00")
        assert holding.unrealized_gain_loss_percent == Decimal("-6.67")

    def test_holding_no_cost_basis(self, sample_security):
        """Test holding without cost basis."""
        holding = Holding(
            account_id="acct_123",
            security=sample_security,
            quantity=Decimal("10"),
            institution_price=Decimal("150.00"),
            institution_value=Decimal("1500.00"),
            cost_basis=None,
            currency="USD",
        )

        assert holding.unrealized_gain_loss is None
        assert holding.unrealized_gain_loss_percent is None

    def test_holding_negative_quantity_validation(self, sample_security):
        """Test that negative quantity is rejected."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            Holding(
                account_id="acct_123",
                security=sample_security,
                quantity=Decimal("-10"),
                institution_price=Decimal("150.00"),
                institution_value=Decimal("1500.00"),
                currency="USD",
            )


class TestInvestmentTransaction:
    """Test InvestmentTransaction model."""

    @pytest.fixture
    def sample_security(self):
        """Sample security for testing."""
        return Security(
            security_id="sec_123",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
        )

    def test_transaction_buy(self, sample_security):
        """Test buy transaction."""
        transaction = InvestmentTransaction(
            transaction_id="tx_123",
            account_id="acct_456",
            security=sample_security,
            transaction_date=date(2025, 11, 15),
            name="AAPL BUY",
            transaction_type=TransactionType.buy,
            quantity=Decimal("10"),
            amount=Decimal("-1500.00"),
            price=Decimal("150.00"),
            fees=Decimal("0.00"),
            currency="USD",
        )

        assert transaction.transaction_id == "tx_123"
        assert transaction.transaction_type == TransactionType.buy
        assert transaction.quantity == Decimal("10")
        assert transaction.amount == Decimal("-1500.00")  # Negative for purchase
        assert transaction.price == Decimal("150.00")

    def test_transaction_sell(self, sample_security):
        """Test sell transaction."""
        transaction = InvestmentTransaction(
            transaction_id="tx_456",
            account_id="acct_456",
            security=sample_security,
            transaction_date=date(2025, 11, 16),
            name="AAPL SELL",
            transaction_type=TransactionType.sell,
            quantity=Decimal("5"),
            amount=Decimal("755.00"),
            price=Decimal("151.00"),
            fees=Decimal("5.00"),
            currency="USD",
        )

        assert transaction.transaction_type == TransactionType.sell
        assert transaction.quantity == Decimal("5")
        assert transaction.amount == Decimal("755.00")  # Positive for sale
        assert transaction.fees == Decimal("5.00")

    def test_transaction_dividend(self, sample_security):
        """Test dividend transaction."""
        transaction = InvestmentTransaction(
            transaction_id="tx_789",
            account_id="acct_456",
            security=sample_security,
            transaction_date=date(2025, 11, 17),
            name="AAPL DIVIDEND",
            transaction_type=TransactionType.dividend,
            quantity=Decimal("0"),  # No shares involved
            amount=Decimal("23.50"),
            price=None,
            fees=None,
            currency="USD",
        )

        assert transaction.transaction_type == TransactionType.dividend
        assert transaction.quantity == Decimal("0")
        assert transaction.amount == Decimal("23.50")
        assert transaction.price is None


class TestInvestmentAccount:
    """Test InvestmentAccount model."""

    @pytest.fixture
    def sample_holdings(self):
        """Sample holdings for testing."""
        security1 = Security(
            security_id="sec_1",
            ticker_symbol="AAPL",
            name="Apple Inc.",
            type=SecurityType.equity,
        )
        security2 = Security(
            security_id="sec_2",
            ticker_symbol="GOOGL",
            name="Alphabet Inc.",
            type=SecurityType.equity,
        )

        return [
            Holding(
                account_id="acct_123",
                security=security1,
                quantity=Decimal("10"),
                institution_price=Decimal("150.00"),
                institution_value=Decimal("1500.00"),
                cost_basis=Decimal("1400.00"),
                currency="USD",
            ),
            Holding(
                account_id="acct_123",
                security=security2,
                quantity=Decimal("5"),
                institution_price=Decimal("140.00"),
                institution_value=Decimal("700.00"),
                cost_basis=Decimal("650.00"),
                currency="USD",
            ),
        ]

    def test_account_creation(self, sample_holdings):
        """Test creating an investment account."""
        account = InvestmentAccount(
            account_id="acct_123",
            name="Fidelity 401k",
            type="investment",
            subtype="401k",
            balances={"current": Decimal("500.00"), "available": Decimal("500.00")},
            holdings=sample_holdings,
        )

        assert account.account_id == "acct_123"
        assert account.name == "Fidelity 401k"
        assert account.subtype == "401k"
        assert len(account.holdings) == 2

    def test_account_total_value(self, sample_holdings):
        """Test total value calculation."""
        account = InvestmentAccount(
            account_id="acct_123",
            name="Test Account",
            type="investment",
            balances={"current": Decimal("500.00")},
            holdings=sample_holdings,
        )

        # Holdings: 1500 + 700 = 2200, Cash: 500, Total: 2700
        assert account.total_value == Decimal("2700.00")

    def test_account_total_cost_basis(self, sample_holdings):
        """Test total cost basis calculation."""
        account = InvestmentAccount(
            account_id="acct_123",
            name="Test Account",
            type="investment",
            balances={"current": Decimal("0")},
            holdings=sample_holdings,
        )

        # Cost basis: 1400 + 650 = 2050
        assert account.total_cost_basis == Decimal("2050.00")

    def test_account_total_unrealized_gain_loss(self, sample_holdings):
        """Test total unrealized P&L calculation."""
        account = InvestmentAccount(
            account_id="acct_123",
            name="Test Account",
            type="investment",
            balances={"current": Decimal("0")},
            holdings=sample_holdings,
        )

        # Value: 2200, Cost: 2050, Gain: 150
        assert account.total_unrealized_gain_loss == Decimal("150.00")

    def test_account_total_unrealized_gain_loss_percent(self, sample_holdings):
        """Test total unrealized P&L percentage calculation."""
        account = InvestmentAccount(
            account_id="acct_123",
            name="Test Account",
            type="investment",
            balances={"current": Decimal("0")},
            holdings=sample_holdings,
        )

        # (150 / 2050) * 100 = 7.32%
        assert account.total_unrealized_gain_loss_percent == Decimal("7.32")

    def test_account_empty_holdings(self):
        """Test account with no holdings."""
        account = InvestmentAccount(
            account_id="acct_123",
            name="Empty Account",
            type="investment",
            balances={"current": Decimal("1000.00")},
            holdings=[],
        )

        assert account.total_value == Decimal("1000.00")
        assert account.total_cost_basis == Decimal("0")
        assert account.total_unrealized_gain_loss == Decimal("0")
        assert account.total_unrealized_gain_loss_percent is None


class TestAssetAllocation:
    """Test AssetAllocation model."""

    def test_allocation_creation(self):
        """Test creating asset allocation."""
        allocation = AssetAllocation(
            by_security_type={
                SecurityType.equity: 65.0,
                SecurityType.etf: 20.0,
                SecurityType.bond: 10.0,
            },
            by_sector={
                "Technology": 40.0,
                "Healthcare": 25.0,
                "Financials": 20.0,
                "Other": 15.0,
            },
            cash_percent=5.0,
        )

        assert allocation.by_security_type[SecurityType.equity] == 65.0
        assert allocation.by_sector["Technology"] == 40.0
        assert allocation.cash_percent == 5.0

    def test_allocation_empty(self):
        """Test empty allocation."""
        allocation = AssetAllocation(
            by_security_type={},
            by_sector={},
            cash_percent=0.0,
        )

        assert len(allocation.by_security_type) == 0
        assert len(allocation.by_sector) == 0
        assert allocation.cash_percent == 0.0

    def test_allocation_cash_percent_validation(self):
        """Test cash_percent validation (0-100)."""
        # Valid: 0%
        allocation1 = AssetAllocation(cash_percent=0.0)
        assert allocation1.cash_percent == 0.0

        # Valid: 100%
        allocation2 = AssetAllocation(cash_percent=100.0)
        assert allocation2.cash_percent == 100.0

        # Invalid: negative
        with pytest.raises(Exception):  # Pydantic ValidationError
            AssetAllocation(cash_percent=-5.0)

        # Invalid: over 100
        with pytest.raises(Exception):  # Pydantic ValidationError
            AssetAllocation(cash_percent=105.0)
