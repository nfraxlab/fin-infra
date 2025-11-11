"""
Pydantic V2 models for net worth tracking.

**Data Models**:
- NetWorthSnapshot: Complete net worth snapshot at a point in time
- AssetAllocation: Asset breakdown by category (for pie charts)
- LiabilityBreakdown: Liability breakdown by category
- AssetDetail: Individual asset account details
- LiabilityDetail: Individual liability account details

**Enums**:
- AssetCategory: CASH, INVESTMENTS, CRYPTO, REAL_ESTATE, VEHICLES, OTHER
- LiabilityCategory: CREDIT_CARD, MORTGAGE, AUTO_LOAN, STUDENT_LOAN, PERSONAL_LOAN, LINE_OF_CREDIT

**API Models**:
- NetWorthRequest/Response: Current net worth endpoint
- SnapshotHistoryRequest/Response: Historical snapshots endpoint
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class AssetCategory(str, Enum):
    """
    Asset category types for classification.

    **Categories**:
    - CASH: Checking, savings, money market accounts (5-15% typical)
    - INVESTMENTS: Stocks, bonds, mutual funds, ETFs (60-80% typical)
    - CRYPTO: Bitcoin, Ethereum, other cryptocurrencies (0-10% typical)
    - REAL_ESTATE: Primary residence, investment properties (10-30% typical)
    - VEHICLES: Cars, boats, motorcycles (0-10% typical)
    - OTHER: Collectibles, precious metals, art (0-5% typical)
    """

    CASH = "cash"
    INVESTMENTS = "investments"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    VEHICLES = "vehicles"
    OTHER = "other"


class LiabilityCategory(str, Enum):
    """
    Liability category types for classification.

    **Categories**:
    - CREDIT_CARD: Credit card balances (15-25% APR, pay off quickly)
    - MORTGAGE: Home loans (70-85% of liabilities, 3-7% APR)
    - AUTO_LOAN: Car loans (5-10% of liabilities, 4-8% APR)
    - STUDENT_LOAN: Student debt (10-20% of liabilities, 3-6% APR)
    - PERSONAL_LOAN: Unsecured loans (0-5% of liabilities, 8-15% APR)
    - LINE_OF_CREDIT: HELOC, personal lines of credit (variable APR)
    """

    CREDIT_CARD = "credit_card"
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    STUDENT_LOAN = "student_loan"
    PERSONAL_LOAN = "personal_loan"
    LINE_OF_CREDIT = "line_of_credit"


class NetWorthSnapshot(BaseModel):
    """
    Net worth snapshot at a specific point in time.

    **Formula**: Net Worth = Total Assets - Total Liabilities

    **Example**:
    ```python
    snapshot = NetWorthSnapshot(
        id="snapshot_123",
        user_id="user_456",
        snapshot_date=datetime(2025, 11, 6),
        total_net_worth=55000.0,
        total_assets=60000.0,
        total_liabilities=5000.0,
        cash=10000.0,
        investments=45000.0,
        crypto=5000.0,
        credit_cards=5000.0,
        ...
    )
    ```
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "id": "snapshot_abc123",
                "user_id": "user_456",
                "snapshot_date": "2025-11-06T00:00:00Z",
                "total_net_worth": 55000.0,
                "total_assets": 60000.0,
                "total_liabilities": 5000.0,
                "change_from_previous": 4000.0,
                "change_percentage": 7.84,
                "cash": 10000.0,
                "investments": 45000.0,
                "crypto": 5000.0,
                "real_estate": 0.0,
                "vehicles": 0.0,
                "other_assets": 0.0,
                "credit_cards": 5000.0,
                "mortgages": 0.0,
                "auto_loans": 0.0,
                "student_loans": 0.0,
                "personal_loans": 0.0,
                "lines_of_credit": 0.0,
                "asset_count": 5,
                "liability_count": 1,
                "providers": ["plaid", "alpaca"],
                "base_currency": "USD",
                "created_at": "2025-11-06T00:05:23Z",
            }
        },
    )

    # Identifiers
    id: str = Field(..., description="Unique snapshot identifier (UUID)")
    user_id: str = Field(..., description="User identifier")
    snapshot_date: datetime = Field(
        ..., description="When snapshot was taken (typically midnight UTC)"
    )

    # Totals
    total_net_worth: float = Field(..., description="Net worth = assets - liabilities")
    total_assets: float = Field(..., ge=0, description="Sum of all assets")
    total_liabilities: float = Field(..., ge=0, description="Sum of all liabilities")

    # Change tracking (None for first snapshot)
    change_from_previous: float | None = Field(
        None, description="Net worth change from previous snapshot (dollars)"
    )
    change_percentage: float | None = Field(
        None, description="Net worth change from previous snapshot (percent)"
    )

    # Asset breakdown (6 categories)
    cash: float = Field(0.0, ge=0, description="Cash accounts (checking, savings, money market)")
    investments: float = Field(0.0, ge=0, description="Investments (stocks, bonds, mutual funds)")
    crypto: float = Field(0.0, ge=0, description="Cryptocurrency holdings")
    real_estate: float = Field(
        0.0, ge=0, description="Real estate value (primary + investment properties)"
    )
    vehicles: float = Field(0.0, ge=0, description="Vehicle value (cars, boats, motorcycles)")
    other_assets: float = Field(
        0.0, ge=0, description="Other assets (collectibles, precious metals)"
    )

    # Liability breakdown (6 categories)
    credit_cards: float = Field(0.0, ge=0, description="Credit card balances")
    mortgages: float = Field(0.0, ge=0, description="Mortgage balances")
    auto_loans: float = Field(0.0, ge=0, description="Auto loan balances")
    student_loans: float = Field(0.0, ge=0, description="Student loan balances")
    personal_loans: float = Field(0.0, ge=0, description="Personal loan balances")
    lines_of_credit: float = Field(0.0, ge=0, description="Line of credit balances (HELOC, etc.)")

    # Metadata
    asset_count: int = Field(0, ge=0, description="Number of asset accounts")
    liability_count: int = Field(0, ge=0, description="Number of liability accounts")
    providers: list[str] = Field(
        default_factory=list, description="List of providers used (plaid, alpaca, ccxt)"
    )
    base_currency: str = Field("USD", description="Currency for all values")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When record was created"
    )


class AssetAllocation(BaseModel):
    """
    Asset allocation breakdown for visualization (pie charts).

    **Example**:
    ```python
    allocation = AssetAllocation(
        cash=10000.0,
        investments=45000.0,
        crypto=5000.0,
        real_estate=0.0,
        vehicles=0.0,
        other_assets=0.0
    )
    # Computed fields automatically calculate percentages
    print(f"Cash: {allocation.cash_percentage:.1f}%")  # 16.7%
    ```
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Amounts (6 categories)
    cash: float = Field(0.0, ge=0, description="Cash balance")
    investments: float = Field(0.0, ge=0, description="Investment balance")
    crypto: float = Field(0.0, ge=0, description="Crypto balance")
    real_estate: float = Field(0.0, ge=0, description="Real estate value")
    vehicles: float = Field(0.0, ge=0, description="Vehicle value")
    other_assets: float = Field(0.0, ge=0, description="Other asset value")

    @computed_field  # type: ignore[misc]
    @property
    def total_assets(self) -> float:
        """Sum of all asset categories."""
        return (
            self.cash
            + self.investments
            + self.crypto
            + self.real_estate
            + self.vehicles
            + self.other_assets
        )

    @computed_field  # type: ignore[misc]
    @property
    def cash_percentage(self) -> float:
        """Cash as percentage of total assets."""
        return (self.cash / self.total_assets * 100) if self.total_assets > 0 else 0.0

    @computed_field  # type: ignore[misc]
    @property
    def investments_percentage(self) -> float:
        """Investments as percentage of total assets."""
        return (self.investments / self.total_assets * 100) if self.total_assets > 0 else 0.0

    @computed_field  # type: ignore[misc]
    @property
    def crypto_percentage(self) -> float:
        """Crypto as percentage of total assets."""
        return (self.crypto / self.total_assets * 100) if self.total_assets > 0 else 0.0

    @computed_field  # type: ignore[misc]
    @property
    def real_estate_percentage(self) -> float:
        """Real estate as percentage of total assets."""
        return (self.real_estate / self.total_assets * 100) if self.total_assets > 0 else 0.0

    @computed_field  # type: ignore[misc]
    @property
    def vehicles_percentage(self) -> float:
        """Vehicles as percentage of total assets."""
        return (self.vehicles / self.total_assets * 100) if self.total_assets > 0 else 0.0

    @computed_field  # type: ignore[misc]
    @property
    def other_percentage(self) -> float:
        """Other assets as percentage of total assets."""
        return (self.other_assets / self.total_assets * 100) if self.total_assets > 0 else 0.0


class LiabilityBreakdown(BaseModel):
    """
    Liability breakdown for visualization (pie charts).

    **Example**:
    ```python
    breakdown = LiabilityBreakdown(
        credit_cards=5000.0,
        mortgages=0.0,
        auto_loans=0.0,
        student_loans=0.0,
        personal_loans=0.0,
        lines_of_credit=0.0
    )
    print(f"Credit Cards: {breakdown.credit_cards_percentage:.1f}%")  # 100.0%
    ```
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Amounts (6 categories)
    credit_cards: float = Field(0.0, ge=0, description="Credit card balance")
    mortgages: float = Field(0.0, ge=0, description="Mortgage balance")
    auto_loans: float = Field(0.0, ge=0, description="Auto loan balance")
    student_loans: float = Field(0.0, ge=0, description="Student loan balance")
    personal_loans: float = Field(0.0, ge=0, description="Personal loan balance")
    lines_of_credit: float = Field(0.0, ge=0, description="Line of credit balance")

    @computed_field  # type: ignore[misc]
    @property
    def total_liabilities(self) -> float:
        """Sum of all liability categories."""
        return (
            self.credit_cards
            + self.mortgages
            + self.auto_loans
            + self.student_loans
            + self.personal_loans
            + self.lines_of_credit
        )

    @computed_field  # type: ignore[misc]
    @property
    def credit_cards_percentage(self) -> float:
        """Credit cards as percentage of total liabilities."""
        return (
            (self.credit_cards / self.total_liabilities * 100)
            if self.total_liabilities > 0
            else 0.0
        )

    @computed_field  # type: ignore[misc]
    @property
    def mortgages_percentage(self) -> float:
        """Mortgages as percentage of total liabilities."""
        return (
            (self.mortgages / self.total_liabilities * 100) if self.total_liabilities > 0 else 0.0
        )

    @computed_field  # type: ignore[misc]
    @property
    def auto_loans_percentage(self) -> float:
        """Auto loans as percentage of total liabilities."""
        return (
            (self.auto_loans / self.total_liabilities * 100) if self.total_liabilities > 0 else 0.0
        )

    @computed_field  # type: ignore[misc]
    @property
    def student_loans_percentage(self) -> float:
        """Student loans as percentage of total liabilities."""
        return (
            (self.student_loans / self.total_liabilities * 100)
            if self.total_liabilities > 0
            else 0.0
        )

    @computed_field  # type: ignore[misc]
    @property
    def personal_loans_percentage(self) -> float:
        """Personal loans as percentage of total liabilities."""
        return (
            (self.personal_loans / self.total_liabilities * 100)
            if self.total_liabilities > 0
            else 0.0
        )

    @computed_field  # type: ignore[misc]
    @property
    def lines_of_credit_percentage(self) -> float:
        """Lines of credit as percentage of total liabilities."""
        return (
            (self.lines_of_credit / self.total_liabilities * 100)
            if self.total_liabilities > 0
            else 0.0
        )


class AssetDetail(BaseModel):
    """
    Individual asset account details.

    **Example**:
    ```python
    detail = AssetDetail(
        account_id="acct_abc123",
        provider="alpaca",
        account_type=AssetCategory.INVESTMENTS,
        name="Brokerage Account",
        balance=45000.0,
        currency="USD",
        market_value=50000.0,
        cost_basis=40000.0,
        gain_loss=10000.0,
        gain_loss_percentage=25.0,
        last_updated=datetime.utcnow()
    )
    ```
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    account_id: str = Field(..., description="Account identifier from provider")
    provider: str = Field(..., description="Provider name (plaid, alpaca, ccxt)")
    account_type: AssetCategory = Field(..., description="Asset category")
    name: str = Field(..., description="Account name (e.g., 'Chase Checking')")
    balance: float = Field(..., ge=0, description="Current balance")
    currency: str = Field("USD", description="Account currency")
    market_value: float | None = Field(None, ge=0, description="Market value (for stocks/crypto)")
    cost_basis: float | None = Field(None, ge=0, description="Original purchase price")
    gain_loss: float | None = Field(
        None, description="Unrealized gain/loss (market_value - cost_basis)"
    )
    gain_loss_percentage: float | None = Field(
        None, description="Percentage gain/loss ((gain_loss / cost_basis) * 100)"
    )
    last_updated: datetime = Field(..., description="Last time balance was fetched")


class LiabilityDetail(BaseModel):
    """
    Individual liability account details.

    **Example**:
    ```python
    detail = LiabilityDetail(
        account_id="acct_xyz789",
        provider="plaid",
        liability_type=LiabilityCategory.CREDIT_CARD,
        name="Chase Freedom",
        balance=5000.0,
        currency="USD",
        interest_rate=0.18,  # 18% APR
        minimum_payment=150.0,
        due_date=datetime(2025, 11, 15),
        last_updated=datetime.utcnow()
    )
    ```
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    account_id: str = Field(..., description="Account identifier from provider")
    provider: str = Field(..., description="Provider name (plaid, teller)")
    liability_type: LiabilityCategory = Field(..., description="Liability category")
    name: str = Field(..., description="Account name (e.g., 'Chase Freedom Credit Card')")
    balance: float = Field(..., ge=0, description="Current balance owed")
    currency: str = Field("USD", description="Account currency")
    interest_rate: float | None = Field(None, ge=0, le=1, description="APR (e.g., 0.18 for 18%)")
    minimum_payment: float | None = Field(None, ge=0, description="Minimum monthly payment")
    due_date: datetime | None = Field(None, description="Next payment due date")
    last_updated: datetime = Field(..., description="Last time balance was fetched")


# API Request/Response Models


class NetWorthRequest(BaseModel):
    """
    Request to calculate current net worth.

    **Example**:
    ```python
    request = NetWorthRequest(
        force_refresh=True,
        include_breakdown=True
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    force_refresh: bool = Field(False, description="Skip cache and recalculate from providers")
    include_breakdown: bool = Field(True, description="Include asset/liability details in response")


class NetWorthResponse(BaseModel):
    """
    Response with current net worth.

    **Example**:
    ```python
    response = NetWorthResponse(
        snapshot=NetWorthSnapshot(...),
        asset_allocation=AssetAllocation(...),
        liability_breakdown=LiabilityBreakdown(...),
        asset_details=[AssetDetail(...)],
        liability_details=[LiabilityDetail(...)],
        processing_time_ms=1250
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    snapshot: NetWorthSnapshot = Field(..., description="Net worth snapshot")
    asset_allocation: AssetAllocation = Field(..., description="Asset breakdown by category")
    liability_breakdown: LiabilityBreakdown = Field(
        ..., description="Liability breakdown by category"
    )
    asset_details: list[AssetDetail] = Field(
        default_factory=list, description="Individual asset account details"
    )
    liability_details: list[LiabilityDetail] = Field(
        default_factory=list, description="Individual liability account details"
    )
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")


class SnapshotHistoryRequest(BaseModel):
    """
    Request for historical snapshots.

    **Example**:
    ```python
    request = SnapshotHistoryRequest(
        days=90,
        granularity="daily"
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    days: int = Field(90, ge=1, le=730, description="Look back N days (max 2 years)")
    granularity: str = Field(
        "daily",
        pattern="^(daily|weekly|monthly)$",
        description="Snapshot granularity (daily, weekly, monthly)",
    )


class SnapshotHistoryResponse(BaseModel):
    """
    Response with historical snapshots.

    **Example**:
    ```python
    response = SnapshotHistoryResponse(
        snapshots=[NetWorthSnapshot(...), ...],
        count=90,
        start_date=datetime(2025, 8, 8),
        end_date=datetime(2025, 11, 6)
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    snapshots: list[NetWorthSnapshot] = Field(default_factory=list, description="List of snapshots")
    count: int = Field(..., ge=0, description="Number of snapshots returned")
    start_date: datetime = Field(..., description="Earliest snapshot date")
    end_date: datetime = Field(..., description="Latest snapshot date")


# ===========================
# V2 LLM Endpoint Models
# ===========================


class InsightsRequest(BaseModel):
    """
    Request for LLM-generated financial insights.

    **Example**:
    ```python
    request = InsightsRequest(
        user_id="user_123",
        type="wealth_trends",
        access_token="plaid_token_abc"
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., description="User identifier")
    type: str = Field(
        ...,
        description="Insight type: wealth_trends, debt_reduction, goal_recommendations, asset_allocation",
    )
    access_token: str | None = Field(None, description="Provider access token")
    days: int = Field(90, ge=7, le=365, description="Historical data period")


class ConversationRequest(BaseModel):
    """
    Request for multi-turn financial conversation.

    **Example**:
    ```python
    request = ConversationRequest(
        user_id="user_123",
        question="How can I save more money each month?",
        session_id="session_abc",
        access_token="plaid_token_abc"
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., description="User identifier")
    question: str = Field(..., min_length=3, max_length=500, description="User question")
    session_id: str | None = Field(None, description="Conversation session ID")
    access_token: str | None = Field(None, description="Provider access token")


class ConversationResponse(BaseModel):
    """
    Response from financial conversation.

    **Example**:
    ```python
    response = ConversationResponse(
        answer="Based on your spending...",
        follow_up_questions=["Would you like...", "Have you considered..."],
        confidence=0.92,
        sources=["current_net_worth", "goal_retirement"]
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    answer: str = Field(..., description="LLM-generated answer")
    follow_up_questions: list[str] = Field(
        default_factory=list, description="Suggested follow-up questions"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Response confidence score")
    sources: list[str] = Field(default_factory=list, description="Data sources used")


class GoalCreateRequest(BaseModel):
    """
    Request to create/validate financial goal.

    **Example**:
    ```python
    request = GoalCreateRequest(
        user_id="user_123",
        goal={
            "type": "retirement",
            "target_amount": 2000000.0,
            "target_age": 65,
            "current_age": 35
        },
        access_token="plaid_token_abc"
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., description="User identifier")
    goal: dict = Field(..., description="Goal details")
    access_token: str | None = Field(None, description="Provider access token")


class GoalProgressResponse(BaseModel):
    """
    Response with goal progress report.

    **Example**:
    ```python
    response = GoalProgressResponse(
        goal_id="goal_abc123",
        progress_percentage=45.0,
        on_track=True,
        required_monthly_savings=1500.0,
        actual_monthly_savings=1650.0,
        estimated_completion_date="2055-01-15",
        recommendations=["Increase contributions...", "Consider..."]
    )
    ```
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    goal_id: str = Field(..., description="Goal identifier")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress %")
    on_track: bool = Field(..., description="Whether goal is on track")
    required_monthly_savings: float = Field(..., description="Required monthly savings")
    actual_monthly_savings: float = Field(..., description="Actual monthly savings")
    estimated_completion_date: str = Field(..., description="Estimated completion date")
    recommendations: list[str] = Field(default_factory=list, description="LLM recommendations")
