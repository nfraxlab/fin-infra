"""
Comprehensive tests for financial data models.

Tests validation, serialization, and edge cases for all financial models.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from fin_infra.models import Account, AccountType, Candle, Money, Quote, Transaction


class TestAccountModel:
    """Tests for Account model."""

    def test_account_creation_minimal(self):
        """Test creating account with minimal required fields."""
        account = Account(id="acc_123", name="Checking", type=AccountType.checking)
        assert account.id == "acc_123"
        assert account.name == "Checking"
        assert account.type == AccountType.checking
        assert account.currency == "USD"  # default

    def test_account_creation_full(self):
        """Test creating account with all fields."""
        account = Account(
            id="acc_456",
            name="Savings",
            type=AccountType.savings,
            mask="1234",
            currency="EUR",
            institution="Chase",
            balance_available=5000.50,
            balance_current=5100.75,
        )
        assert account.id == "acc_456"
        assert account.mask == "1234"
        assert account.currency == "EUR"
        assert account.institution == "Chase"
        assert account.balance_available == 5000.50
        assert account.balance_current == 5100.75

    def test_account_all_types(self):
        """Test all account types are valid."""
        for account_type in AccountType:
            account = Account(id=f"acc_{account_type.value}", name="Test", type=account_type)
            assert account.type == account_type

    def test_account_serialization(self):
        """Test account JSON serialization."""
        account = Account(
            id="acc_789",
            name="Investment",
            type=AccountType.investment,
            balance_current=10000.0,
        )
        data = account.model_dump()
        assert data["id"] == "acc_789"
        assert data["type"] == "investment"
        assert data["balance_current"] == 10000.0

    def test_account_deserialization(self):
        """Test account creation from dict."""
        data = {
            "id": "acc_999",
            "name": "Credit Card",
            "type": "credit",
            "mask": "5678",
            "balance_current": -500.0,
        }
        account = Account(**data)
        assert account.id == "acc_999"
        assert account.type == AccountType.credit
        assert account.balance_current == -500.0

    def test_account_missing_required_fields(self):
        """Test account creation fails without required fields."""
        with pytest.raises(ValidationError):
            Account(name="Test")  # missing id and type

        with pytest.raises(ValidationError):
            Account(id="acc_1")  # missing name and type


class TestTransactionModel:
    """Tests for Transaction model."""

    def test_transaction_creation_minimal(self):
        """Test creating transaction with minimal required fields."""
        txn = Transaction(
            id="txn_123",
            account_id="acc_456",
            date=date(2025, 11, 4),
            amount=50.25,
        )
        assert txn.id == "txn_123"
        assert txn.account_id == "acc_456"
        assert txn.date == date(2025, 11, 4)
        assert txn.amount == 50.25
        assert txn.currency == "USD"  # default

    def test_transaction_creation_full(self):
        """Test creating transaction with all fields."""
        txn = Transaction(
            id="txn_789",
            account_id="acc_999",
            date=date(2025, 11, 3),
            amount=-120.50,
            currency="GBP",
            description="Amazon purchase",
            category="Shopping",
        )
        assert txn.id == "txn_789"
        assert txn.amount == -120.50
        assert txn.currency == "GBP"
        assert txn.description == "Amazon purchase"
        assert txn.category == "Shopping"

    def test_transaction_negative_amounts(self):
        """Test transactions support negative amounts (debits)."""
        debit = Transaction(id="txn_d1", account_id="acc_1", date=date.today(), amount=-100.0)
        credit = Transaction(id="txn_c1", account_id="acc_1", date=date.today(), amount=100.0)
        assert debit.amount < 0
        assert credit.amount > 0

    def test_transaction_serialization(self):
        """Test transaction JSON serialization."""
        txn = Transaction(
            id="txn_serial",
            account_id="acc_serial",
            date=date(2025, 11, 4),
            amount=75.99,
            description="Test transaction",
        )
        data = txn.model_dump()
        assert data["id"] == "txn_serial"
        assert data["amount"] == 75.99
        assert data["date"] == date(2025, 11, 4)

    def test_transaction_missing_required_fields(self):
        """Test transaction creation fails without required fields."""
        with pytest.raises(ValidationError):
            Transaction(account_id="acc_1", date=date.today(), amount=10.0)  # missing id

        with pytest.raises(ValidationError):
            Transaction(id="txn_1", date=date.today(), amount=10.0)  # missing account_id


class TestQuoteModel:
    """Tests for Quote model."""

    def test_quote_creation(self):
        """Test creating quote."""
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.25"),
            currency="USD",
            as_of=datetime(2025, 11, 4, 10, 30, 0),
        )
        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.25")
        assert quote.currency == "USD"
        assert quote.as_of.year == 2025

    def test_quote_serialization(self):
        """Test quote JSON serialization."""
        quote = Quote(
            symbol="TSLA",
            price=Decimal("250.50"),
            currency="USD",
            as_of=datetime(2025, 11, 4, 15, 0, 0),
        )
        data = quote.model_dump()
        assert data["symbol"] == "TSLA"
        assert data["price"] == Decimal("250.50")


class TestCandleModel:
    """Tests for Candle model."""

    def test_candle_creation(self):
        """Test creating candle."""
        # Epoch milliseconds for November 4, 2025 12:00:00 UTC
        ts = int(datetime(2025, 11, 4, 12, 0, 0).timestamp() * 1000)
        candle = Candle(
            ts=ts,
            open=Decimal("50000.0"),
            high=Decimal("51000.0"),
            low=Decimal("49500.0"),
            close=Decimal("50500.0"),
            volume=Decimal("1234.56"),
        )
        assert candle.ts == ts
        assert candle.open == Decimal("50000.0")
        assert candle.high == Decimal("51000.0")
        assert candle.low == Decimal("49500.0")
        assert candle.close == Decimal("50500.0")
        assert candle.volume == Decimal("1234.56")

    def test_candle_ohlc_consistency(self):
        """Test candle OHLC values are logically consistent."""
        # High should be >= low
        ts = int(datetime.now().timestamp() * 1000)
        candle = Candle(
            ts=ts,
            open=Decimal("2000.0"),
            high=Decimal("2100.0"),
            low=Decimal("1900.0"),
            close=Decimal("2050.0"),
            volume=Decimal("100.0"),
        )
        assert candle.high >= candle.low
        assert candle.high >= candle.open
        assert candle.high >= candle.close


class TestMoneyModel:
    """Tests for Money model."""

    def test_money_creation(self):
        """Test creating money object."""
        money = Money(amount=100.50, currency="USD")
        assert money.amount == 100.50
        assert money.currency == "USD"

    def test_money_different_currencies(self):
        """Test money with various currencies."""
        currencies = ["USD", "EUR", "GBP", "JPY", "BTC"]
        for curr in currencies:
            money = Money(amount=100.0, currency=curr)
            assert money.currency == curr

    def test_money_serialization(self):
        """Test money JSON serialization."""
        money = Money(amount=500.75, currency="EUR")
        data = money.model_dump()
        assert data["amount"] == 500.75
        assert data["currency"] == "EUR"


class TestModelIntegration:
    """Integration tests across multiple models."""

    def test_account_with_transactions(self):
        """Test account and transaction models work together."""
        account = Account(
            id="acc_main",
            name="Main Checking",
            type=AccountType.checking,
            balance_current=1000.0,
        )

        txn1 = Transaction(
            id="txn_1",
            account_id=account.id,
            date=date.today(),
            amount=-50.0,
            description="Coffee",
        )

        txn2 = Transaction(
            id="txn_2",
            account_id=account.id,
            date=date.today(),
            amount=500.0,
            description="Paycheck",
        )

        # Verify they reference same account
        assert txn1.account_id == account.id
        assert txn2.account_id == account.id

    def test_quote_and_candle_integration(self):
        """Test quote and candle models can coexist."""
        symbol = "AAPL"
        timestamp = datetime(2025, 11, 4, 14, 0, 0)
        ts_ms = int(timestamp.timestamp() * 1000)

        quote = Quote(symbol=symbol, price=Decimal("150.0"), currency="USD", as_of=timestamp)

        candle = Candle(
            ts=ts_ms,
            open=Decimal("149.5"),
            high=Decimal("151.0"),
            low=Decimal("149.0"),
            close=Decimal("150.0"),
            volume=Decimal("1000000.0"),
        )

        # Verify both models work independently
        assert quote.symbol == symbol
        assert quote.price == Decimal("150.0")
        # Quote price should be within candle range
        assert candle.low <= quote.price <= candle.high
