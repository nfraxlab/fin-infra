"""Pydantic models for investment holdings and portfolio data.

This module defines the data models used across all investment providers.
Models are provider-agnostic and normalize data from Plaid, SnapTrade, etc.

**Data Models**:
- Security: Security details (stock, bond, ETF, etc.)
- Holding: Investment holding with current value and cost basis
- InvestmentTransaction: Investment transaction (buy, sell, dividend, etc.)
- InvestmentAccount: Investment account with aggregated holdings and metrics
- AssetAllocation: Asset allocation breakdown by security type and sector

**Enums**:
- SecurityType: equity, etf, mutual_fund, bond, cash, derivative, other
- TransactionType: buy, sell, dividend, interest, fee, tax, transfer, split, merger, cancel, other
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class SecurityType(str, Enum):
    """Security type classification.
    
    Categories:
    - equity: Common stock (AAPL, GOOGL, etc.)
    - etf: Exchange-traded fund (SPY, QQQ, etc.)
    - mutual_fund: Mutual fund (VTSAX, FXAIX, etc.)
    - bond: Fixed income (government, corporate, municipal)
    - cash: Cash or money market
    - derivative: Options, futures, warrants
    - other: Other/unknown security types
    """

    equity = "equity"
    etf = "etf"
    mutual_fund = "mutual_fund"
    bond = "bond"
    cash = "cash"
    derivative = "derivative"
    other = "other"


class TransactionType(str, Enum):
    """Investment transaction type.
    
    Categories:
    - buy: Purchase of security
    - sell: Sale of security
    - dividend: Dividend payment
    - interest: Interest payment
    - fee: Fee charged
    - tax: Tax withholding
    - transfer: Transfer of holdings
    - split: Stock split
    - merger: Merger/acquisition
    - cancel: Cancelled transaction
    - other: Other transaction type
    """

    buy = "buy"
    sell = "sell"
    dividend = "dividend"
    interest = "interest"
    fee = "fee"
    tax = "tax"
    transfer = "transfer"
    split = "split"  # type: ignore[assignment]  # str.split() name conflict
    merger = "merger"
    cancel = "cancel"
    other = "other"


class Security(BaseModel):
    """Security details (stock, bond, ETF, etc.).
    
    Represents a tradable security with identifying information and current market data.
    Normalized across providers (Plaid, SnapTrade).
    
    Example:
        >>> security = Security(
        ...     security_id="plaid_sec_123",
        ...     cusip="037833100",
        ...     isin="US0378331005",
        ...     ticker_symbol="AAPL",
        ...     name="Apple Inc.",
        ...     type=SecurityType.equity,
        ...     close_price=150.00,
        ...     close_price_as_of=date(2025, 11, 19),
        ...     exchange="NASDAQ",
        ...     currency="USD"
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "security_id": "plaid_sec_abc123",
                "cusip": "037833100",
                "isin": "US0378331005",
                "sedol": None,
                "ticker_symbol": "AAPL",
                "name": "Apple Inc.",
                "type": "equity",
                "sector": "Technology",
                "close_price": 150.25,
                "close_price_as_of": "2025-11-19",
                "exchange": "NASDAQ",
                "currency": "USD",
            }
        },
    )

    # Identifiers (at least one required for matching)
    security_id: str = Field(..., description="Provider-specific security ID")
    cusip: Optional[str] = Field(None, description="CUSIP identifier (US securities)")
    isin: Optional[str] = Field(None, description="ISIN identifier (international)")
    sedol: Optional[str] = Field(None, description="SEDOL identifier (UK securities)")
    ticker_symbol: Optional[str] = Field(None, description="Trading symbol (AAPL, GOOGL)")

    # Basic info
    name: str = Field(..., description="Security name")
    type: SecurityType = Field(..., description="Security type (equity, etf, bond, etc.)")
    sector: Optional[str] = Field(None, description="Sector classification (Technology, Healthcare)")

    # Market data
    close_price: Optional[Decimal] = Field(None, ge=0, description="Latest closing price")
    close_price_as_of: Optional[date] = Field(None, description="Date of close_price")
    exchange: Optional[str] = Field(None, description="Exchange (NASDAQ, NYSE, etc.)")
    currency: str = Field("USD", description="Currency code (USD, EUR, etc.)")


class Holding(BaseModel):
    """Investment holding with current value and cost basis.
    
    Represents a position in a specific security within an investment account.
    Includes quantity, current value, cost basis, and calculated P&L.
    
    Example:
        >>> holding = Holding(
        ...     account_id="acct_123",
        ...     security=Security(...),
        ...     quantity=10.0,
        ...     institution_price=150.00,
        ...     institution_value=1500.00,
        ...     cost_basis=1400.00,
        ...     currency="USD",
        ...     as_of_date=date.today()
        ... )
        >>> print(f"Unrealized P&L: ${holding.unrealized_gain_loss}")
        >>> # Output: Unrealized P&L: $100.0
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "account_id": "acct_abc123",
                "security": {
                    "security_id": "plaid_sec_abc123",
                    "ticker_symbol": "AAPL",
                    "name": "Apple Inc.",
                    "type": "equity",
                    "close_price": 150.25,
                    "close_price_as_of": "2025-11-19",
                    "currency": "USD",
                },
                "quantity": 10.5,
                "institution_price": 150.25,
                "institution_value": 1577.63,
                "cost_basis": 1522.50,
                "unrealized_gain_loss": 55.13,
                "unrealized_gain_loss_percent": 3.62,
                "currency": "USD",
                "as_of_date": "2025-11-19",
            }
        },
    )

    # Account and security
    account_id: str = Field(..., description="Investment account ID")
    security: Security = Field(..., description="Security details")

    # Position data
    quantity: Decimal = Field(..., ge=0, description="Number of shares/units held")
    institution_price: Decimal = Field(..., ge=0, description="Current price per share")
    institution_value: Decimal = Field(..., ge=0, description="Current market value (quantity × price)")
    cost_basis: Optional[Decimal] = Field(None, ge=0, description="Total cost basis (original purchase price)")

    # Additional data
    currency: str = Field("USD", description="Currency code")
    unofficial_currency_code: Optional[str] = Field(None, description="For crypto/alt currencies")
    as_of_date: Optional[date] = Field(None, description="Date of pricing data")

    @computed_field
    @property
    def unrealized_gain_loss(self) -> Optional[Decimal]:
        """Calculate unrealized gain/loss (current value - cost basis)."""
        if self.cost_basis is None:
            return None
        return self.institution_value - self.cost_basis

    @computed_field
    @property
    def unrealized_gain_loss_percent(self) -> Optional[Decimal]:
        """Calculate unrealized gain/loss percentage."""
        if self.cost_basis is None or self.cost_basis == 0:
            return None
        gain_loss = self.institution_value - self.cost_basis
        return round((gain_loss / self.cost_basis) * 100, 2)


class InvestmentTransaction(BaseModel):
    """Investment transaction (buy, sell, dividend, etc.).
    
    Represents a single transaction in an investment account.
    Used to calculate realized gains and track transaction history.
    
    Example:
        >>> transaction = InvestmentTransaction(
        ...     transaction_id="tx_123",
        ...     account_id="acct_456",
        ...     security=Security(...),
        ...     date=date(2025, 11, 15),
        ...     name="AAPL BUY",
        ...     type=TransactionType.buy,
        ...     quantity=10,
        ...     amount=1500.00,
        ...     price=150.00,
        ...     fees=0.00,
        ...     currency="USD"
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "transaction_id": "tx_abc123",
                "account_id": "acct_abc123",
                "security": {
                    "security_id": "plaid_sec_abc123",
                    "ticker_symbol": "AAPL",
                    "name": "Apple Inc.",
                    "type": "equity",
                },
                "date": "2025-11-15",
                "name": "AAPL BUY",
                "type": "buy",
                "subtype": None,
                "quantity": 10.0,
                "amount": 1500.00,
                "price": 150.00,
                "fees": 0.00,
                "currency": "USD",
            }
        },
    )

    # Identifiers
    transaction_id: str = Field(..., description="Provider-specific transaction ID")
    account_id: str = Field(..., description="Investment account ID")
    security: Security = Field(..., description="Security involved in transaction")

    # Transaction details
    transaction_date: date = Field(..., alias="date", description="Transaction date")
    name: str = Field(..., description="Transaction description")
    transaction_type: TransactionType = Field(..., alias="type", description="Transaction type (buy, sell, dividend)")
    subtype: Optional[str] = Field(None, description="Provider-specific subtype")

    # Amounts
    quantity: Decimal = Field(..., description="Number of shares (0 for fees/dividends)")
    amount: Decimal = Field(..., description="Transaction amount (negative for purchases)")
    price: Optional[Decimal] = Field(None, ge=0, description="Price per share")
    fees: Optional[Decimal] = Field(None, ge=0, description="Transaction fees")

    # Additional data
    currency: str = Field("USD", description="Currency code")
    unofficial_currency_code: Optional[str] = Field(None, description="For crypto/alt currencies")


class InvestmentAccount(BaseModel):
    """Investment account with aggregated holdings and metrics.
    
    Represents a complete investment account with all holdings, balances, and P&L.
    Includes calculated fields for total value, cost basis, and unrealized gains.
    
    Example:
        >>> account = InvestmentAccount(
        ...     account_id="acct_123",
        ...     name="Fidelity 401k",
        ...     type="investment",
        ...     subtype="401k",
        ...     holdings=[...],
        ...     balances={"current": 50000.00, "available": 50000.00}
        ... )
        >>> print(f"Total P&L: ${account.total_unrealized_gain_loss}")
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "account_id": "acct_abc123",
                "name": "Fidelity 401k",
                "type": "investment",
                "subtype": "401k",
                "balances": {"current": 50245.38, "available": 50245.38, "limit": None},
                "holdings": [
                    {
                        "account_id": "acct_abc123",
                        "security": {"ticker_symbol": "AAPL", "name": "Apple Inc.", "type": "equity"},
                        "quantity": 10.5,
                        "institution_price": 150.25,
                        "institution_value": 1577.63,
                        "cost_basis": 1522.50,
                    }
                ],
                "total_value": 50245.38,
                "total_cost_basis": 48000.00,
                "total_unrealized_gain_loss": 2245.38,
                "total_unrealized_gain_loss_percent": 4.68,
            }
        },
    )

    # Account info
    account_id: str = Field(..., description="Account identifier")
    name: str = Field(..., description="Account name (Fidelity 401k)")
    type: str = Field(..., description="Account type (investment)")
    subtype: Optional[str] = Field(None, description="Account subtype (401k, ira, brokerage)")

    # Balances
    balances: Dict[str, Optional[Decimal]] = Field(
        ..., description="Current, available, and limit balances"
    )

    # Holdings
    holdings: List[Holding] = Field(default_factory=list, description="List of holdings in account")

    @computed_field
    @property
    def total_value(self) -> Decimal:
        """Calculate total account value (sum of holdings + cash)."""
        holdings_value = sum(h.institution_value for h in self.holdings)
        cash_balance = self.balances.get("current") or Decimal(0)
        return holdings_value + cash_balance

    @computed_field
    @property
    def total_cost_basis(self) -> Decimal:
        """Calculate total cost basis (sum of cost_basis across holdings)."""
        return sum(h.cost_basis for h in self.holdings if h.cost_basis is not None)

    @computed_field
    @property
    def total_unrealized_gain_loss(self) -> Decimal:
        """Calculate total unrealized P&L (value - cost_basis)."""
        holdings_value = sum(h.institution_value for h in self.holdings)
        return holdings_value - self.total_cost_basis

    @computed_field
    @property
    def total_unrealized_gain_loss_percent(self) -> Optional[Decimal]:
        """Calculate total unrealized P&L percentage."""
        if self.total_cost_basis == 0:
            return None
        return round((self.total_unrealized_gain_loss / self.total_cost_basis) * 100, 2)


class AssetAllocation(BaseModel):
    """Asset allocation breakdown by security type and sector.
    
    Provides percentage breakdown of portfolio by security type and sector.
    Used for diversification analysis and portfolio visualization.
    
    Example:
        >>> allocation = AssetAllocation(
        ...     by_security_type={
        ...         SecurityType.equity: 65.0,
        ...         SecurityType.etf: 20.0,
        ...         SecurityType.bond: 10.0
        ...     },
        ...     by_sector={"Technology": 40.0, "Healthcare": 25.0},
        ...     cash_percent=5.0
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "by_security_type": {
                    "equity": 65.0,
                    "etf": 20.0,
                    "bond": 10.0,
                    "cash": 5.0,
                },
                "by_sector": {
                    "Technology": 40.0,
                    "Healthcare": 25.0,
                    "Financials": 15.0,
                    "Consumer": 10.0,
                    "Other": 10.0,
                },
                "cash_percent": 5.0,
            }
        },
    )

    by_security_type: Dict[SecurityType, float] = Field(
        default_factory=dict,
        description="Percentage breakdown by security type (equity, bond, etc.)",
    )
    by_sector: Dict[str, float] = Field(
        default_factory=dict,
        description="Percentage breakdown by sector (Technology, Healthcare, etc.)",
    )
    cash_percent: float = Field(0.0, ge=0, le=100, description="Cash percentage of portfolio")


__all__ = [
    "SecurityType",
    "TransactionType",
    "Security",
    "Holding",
    "InvestmentTransaction",
    "InvestmentAccount",
    "AssetAllocation",
]
