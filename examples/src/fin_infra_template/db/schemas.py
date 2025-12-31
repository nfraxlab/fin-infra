"""Pydantic schemas for API serialization/validation.

Provides Base/Create/Read/Update schemas for all financial models.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============================================================================
# User Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    full_name: str
    currency: str = "USD"
    risk_tolerance: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user (all fields optional)."""

    email: EmailStr | None = None
    full_name: str | None = None
    currency: str | None = None
    risk_tolerance: str | None = None


class UserRead(UserBase):
    """Schema for reading a user (includes metadata)."""

    id: int
    plaid_linked: bool
    alpaca_linked: bool
    experian_linked: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Account Schemas
# ============================================================================


class AccountBase(BaseModel):
    """Base account fields."""

    name: str
    account_type: str
    provider: str = "manual"
    provider_account_id: str | None = None
    institution: str | None = None
    account_number_last4: str | None = None
    balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    currency: str = "USD"
    is_active: bool = True


class AccountCreate(AccountBase):
    """Schema for creating a new account."""

    user_id: int | None = None


class AccountUpdate(BaseModel):
    """Schema for updating an account (all fields optional)."""

    name: str | None = None
    account_type: str | None = None
    balance: Decimal | None = None
    currency: str | None = None
    is_active: bool | None = None


class AccountRead(AccountBase):
    """Schema for reading an account (includes metadata)."""

    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Transaction Schemas
# ============================================================================


class TransactionBase(BaseModel):
    """Base transaction fields."""

    account_id: int
    date: date
    description: str
    amount: Decimal = Field(decimal_places=2)
    currency: str = "USD"
    provider_transaction_id: str | None = None
    category: str | None = None
    subcategory: str | None = None
    is_recurring: bool = False
    recurring_pattern: str | None = None
    merchant: str | None = None
    location: str | None = None


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    user_id: int | None = None


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction (all fields optional)."""

    date: date | None = None
    description: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    category: str | None = None
    subcategory: str | None = None
    is_recurring: bool | None = None
    recurring_pattern: str | None = None
    merchant: str | None = None
    location: str | None = None


class TransactionRead(TransactionBase):
    """Schema for reading a transaction (includes metadata)."""

    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Position Schemas
# ============================================================================


class PositionBase(BaseModel):
    """Base position fields."""

    account_id: int
    symbol: str
    asset_type: str
    asset_name: str | None = None
    quantity: Decimal = Field(decimal_places=8)
    cost_basis: Decimal = Field(decimal_places=2)
    current_price: Decimal | None = Field(default=None, decimal_places=2)
    market_value: Decimal | None = Field(default=None, decimal_places=2)
    unrealized_gain_loss: Decimal | None = Field(default=None, decimal_places=2)
    unrealized_gain_loss_pct: Decimal | None = Field(default=None, decimal_places=4)


class PositionCreate(PositionBase):
    """Schema for creating a new position."""

    user_id: int | None = None


class PositionUpdate(BaseModel):
    """Schema for updating a position (all fields optional)."""

    quantity: Decimal | None = None
    cost_basis: Decimal | None = None
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_gain_loss: Decimal | None = None
    unrealized_gain_loss_pct: Decimal | None = None


class PositionRead(PositionBase):
    """Schema for reading a position (includes metadata)."""

    id: int
    user_id: int | None = None
    last_updated: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Holding Schemas (Investment Holdings from Plaid/SnapTrade)
# ============================================================================


class HoldingBase(BaseModel):
    """Base holding fields."""

    account_id: int
    provider: str  # plaid, snaptrade, teller
    provider_account_id: str
    provider_security_id: str
    ticker_symbol: str | None = None
    security_name: str
    security_type: str  # equity, etf, mutual_fund, bond, cash, derivative
    cusip: str | None = None
    isin: str | None = None
    sector: str | None = None
    quantity: Decimal = Field(decimal_places=8)
    institution_price: Decimal = Field(decimal_places=4)
    institution_value: Decimal = Field(decimal_places=2)
    cost_basis: Decimal | None = Field(default=None, decimal_places=2)
    currency: str = "USD"
    close_price: Decimal | None = Field(default=None, decimal_places=4)
    close_price_as_of: datetime | None = None
    unrealized_gain_loss: Decimal | None = Field(default=None, decimal_places=2)
    unrealized_gain_loss_percent: Decimal | None = Field(default=None, decimal_places=4)
    sync_status: str = "synced"  # synced, pending, failed


class HoldingCreate(HoldingBase):
    """Schema for creating a new holding."""

    user_id: int | None = None


class HoldingUpdate(BaseModel):
    """Schema for updating a holding (all fields optional)."""

    quantity: Decimal | None = None
    institution_price: Decimal | None = None
    institution_value: Decimal | None = None
    cost_basis: Decimal | None = None
    close_price: Decimal | None = None
    close_price_as_of: datetime | None = None
    unrealized_gain_loss: Decimal | None = None
    unrealized_gain_loss_percent: Decimal | None = None
    sync_status: str | None = None


class HoldingRead(HoldingBase):
    """Schema for reading a holding (includes metadata)."""

    id: int
    user_id: int | None = None
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Goal Schemas
# ============================================================================


class GoalBase(BaseModel):
    """Base goal fields."""

    name: str
    description: str | None = None
    goal_type: str
    target_amount: Decimal = Field(decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    currency: str = "USD"
    target_date: date | None = None
    linked_account_id: int | None = None


class GoalCreate(GoalBase):
    """Schema for creating a new goal."""

    user_id: int | None = None


class GoalUpdate(BaseModel):
    """Schema for updating a goal (all fields optional)."""

    name: str | None = None
    description: str | None = None
    goal_type: str | None = None
    target_amount: Decimal | None = None
    current_amount: Decimal | None = None
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: int | None = None


class GoalRead(GoalBase):
    """Schema for reading a goal (includes metadata)."""

    id: int
    user_id: int | None = None
    progress_pct: Decimal
    is_completed: bool
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Budget Schemas
# ============================================================================


class BudgetBase(BaseModel):
    """Base budget fields."""

    name: str
    category: str
    period: str
    planned_amount: Decimal = Field(decimal_places=2)
    actual_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    currency: str = "USD"
    period_start: date
    period_end: date
    is_active: bool = True


class BudgetCreate(BudgetBase):
    """Schema for creating a new budget."""

    user_id: int | None = None


class BudgetUpdate(BaseModel):
    """Schema for updating a budget (all fields optional)."""

    name: str | None = None
    category: str | None = None
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    currency: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    is_active: bool | None = None


class BudgetRead(BudgetBase):
    """Schema for reading a budget (includes metadata)."""

    id: int
    user_id: int | None = None
    is_overspent: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Document Schemas
# ============================================================================


class DocumentBase(BaseModel):
    """Base document fields."""

    filename: str
    document_type: str
    mime_type: str
    file_size: int
    storage_path: str
    storage_provider: str = "local"
    extracted_text: str | None = None
    ai_summary: str | None = None
    key_fields: str | None = None
    document_date: date | None = None
    tags: str | None = None
    related_transaction_id: int | None = None
    related_account_id: int | None = None


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    user_id: int | None = None


class DocumentUpdate(BaseModel):
    """Schema for updating a document (all fields optional)."""

    filename: str | None = None
    document_type: str | None = None
    extracted_text: str | None = None
    ai_summary: str | None = None
    key_fields: str | None = None
    document_date: date | None = None
    tags: str | None = None
    related_transaction_id: int | None = None
    related_account_id: int | None = None


class DocumentRead(DocumentBase):
    """Schema for reading a document (includes metadata)."""

    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# NetWorthSnapshot Schemas
# ============================================================================


class NetWorthSnapshotBase(BaseModel):
    """Base net worth snapshot fields."""

    snapshot_date: date
    total_assets: Decimal = Field(decimal_places=2)
    liquid_assets: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    investment_assets: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_liabilities: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    credit_card_debt: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    loan_debt: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    net_worth: Decimal = Field(decimal_places=2)
    currency: str = "USD"
    calculation_method: str = "automatic"
    notes: str | None = None


class NetWorthSnapshotCreate(NetWorthSnapshotBase):
    """Schema for creating a new net worth snapshot."""

    user_id: int | None = None


class NetWorthSnapshotUpdate(BaseModel):
    """Schema for updating a net worth snapshot (all fields optional)."""

    snapshot_date: date | None = None
    total_assets: Decimal | None = None
    liquid_assets: Decimal | None = None
    investment_assets: Decimal | None = None
    total_liabilities: Decimal | None = None
    credit_card_debt: Decimal | None = None
    loan_debt: Decimal | None = None
    net_worth: Decimal | None = None
    currency: str | None = None
    calculation_method: str | None = None
    notes: str | None = None


class NetWorthSnapshotRead(NetWorthSnapshotBase):
    """Schema for reading a net worth snapshot (includes metadata)."""

    id: int
    user_id: int | None = None
    change_from_previous: Decimal | None = None
    change_from_previous_pct: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
