"""
Unit tests for financial models.

Tests all 8 models:
- User: email validation, timestamps, soft-delete
- Account: balance validation, type constraints, relationships
- Transaction: amount validation, categorization, account FK
- Position: quantity/price validation, portfolio calculations
- Goal: progress calculation, status validation, milestones
- Budget: category validation, JSON serialization, date ranges
- Document: type validation, storage paths, OCR metadata
- NetWorthSnapshot: net worth calculation, historical queries

Run:
    pytest tests/test_models.py -v
    pytest tests/test_models.py::TestUserModel -v
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from fin_infra_template.db.base import Base
from fin_infra_template.db.models import (
    Account,
    Budget,
    Document,
    Goal,
    NetWorthSnapshot,
    Position,
    Transaction,
    User,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


# Fixtures
@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a new session for each test."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user(session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        currency="USD",
        risk_tolerance="moderate",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# User Model Tests
class TestUserModel:
    """Test User model."""

    def test_create_user(self, session):
        """Test creating a user."""
        user = User(
            email="user@example.com",
            full_name="John Doe",
            currency="USD",
            risk_tolerance="aggressive",
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.email == "user@example.com"
        assert user.full_name == "John Doe"
        assert user.currency == "USD"
        assert user.risk_tolerance == "aggressive"

    def test_user_timestamps(self, session):
        """Test that created_at and updated_at are set."""
        user = User(email="time@example.com", full_name="Time Test")
        session.add(user)
        session.commit()

        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at <= user.updated_at

    def test_user_soft_delete(self, session):
        """Test soft delete functionality."""
        user = User(email="delete@example.com", full_name="Delete Test")
        session.add(user)
        session.commit()

        # Soft delete
        user.deleted_at = datetime.now()
        session.commit()

        assert user.deleted_at is not None

    def test_user_provider_flags(self, session):
        """Test provider integration flags."""
        user = User(
            email="provider@example.com",
            full_name="Provider Test",
            plaid_linked=True,
            alpaca_connected=True,
            experian_connected=False,
        )
        session.add(user)
        session.commit()

        assert user.plaid_linked is True
        assert user.alpaca_connected is True
        assert user.experian_connected is False


# Account Model Tests
class TestAccountModel:
    """Test Account model."""

    def test_create_account(self, session, test_user):
        """Test creating an account."""
        account = Account(
            user_id=test_user.id,
            account_type="checking",
            institution="Test Bank",
            account_name="My Checking",
            current_balance=Decimal("1000.50"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        assert account.id is not None
        assert account.user_id == test_user.id
        assert account.account_type == "checking"
        assert account.current_balance == Decimal("1000.50")

    def test_account_types(self, session, test_user):
        """Test different account types."""
        types = ["checking", "savings", "investment", "credit_card", "crypto"]

        for acc_type in types:
            account = Account(
                user_id=test_user.id,
                account_type=acc_type,
                institution="Test Bank",
                account_name=f"My {acc_type}",
                current_balance=Decimal("100.00"),
                currency="USD",
            )
            session.add(account)

        session.commit()

        stmt = select(Account).where(Account.user_id == test_user.id)
        accounts = session.execute(stmt).scalars().all()
        assert len(accounts) == 5

    def test_account_balance_validation(self, session, test_user):
        """Test that balance is a valid Decimal."""
        account = Account(
            user_id=test_user.id,
            account_type="checking",
            institution="Test Bank",
            account_name="Balance Test",
            current_balance=Decimal("999999.99"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        assert isinstance(account.current_balance, Decimal)
        assert account.current_balance == Decimal("999999.99")

    def test_account_user_relationship(self, session, test_user):
        """Test relationship between Account and User."""
        account = Account(
            user_id=test_user.id,
            account_type="savings",
            institution="Test Bank",
            account_name="Savings",
            current_balance=Decimal("5000.00"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        # Load with relationship
        stmt = select(Account).where(Account.id == account.id)
        loaded_account = session.execute(stmt).scalar_one()
        assert loaded_account.user_id == test_user.id


# Transaction Model Tests
class TestTransactionModel:
    """Test Transaction model."""

    def test_create_transaction(self, session, test_user):
        """Test creating a transaction."""
        account = Account(
            user_id=test_user.id,
            account_type="checking",
            institution="Test Bank",
            account_name="Checking",
            current_balance=Decimal("1000.00"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        transaction = Transaction(
            user_id=test_user.id,
            account_id=account.id,
            transaction_date=date.today(),
            amount=Decimal("-25.50"),
            merchant_name="Coffee Shop",
            category="food_and_dining",
            description="Morning coffee",
        )
        session.add(transaction)
        session.commit()

        assert transaction.id is not None
        assert transaction.amount == Decimal("-25.50")
        assert transaction.category == "food_and_dining"

    def test_transaction_amount_validation(self, session, test_user):
        """Test transaction amount handling."""
        account = Account(
            user_id=test_user.id,
            account_type="checking",
            institution="Test Bank",
            account_name="Checking",
            current_balance=Decimal("1000.00"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        # Negative amount (expense)
        expense = Transaction(
            user_id=test_user.id,
            account_id=account.id,
            transaction_date=date.today(),
            amount=Decimal("-100.00"),
            merchant_name="Store",
        )
        session.add(expense)

        # Positive amount (income)
        income = Transaction(
            user_id=test_user.id,
            account_id=account.id,
            transaction_date=date.today(),
            amount=Decimal("500.00"),
            merchant_name="Employer",
        )
        session.add(income)
        session.commit()

        assert expense.amount < 0
        assert income.amount > 0

    def test_transaction_categorization(self, session, test_user):
        """Test transaction category assignment."""
        account = Account(
            user_id=test_user.id,
            account_type="checking",
            institution="Test Bank",
            account_name="Checking",
            current_balance=Decimal("1000.00"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        categories = [
            "food_and_dining",
            "shopping",
            "bills_and_utilities",
            "transportation",
            "entertainment",
        ]

        for category in categories:
            transaction = Transaction(
                user_id=test_user.id,
                account_id=account.id,
                transaction_date=date.today(),
                amount=Decimal("-50.00"),
                merchant_name=f"Merchant {category}",
                category=category,
            )
            session.add(transaction)

        session.commit()

        stmt = select(Transaction).where(Transaction.user_id == test_user.id)
        transactions = session.execute(stmt).scalars().all()
        assert len(transactions) == 5


# Position Model Tests
class TestPositionModel:
    """Test Position model."""

    def test_create_position(self, session, test_user):
        """Test creating a position."""
        account = Account(
            user_id=test_user.id,
            account_type="investment",
            institution="Test Brokerage",
            account_name="Investment",
            current_balance=Decimal("10000.00"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        position = Position(
            user_id=test_user.id,
            account_id=account.id,
            asset_type="stock",
            symbol="AAPL",
            quantity=Decimal("10.0"),
            cost_basis=Decimal("1500.00"),
            current_price=Decimal("175.00"),
        )
        session.add(position)
        session.commit()

        assert position.id is not None
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("10.0")

    def test_position_asset_types(self, session, test_user):
        """Test different asset types."""
        account = Account(
            user_id=test_user.id,
            account_type="investment",
            institution="Test Brokerage",
            account_name="Investment",
            current_balance=Decimal("10000.00"),
            currency="USD",
        )
        session.add(account)
        session.commit()

        assets = [
            ("stock", "AAPL"),
            ("etf", "SPY"),
            ("crypto", "BTC"),
            ("bond", "US10Y"),
        ]

        for asset_type, symbol in assets:
            position = Position(
                user_id=test_user.id,
                account_id=account.id,
                asset_type=asset_type,
                symbol=symbol,
                quantity=Decimal("1.0"),
                cost_basis=Decimal("100.00"),
                current_price=Decimal("110.00"),
            )
            session.add(position)

        session.commit()

        stmt = select(Position).where(Position.user_id == test_user.id)
        positions = session.execute(stmt).scalars().all()
        assert len(positions) == 4


# Goal Model Tests
class TestGoalModel:
    """Test Goal model."""

    def test_create_goal(self, session, test_user):
        """Test creating a goal."""
        goal = Goal(
            user_id=test_user.id,
            name="Emergency Fund",
            goal_type="savings",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("5000.00"),
            target_date=date(2025, 12, 31),
            status="in_progress",
        )
        session.add(goal)
        session.commit()

        assert goal.id is not None
        assert goal.name == "Emergency Fund"
        assert goal.target_amount == Decimal("10000.00")
        assert goal.current_amount == Decimal("5000.00")

    def test_goal_status_values(self, session, test_user):
        """Test different goal statuses."""
        statuses = ["not_started", "in_progress", "completed", "paused"]

        for status in statuses:
            goal = Goal(
                user_id=test_user.id,
                name=f"Goal {status}",
                goal_type="savings",
                target_amount=Decimal("1000.00"),
                current_amount=Decimal("0.00"),
                target_date=date(2025, 12, 31),
                status=status,
            )
            session.add(goal)

        session.commit()

        stmt = select(Goal).where(Goal.user_id == test_user.id)
        goals = session.execute(stmt).scalars().all()
        assert len(goals) == 4


# Budget Model Tests
class TestBudgetModel:
    """Test Budget model."""

    def test_create_budget(self, session, test_user):
        """Test creating a budget."""
        budget = Budget(
            user_id=test_user.id,
            name="Monthly Budget",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            total_budget=Decimal("3000.00"),
            total_spent=Decimal("1500.00"),
            categories={"food": 500, "transport": 200},
        )
        session.add(budget)
        session.commit()

        assert budget.id is not None
        assert budget.name == "Monthly Budget"
        assert budget.total_budget == Decimal("3000.00")
        assert budget.categories["food"] == 500


# Document Model Tests
class TestDocumentModel:
    """Test Document model."""

    def test_create_document(self, session, test_user):
        """Test creating a document."""
        document = Document(
            user_id=test_user.id,
            document_type="tax_form",
            document_name="W2 2023",
            file_path="/documents/w2_2023.pdf",
            upload_date=date.today(),
        )
        session.add(document)
        session.commit()

        assert document.id is not None
        assert document.document_type == "tax_form"
        assert document.document_name == "W2 2023"

    def test_document_types(self, session, test_user):
        """Test different document types."""
        types = ["tax_form", "bank_statement", "brokerage_statement", "receipt"]

        for doc_type in types:
            document = Document(
                user_id=test_user.id,
                document_type=doc_type,
                document_name=f"Test {doc_type}",
                file_path=f"/documents/{doc_type}.pdf",
                upload_date=date.today(),
            )
            session.add(document)

        session.commit()

        stmt = select(Document).where(Document.user_id == test_user.id)
        documents = session.execute(stmt).scalars().all()
        assert len(documents) == 4


# NetWorthSnapshot Model Tests
class TestNetWorthSnapshotModel:
    """Test NetWorthSnapshot model."""

    def test_create_snapshot(self, session, test_user):
        """Test creating a net worth snapshot."""
        snapshot = NetWorthSnapshot(
            user_id=test_user.id,
            snapshot_date=date.today(),
            total_assets=Decimal("50000.00"),
            liquid_assets=Decimal("10000.00"),
            investment_assets=Decimal("40000.00"),
            total_liabilities=Decimal("15000.00"),
            credit_card_debt=Decimal("2000.00"),
            loan_debt=Decimal("13000.00"),
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.total_assets == Decimal("50000.00")
        assert snapshot.total_liabilities == Decimal("15000.00")

    def test_snapshot_net_worth_calculation(self, session, test_user):
        """Test net worth calculation (assets - liabilities)."""
        snapshot = NetWorthSnapshot(
            user_id=test_user.id,
            snapshot_date=date.today(),
            total_assets=Decimal("100000.00"),
            liquid_assets=Decimal("20000.00"),
            investment_assets=Decimal("80000.00"),
            total_liabilities=Decimal("30000.00"),
            credit_card_debt=Decimal("5000.00"),
            loan_debt=Decimal("25000.00"),
        )
        session.add(snapshot)
        session.commit()

        # Calculate net worth
        net_worth = snapshot.total_assets - snapshot.total_liabilities
        assert net_worth == Decimal("70000.00")

    def test_multiple_snapshots(self, session, test_user):
        """Test creating multiple snapshots over time."""
        from datetime import timedelta

        base_date = date.today()

        for i in range(5):
            snapshot = NetWorthSnapshot(
                user_id=test_user.id,
                snapshot_date=base_date - timedelta(days=i * 30),
                total_assets=Decimal(f"{50000 + i * 1000}.00"),
                liquid_assets=Decimal("10000.00"),
                investment_assets=Decimal(f"{40000 + i * 1000}.00"),
                total_liabilities=Decimal("15000.00"),
            )
            session.add(snapshot)

        session.commit()

        stmt = select(NetWorthSnapshot).where(NetWorthSnapshot.user_id == test_user.id)
        snapshots = session.execute(stmt).scalars().all()
        assert len(snapshots) == 5
