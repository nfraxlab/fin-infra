# Net Worth Tracking - Research Document

**Date**: 2025-11-06  
**Version**: V1 Research  
**Goal**: Calculate and track net worth from multi-provider aggregation with daily snapshots

## Executive Summary

Net worth tracking requires:
1. **Multi-provider aggregation**: Banking (Plaid/Teller) + Brokerage (Alpaca) + Crypto (CCXT/CoinGecko)
2. **Currency normalization**: Convert all balances to base currency (USD) using exchange rates
3. **Market value calculation**: Real-time quotes for stocks/crypto, periodic appraisal for real estate
4. **Historical snapshots**: Daily storage with retention policy (daily → weekly → monthly)
5. **Change detection**: Trigger alerts for significant changes (>5% or >$10k)

**svc-infra Reuse**:
- ✅ **svc_infra.db**: SQLAlchemy models for snapshot storage
- ✅ **svc_infra.jobs**: Daily snapshot scheduling with scheduler.add_task()
- ✅ **svc_infra.cache**: Current net worth caching (1h TTL, 95% hit rate expected)
- ✅ **svc_infra.webhooks**: Alerts for significant changes

**Classification**: Type A (financial-specific net worth calculation; svc-infra provides infrastructure only)

## 1. Net Worth Calculation Methodology

### Formula

```
Net Worth = Total Assets - Total Liabilities
```

### Asset Categories

| Category | Examples | Valuation Method | Provider |
|----------|----------|------------------|----------|
| **Cash** | Checking, savings, money market | Current balance | Banking (Plaid/Teller) |
| **Investments** | Stocks, bonds, mutual funds, ETFs | Market value (real-time quotes) | Brokerage (Alpaca) + Market (Alpha Vantage) |
| **Crypto** | Bitcoin, Ethereum, altcoins | Market value (real-time quotes) | Crypto (CCXT/CoinGecko) |
| **Real Estate** | Primary residence, investment properties | Periodic appraisal or Zillow estimate | Manual entry (V1), Zillow API (V2) |
| **Vehicles** | Cars, boats, RVs | KBB value or manual entry | Manual entry (V1), KBB API (V2) |
| **Other** | Collectibles, precious metals, art | Manual entry or appraisal | Manual entry |

**Asset Breakdown** (typical distribution):
- Cash: 5-15% (emergency fund, liquidity)
- Investments: 60-80% (long-term growth)
- Real Estate: 10-30% (primary residence, rental properties)
- Vehicles: 0-10% (depreciating assets)
- Crypto: 0-10% (high-risk, high-reward)
- Other: 0-5% (collectibles, precious metals)

### Liability Categories

| Category | Examples | Balance Type | Interest Rate | Provider |
|----------|----------|--------------|---------------|----------|
| **Credit Cards** | Visa, Mastercard, Amex | Revolving | 15-25% APR | Banking (Plaid/Teller) |
| **Mortgages** | Primary, investment properties | Installment | 3-7% APR | Banking (Plaid/Teller) |
| **Auto Loans** | Car, truck, RV | Installment | 4-8% APR | Banking (Plaid/Teller) |
| **Student Loans** | Federal, private | Installment | 3-6% APR | Banking (Plaid/Teller) |
| **Personal Loans** | Unsecured debt | Installment | 8-15% APR | Banking (Plaid/Teller) |
| **Lines of Credit** | HELOC, personal LOC | Revolving | 5-10% APR | Banking (Plaid/Teller) |

**Liability Breakdown** (typical distribution):
- Mortgages: 70-85% (largest debt, lowest interest)
- Student Loans: 10-20% (long-term, low interest)
- Auto Loans: 5-10% (medium-term, medium interest)
- Credit Cards: 0-10% (high interest, should be paid off quickly)
- Personal Loans: 0-5% (uncommon)

### Currency Normalization

All balances must be converted to base currency (default: USD) for accurate aggregation.

**Exchange Rate Sources**:
- V1: ExchangeRate-API (free tier, 1,500 requests/month, daily updates)
- V2: Forex provider (real-time rates, paid tier)

**Normalization Algorithm**:
```python
def normalize_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convert amount from one currency to another.
    
    Args:
        amount: Amount in original currency
        from_currency: ISO 4217 code (e.g., "EUR")
        to_currency: ISO 4217 code (e.g., "USD")
    
    Returns:
        Amount in target currency
    
    Example:
        >>> normalize_currency(1000.0, "EUR", "USD")
        1080.0  # Assuming 1 EUR = 1.08 USD
    """
    if from_currency == to_currency:
        return amount
    
    # Fetch exchange rate from provider (cached 1h)
    rate = get_exchange_rate(from_currency, to_currency)
    
    return amount * rate
```

**Caching Strategy**:
- Exchange rates cached for 1 hour (svc-infra.cache)
- Reduces API calls by 95%+ (rates don't change frequently)
- Cache key: `exchange_rate:{from_currency}:{to_currency}`

### Market Value Calculation

For stocks, ETFs, crypto:

**Algorithm**:
```python
def calculate_market_value(holdings: list[Holding]) -> float:
    """
    Calculate total market value of investment holdings.
    
    Args:
        holdings: List of holdings (symbol, quantity, currency)
    
    Returns:
        Total market value in base currency
    
    Example:
        >>> holdings = [
        ...     Holding(symbol="AAPL", quantity=10, currency="USD"),
        ...     Holding(symbol="BTC", quantity=0.5, currency="USD"),
        ... ]
        >>> calculate_market_value(holdings)
        18500.0  # $1750/share * 10 + $16,000/BTC * 0.5
    """
    total = 0.0
    
    for holding in holdings:
        # Fetch current price from market data provider
        price = get_current_price(holding.symbol)
        
        # Calculate value
        value = price * holding.quantity
        
        # Normalize currency
        value_usd = normalize_currency(value, holding.currency, "USD")
        
        total += value_usd
    
    return total
```

**Price Sources**:
- Stocks/ETFs: Alpha Vantage (V1), Yahoo Finance (fallback)
- Crypto: CoinGecko (free), CCXT (pro)
- Forex: ExchangeRate-API (V1), real-time provider (V2)

**Caching Strategy**:
- Stock prices cached for 15 minutes during market hours (svc-infra.cache)
- Crypto prices cached for 1 minute (more volatile)
- After-hours: cache until market open (reduce API calls)

## 2. Historical Tracking Strategies

### Snapshot Schedule

**Daily Snapshots** (default):
- Run at midnight UTC (configurable timezone)
- Store: net worth, asset breakdown, liability breakdown, timestamp
- Retention: Keep daily for 90 days

**Change-Triggered Snapshots**:
- Trigger on significant change: >5% OR >$10,000 (configurable)
- Use case: Detect market crashes, windfalls, large purchases
- Example: Net worth drops from $500k → $450k (10% drop) → extra snapshot + webhook alert

**Weekly Snapshots**:
- Aggregate from daily snapshots (every Sunday)
- Retention: Keep weekly for 1 year

**Monthly Snapshots**:
- Aggregate from weekly snapshots (last day of month)
- Retention: Keep monthly for 10 years

### Snapshot Data Model

```python
@dataclass
class NetWorthSnapshot:
    id: str                           # UUID
    user_id: str                      # User identifier
    snapshot_date: datetime           # When snapshot was taken
    total_net_worth: float            # Assets - liabilities
    total_assets: float               # Sum of all assets
    total_liabilities: float          # Sum of all liabilities
    change_from_previous: float       # Net worth change from last snapshot
    change_percentage: float          # Percentage change
    
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

### Storage Strategy

**Database Schema** (SQLAlchemy):
```python
class NetWorthSnapshotModel(Base):
    __tablename__ = "net_worth_snapshots"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    snapshot_date = Column(DateTime, index=True, nullable=False)
    total_net_worth = Column(Float, nullable=False)
    total_assets = Column(Float, nullable=False)
    total_liabilities = Column(Float, nullable=False)
    change_from_previous = Column(Float)
    change_percentage = Column(Float)
    
    # Asset breakdown (JSONB for flexibility)
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

**Retention Policy** (automated cleanup):
```python
# Delete snapshots older than retention period
DELETE FROM net_worth_snapshots
WHERE user_id = :user_id
  AND snapshot_date < :cutoff_date
  AND snapshot_type = 'daily'
```

**Retention periods**:
- Daily: 90 days (3 months)
- Weekly: 365 days (1 year)
- Monthly: 3,650 days (10 years)

### Change Detection

**Algorithm**:
```python
def detect_significant_change(
    current: NetWorthSnapshot,
    previous: NetWorthSnapshot,
    threshold_percent: float = 0.05,  # 5%
    threshold_amount: float = 10000.0  # $10k
) -> bool:
    """
    Detect if net worth change is significant.
    
    Args:
        current: Current snapshot
        previous: Previous snapshot
        threshold_percent: Percentage change threshold (default: 5%)
        threshold_amount: Absolute change threshold (default: $10k)
    
    Returns:
        True if change is significant
    
    Examples:
        >>> current = NetWorthSnapshot(total_net_worth=550000)
        >>> previous = NetWorthSnapshot(total_net_worth=500000)
        >>> detect_significant_change(current, previous)
        True  # 10% increase, exceeds 5% threshold
        
        >>> current = NetWorthSnapshot(total_net_worth=510000)
        >>> previous = NetWorthSnapshot(total_net_worth=500000)
        >>> detect_significant_change(current, previous)
        True  # $10k increase, matches threshold
    """
    # Calculate change
    change_amount = current.total_net_worth - previous.total_net_worth
    change_percent = abs(change_amount / previous.total_net_worth)
    
    # Check thresholds
    return (
        change_percent >= threshold_percent or
        abs(change_amount) >= threshold_amount
    )
```

**Webhook Alerts** (svc-infra.webhooks):
```python
# Emit event when significant change detected
await emit_event(
    event_type="net_worth.significant_change",
    data={
        "user_id": user_id,
        "previous_net_worth": previous.total_net_worth,
        "current_net_worth": current.total_net_worth,
        "change_amount": change_amount,
        "change_percentage": change_percent,
        "snapshot_date": current.snapshot_date.isoformat(),
    }
)
```

## 3. Multi-Provider Aggregation

### Provider Integration

**Banking** (cash + credit cards + loans):
- Plaid (primary, 12,000+ institutions)
- Teller (alternative, 5,000+ institutions)
- Returns: Account balances, credit card balances, loan balances

**Brokerage** (stocks, bonds, ETFs):
- Alpaca (paper/live trading)
- SnapTrade (V2, multi-broker aggregation)
- Returns: Holdings (symbol, quantity, cost basis), cash balance

**Crypto** (Bitcoin, Ethereum, altcoins):
- CCXT (exchange integration)
- CoinGecko (price data)
- Returns: Wallet balances, exchange balances

**Market Data** (stock/crypto prices):
- Alpha Vantage (stocks, default)
- CoinGecko (crypto, free)
- Yahoo Finance (fallback)
- Returns: Real-time quotes, historical prices

### Aggregation Algorithm

```python
async def aggregate_net_worth(
    user_id: str,
    banking_provider: BankingProvider,
    brokerage_provider: BrokerageProvider,
    crypto_provider: CryptoProvider,
    market_provider: MarketProvider,
    base_currency: str = "USD"
) -> NetWorthSnapshot:
    """
    Aggregate net worth from all providers.
    
    Args:
        user_id: User identifier
        banking_provider: Banking integration (Plaid/Teller)
        brokerage_provider: Brokerage integration (Alpaca)
        crypto_provider: Crypto integration (CCXT)
        market_provider: Market data (Alpha Vantage)
        base_currency: Target currency (default: USD)
    
    Returns:
        NetWorthSnapshot with aggregated data
    """
    # 1. Fetch banking accounts (cash + credit cards + loans)
    banking_accounts = await banking_provider.get_accounts(user_id)
    
    # 2. Fetch brokerage holdings (stocks + cash)
    brokerage_holdings = await brokerage_provider.get_holdings(user_id)
    
    # 3. Fetch crypto balances
    crypto_balances = await crypto_provider.get_balances(user_id)
    
    # 4. Calculate asset totals
    cash = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type in ["checking", "savings", "money_market"]
    )
    
    investments = await calculate_investment_value(
        brokerage_holdings, market_provider, base_currency
    )
    
    crypto = await calculate_crypto_value(
        crypto_balances, market_provider, base_currency
    )
    
    # V1: Manual entry for real estate, vehicles, other
    real_estate = 0.0  # TODO: Manual entry
    vehicles = 0.0     # TODO: Manual entry
    other_assets = 0.0 # TODO: Manual entry
    
    total_assets = cash + investments + crypto + real_estate + vehicles + other_assets
    
    # 5. Calculate liability totals
    credit_cards = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type == "credit_card"
    )
    
    mortgages = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type == "mortgage"
    )
    
    auto_loans = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type == "auto_loan"
    )
    
    student_loans = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type == "student_loan"
    )
    
    personal_loans = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type == "personal_loan"
    )
    
    lines_of_credit = sum(
        normalize_currency(acc.balance, acc.currency, base_currency)
        for acc in banking_accounts
        if acc.type == "line_of_credit"
    )
    
    total_liabilities = (
        credit_cards + mortgages + auto_loans + 
        student_loans + personal_loans + lines_of_credit
    )
    
    # 6. Calculate net worth
    total_net_worth = total_assets - total_liabilities
    
    # 7. Get previous snapshot for change calculation
    previous = await get_latest_snapshot(user_id)
    change_from_previous = (
        total_net_worth - previous.total_net_worth 
        if previous else 0.0
    )
    change_percentage = (
        change_from_previous / previous.total_net_worth 
        if previous and previous.total_net_worth > 0 else 0.0
    )
    
    # 8. Build snapshot
    return NetWorthSnapshot(
        id=str(uuid.uuid4()),
        user_id=user_id,
        snapshot_date=datetime.utcnow(),
        total_net_worth=total_net_worth,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        change_from_previous=change_from_previous,
        change_percentage=change_percentage,
        cash=cash,
        investments=investments,
        crypto=crypto,
        real_estate=real_estate,
        vehicles=vehicles,
        other_assets=other_assets,
        credit_cards=credit_cards,
        mortgages=mortgages,
        auto_loans=auto_loans,
        student_loans=student_loans,
        personal_loans=personal_loans,
        lines_of_credit=lines_of_credit,
        asset_count=len(banking_accounts) + len(brokerage_holdings) + len(crypto_balances),
        liability_count=len([acc for acc in banking_accounts if acc.balance < 0]),
        providers=["banking", "brokerage", "crypto"],
        base_currency=base_currency,
        created_at=datetime.utcnow()
    )
```

### Error Handling

**Provider Failures**:
- If banking provider fails → continue with brokerage + crypto (partial snapshot)
- If all providers fail → return cached snapshot (stale data better than no data)
- Log errors to svc-infra.logging with context

**Data Quality Issues**:
- Missing prices: Use last known price (cached) or skip asset
- Invalid balances: Log warning, exclude from calculation
- Currency conversion failure: Fall back to manual rate or skip account

## 4. svc-infra Integration

### Database (svc-infra.db)

**Snapshot Storage**:
```python
from svc_infra.db import get_session
from fin_infra.net_worth.models import NetWorthSnapshotModel

async def save_snapshot(snapshot: NetWorthSnapshot):
    """Save snapshot to database using svc-infra.db."""
    async with get_session() as session:
        model = NetWorthSnapshotModel(
            id=snapshot.id,
            user_id=snapshot.user_id,
            snapshot_date=snapshot.snapshot_date,
            total_net_worth=snapshot.total_net_worth,
            total_assets=snapshot.total_assets,
            total_liabilities=snapshot.total_liabilities,
            change_from_previous=snapshot.change_from_previous,
            change_percentage=snapshot.change_percentage,
            asset_breakdown={
                "cash": snapshot.cash,
                "investments": snapshot.investments,
                "crypto": snapshot.crypto,
                "real_estate": snapshot.real_estate,
                "vehicles": snapshot.vehicles,
                "other_assets": snapshot.other_assets,
            },
            liability_breakdown={
                "credit_cards": snapshot.credit_cards,
                "mortgages": snapshot.mortgages,
                "auto_loans": snapshot.auto_loans,
                "student_loans": snapshot.student_loans,
                "personal_loans": snapshot.personal_loans,
                "lines_of_credit": snapshot.lines_of_credit,
            },
            asset_count=snapshot.asset_count,
            liability_count=snapshot.liability_count,
            providers=snapshot.providers,
            base_currency=snapshot.base_currency,
        )
        session.add(model)
        await session.commit()
```

### Jobs (svc-infra.jobs)

**Daily Snapshot Scheduler**:
```python
from svc_infra.jobs.easy import easy_jobs
from fin_infra.net_worth import easy_net_worth

# Setup jobs
queue, scheduler = easy_jobs(app, driver="redis", redis_url="redis://localhost")

# Setup net worth tracker
net_worth_tracker = easy_net_worth(
    banking=easy_banking(),
    brokerage=easy_brokerage(),
    crypto=easy_crypto()
)

# Define snapshot task
async def daily_net_worth_snapshot():
    """Run daily at midnight UTC."""
    users = await get_all_users()
    
    for user in users:
        # Calculate net worth
        snapshot = await net_worth_tracker.create_snapshot(user.id)
        
        # Save to database
        await save_snapshot(snapshot)
        
        # Check for significant change
        if snapshot.change_percentage >= 0.05 or abs(snapshot.change_from_previous) >= 10000:
            # Emit webhook
            await emit_event(
                event_type="net_worth.significant_change",
                data={
                    "user_id": user.id,
                    "net_worth": snapshot.total_net_worth,
                    "change": snapshot.change_from_previous,
                    "change_percentage": snapshot.change_percentage,
                }
            )

# Schedule daily at midnight (86400 seconds = 24 hours)
scheduler.add_task(
    name="daily_net_worth_snapshot",
    interval_seconds=86400,
    func=daily_net_worth_snapshot
)
```

### Cache (svc-infra.cache)

**Current Net Worth** (1h TTL):
```python
from svc_infra.cache import cache_read, cache_write

@cache_read(key="net_worth:current:{user_id}", ttl=3600)  # 1 hour
async def get_current_net_worth(user_id: str) -> NetWorthSnapshot:
    """Get current net worth (cached 1h)."""
    return await net_worth_tracker.calculate_net_worth(user_id)

@cache_write(
    key="net_worth:current:{user_id}",
    ttl=3600,
    tags=["net_worth", "user:{user_id}"]
)
async def save_current_net_worth(user_id: str, snapshot: NetWorthSnapshot):
    """Cache current net worth."""
    pass
```

**Exchange Rates** (1h TTL):
```python
@cache_read(key="exchange_rate:{from_currency}:{to_currency}", ttl=3600)
async def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Get exchange rate (cached 1h)."""
    provider = ExchangeRateProvider()
    return await provider.get_rate(from_currency, to_currency)
```

**Stock Prices** (15min TTL during market hours):
```python
@cache_read(key="stock_price:{symbol}", ttl=900)  # 15 minutes
async def get_stock_price(symbol: str) -> float:
    """Get stock price (cached 15min)."""
    market_provider = easy_market()
    quote = market_provider.quote(symbol)
    return quote.price
```

### Webhooks (svc-infra.webhooks)

**Significant Change Alerts**:
```python
from svc_infra.webhooks.add import add_webhooks
from svc_infra.webhooks import emit_event

# Setup webhooks
add_webhooks(
    app,
    signing_secret="your-webhook-secret",
    event_types=[
        "net_worth.snapshot_created",
        "net_worth.significant_change",
        "net_worth.milestone_reached",
    ]
)

# Emit events
async def on_snapshot_created(snapshot: NetWorthSnapshot):
    """Called after snapshot is saved."""
    await emit_event(
        event_type="net_worth.snapshot_created",
        data={
            "user_id": snapshot.user_id,
            "net_worth": snapshot.total_net_worth,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
        }
    )

async def on_significant_change(snapshot: NetWorthSnapshot):
    """Called when change exceeds threshold."""
    await emit_event(
        event_type="net_worth.significant_change",
        data={
            "user_id": snapshot.user_id,
            "previous_net_worth": snapshot.total_net_worth - snapshot.change_from_previous,
            "current_net_worth": snapshot.total_net_worth,
            "change_amount": snapshot.change_from_previous,
            "change_percentage": snapshot.change_percentage,
        }
    )

async def on_milestone_reached(user_id: str, milestone: float):
    """Called when net worth reaches milestone ($100k, $1M, etc.)."""
    await emit_event(
        event_type="net_worth.milestone_reached",
        data={
            "user_id": user_id,
            "milestone": milestone,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

## 5. Performance Benchmarks

### Target Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Snapshot calculation | <2 seconds | Acceptable for background job |
| API response (cached) | <100ms | Fast user experience |
| API response (uncached) | <2 seconds | Real-time calculation acceptable |
| Database query | <50ms | Efficient snapshot retrieval |
| Cache hit rate | >95% | Minimize API calls |

### Optimization Strategies

1. **Parallel provider calls**: Fetch banking, brokerage, crypto concurrently
2. **Aggressive caching**: 1h TTL for net worth, exchange rates, stock prices
3. **Database indexing**: Index user_id + snapshot_date for fast queries
4. **Snapshot compression**: Store only changed fields (delta encoding)
5. **Batch processing**: Calculate snapshots for all users in single job

## 6. Test Requirements

### Unit Tests (Coverage: 90%+)

1. **Net worth calculation**: Assets - liabilities = net worth
2. **Multi-provider aggregation**: Banking + brokerage + crypto
3. **Currency normalization**: EUR → USD conversion
4. **Market value calculation**: Stock prices * quantity
5. **Asset allocation**: Calculate percentages
6. **Snapshot creation**: Store in database
7. **Historical retrieval**: Get last N snapshots
8. **Change detection**: Detect 10% increase
9. **Easy builder**: Validate providers, config defaults

### Acceptance Tests (Real Providers)

1. **Plaid integration**: Fetch real bank accounts
2. **Alpaca integration**: Fetch real brokerage holdings
3. **CCXT integration**: Fetch real crypto balances
4. **Alpha Vantage integration**: Fetch real stock prices
5. **ExchangeRate-API**: Fetch real exchange rates

### Test Data Requirements

**Mock Accounts**:
- 3 bank accounts (checking $10k, savings $20k, credit card -$5k)
- 2 brokerage accounts (AAPL 10 shares @ $175, TSLA 5 shares @ $250)
- 1 crypto wallet (BTC 0.5 @ $60,000, ETH 2 @ $3,000)

**Expected Results**:
- Total assets: $10k + $20k + $1,750 + $1,250 + $30k + $6k = $69k
- Total liabilities: $5k
- Net worth: $69k - $5k = $64k
- Asset allocation: Cash 46%, Investments 45%, Crypto 9%

## 7. Success Metrics

**V1 Completion Criteria**:
- ✅ Multi-provider aggregation (banking + brokerage + crypto)
- ✅ Currency normalization (all currencies → USD)
- ✅ Daily snapshots (stored in database)
- ✅ Historical retrieval (last 90 days)
- ✅ Change detection (>5% or >$10k)
- ✅ Easy builder (`easy_net_worth()`)
- ✅ FastAPI integration (`add_net_worth_tracking(app)`)
- ✅ Comprehensive tests (90%+ coverage)
- ✅ Documentation (methodology + API reference)

**Quality Gates**:
- Unit tests: 90%+ coverage
- Acceptance tests: Real provider integration
- Performance: <2s snapshot calculation, <100ms API response (cached)
- Documentation: Comprehensive guide with examples

## 8. V2 Roadmap Preview

**LLM Enhancements** (planned):
- Natural language insights: "Your net worth increased 15% this year..."
- Debt reduction strategies: "Pay off credit card first (22% APR)..."
- Goal recommendations: "To reach $1M by 2030, save $800/month..."
- Asset allocation advice: "Your portfolio is 90% stocks (high risk)..."
- Multi-turn conversation: "How can I save more?", "Should I pay off mortgage early?"

**Additional Features**:
- Real estate integration: Zillow API for property values
- Vehicle valuation: KBB API for car values
- Manual asset entry: Collectibles, precious metals, art
- Tax estimation: Estimate tax liability based on income/deductions
- Retirement planning: Social Security, 401k projections

---

**Research Complete**: 2025-11-06  
**Next Step**: Design phase (DTOs, ADR-0020, easy builder signature)
