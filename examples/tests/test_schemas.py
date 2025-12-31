"""Tests for Pydantic schemas.

Tests schema validation, serialization/deserialization, and field constraints
for all financial models: User, Account, Transaction, Position, Goal, Budget,
Document, NetWorthSnapshot.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fin_infra_template.db.schemas import (
    # Account schemas
    AccountBase,
    AccountCreate,
    AccountRead,
    AccountUpdate,
    # Budget schemas
    BudgetBase,
    BudgetCreate,
    BudgetUpdate,
    # Document schemas
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    # Goal schemas
    GoalBase,
    GoalCreate,
    GoalUpdate,
    # NetWorthSnapshot schemas
    NetWorthSnapshotBase,
    NetWorthSnapshotCreate,
    NetWorthSnapshotRead,
    # Position schemas
    PositionBase,
    PositionCreate,
    PositionUpdate,
    # Transaction schemas
    TransactionBase,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    # User schemas
    UserBase,
    UserCreate,
    UserRead,
    UserUpdate,
)
from pydantic import ValidationError

# ============================================================================
# User Schema Tests
# ============================================================================


class TestUserSchemas:
    """Test User schemas (Base/Create/Read/Update)."""

    def test_user_base_valid(self):
        """Test UserBase with valid data."""
        user = UserBase(
            email="test@example.com",
            full_name="Test User",
            currency="USD",
            risk_tolerance="moderate",
        )
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.currency == "USD"
        assert user.risk_tolerance == "moderate"

    def test_user_base_email_validation(self):
        """Test UserBase email validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(email="invalid-email", full_name="Test User")

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("email",) for err in errors)

    def test_user_create_inherits_base(self):
        """Test UserCreate inherits from UserBase."""
        user = UserCreate(
            email="new@example.com",
            full_name="New User",
        )
        assert user.email == "new@example.com"
        assert user.currency == "USD"  # Default value

    def test_user_update_all_optional(self):
        """Test UserUpdate allows partial updates."""
        # Empty update
        update = UserUpdate()
        assert update.email is None
        assert update.full_name is None

        # Partial update
        update = UserUpdate(email="updated@example.com")
        assert update.email == "updated@example.com"
        assert update.full_name is None

    def test_user_read_includes_metadata(self):
        """Test UserRead includes id and timestamps."""
        now = datetime.utcnow()
        user = UserRead(
            id=1,
            email="read@example.com",
            full_name="Read User",
            currency="USD",
            risk_tolerance=None,
            plaid_linked=True,
            alpaca_linked=False,
            experian_linked=False,
            created_at=now,
            updated_at=now,
        )
        assert user.id == 1
        assert user.plaid_linked is True
        assert user.created_at == now


# ============================================================================
# Account Schema Tests
# ============================================================================


class TestAccountSchemas:
    """Test Account schemas (Base/Create/Read/Update)."""

    def test_account_base_valid(self):
        """Test AccountBase with valid data."""
        account = AccountBase(
            name="My Checking",
            account_type="checking",
            provider="plaid",
            institution="Chase",
            balance=Decimal("1000.50"),
            currency="USD",
        )
        assert account.name == "My Checking"
        assert account.balance == Decimal("1000.50")
        assert isinstance(account.balance, Decimal)

    def test_account_base_default_values(self):
        """Test AccountBase default values."""
        account = AccountBase(
            name="Test Account",
            account_type="savings",
        )
        assert account.provider == "manual"
        assert account.balance == Decimal("0.00")
        assert account.currency == "USD"
        assert account.is_active is True

    def test_account_create_requires_user_id(self):
        """Test AccountCreate requires user_id."""
        account = AccountCreate(
            user_id=1,
            name="New Account",
            account_type="checking",
        )
        assert account.user_id == 1
        assert account.name == "New Account"

    def test_account_update_partial(self):
        """Test AccountUpdate allows partial updates."""
        update = AccountUpdate(balance=Decimal("2000.00"))
        assert update.balance == Decimal("2000.00")
        assert update.name is None
        assert update.account_type is None

    def test_account_read_from_orm(self):
        """Test AccountRead can deserialize from ORM."""
        now = datetime.utcnow()
        # Simulate ORM object dict
        account_data = {
            "id": 1,
            "user_id": 1,
            "name": "Test Account",
            "account_type": "checking",
            "provider": "plaid",
            "provider_account_id": "acc_123",
            "institution": "Chase",
            "account_number_last4": "1234",
            "balance": Decimal("1500.00"),
            "currency": "USD",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
        account = AccountRead(**account_data)
        assert account.id == 1
        assert account.balance == Decimal("1500.00")


# ============================================================================
# Transaction Schema Tests
# ============================================================================


class TestTransactionSchemas:
    """Test Transaction schemas (Base/Create/Read/Update)."""

    def test_transaction_base_valid(self):
        """Test TransactionBase with valid data."""
        txn = TransactionBase(
            account_id=1,
            transaction_date=date.today(),
            amount=Decimal("-25.50"),
            merchant_name="Coffee Shop",
            category="food_and_dining",
            description="Morning coffee",
        )
        assert txn.amount == Decimal("-25.50")
        assert txn.merchant_name == "Coffee Shop"
        assert isinstance(txn.transaction_date, date)

    def test_transaction_create_requires_user_id(self):
        """Test TransactionCreate requires user_id."""
        txn = TransactionCreate(
            user_id=1,
            account_id=1,
            transaction_date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Store",
        )
        assert txn.user_id == 1
        assert txn.account_id == 1

    def test_transaction_update_partial(self):
        """Test TransactionUpdate allows partial updates."""
        update = TransactionUpdate(category="shopping")
        assert update.category == "shopping"
        assert update.amount is None

    def test_transaction_read_includes_metadata(self):
        """Test TransactionRead includes timestamps."""
        now = datetime.utcnow()
        txn_data = {
            "id": 1,
            "user_id": 1,
            "account_id": 1,
            "transaction_date": date.today(),
            "amount": Decimal("-100.00"),
            "merchant_name": "Test Store",
            "category": None,
            "description": None,
            "is_recurring": False,
            "created_at": now,
            "updated_at": now,
        }
        txn = TransactionRead(**txn_data)
        assert txn.id == 1
        assert txn.created_at == now


# ============================================================================
# Position Schema Tests
# ============================================================================


class TestPositionSchemas:
    """Test Position schemas (Base/Create/Read/Update)."""

    def test_position_base_valid(self):
        """Test PositionBase with valid data."""
        position = PositionBase(
            account_id=1,
            asset_type="stock",
            symbol="AAPL",
            quantity=Decimal("10.0"),
            cost_basis=Decimal("1500.00"),
            current_price=Decimal("175.00"),
        )
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("10.0")
        assert isinstance(position.current_price, Decimal)

    def test_position_create_requires_user_id(self):
        """Test PositionCreate requires user_id."""
        position = PositionCreate(
            user_id=1,
            account_id=1,
            asset_type="etf",
            symbol="SPY",
            quantity=Decimal("5.0"),
            cost_basis=Decimal("2000.00"),
            current_price=Decimal("450.00"),
        )
        assert position.user_id == 1
        assert position.asset_type == "etf"

    def test_position_update_partial(self):
        """Test PositionUpdate allows partial updates."""
        update = PositionUpdate(
            current_price=Decimal("180.00"),
            quantity=Decimal("12.0"),
        )
        assert update.current_price == Decimal("180.00")
        assert update.quantity == Decimal("12.0")
        assert update.symbol is None


# ============================================================================
# Goal Schema Tests
# ============================================================================


class TestGoalSchemas:
    """Test Goal schemas (Base/Create/Read/Update)."""

    def test_goal_base_valid(self):
        """Test GoalBase with valid data."""
        goal = GoalBase(
            name="Emergency Fund",
            goal_type="savings",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("2500.00"),
            deadline=date.today() + timedelta(days=365),
        )
        assert goal.name == "Emergency Fund"
        assert goal.target_amount == Decimal("10000.00")
        assert goal.goal_type == "savings"

    def test_goal_base_default_current_amount(self):
        """Test GoalBase default current_amount."""
        goal = GoalBase(
            name="Vacation",
            goal_type="savings",
            target_amount=Decimal("5000.00"),
            deadline=date.today() + timedelta(days=180),
        )
        assert goal.current_amount == Decimal("0.00")

    def test_goal_create_requires_user_id(self):
        """Test GoalCreate requires user_id."""
        goal = GoalCreate(
            user_id=1,
            name="Down Payment",
            goal_type="savings",
            target_amount=Decimal("50000.00"),
            deadline=date.today() + timedelta(days=730),
        )
        assert goal.user_id == 1

    def test_goal_update_partial(self):
        """Test GoalUpdate allows partial updates."""
        update = GoalUpdate(current_amount=Decimal("3000.00"))
        assert update.current_amount == Decimal("3000.00")
        assert update.name is None


# ============================================================================
# Budget Schema Tests
# ============================================================================


class TestBudgetSchemas:
    """Test Budget schemas (Base/Create/Read/Update)."""

    def test_budget_base_valid(self):
        """Test BudgetBase with valid data."""
        budget = BudgetBase(
            name="Monthly Food Budget",
            category="food_and_dining",
            amount=Decimal("500.00"),
            period="monthly",
            start_date=date.today(),
        )
        assert budget.name == "Monthly Food Budget"
        assert budget.amount == Decimal("500.00")
        assert budget.period == "monthly"

    def test_budget_create_requires_user_id(self):
        """Test BudgetCreate requires user_id."""
        budget = BudgetCreate(
            user_id=1,
            name="Entertainment Budget",
            category="entertainment",
            amount=Decimal("200.00"),
            period="monthly",
            start_date=date.today(),
        )
        assert budget.user_id == 1

    def test_budget_update_partial(self):
        """Test BudgetUpdate allows partial updates."""
        update = BudgetUpdate(amount=Decimal("600.00"))
        assert update.amount == Decimal("600.00")
        assert update.name is None


# ============================================================================
# Document Schema Tests
# ============================================================================


class TestDocumentSchemas:
    """Test Document schemas (Base/Create/Read/Update)."""

    def test_document_base_valid(self):
        """Test DocumentBase with valid data."""
        doc = DocumentBase(
            document_type="tax_form",
            file_name="W2_2024.pdf",
            file_path="s3://bucket/docs/W2_2024.pdf",
            file_size_bytes=250000,
            mime_type="application/pdf",
        )
        assert doc.document_type == "tax_form"
        assert doc.file_name == "W2_2024.pdf"
        assert doc.file_size_bytes == 250000

    def test_document_create_requires_user_id(self):
        """Test DocumentCreate requires user_id."""
        doc = DocumentCreate(
            user_id=1,
            document_type="receipt",
            file_name="receipt.jpg",
            file_path="s3://bucket/receipts/receipt.jpg",
            file_size_bytes=100000,
            mime_type="image/jpeg",
        )
        assert doc.user_id == 1

    def test_document_update_partial(self):
        """Test DocumentUpdate allows partial updates."""
        update = DocumentUpdate(tax_year=2024)
        assert update.tax_year == 2024
        assert update.file_name is None


# ============================================================================
# NetWorthSnapshot Schema Tests
# ============================================================================


class TestNetWorthSnapshotSchemas:
    """Test NetWorthSnapshot schemas (Base/Create/Read)."""

    def test_snapshot_base_valid(self):
        """Test NetWorthSnapshotBase with valid data."""
        snapshot = NetWorthSnapshotBase(
            snapshot_date=date.today(),
            total_assets=Decimal("150000.00"),
            total_liabilities=Decimal("50000.00"),
            net_worth=Decimal("100000.00"),
            liquid_assets=Decimal("25000.00"),
            invested_assets=Decimal("100000.00"),
            real_estate_assets=Decimal("25000.00"),
        )
        assert snapshot.net_worth == Decimal("100000.00")
        assert snapshot.total_assets == Decimal("150000.00")
        assert isinstance(snapshot.snapshot_date, date)

    def test_snapshot_base_default_values(self):
        """Test NetWorthSnapshotBase default values."""
        snapshot = NetWorthSnapshotBase(
            snapshot_date=date.today(),
            total_assets=Decimal("100000.00"),
            total_liabilities=Decimal("20000.00"),
            net_worth=Decimal("80000.00"),
        )
        assert snapshot.liquid_assets == Decimal("0.00")
        assert snapshot.invested_assets == Decimal("0.00")

    def test_snapshot_create_requires_user_id(self):
        """Test NetWorthSnapshotCreate requires user_id."""
        snapshot = NetWorthSnapshotCreate(
            user_id=1,
            snapshot_date=date.today(),
            total_assets=Decimal("200000.00"),
            total_liabilities=Decimal("75000.00"),
            net_worth=Decimal("125000.00"),
        )
        assert snapshot.user_id == 1

    def test_snapshot_read_includes_metadata(self):
        """Test NetWorthSnapshotRead includes timestamps."""
        now = datetime.utcnow()
        snapshot_data = {
            "id": 1,
            "user_id": 1,
            "snapshot_date": date.today(),
            "total_assets": Decimal("150000.00"),
            "total_liabilities": Decimal("50000.00"),
            "net_worth": Decimal("100000.00"),
            "liquid_assets": Decimal("25000.00"),
            "invested_assets": Decimal("100000.00"),
            "real_estate_assets": Decimal("25000.00"),
            "personal_property_assets": Decimal("0.00"),
            "business_assets": Decimal("0.00"),
            "other_assets": Decimal("0.00"),
            "short_term_liabilities": Decimal("5000.00"),
            "long_term_liabilities": Decimal("45000.00"),
            "mortgage_liabilities": Decimal("0.00"),
            "credit_card_liabilities": Decimal("0.00"),
            "student_loan_liabilities": Decimal("0.00"),
            "other_liabilities": Decimal("0.00"),
            "created_at": now,
        }
        snapshot = NetWorthSnapshotRead(**snapshot_data)
        assert snapshot.id == 1
        assert snapshot.created_at == now


# ============================================================================
# Cross-Schema Validation Tests
# ============================================================================


class TestCrossSchemaValidation:
    """Test validation rules that apply across schemas."""

    def test_decimal_precision(self):
        """Test Decimal fields maintain precision."""
        account = AccountBase(
            name="Precision Test",
            account_type="savings",
            balance=Decimal("1234.567"),  # More than 2 decimal places
        )
        # Pydantic should accept this, but database will enforce precision
        assert isinstance(account.balance, Decimal)

    def test_email_validation_across_schemas(self):
        """Test email validation in User schemas."""
        valid_emails = [
            "test@example.com",
            "user+tag@domain.co.uk",
            "first.last@company.org",
        ]
        for email in valid_emails:
            user = UserBase(email=email, full_name="Test")
            assert user.email == email

        invalid_emails = ["not-an-email", "@domain.com", "user@", "user"]
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserBase(email=email, full_name="Test")

    def test_optional_fields_null_handling(self):
        """Test optional fields accept None."""
        account = AccountBase(
            name="Test",
            account_type="checking",
            institution=None,  # Optional field
            provider_account_id=None,  # Optional field
        )
        assert account.institution is None
        assert account.provider_account_id is None

    def test_datetime_serialization(self):
        """Test datetime fields serialize correctly."""
        now = datetime.utcnow()
        user = UserRead(
            id=1,
            email="test@example.com",
            full_name="Test User",
            currency="USD",
            risk_tolerance=None,
            plaid_linked=False,
            alpaca_linked=False,
            experian_linked=False,
            created_at=now,
            updated_at=now,
        )
        # Should be able to serialize to dict
        user_dict = user.model_dump()
        assert isinstance(user_dict["created_at"], datetime)

        # Should be able to serialize to JSON
        user_json = user.model_dump_json()
        assert isinstance(user_json, str)
        assert "test@example.com" in user_json
