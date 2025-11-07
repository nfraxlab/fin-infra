# ADR-0020: Net Worth Tracking Architecture

**Status**: Accepted  
**Date**: 2025-11-06  
**Deciders**: fin-infra team  
**Context**: Section 17 V1 - Net Worth Tracking

## Context

Users need a comprehensive view of their financial health through net worth tracking that:
- Aggregates balances from multiple providers (banking, brokerage, crypto)
- Tracks historical changes over time (daily snapshots)
- Normalizes currencies for accurate totals
- Calculates market values for investments
- Detects significant changes and sends alerts
- Provides asset allocation breakdown for visualization

**Use Cases**:
- Personal finance apps (Mint, Credit Karma, Personal Capital)
- Wealth management dashboards
- Financial planning tools
- Retirement tracking
- Goal monitoring (reach $1M net worth by 2030)

**Current Limitations**:
- fin-infra has market data, banking, brokerage, crypto providers but no aggregation
- No historical tracking of net worth over time
- No unified view across providers
- svc-infra has infrastructure (db, jobs, cache, webhooks) but no financial aggregation logic

## Decision

Implement net worth tracking with **4-layer architecture**:

### Layer 1: Multi-Provider Aggregation
Fetch balances from all connected providers and normalize to base currency.

**Components**:
- `NetWorthAggregator`: Orchestrates provider calls, handles failures gracefully
- Provider integration: Banking (Plaid/Teller), Brokerage (Alpaca), Crypto (CCXT/CoinGecko)
- Currency normalization: ExchangeRate-API with 1h cache
- Market value calculation: Real-time quotes from market data providers

**Algorithm**:
```python
async def aggregate_net_worth(user_id: str) -> NetWorthSnapshot:
    # Parallel provider calls
    banking_task = fetch_banking_accounts(user_id)
    brokerage_task = fetch_brokerage_holdings(user_id)
    crypto_task = fetch_crypto_balances(user_id)
    
    # Wait for all (with timeout)
    banking, brokerage, crypto = await asyncio.gather(
        banking_task, brokerage_task, crypto_task,
        return_exceptions=True  # Don't fail if one provider fails
    )
    
    # Calculate totals
    total_assets = calculate_assets(banking, brokerage, crypto)
    total_liabilities = calculate_liabilities(banking)
    
    return NetWorthSnapshot(
        total_net_worth=total_assets - total_liabilities,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        ...
    )
```

### Layer 2: Snapshot Storage & Retrieval
Store historical snapshots with retention policy.

**Database Schema** (SQLAlchemy):
```python
class NetWorthSnapshotModel(Base):
    __tablename__ = "net_worth_snapshots"
    
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, index=True, nullable=False)
    snapshot_date = Column(DateTime, index=True, nullable=False)
    
    # Totals
    total_net_worth = Column(Float, nullable=False)
    total_assets = Column(Float, nullable=False)
    total_liabilities = Column(Float, nullable=False)
    
    # Change tracking
    change_from_previous = Column(Float)
    change_percentage = Column(Float)
    
    # Breakdowns (JSONB for flexibility)
    asset_breakdown = Column(JSON, nullable=False)
    liability_breakdown = Column(JSON, nullable=False)
    
    # Metadata
    asset_count = Column(Integer)
    liability_count = Column(Integer)
    providers = Column(JSON)
    base_currency = Column(String, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'snapshot_date'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )
```

**Retention Policy**:
- Daily snapshots: Keep for 90 days
- Weekly snapshots: Keep for 1 year (aggregate from daily)
- Monthly snapshots: Keep for 10 years (aggregate from weekly)
- Automated cleanup job runs weekly

### Layer 3: Change Detection & Alerts
Detect significant changes and emit webhook events.

**Detection Algorithm**:
```python
def detect_significant_change(current, previous) -> bool:
    change_amount = current.total_net_worth - previous.total_net_worth
    change_percent = abs(change_amount / previous.total_net_worth)
    
    return (
        change_percent >= 0.05 or      # 5% threshold
        abs(change_amount) >= 10000.0  # $10k threshold
    )
```

**Webhook Events**:
- `net_worth.snapshot_created`: After every snapshot (daily job)
- `net_worth.significant_change`: When change exceeds threshold
- `net_worth.milestone_reached`: When crossing $100k, $1M, etc.

### Layer 4: API & Builder
Easy integration for applications.

**Builder Pattern**:
```python
def easy_net_worth(
    banking: BankingProvider = None,
    brokerage: BrokerageProvider = None,
    crypto: CryptoProvider = None,
    market: MarketProvider = None,
    base_currency: str = "USD",
    snapshot_schedule: str = "daily",  # daily, weekly, manual
    change_threshold_percent: float = 0.05,
    change_threshold_amount: float = 10000.0,
    **config
) -> NetWorthTracker
```

**FastAPI Integration**:
```python
def add_net_worth_tracking(
    app: FastAPI,
    tracker: NetWorthTracker = None,
    prefix: str = "/net-worth",
    include_in_schema: bool = True,
) -> NetWorthTracker
```

**Endpoints**:
- `GET /net-worth/current`: Current net worth (cached 1h)
- `GET /net-worth/snapshots`: Historical snapshots (query: days, granularity)
- `GET /net-worth/breakdown`: Asset/liability breakdown (pie chart data)
- `POST /net-worth/snapshot`: Force snapshot creation (admin only)

## Data Models

### NetWorthSnapshot (Core DTO)

```python
@dataclass
class NetWorthSnapshot:
    """Net worth snapshot at a point in time."""
    
    # Identifiers
    id: str                           # UUID
    user_id: str                      # User identifier
    snapshot_date: datetime           # When snapshot was taken
    
    # Totals
    total_net_worth: float            # Assets - liabilities
    total_assets: float               # Sum of all assets
    total_liabilities: float          # Sum of all liabilities
    
    # Change tracking
    change_from_previous: float | None  # Net worth change from last snapshot
    change_percentage: float | None     # Percentage change
    
    # Asset breakdown
    cash: float                       # Checking, savings
    investments: float                # Stocks, bonds, mutual funds
    crypto: float                     # Bitcoin, Ethereum, etc.
    real_estate: float                # Property values
    vehicles: float                   # Car, boat values
    other_assets: float               # Collectibles, etc.
    
    # Liability breakdown
    credit_cards: float               # Credit card balances
    mortgages: float                  # Home loans
    auto_loans: float                 # Car loans
    student_loans: float              # Student debt
    personal_loans: float             # Unsecured debt
    lines_of_credit: float            # HELOC, etc.
    
    # Metadata
    asset_count: int                  # Number of asset accounts
    liability_count: int              # Number of liability accounts
    providers: list[str]              # List of providers used
    base_currency: str                # Currency for values (default: USD)
    created_at: datetime              # When record was created
```

### AssetAllocation (Breakdown DTO)

```python
@dataclass
class AssetAllocation:
    """Asset allocation breakdown for visualization."""
    
    # Amounts
    cash: float
    investments: float
    crypto: float
    real_estate: float
    vehicles: float
    other_assets: float
    
    # Percentages (calculated)
    cash_percentage: float
    investments_percentage: float
    crypto_percentage: float
    real_estate_percentage: float
    vehicles_percentage: float
    other_percentage: float
    
    # Total
    total_assets: float
```

### LiabilityBreakdown (Breakdown DTO)

```python
@dataclass
class LiabilityBreakdown:
    """Liability breakdown for visualization."""
    
    # Amounts
    credit_cards: float
    mortgages: float
    auto_loans: float
    student_loans: float
    personal_loans: float
    lines_of_credit: float
    
    # Percentages (calculated)
    credit_cards_percentage: float
    mortgages_percentage: float
    auto_loans_percentage: float
    student_loans_percentage: float
    personal_loans_percentage: float
    lines_of_credit_percentage: float
    
    # Total
    total_liabilities: float
```

### AssetDetail (Individual Asset DTO)

```python
@dataclass
class AssetDetail:
    """Individual asset account details."""
    
    account_id: str                   # Account identifier
    provider: str                     # Provider name (plaid, alpaca, ccxt)
    account_type: AssetCategory       # CASH, INVESTMENTS, CRYPTO, etc.
    name: str                         # Account name
    balance: float                    # Current balance
    currency: str                     # Account currency (USD, EUR, etc.)
    market_value: float | None        # Market value (for stocks/crypto)
    cost_basis: float | None          # Original purchase price
    gain_loss: float | None           # Unrealized gain/loss
    gain_loss_percentage: float | None  # Percentage gain/loss
    last_updated: datetime            # Last time balance was fetched
```

### LiabilityDetail (Individual Liability DTO)

```python
@dataclass
class LiabilityDetail:
    """Individual liability account details."""
    
    account_id: str                   # Account identifier
    provider: str                     # Provider name (plaid, teller)
    liability_type: LiabilityCategory # CREDIT_CARD, MORTGAGE, etc.
    name: str                         # Account name
    balance: float                    # Current balance owed
    currency: str                     # Account currency
    interest_rate: float | None       # APR (e.g., 0.18 for 18%)
    minimum_payment: float | None     # Minimum monthly payment
    due_date: datetime | None         # Next payment due date
    last_updated: datetime            # Last time balance was fetched
```

### Enums

```python
class AssetCategory(str, Enum):
    """Asset category types."""
    CASH = "cash"
    INVESTMENTS = "investments"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    VEHICLES = "vehicles"
    OTHER = "other"

class LiabilityCategory(str, Enum):
    """Liability category types."""
    CREDIT_CARD = "credit_card"
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    STUDENT_LOAN = "student_loan"
    PERSONAL_LOAN = "personal_loan"
    LINE_OF_CREDIT = "line_of_credit"
```

### API Request/Response Models

```python
@dataclass
class NetWorthRequest:
    """Request to calculate current net worth."""
    force_refresh: bool = False  # Skip cache, recalculate
    include_breakdown: bool = True  # Include asset/liability details

@dataclass
class NetWorthResponse:
    """Response with current net worth."""
    snapshot: NetWorthSnapshot
    asset_allocation: AssetAllocation
    liability_breakdown: LiabilityBreakdown
    asset_details: list[AssetDetail]
    liability_details: list[LiabilityDetail]
    processing_time_ms: int

@dataclass
class SnapshotHistoryRequest:
    """Request for historical snapshots."""
    days: int = 90  # Look back N days (max 730)
    granularity: str = "daily"  # daily, weekly, monthly

@dataclass
class SnapshotHistoryResponse:
    """Response with historical snapshots."""
    snapshots: list[NetWorthSnapshot]
    count: int
    start_date: datetime
    end_date: datetime
```

## svc-infra Integration

### Database (svc-infra.db)

**Usage**:
```python
from svc_infra.db import get_session

async def save_snapshot(snapshot: NetWorthSnapshot):
    async with get_session() as session:
        model = NetWorthSnapshotModel(...)
        session.add(model)
        await session.commit()

async def get_snapshots(user_id: str, days: int = 90):
    async with get_session() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(NetWorthSnapshotModel)
            .where(NetWorthSnapshotModel.user_id == user_id)
            .where(NetWorthSnapshotModel.snapshot_date >= cutoff)
            .order_by(NetWorthSnapshotModel.snapshot_date.desc())
        )
        return result.scalars().all()
```

**Migration** (Alembic):
```python
def upgrade():
    op.create_table(
        'net_worth_snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('total_net_worth', sa.Float(), nullable=False),
        sa.Column('total_assets', sa.Float(), nullable=False),
        sa.Column('total_liabilities', sa.Float(), nullable=False),
        sa.Column('change_from_previous', sa.Float()),
        sa.Column('change_percentage', sa.Float()),
        sa.Column('asset_breakdown', sa.JSON(), nullable=False),
        sa.Column('liability_breakdown', sa.JSON(), nullable=False),
        sa.Column('asset_count', sa.Integer()),
        sa.Column('liability_count', sa.Integer()),
        sa.Column('providers', sa.JSON()),
        sa.Column('base_currency', sa.String(), default='USD'),
        sa.Column('created_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
    )
    
    op.create_index('idx_user_date', 'net_worth_snapshots', ['user_id', 'snapshot_date'])
    op.create_index('idx_user_created', 'net_worth_snapshots', ['user_id', 'created_at'])
```

### Jobs (svc-infra.jobs)

**Daily Snapshot Scheduler**:
```python
from svc_infra.jobs.easy import easy_jobs

queue, scheduler = easy_jobs(app, driver="redis")

async def daily_net_worth_snapshot():
    """Run daily at midnight UTC."""
    users = await get_all_users()
    
    for user in users:
        try:
            # Calculate net worth
            snapshot = await net_worth_tracker.create_snapshot(user.id)
            
            # Save to database
            await save_snapshot(snapshot)
            
            # Check for significant change
            if is_significant_change(snapshot):
                await emit_event(
                    event_type="net_worth.significant_change",
                    data=snapshot.dict()
                )
        except Exception as e:
            logger.error(f"Failed to create snapshot for user {user.id}", exc_info=e)

scheduler.add_task(
    name="daily_net_worth_snapshot",
    interval_seconds=86400,  # 24 hours
    func=daily_net_worth_snapshot
)
```

### Cache (svc-infra.cache)

**Current Net Worth** (1h TTL):
```python
from svc_infra.cache import cache_read, cache_write

@cache_read(key="net_worth:current:{user_id}", ttl=3600)
async def get_current_net_worth(user_id: str) -> NetWorthSnapshot:
    return await net_worth_tracker.calculate_net_worth(user_id)
```

**Exchange Rates** (1h TTL):
```python
@cache_read(key="exchange_rate:{from_currency}:{to_currency}", ttl=3600)
async def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    provider = ExchangeRateProvider()
    return await provider.get_rate(from_currency, to_currency)
```

**Stock Prices** (15min TTL during market hours):
```python
@cache_read(key="stock_price:{symbol}", ttl=900)
async def get_stock_price(symbol: str) -> float:
    market_provider = easy_market()
    quote = market_provider.quote(symbol)
    return quote.price
```

**Cache Invalidation**:
- Current net worth: Invalidate after snapshot creation
- Exchange rates: Auto-expire after 1h
- Stock prices: Auto-expire after 15min (market hours) or until market open (after-hours)

### Webhooks (svc-infra.webhooks)

**Event Types**:
```python
from svc_infra.webhooks.add import add_webhooks

add_webhooks(
    app,
    signing_secret="your-webhook-secret",
    event_types=[
        "net_worth.snapshot_created",
        "net_worth.significant_change",
        "net_worth.milestone_reached",
    ]
)
```

**Event Payloads**:
```python
# Snapshot created (every daily run)
{
    "event_type": "net_worth.snapshot_created",
    "timestamp": "2025-11-06T00:00:00Z",
    "data": {
        "user_id": "user_123",
        "net_worth": 64000.0,
        "snapshot_date": "2025-11-06T00:00:00Z"
    }
}

# Significant change (>5% or >$10k)
{
    "event_type": "net_worth.significant_change",
    "timestamp": "2025-11-06T00:00:00Z",
    "data": {
        "user_id": "user_123",
        "previous_net_worth": 60000.0,
        "current_net_worth": 64000.0,
        "change_amount": 4000.0,
        "change_percentage": 0.0667,
        "snapshot_date": "2025-11-06T00:00:00Z"
    }
}

# Milestone reached ($100k, $1M, etc.)
{
    "event_type": "net_worth.milestone_reached",
    "timestamp": "2025-11-06T00:00:00Z",
    "data": {
        "user_id": "user_123",
        "milestone": 100000.0,
        "net_worth": 102000.0,
        "snapshot_date": "2025-11-06T00:00:00Z"
    }
}
```

## Implementation Plan

### Phase 1: Core Models & Calculator (Day 1)
- Create `models.py` with Pydantic V2 models (7 DTOs + 2 enums)
- Create `calculator.py` with net worth calculation logic
- Unit tests for calculation (assets - liabilities)

### Phase 2: Multi-Provider Aggregator (Day 2)
- Create `aggregator.py` with NetWorthAggregator class
- Integrate banking, brokerage, crypto providers
- Currency normalization with ExchangeRate-API
- Market value calculation for stocks/crypto
- Unit tests for aggregation

### Phase 3: Snapshot Storage (Day 3)
- Create SQLAlchemy model for snapshots
- Implement save/retrieve functions with svc-infra.db
- Change detection algorithm
- Retention policy cleanup job
- Unit tests for storage

### Phase 4: Easy Builder & FastAPI (Day 4)
- Create `ease.py` with easy_net_worth() builder
- Create `add.py` with add_net_worth_tracking() FastAPI integration
- 4 API endpoints (current, snapshots, breakdown, force snapshot)
- Integration with svc-infra dual routers
- Unit tests for builder and API

### Phase 5: Jobs & Webhooks Integration (Day 5)
- Daily snapshot scheduler with svc-infra.jobs
- Webhook events for significant changes
- Cache integration (current net worth, exchange rates, prices)
- End-to-end tests
- Documentation

## Alternatives Considered

### Alternative 1: Real-Time Calculation Only (No Snapshots)
**Pros**: Simpler implementation, no database storage needed  
**Cons**: No historical tracking, expensive to recalculate for charts, no change detection  
**Decision**: Rejected - historical tracking is core requirement

### Alternative 2: Store All Account Balances (Not Aggregated)
**Pros**: More granular data, can recalculate net worth later  
**Cons**: Large storage requirements, privacy concerns, complex queries  
**Decision**: Rejected - snapshots are sufficient, store breakdowns in JSONB

### Alternative 3: Manual Snapshot Creation Only
**Pros**: User control, fewer API calls to providers  
**Cons**: Users forget to create snapshots, gaps in historical data  
**Decision**: Rejected - automated daily snapshots are essential

### Alternative 4: Use Time-Series Database (InfluxDB, TimescaleDB)
**Pros**: Optimized for time-series queries, better performance  
**Cons**: Additional infrastructure, complexity, svc-infra uses PostgreSQL  
**Decision**: Rejected for V1 - PostgreSQL is sufficient, can migrate to TimescaleDB in V2 if needed

## Success Metrics

**V1 Completion Criteria**:
- ✅ Multi-provider aggregation (banking + brokerage + crypto)
- ✅ Currency normalization (all currencies → USD)
- ✅ Daily snapshots (stored in database with svc-infra.db)
- ✅ Historical retrieval (last 90 days)
- ✅ Change detection (>5% or >$10k triggers webhook)
- ✅ Easy builder (`easy_net_worth()`)
- ✅ FastAPI integration (4 endpoints)
- ✅ Comprehensive tests (90%+ coverage)
- ✅ Documentation (methodology + API reference)

**Performance Targets**:
- Snapshot calculation: <2 seconds (acceptable for background job)
- API response (cached): <100ms (fast user experience)
- API response (uncached): <2 seconds (real-time acceptable)
- Cache hit rate: >95% (minimize provider API calls)
- Database query: <50ms (efficient snapshot retrieval)

## Risks & Mitigations

### Risk 1: Provider API Failures
**Impact**: Incomplete net worth calculation  
**Mitigation**: 
- Graceful degradation (continue with available providers)
- Return cached snapshot if all providers fail
- Log errors with svc-infra.logging

### Risk 2: Exchange Rate API Limits
**Impact**: Currency normalization fails  
**Mitigation**:
- Cache rates for 1h (1,500 req/month free tier = 50/day, sufficient)
- Fall back to manual rates if API fails
- Upgrade to paid tier if needed ($9/month for 100,000 requests)

### Risk 3: Stock Price Staleness
**Impact**: Inaccurate market value for investments  
**Mitigation**:
- Cache prices for 15min during market hours
- Show last_updated timestamp in UI
- Refresh on user request (force_refresh parameter)

### Risk 4: Database Storage Growth
**Impact**: Large storage requirements for snapshots  
**Mitigation**:
- Retention policy (90 days daily, 1 year weekly, 10 years monthly)
- JSONB for flexible breakdowns (no schema changes)
- Automated cleanup job (weekly)

## Future Enhancements (V2)

**LLM-Enhanced Insights**:
- Natural language insights: "Your net worth increased 15% this year..."
- Debt reduction strategies: "Pay off credit card first (22% APR)..."
- Goal recommendations: "To reach $1M by 2030, save $800/month..."
- Asset allocation advice: "Your portfolio is 90% stocks (high risk)..."
- Multi-turn conversation: "How can I save more?", "Should I pay off mortgage early?"

**Additional Data Sources**:
- Real estate: Zillow API for property values
- Vehicles: KBB API for car values
- Manual asset entry: Collectibles, precious metals, art
- Tax estimation: Estimate tax liability based on income/deductions
- Retirement accounts: 401k, IRA projections

**Advanced Features**:
- Net worth forecasting: Predict net worth in 5/10/20 years
- What-if scenarios: "What if I pay off mortgage early?"
- Peer comparison: "You're in top 20% for your age group"
- Goal tracking: Create goals (retirement, home purchase) and track progress

---

**Decision Date**: 2025-11-06  
**Status**: Accepted  
**Next Steps**: Implementation (models.py, calculator.py, aggregator.py)
