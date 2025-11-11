"""Tax document data models (W-2, 1099-*, crypto tax reports).

Models for tax forms and crypto tax calculations:
- TaxDocument: Base model for all tax forms
- TaxFormW2: Wage and Tax Statement (employer wages)
- TaxForm1099INT: Interest Income
- TaxForm1099DIV: Dividends and Distributions
- TaxForm1099B: Proceeds from Broker Transactions (stocks, crypto)
- TaxForm1099MISC: Miscellaneous Income (staking, airdrops, freelance)
- CryptoTaxReport: Capital gains summary for cryptocurrency
- CryptoTransaction: Individual crypto trade details
- TaxLiability: Estimated tax liability calculation

IRS Requirements:
- Retain tax documents for 7 years (use svc-infra RetentionPolicy)
- Provide accurate Form 8949 data for crypto reporting
- Support both short-term (<= 1 year) and long-term (> 1 year) gains

Example:
    >>> from fin_infra.models.tax import TaxFormW2
    >>> w2 = TaxFormW2(
    ...     document_id="w2_2024_001",
    ...     user_id="user_123",
    ...     tax_year=2024,
    ...     issuer="Acme Corp",
    ...     issuer_ein="12-3456789",
    ...     wages=Decimal("75000.00"),
    ...     federal_tax_withheld=Decimal("12000.00"),
    ...     social_security_wages=Decimal("75000.00"),
    ...     social_security_tax_withheld=Decimal("4650.00"),
    ...     medicare_wages=Decimal("75000.00"),
    ...     medicare_tax_withheld=Decimal("1087.50")
    ... )
    >>> print(w2.wages)
    75000.00
"""

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class TaxDocument(BaseModel):
    """Base model for all tax documents.

    Common fields for all tax forms (W-2, 1099-*, etc.).
    Subclasses add form-specific fields.

    Attributes:
        document_id: Unique document identifier
        user_id: User who owns this document
        form_type: IRS form type (W2, 1099-INT, 1099-DIV, etc.)
        tax_year: Tax year (e.g., 2024)
        issuer: Employer or payer name
        issuer_ein: Employer Identification Number (optional)
        download_url: S3/GCS URL or local path to PDF (optional)
        status: Document status (pending, available, downloaded, error)
        created_at: Document creation timestamp
        updated_at: Last update timestamp
    """

    document_id: str
    user_id: str
    form_type: str  # "W2", "1099-INT", "1099-DIV", "1099-B", "1099-MISC"
    tax_year: int
    issuer: str  # Employer or payer name
    issuer_ein: str | None = None  # Employer Identification Number
    download_url: str | None = None  # S3/GCS URL or local path
    status: str = "available"  # "pending", "available", "downloaded", "error"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)


class TaxFormW2(TaxDocument):
    """Form W-2: Wage and Tax Statement.

    Employer-issued form reporting wages, tips, and taxes withheld.

    IRS Boxes:
        Box 1: Wages, tips, other compensation
        Box 2: Federal income tax withheld
        Box 3-4: Social Security wages and tax
        Box 5-6: Medicare wages and tax
        Box 12: Codes (retirement contributions, etc.)
        Box 13: Checkboxes (retirement plan, statutory employee, etc.)
        Box 15-20: State/local taxes

    Example:
        >>> w2 = TaxFormW2(
        ...     document_id="w2_2024_001",
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     issuer="Acme Corp",
        ...     wages=Decimal("75000.00"),
        ...     federal_tax_withheld=Decimal("12000.00"),
        ...     social_security_wages=Decimal("75000.00"),
        ...     social_security_tax_withheld=Decimal("4650.00"),
        ...     medicare_wages=Decimal("75000.00"),
        ...     medicare_tax_withheld=Decimal("1087.50"),
        ...     retirement_plan=True
        ... )
    """

    form_type: str = Field(default="W2", frozen=True)

    # Box 1: Wages, tips, other compensation
    wages: Decimal

    # Box 2: Federal income tax withheld
    federal_tax_withheld: Decimal

    # Box 3-4: Social Security
    social_security_wages: Decimal
    social_security_tax_withheld: Decimal

    # Box 5-6: Medicare
    medicare_wages: Decimal
    medicare_tax_withheld: Decimal

    # Box 12: Codes (retirement contributions, etc.)
    # {"D": "401k elective deferrals", "DD": "employer health coverage"}
    box_12_codes: dict[str, Decimal] = Field(default_factory=dict)

    # Box 13: Checkboxes
    statutory_employee: bool = False
    retirement_plan: bool = False
    third_party_sick_pay: bool = False

    # Box 15-20: State/local taxes
    state_wages: Decimal | None = None
    state_tax_withheld: Decimal | None = None
    state: str | None = None  # Two-letter state code (e.g., "CA")


class TaxForm1099INT(TaxDocument):
    """Form 1099-INT: Interest Income.

    Issued by banks and financial institutions for interest income >= $10.

    IRS Boxes:
        Box 1: Interest income
        Box 2: Early withdrawal penalty
        Box 3: Interest on U.S. Savings Bonds
        Box 4: Federal income tax withheld
        Box 8: Tax-exempt interest

    Example:
        >>> f1099int = TaxForm1099INT(
        ...     document_id="1099int_2024_001",
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     issuer="Acme Bank",
        ...     interest_income=Decimal("250.00")
        ... )
    """

    form_type: str = Field(default="1099-INT", frozen=True)

    # Box 1: Interest income
    interest_income: Decimal

    # Box 2: Early withdrawal penalty
    early_withdrawal_penalty: Decimal = Decimal("0.00")

    # Box 3: Interest on U.S. Savings Bonds
    us_savings_bonds_interest: Decimal = Decimal("0.00")

    # Box 4: Federal income tax withheld
    federal_tax_withheld: Decimal = Decimal("0.00")

    # Box 8: Tax-exempt interest
    tax_exempt_interest: Decimal = Decimal("0.00")


class TaxForm1099DIV(TaxDocument):
    """Form 1099-DIV: Dividends and Distributions.

    Issued by brokerages and mutual funds for dividend income >= $10.

    IRS Boxes:
        Box 1a: Total ordinary dividends
        Box 1b: Qualified dividends (taxed at lower rate)
        Box 2a: Total capital gain distributions
        Box 3: Nondividend distributions
        Box 4: Federal income tax withheld

    Example:
        >>> f1099div = TaxForm1099DIV(
        ...     document_id="1099div_2024_001",
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     issuer="Vanguard",
        ...     ordinary_dividends=Decimal("500.00"),
        ...     qualified_dividends=Decimal("400.00")
        ... )
    """

    form_type: str = Field(default="1099-DIV", frozen=True)

    # Box 1a: Total ordinary dividends
    ordinary_dividends: Decimal

    # Box 1b: Qualified dividends (taxed at lower capital gains rate)
    qualified_dividends: Decimal = Decimal("0.00")

    # Box 2a: Total capital gain distributions
    capital_gain_distributions: Decimal = Decimal("0.00")

    # Box 3: Nondividend distributions (return of capital)
    nondividend_distributions: Decimal = Decimal("0.00")

    # Box 4: Federal income tax withheld
    federal_tax_withheld: Decimal = Decimal("0.00")


class TaxForm1099B(TaxDocument):
    """Form 1099-B: Proceeds from Broker Transactions.

    Issued by brokerages for stock, bond, crypto sales.
    Used to calculate capital gains/losses.

    IRS Boxes:
        Description: Security or crypto asset sold
        Date acquired: Purchase date
        Date sold: Sale date
        Proceeds: Sale price
        Cost basis: Purchase price + fees
        Gain/Loss: Proceeds - Cost basis
        Holding period: Short-term (<= 1 year) or long-term (> 1 year)

    Example:
        >>> f1099b = TaxForm1099B(
        ...     document_id="1099b_2024_001",
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     issuer="Robinhood",
        ...     description="100 shares AAPL",
        ...     date_acquired=date(2023, 1, 15),
        ...     date_sold=date(2024, 6, 20),
        ...     proceeds=Decimal("15000.00"),
        ...     cost_basis=Decimal("10000.00"),
        ...     gain_or_loss=Decimal("5000.00"),
        ...     holding_period="long_term"
        ... )
    """

    form_type: str = Field(default="1099-B", frozen=True)

    # Description of property (stock, crypto, etc.)
    description: str

    # Date acquired and sold
    date_acquired: date | None = None
    date_sold: date

    # Proceeds (sales price)
    proceeds: Decimal

    # Cost or other basis (purchase price + fees)
    cost_basis: Decimal | None = None

    # Gain or loss (calculated: proceeds - cost_basis)
    gain_or_loss: Decimal | None = None

    # Short-term (<= 1 year) or long-term (> 1 year)
    holding_period: str = "unknown"  # "short_term", "long_term", "unknown"

    # Box 5: Federal income tax withheld
    federal_tax_withheld: Decimal = Decimal("0.00")


class TaxForm1099MISC(TaxDocument):
    """Form 1099-MISC: Miscellaneous Income.

    Issued for freelance income, staking rewards, airdrops, etc.

    IRS Boxes:
        Box 1: Rents
        Box 2: Royalties
        Box 3: Other income (freelance, staking, airdrops)
        Box 4: Federal income tax withheld

    Example:
        >>> f1099misc = TaxForm1099MISC(
        ...     document_id="1099misc_2024_001",
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     issuer="Coinbase",
        ...     other_income=Decimal("1200.00")  # Staking rewards
        ... )
    """

    form_type: str = Field(default="1099-MISC", frozen=True)

    # Box 1: Rents
    rents: Decimal = Decimal("0.00")

    # Box 2: Royalties
    royalties: Decimal = Decimal("0.00")

    # Box 3: Other income (staking rewards, airdrops, freelance)
    other_income: Decimal = Decimal("0.00")

    # Box 4: Federal income tax withheld
    federal_tax_withheld: Decimal = Decimal("0.00")


class CryptoTransaction(BaseModel):
    """Individual cryptocurrency transaction.

    Represents a single buy/sell trade for capital gains calculation.

    Attributes:
        transaction_id: Unique transaction ID
        symbol: Crypto symbol (BTC, ETH, etc.)
        transaction_type: "buy", "sell", "trade"
        date: Transaction date
        quantity: Amount of crypto
        price_per_unit: Price per coin/token
        total_value: quantity * price_per_unit
        fees: Exchange fees
        cost_basis: Purchase price (for sells)
        gain_or_loss: Profit/loss (for sells)
        holding_period: "short_term" or "long_term"

    Example:
        >>> tx = CryptoTransaction(
        ...     transaction_id="tx_001",
        ...     symbol="BTC",
        ...     transaction_type="sell",
        ...     date=date(2024, 6, 15),
        ...     quantity=Decimal("0.5"),
        ...     price_per_unit=Decimal("60000.00"),
        ...     total_value=Decimal("30000.00"),
        ...     fees=Decimal("50.00"),
        ...     cost_basis=Decimal("20000.00"),
        ...     gain_or_loss=Decimal("9950.00"),
        ...     holding_period="long_term"
        ... )
    """

    transaction_id: str
    symbol: str  # BTC, ETH, DOGE, etc.
    transaction_type: str  # "buy", "sell", "trade"
    date: date
    quantity: Decimal  # Amount of crypto
    price_per_unit: Decimal  # Price per coin/token
    total_value: Decimal  # quantity * price_per_unit
    fees: Decimal = Decimal("0.00")  # Exchange fees

    # For sell transactions
    cost_basis: Decimal | None = None  # Purchase price
    gain_or_loss: Decimal | None = None  # Profit/loss
    holding_period: str | None = None  # "short_term", "long_term"

    model_config = ConfigDict(from_attributes=True)


class CryptoTaxReport(BaseModel):
    """Cryptocurrency capital gains summary.

    Aggregated report for all crypto trades in a tax year.
    Used to generate Form 8949 and Schedule D.

    Attributes:
        user_id: User who owns this report
        tax_year: Tax year (e.g., 2024)
        total_gain_loss: Total net gain/loss
        short_term_gain_loss: Gains from assets held <= 1 year
        long_term_gain_loss: Gains from assets held > 1 year
        transaction_count: Number of trades
        cost_basis_method: "FIFO", "LIFO", "HIFO"
        transactions: Detailed list of all trades
        form_8949_data: IRS Form 8949 JSON (if available)

    Example:
        >>> report = CryptoTaxReport(
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     total_gain_loss=Decimal("15000.00"),
        ...     short_term_gain_loss=Decimal("5000.00"),
        ...     long_term_gain_loss=Decimal("10000.00"),
        ...     transaction_count=25,
        ...     cost_basis_method="FIFO",
        ...     transactions=[]
        ... )
    """

    user_id: str
    tax_year: int

    # Total capital gains/losses
    total_gain_loss: Decimal

    # Short-term (held <= 1 year, taxed as ordinary income)
    short_term_gain_loss: Decimal

    # Long-term (held > 1 year, taxed at lower capital gains rate)
    long_term_gain_loss: Decimal

    # Number of transactions
    transaction_count: int

    # Cost basis method (determines which coins are "sold" first)
    cost_basis_method: str  # "FIFO" (default), "LIFO", "HIFO"

    # Detailed transactions
    transactions: list[CryptoTransaction] = Field(default_factory=list)

    # Form 8949 data (if available from provider like TaxBit)
    form_8949_data: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class TaxLiability(BaseModel):
    """Estimated tax liability calculation.

    Basic tax estimate based on income, deductions, and filing status.
    NOT a substitute for professional tax advice.

    Attributes:
        user_id: User who owns this calculation
        tax_year: Tax year
        filing_status: "single", "married_joint", "married_separate", "head_of_household"
        gross_income: Total income before deductions
        deductions: Standard or itemized deductions
        taxable_income: gross_income - deductions
        federal_tax: Estimated federal income tax
        state_tax: Estimated state income tax (optional)
        total_tax: federal_tax + state_tax
        effective_tax_rate: (total_tax / gross_income) * 100

    Example:
        >>> liability = TaxLiability(
        ...     user_id="user_123",
        ...     tax_year=2024,
        ...     filing_status="single",
        ...     gross_income=Decimal("100000.00"),
        ...     deductions=Decimal("14600.00"),
        ...     taxable_income=Decimal("85400.00"),
        ...     federal_tax=Decimal("14296.00"),
        ...     state_tax=Decimal("5000.00"),
        ...     total_tax=Decimal("19296.00"),
        ...     effective_tax_rate=Decimal("19.30")
        ... )
    """

    user_id: str
    tax_year: int
    filing_status: str  # "single", "married_joint", "married_separate", "head_of_household"

    # Income and deductions
    gross_income: Decimal
    deductions: Decimal  # Standard or itemized
    taxable_income: Decimal  # gross_income - deductions

    # Tax calculations
    federal_tax: Decimal
    state_tax: Decimal = Decimal("0.00")
    total_tax: Decimal  # federal_tax + state_tax

    # Effective tax rate (percentage)
    effective_tax_rate: Decimal  # (total_tax / gross_income) * 100

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "TaxDocument",
    "TaxFormW2",
    "TaxForm1099INT",
    "TaxForm1099DIV",
    "TaxForm1099B",
    "TaxForm1099MISC",
    "CryptoTransaction",
    "CryptoTaxReport",
    "TaxLiability",
]
