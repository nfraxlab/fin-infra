"""Pydantic schemas for API serialization/validation.

Provides Base/Create/Read/Update schemas for all financial models.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============================================================================
# User Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    full_name: str
    currency: str = "USD"
    risk_tolerance: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user (all fields optional)."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    currency: Optional[str] = None
    risk_tolerance: Optional[str] = None


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
    provider_account_id: Optional[str] = None
    institution: Optional[str] = None
    account_number_last4: Optional[str] = None
    balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    currency: str = "USD"
    is_active: bool = True


class AccountCreate(AccountBase):
    """Schema for creating a new account."""

    user_id: Optional[int] = None


class AccountUpdate(BaseModel):
    """Schema for updating an account (all fields optional)."""

    name: Optional[str] = None
    account_type: Optional[str] = None
    balance: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class AccountRead(AccountBase):
    """Schema for reading an account (includes metadata)."""

    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

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
    provider_transaction_id: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    is_recurring: bool = False
    recurring_pattern: Optional[str] = None
    merchant: Optional[str] = None
    location: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    user_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction (all fields optional)."""

    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurring_pattern: Optional[str] = None
    merchant: Optional[str] = None
    location: Optional[str] = None


class TransactionRead(TransactionBase):
    """Schema for reading a transaction (includes metadata)."""

    id: int
    user_id: Optional[int] = None
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
    asset_name: Optional[str] = None
    quantity: Decimal = Field(decimal_places=8)
    cost_basis: Decimal = Field(decimal_places=2)
    current_price: Optional[Decimal] = Field(default=None, decimal_places=2)
    market_value: Optional[Decimal] = Field(default=None, decimal_places=2)
    unrealized_gain_loss: Optional[Decimal] = Field(default=None, decimal_places=2)
    unrealized_gain_loss_pct: Optional[Decimal] = Field(default=None, decimal_places=4)


class PositionCreate(PositionBase):
    """Schema for creating a new position."""

    user_id: Optional[int] = None


class PositionUpdate(BaseModel):
    """Schema for updating a position (all fields optional)."""

    quantity: Optional[Decimal] = None
    cost_basis: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_gain_loss: Optional[Decimal] = None
    unrealized_gain_loss_pct: Optional[Decimal] = None


class PositionRead(PositionBase):
    """Schema for reading a position (includes metadata)."""

    id: int
    user_id: Optional[int] = None
    last_updated: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Goal Schemas
# ============================================================================


class GoalBase(BaseModel):
    """Base goal fields."""

    name: str
    description: Optional[str] = None
    goal_type: str
    target_amount: Decimal = Field(decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    currency: str = "USD"
    target_date: Optional[date] = None
    linked_account_id: Optional[int] = None


class GoalCreate(GoalBase):
    """Schema for creating a new goal."""

    user_id: Optional[int] = None


class GoalUpdate(BaseModel):
    """Schema for updating a goal (all fields optional)."""

    name: Optional[str] = None
    description: Optional[str] = None
    goal_type: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    target_date: Optional[date] = None
    linked_account_id: Optional[int] = None


class GoalRead(GoalBase):
    """Schema for reading a goal (includes metadata)."""

    id: int
    user_id: Optional[int] = None
    progress_pct: Decimal
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

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

    user_id: Optional[int] = None


class BudgetUpdate(BaseModel):
    """Schema for updating a budget (all fields optional)."""

    name: Optional[str] = None
    category: Optional[str] = None
    planned_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    is_active: Optional[bool] = None


class BudgetRead(BudgetBase):
    """Schema for reading a budget (includes metadata)."""

    id: int
    user_id: Optional[int] = None
    is_overspent: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

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
    extracted_text: Optional[str] = None
    ai_summary: Optional[str] = None
    key_fields: Optional[str] = None
    document_date: Optional[date] = None
    tags: Optional[str] = None
    related_transaction_id: Optional[int] = None
    related_account_id: Optional[int] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    user_id: Optional[int] = None


class DocumentUpdate(BaseModel):
    """Schema for updating a document (all fields optional)."""

    filename: Optional[str] = None
    document_type: Optional[str] = None
    extracted_text: Optional[str] = None
    ai_summary: Optional[str] = None
    key_fields: Optional[str] = None
    document_date: Optional[date] = None
    tags: Optional[str] = None
    related_transaction_id: Optional[int] = None
    related_account_id: Optional[int] = None


class DocumentRead(DocumentBase):
    """Schema for reading a document (includes metadata)."""

    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

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
    notes: Optional[str] = None


class NetWorthSnapshotCreate(NetWorthSnapshotBase):
    """Schema for creating a new net worth snapshot."""

    user_id: Optional[int] = None


class NetWorthSnapshotUpdate(BaseModel):
    """Schema for updating a net worth snapshot (all fields optional)."""

    snapshot_date: Optional[date] = None
    total_assets: Optional[Decimal] = None
    liquid_assets: Optional[Decimal] = None
    investment_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    credit_card_debt: Optional[Decimal] = None
    loan_debt: Optional[Decimal] = None
    net_worth: Optional[Decimal] = None
    currency: Optional[str] = None
    calculation_method: Optional[str] = None
    notes: Optional[str] = None


class NetWorthSnapshotRead(NetWorthSnapshotBase):
    """Schema for reading a net worth snapshot (includes metadata)."""

    id: int
    user_id: Optional[int] = None
    change_from_previous: Optional[Decimal] = None
    change_from_previous_pct: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
