"""Financial database models for fin-infra-template.

Demonstrates fin-infra patterns for:
- Banking accounts and transactions
- Investment positions and portfolio tracking
- Financial goals and budgets
- Document storage and analysis
- Net worth snapshots over time
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Date, DateTime, String, Text, func, inspect
from sqlalchemy.orm import Mapped, mapped_column

from fin_infra_template.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UserOwnedMixin,
)


class User(Base, TimestampMixin):
    """
    User model for authentication and profile.

    Demonstrates:
    - Basic user info
    - Financial preferences
    - Provider integrations tracking
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Financial preferences
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    risk_tolerance: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # conservative, moderate, aggressive

    # Provider integration status
    plaid_linked: Mapped[bool] = mapped_column(default=False, nullable=False)
    alpaca_linked: Mapped[bool] = mapped_column(default=False, nullable=False)
    experian_linked: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<User at {hex(id(self))}>"
        return f"<User(id={self.id}, email={self.email!r})>"


class Account(Base, TimestampMixin, SoftDeleteMixin, UserOwnedMixin):
    """
    Financial account (bank, brokerage, credit card, crypto).

    Demonstrates:
    - Multi-provider account aggregation
    - Account types and institutions
    - Balance tracking
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Provider info
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # plaid, teller, alpaca, manual
    provider_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Account details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # checking, savings, investment, credit_card, crypto
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)

    # Balance (current)
    balance: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Account at {hex(id(self))}>"
        return f"<Account(id={self.id}, name={self.name!r}, type={self.account_type})>"


class Transaction(Base, TimestampMixin, UserOwnedMixin):
    """
    Financial transaction (income, expense, transfer).

    Demonstrates:
    - Transaction categorization
    - Recurring transaction detection
    - Multi-currency support
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(nullable=False, index=True)

    # Provider info
    provider_transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Transaction details
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)  # negative for expenses
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Categorization
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    recurring_pattern: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # monthly, weekly, yearly

    # Metadata
    merchant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Transaction at {hex(id(self))}>"
        return f"<Transaction(id={self.id}, date={self.date}, amount={self.amount}, desc={self.description[:30]!r})>"


class Position(Base, TimestampMixin, UserOwnedMixin):
    """
    Investment position (stock, crypto, bond, etc.).

    Demonstrates:
    - Portfolio tracking
    - Cost basis and P&L
    - Multi-asset support
    """

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(nullable=False, index=True)

    # Asset details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # stock, crypto, bond, etf, mutual_fund
    asset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Position details
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)  # total cost in USD
    current_price: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True
    )  # price per unit in USD
    market_value: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True
    )  # total value in USD

    # P&L tracking
    unrealized_gain_loss: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    unrealized_gain_loss_pct: Mapped[Decimal | None] = mapped_column(DECIMAL(8, 4), nullable=True)

    # Metadata
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Position at {hex(id(self))}>"
        return f"<Position(id={self.id}, symbol={self.symbol!r}, qty={self.quantity}, value={self.market_value})>"


class Holding(Base, TimestampMixin, UserOwnedMixin):
    """
    Investment holding snapshot (from Plaid/SnapTrade/aggregators).

    Demonstrates:
    - Real-time holdings from investment providers
    - Cost basis and P/L tracking from external sources
    - Security metadata (ticker, name, type, price)
    - Multi-account aggregation

    Note: Different from Position model:
    - Position: Internal brokerage positions (Alpaca trading)
    - Holding: External aggregated holdings (Plaid/SnapTrade 401k, IRA, retail brokerages)
    """

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(nullable=False, index=True)

    # Provider info (Plaid, SnapTrade, etc.)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # plaid, snaptrade, teller
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_security_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Security details
    ticker_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    security_name: Mapped[str] = mapped_column(String(255), nullable=False)
    security_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # equity, etf, mutual_fund, bond, cash, derivative
    cusip: Mapped[str | None] = mapped_column(String(9), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Position details
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(20, 8), nullable=False)
    institution_price: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 4), nullable=False
    )  # price per unit from provider
    institution_value: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), nullable=False
    )  # total value from provider
    cost_basis: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True
    )  # total cost (may be unavailable)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Market data (latest close price from provider)
    close_price: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 4), nullable=True)
    close_price_as_of: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # P&L (calculated from cost_basis and institution_value)
    unrealized_gain_loss: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    unrealized_gain_loss_percent: Mapped[Decimal | None] = mapped_column(
        DECIMAL(8, 4), nullable=True
    )

    # Sync metadata
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="synced"
    )  # synced, pending, failed

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Holding at {hex(id(self))}>"
        return f"<Holding(id={self.id}, symbol={self.ticker_symbol!r}, qty={self.quantity}, value={self.institution_value})>"


class Goal(Base, TimestampMixin, SoftDeleteMixin, UserOwnedMixin):
    """
    Financial goal (emergency fund, retirement, house, etc.).

    Demonstrates:
    - Goal tracking with milestones
    - Target dates and amounts
    - Progress monitoring
    """

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Goal details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # emergency, retirement, house, vacation, debt_payoff

    # Target
    target_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Progress
    progress_pct: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Linked accounts (optional)
    linked_account_id: Mapped[int | None] = mapped_column(nullable=True, index=True)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Goal at {hex(id(self))}>"
        return f"<Goal(id={self.id}, name={self.name!r}, progress={self.progress_pct}%)>"


class Budget(Base, TimestampMixin, SoftDeleteMixin, UserOwnedMixin):
    """
    Budget (monthly, category-based).

    Demonstrates:
    - Budget planning and tracking
    - Category-level budgets
    - Overspending alerts
    """

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Budget details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # monthly, weekly, yearly

    # Amounts
    planned_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Period tracking
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_overspent: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Budget at {hex(id(self))}>"
        return f"<Budget(id={self.id}, category={self.category!r}, planned={self.planned_amount})>"


class Document(Base, TimestampMixin, SoftDeleteMixin, UserOwnedMixin):
    """
    Financial document (tax form, statement, receipt).

    Demonstrates:
    - Document management
    - OCR and AI analysis
    - Tagging and search
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Document details
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # tax_form, statement, receipt, contract
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)  # bytes

    # Storage
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="local"
    )  # local, s3, gcs

    # Analysis (OCR + AI)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_fields: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string of extracted fields

    # Metadata
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated tags
    related_transaction_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    related_account_id: Mapped[int | None] = mapped_column(nullable=True, index=True)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<Document at {hex(id(self))}>"
        return f"<Document(id={self.id}, filename={self.filename!r}, type={self.document_type})>"


class NetWorthSnapshot(Base, TimestampMixin, UserOwnedMixin):
    """
    Net worth snapshot (point-in-time calculation).

    Demonstrates:
    - Historical net worth tracking
    - Asset/liability breakdown
    - Trend analysis
    """

    __tablename__ = "net_worth_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Snapshot details
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Assets
    total_assets: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    liquid_assets: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), nullable=False, default=0
    )  # cash, checking, savings
    investment_assets: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2), nullable=False, default=0
    )  # stocks, bonds, crypto

    # Liabilities
    total_liabilities: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False, default=0)
    credit_card_debt: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False, default=0)
    loan_debt: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False, default=0)

    # Net worth
    net_worth: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Change tracking
    change_from_previous: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    change_from_previous_pct: Mapped[Decimal | None] = mapped_column(DECIMAL(8, 4), nullable=True)

    # Metadata
    calculation_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="automatic"
    )  # automatic, manual
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.detached or state.expired:
            return f"<NetWorthSnapshot at {hex(id(self))}>"
        return f"<NetWorthSnapshot(id={self.id}, date={self.snapshot_date}, net_worth={self.net_worth})>"


# To use these models:
# 1. Run: python -m svc_infra.cli sql init --project-root /path/to/fin-infra/examples
# 2. Run: python -m svc_infra.cli sql revision -m "Initial financial models" --project-root /path/to/fin-infra/examples
# 3. Run: python -m svc_infra.cli sql upgrade head --project-root /path/to/fin-infra/examples

# Or use the Makefile:
# make setup  # Runs scaffold + migrate automatically
