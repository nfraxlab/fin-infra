# Net Worth Tracking

> **Multi-provider net worth aggregation with historical tracking, change detection, and REST API**

## Overview

Net worth tracking calculates total wealth by aggregating assets and liabilities across multiple financial providers (banking, brokerage, crypto). The formula is simple:

```
Net Worth = Total Assets - Total Liabilities
```

### Key Features

- **Multi-Provider Aggregation**: Combine accounts from banking (Plaid, Teller), brokerage (Alpaca), and crypto (CCXT, CoinGecko) providers
- **Asset Categories**: Cash, investments, crypto, real estate, vehicles, other assets (6 types)
- **Liability Categories**: Credit cards, mortgages, auto loans, student loans, personal loans, lines of credit (6 types)
- **Historical Tracking**: Daily snapshots with configurable retention policies
- **Change Detection**: Alert when net worth changes by ≥5% OR ≥$10k (configurable thresholds)
- **REST API**: 4 endpoints for current net worth, historical snapshots, breakdowns, and manual snapshots
- **svc-infra Integration**: Uses svc-infra for jobs (daily snapshots), DB (storage), and cache (1h TTL)

### Use Cases

- **Personal Finance Apps**: Mint, Personal Capital, YNAB (net worth dashboard)
- **Wealth Management**: Financial advisors tracking client portfolios
- **Fintech Dashboards**: Real-time net worth with multi-broker/bank aggregation
- **Goal Tracking**: Monitor progress toward retirement, home purchase, debt-free milestones

---

## Quick Start

### 1. Basic Setup (Programmatic)

```python
from fin_infra.net_worth import easy_net_worth
from fin_infra.banking import easy_banking
from fin_infra.brokerage import easy_brokerage

# Setup providers
banking = easy_banking(provider="plaid", client_id="...", secret="...")
brokerage = easy_brokerage(provider="alpaca", api_key="...", secret_key="...")

# Create tracker
tracker = easy_net_worth(
    banking=banking,
    brokerage=brokerage,
    base_currency="USD",
    snapshot_schedule="daily",  # Daily snapshots
    change_threshold_percent=5.0,  # Alert on 5% change
    change_threshold_amount=10000.0,  # OR $10k change
)

# Calculate net worth
result = await tracker.calculate_net_worth(
    user_id="user_123",
    access_token="plaid_access_token",
)

print(f"Net Worth: ${result['total_net_worth']:,.2f}")
print(f"Assets: ${result['total_assets']:,.2f}")
print(f"Liabilities: ${result['total_liabilities']:,.2f}")
```

### 2. FastAPI Integration

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.net_worth import add_net_worth_tracking, easy_net_worth
from fin_infra.banking import easy_banking

# Create app (svc-infra)
app = easy_service_app(name="FinanceAPI")

# Setup providers
banking = easy_banking(provider="plaid", client_id="...", secret="...")

# Add net worth tracking
tracker = add_net_worth_tracking(
    app,
    tracker=easy_net_worth(banking=banking),
    prefix="/net-worth",  # Default prefix
    include_in_schema=True,  # Show in OpenAPI docs
)

# Endpoints available:
# GET  /net-worth/current
# GET  /net-worth/snapshots
# GET  /net-worth/breakdown
# POST /net-worth/snapshot
```

### 3. API Usage (cURL Examples)

```bash
# Get current net worth
curl -X GET "http://localhost:8000/net-worth/current?user_id=user_123&access_token=plaid_token"

# Get historical snapshots (last 90 days)
curl -X GET "http://localhost:8000/net-worth/snapshots?user_id=user_123&days=90"

# Get asset/liability breakdown (pie chart data)
curl -X GET "http://localhost:8000/net-worth/breakdown?user_id=user_123&access_token=plaid_token"

# Force snapshot creation (admin)
curl -X POST "http://localhost:8000/net-worth/snapshot" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "access_token": "plaid_token"}'
```

---

## Asset Types & Categorization

Net worth tracking supports **6 asset categories** with automatic categorization:

### 1. Cash (5-15% typical allocation)

**Description**: Checking, savings, money market accounts

**Examples**:
- Checking accounts
- Savings accounts
- Money market accounts
- Certificates of Deposit (CDs)

**Categorization**:
```python
# Banking provider account types → CASH
account_types = ["depository", "checking", "savings", "money_market"]
```

**Data Model**:
```python
AssetDetail(
    account_id="acct_checking",
    provider="plaid",
    account_type=AssetCategory.CASH,
    name="Chase Checking",
    balance=10000.0,
    currency="USD",
    last_updated=datetime.utcnow(),
)
```

### 2. Investments (60-80% typical allocation)

**Description**: Stocks, bonds, ETFs, mutual funds, retirement accounts

**Examples**:
- Brokerage accounts (Robinhood, Fidelity, Vanguard)
- 401(k) / IRA accounts
- Individual stocks (AAPL, MSFT)
- ETFs (VOO, VTI)

**Categorization**:
```python
# Brokerage provider account types → INVESTMENTS
account_types = ["brokerage", "retirement", "401k", "ira"]
```

**Data Model**:
```python
AssetDetail(
    account_id="acct_brokerage",
    provider="alpaca",
    account_type=AssetCategory.INVESTMENTS,
    name="Alpaca Brokerage",
    balance=40000.0,  # Cost basis
    currency="USD",
    market_value=50000.0,  # Current market value (USES THIS)
    cost_basis=40000.0,
    gain_loss=10000.0,  # $10k unrealized gain
    gain_loss_percentage=25.0,  # 25% gain
    last_updated=datetime.utcnow(),
)
```

**Important**: Net worth uses `market_value` (not `balance` or `cost_basis`) for investments.

### 3. Crypto (0-10% typical allocation)

**Description**: Bitcoin, Ethereum, altcoins (wallet + exchange balances)

**Examples**:
- Bitcoin (BTC)
- Ethereum (ETH)
- Coinbase account
- Hardware wallet (Ledger, Trezor)

**Categorization**:
```python
# Crypto provider account types → CRYPTO
account_types = ["crypto", "wallet", "exchange"]
```

**Data Model**:
```python
AssetDetail(
    account_id="acct_crypto",
    provider="coinbase",
    account_type=AssetCategory.CRYPTO,
    name="Bitcoin Wallet",
    balance=5000.0,  # USD value
    currency="USD",
    market_value=5000.0,  # Latest BTC price
    cost_basis=3000.0,  # Purchase price
    gain_loss=2000.0,  # $2k unrealized gain
    last_updated=datetime.utcnow(),
)
```

### 4. Real Estate (10-30% typical allocation)

**Description**: Primary residence, investment properties, land

**Examples**:
- Primary home
- Rental properties
- Vacation home
- Land/lots

**Categorization**:
```python
# Manual entry or real estate API → REAL_ESTATE
account_types = ["real_estate", "property"]
```

**Data Model**:
```python
AssetDetail(
    account_id="acct_home",
    provider="zillow",  # Or manual entry
    account_type=AssetCategory.REAL_ESTATE,
    name="Primary Residence",
    balance=400000.0,  # Estimated market value
    currency="USD",
    market_value=400000.0,
    cost_basis=350000.0,  # Purchase price
    gain_loss=50000.0,  # $50k appreciation
    last_updated=datetime.utcnow(),
)
```

### 5. Vehicles (0-10% typical allocation)

**Description**: Cars, boats, motorcycles (deprecating assets)

**Examples**:
- Cars
- Trucks
- Motorcycles
- Boats

**Categorization**:
```python
# Manual entry or KBB API → VEHICLES
account_types = ["vehicle", "auto"]
```

**Data Model**:
```python
AssetDetail(
    account_id="acct_car",
    provider="kbb",  # Kelly Blue Book API
    account_type=AssetCategory.VEHICLES,
    name="2020 Tesla Model 3",
    balance=35000.0,  # Current market value
    currency="USD",
    market_value=35000.0,
    cost_basis=50000.0,  # Purchase price
    gain_loss=-15000.0,  # $15k depreciation
    last_updated=datetime.utcnow(),
)
```

### 6. Other Assets (0-5% typical allocation)

**Description**: Collectibles, precious metals, art, intellectual property

**Examples**:
- Gold/silver bullion
- Art collections
- Rare coins
- Intellectual property

**Categorization**:
```python
# Manual entry → OTHER
account_types = ["collectible", "precious_metal", "art", "other"]
```

**Data Model**:
```python
AssetDetail(
    account_id="acct_gold",
    provider="manual",
    account_type=AssetCategory.OTHER,
    name="Gold Bullion",
    balance=10000.0,
    currency="USD",
    market_value=10000.0,
    last_updated=datetime.utcnow(),
)
```

---

## Liability Types & Categorization

Net worth tracking supports **6 liability categories**:

### 1. Credit Cards (0-10% typical allocation, 15-25% APR)

**Description**: Revolving credit card debt

**Examples**:
- Visa/Mastercard credit cards
- Store credit cards
- Charge cards

**Categorization**:
```python
# Banking provider account types → CREDIT_CARD
account_types = ["credit", "credit_card"]
```

**Data Model**:
```python
LiabilityDetail(
    account_id="acct_cc",
    provider="plaid",
    liability_type=LiabilityCategory.CREDIT_CARD,
    name="Chase Sapphire Reserve",
    balance=5000.0,  # Current balance
    currency="USD",
    interest_rate=0.18,  # 18% APR
    minimum_payment=150.0,
    due_date=datetime(2024, 12, 15),
    last_updated=datetime.utcnow(),
)
```

### 2. Mortgages (70-85% typical allocation, 3-7% APR)

**Description**: Home loans (largest debt for most people)

**Examples**:
- Primary mortgage
- Second mortgage
- Home equity loan

**Categorization**:
```python
# Banking provider account types → MORTGAGE
account_types = ["mortgage", "home_loan"]
```

**Data Model**:
```python
LiabilityDetail(
    account_id="acct_mortgage",
    provider="plaid",
    liability_type=LiabilityCategory.MORTGAGE,
    name="Primary Mortgage",
    balance=300000.0,  # Remaining principal
    currency="USD",
    interest_rate=0.04,  # 4% APR
    minimum_payment=2000.0,  # Monthly payment
    due_date=datetime(2024, 12, 1),
    last_updated=datetime.utcnow(),
)
```

### 3. Auto Loans (5-10% typical allocation, 4-8% APR)

**Description**: Car loans, truck loans

**Examples**:
- New car loan
- Used car loan
- Lease (if counted as liability)

**Categorization**:
```python
# Banking provider account types → AUTO_LOAN
account_types = ["auto", "vehicle_loan", "car_loan"]
```

**Data Model**:
```python
LiabilityDetail(
    account_id="acct_auto",
    provider="plaid",
    liability_type=LiabilityCategory.AUTO_LOAN,
    name="Tesla Model 3 Loan",
    balance=25000.0,
    currency="USD",
    interest_rate=0.05,  # 5% APR
    minimum_payment=500.0,
    due_date=datetime(2024, 12, 10),
    last_updated=datetime.utcnow(),
)
```

### 4. Student Loans (10-20% typical allocation, 3-6% APR)

**Description**: Education debt (federal + private)

**Examples**:
- Federal student loans
- Private student loans
- Parent PLUS loans

**Categorization**:
```python
# Banking provider account types → STUDENT_LOAN
account_types = ["student", "education_loan"]
```

**Data Model**:
```python
LiabilityDetail(
    account_id="acct_student",
    provider="plaid",
    liability_type=LiabilityCategory.STUDENT_LOAN,
    name="Federal Student Loan",
    balance=40000.0,
    currency="USD",
    interest_rate=0.045,  # 4.5% APR
    minimum_payment=300.0,
    due_date=datetime(2024, 12, 20),
    last_updated=datetime.utcnow(),
)
```

### 5. Personal Loans (0-5% typical allocation, 8-15% APR)

**Description**: Unsecured personal loans

**Examples**:
- Personal loans (SoFi, LendingClub)
- Medical debt
- Consolidation loans

**Categorization**:
```python
# Banking provider account types → PERSONAL_LOAN
account_types = ["personal", "unsecured_loan"]
```

**Data Model**:
```python
LiabilityDetail(
    account_id="acct_personal",
    provider="plaid",
    liability_type=LiabilityCategory.PERSONAL_LOAN,
    name="Personal Loan",
    balance=10000.0,
    currency="USD",
    interest_rate=0.12,  # 12% APR
    minimum_payment=250.0,
    due_date=datetime(2024, 12, 5),
    last_updated=datetime.utcnow(),
)
```

### 6. Lines of Credit (Variable allocation, 5-10% APR)

**Description**: Home equity lines of credit (HELOC), business LOC

**Examples**:
- HELOC (home equity line of credit)
- Business line of credit
- Personal line of credit

**Categorization**:
```python
# Banking provider account types → LINE_OF_CREDIT
account_types = ["line_of_credit", "heloc", "loc"]
```

**Data Model**:
```python
LiabilityDetail(
    account_id="acct_heloc",
    provider="plaid",
    liability_type=LiabilityCategory.LINE_OF_CREDIT,
    name="Home Equity Line of Credit",
    balance=50000.0,  # Current balance
    currency="USD",
    interest_rate=0.07,  # 7% APR (variable)
    minimum_payment=400.0,
    due_date=datetime(2024, 12, 1),
    last_updated=datetime.utcnow(),
)
```

---

## Calculation Methodology

### Net Worth Formula

```python
# Step 1: Sum all asset market values
total_assets = sum(asset.market_value or asset.balance for asset in assets)

# Step 2: Sum all liability balances
total_liabilities = sum(liability.balance for liability in liabilities)

# Step 3: Calculate net worth
net_worth = total_assets - total_liabilities
```

### Currency Normalization (V1 Limitation)

**Current Behavior**: V1 only supports USD. Non-USD accounts are **skipped** during calculation.

```python
# V1: Skip non-USD accounts
for asset in assets:
    if asset.currency != "USD":
        continue  # Skip this account
    total_assets += asset.market_value or asset.balance

# V2 (Planned): Use exchange rate API
for asset in assets:
    if asset.currency != base_currency:
        amount = normalize_currency(
            asset.balance,
            from_currency=asset.currency,
            to_currency=base_currency,
            exchange_rate=get_exchange_rate(asset.currency, base_currency),
        )
    else:
        amount = asset.balance
    total_assets += amount
```

**Workaround for V1**: Use only USD accounts, or manually convert balances before passing to tracker.

### Market Value vs Balance

**Investments (stocks, bonds, ETFs)**: Always use `market_value` (current market price), NOT `balance` or `cost_basis`.

```python
# ✅ CORRECT: Use market value for investments
if asset.account_type == AssetCategory.INVESTMENTS:
    value = asset.market_value or asset.balance
else:
    value = asset.balance
```

**Why**: Net worth reflects current wealth, not historical cost. Example:
- Bought 100 shares of AAPL at $150 = $15,000 cost basis
- Current price: $200/share = $20,000 market value
- **Net worth uses $20,000** (market value), not $15,000 (cost basis)

---

## Historical Snapshots & Change Detection

### Snapshot Strategy

Net worth tracking creates **snapshots** at regular intervals to track progress over time.

**Snapshot Schedule Options**:
- `"daily"`: Create snapshot every 24 hours at midnight UTC (default)
- `"weekly"`: Create snapshot every 7 days on Sunday at midnight UTC
- `"monthly"`: Create snapshot on 1st of each month at midnight UTC
- `"on_change"`: Create snapshot only when significant change detected (≥5% OR ≥$10k)

**Example**:
```python
tracker = easy_net_worth(
    banking=banking,
    snapshot_schedule="daily",  # Daily snapshots
)
```

### Change Detection

Net worth tracking detects **significant changes** and triggers alerts (webhooks, notifications).

**Thresholds** (configurable):
- **Percentage Threshold**: Default 5% (trigger if net worth changes by ≥5%)
- **Amount Threshold**: Default $10,000 (trigger if net worth changes by ≥$10k)

**Logic**: Change is significant if **EITHER** threshold is exceeded (OR logic).

```python
# Example 1: 10% increase on $60k → significant (exceeds 5% threshold)
is_significant = detect_significant_change(66000.0, 60000.0)
# Result: True (10% > 5%)

# Example 2: 3% increase on $500k → significant (exceeds $10k threshold)
is_significant = detect_significant_change(515000.0, 500000.0)
# Result: True ($15k > $10k)

# Example 3: 2% increase on $50k → not significant (below both thresholds)
is_significant = detect_significant_change(51000.0, 50000.0)
# Result: False (2% < 5% AND $1k < $10k)
```

**Custom Thresholds**:
```python
tracker = easy_net_worth(
    banking=banking,
    change_threshold_percent=10.0,  # Alert on 10% change (instead of 5%)
    change_threshold_amount=50000.0,  # Alert on $50k change (instead of $10k)
)
```

### Snapshot Retention Policy (V2 Planned)

**Goal**: Reduce storage costs by aggregating old snapshots.

**Retention Policy**:
- **Last 30 days**: Keep all daily snapshots (30 snapshots)
- **30-365 days**: Keep weekly snapshots, delete daily (52 snapshots)
- **1+ years**: Keep monthly snapshots, delete weekly (12 snapshots/year)

**Example**: After 2 years, you have:
- 30 daily snapshots (last month)
- 52 weekly snapshots (last year)
- 12 monthly snapshots (year 2)
- Total: 94 snapshots (instead of 730)

**Implementation** (V2 with svc-infra jobs):
```python
# svc-infra job to aggregate snapshots
from svc_infra.jobs import add_job

@add_job(schedule="0 0 * * *")  # Daily at midnight
async def aggregate_snapshots():
    # Delete daily snapshots older than 30 days
    # Aggregate to weekly snapshots for 30-365 days
    # Aggregate to monthly snapshots for 1+ years
    pass
```

---

## API Reference

### 1. GET /net-worth/current

Get current net worth (real-time calculation, cached 1 hour).

**Request**:
```http
GET /net-worth/current?user_id=user_123&access_token=plaid_token HTTP/1.1
```

**Query Parameters**:
- `user_id` (required): User identifier
- `access_token` (required): Provider access token (e.g., Plaid access token)

**Response** (200 OK):
```json
{
  "total_net_worth": 60000.0,
  "total_assets": 65000.0,
  "total_liabilities": 5000.0,
  "change_from_previous": 4000.0,
  "change_percentage": 6.67,
  "is_significant_change": true,
  "asset_allocation": {
    "cash": 10000.0,
    "cash_percentage": 15.38,
    "investments": 50000.0,
    "investments_percentage": 76.92,
    "crypto": 5000.0,
    "crypto_percentage": 7.69,
    "real_estate": 0.0,
    "real_estate_percentage": 0.0,
    "vehicles": 0.0,
    "vehicles_percentage": 0.0,
    "other_assets": 0.0,
    "other_percentage": 0.0,
    "total_assets": 65000.0
  },
  "liability_breakdown": {
    "credit_cards": 5000.0,
    "credit_cards_percentage": 100.0,
    "mortgages": 0.0,
    "mortgages_percentage": 0.0,
    "auto_loans": 0.0,
    "auto_loans_percentage": 0.0,
    "student_loans": 0.0,
    "student_loans_percentage": 0.0,
    "personal_loans": 0.0,
    "personal_loans_percentage": 0.0,
    "lines_of_credit": 0.0,
    "lines_of_credit_percentage": 0.0,
    "total_liabilities": 5000.0
  },
  "processing_time_ms": 250
}
```

**Caching**: Response cached for 1 hour (via svc-infra cache).

---

### 2. GET /net-worth/snapshots

Get historical snapshots for charting (line chart of net worth over time).

**Request**:
```http
GET /net-worth/snapshots?user_id=user_123&days=90&granularity=daily HTTP/1.1
```

**Query Parameters**:
- `user_id` (required): User identifier
- `days` (optional): Number of days to retrieve (default: 90)
- `granularity` (optional): `"daily"`, `"weekly"`, `"monthly"` (default: `"daily"`)

**Response** (200 OK):
```json
{
  "snapshots": [
    {
      "date": "2024-09-01T00:00:00Z",
      "net_worth": 56000.0,
      "assets": 61000.0,
      "liabilities": 5000.0
    },
    {
      "date": "2024-10-01T00:00:00Z",
      "net_worth": 58000.0,
      "assets": 63000.0,
      "liabilities": 5000.0
    },
    {
      "date": "2024-11-01T00:00:00Z",
      "net_worth": 60000.0,
      "assets": 65000.0,
      "liabilities": 5000.0
    }
  ],
  "total_snapshots": 3,
  "start_date": "2024-09-01T00:00:00Z",
  "end_date": "2024-11-01T00:00:00Z"
}
```

**Use Case**: Line chart showing net worth trend over last 90 days.

---

### 3. GET /net-worth/breakdown

Get simplified asset/liability breakdown (pie chart data).

**Request**:
```http
GET /net-worth/breakdown?user_id=user_123&access_token=plaid_token HTTP/1.1
```

**Query Parameters**:
- `user_id` (required): User identifier
- `access_token` (required): Provider access token

**Response** (200 OK):
```json
{
  "assets": {
    "cash": {"amount": 10000.0, "percentage": 15.38},
    "investments": {"amount": 50000.0, "percentage": 76.92},
    "crypto": {"amount": 5000.0, "percentage": 7.69},
    "real_estate": {"amount": 0.0, "percentage": 0.0},
    "vehicles": {"amount": 0.0, "percentage": 0.0},
    "other": {"amount": 0.0, "percentage": 0.0}
  },
  "liabilities": {
    "credit_cards": {"amount": 5000.0, "percentage": 100.0},
    "mortgages": {"amount": 0.0, "percentage": 0.0},
    "auto_loans": {"amount": 0.0, "percentage": 0.0},
    "student_loans": {"amount": 0.0, "percentage": 0.0},
    "personal_loans": {"amount": 0.0, "percentage": 0.0},
    "lines_of_credit": {"amount": 0.0, "percentage": 0.0}
  },
  "total_assets": 65000.0,
  "total_liabilities": 5000.0
}
```

**Use Case**: Pie charts for asset allocation and liability breakdown.

---

### 4. POST /net-worth/snapshot

Force snapshot creation (admin only, for manual snapshots).

**Request**:
```http
POST /net-worth/snapshot HTTP/1.1
Content-Type: application/json

{
  "user_id": "user_123",
  "access_token": "plaid_token"
}
```

**Response** (201 Created):
```json
{
  "snapshot_id": "snap_abc123",
  "user_id": "user_123",
  "snapshot_date": "2024-11-07T12:00:00Z",
  "total_net_worth": 60000.0,
  "total_assets": 65000.0,
  "total_liabilities": 5000.0,
  "message": "Snapshot created successfully"
}
```

**Use Case**: Admin dashboard to force snapshot creation (e.g., before/after major purchase).

---

## svc-infra Integration

Net worth tracking leverages **svc-infra** for backend infrastructure:

### 1. Jobs (Daily Snapshots)

Use `svc-infra.jobs` to create snapshots automatically.

**Example**:
```python
from svc_infra.jobs import easy_jobs

# Setup jobs
worker, scheduler = easy_jobs(app)

# Add daily snapshot job
@scheduler.add_task(interval=86400)  # 24 hours
async def create_daily_snapshots():
    """Create daily net worth snapshots for all users."""
    users = await get_all_users()  # svc-infra.db query
    for user in users:
        await tracker.create_snapshot(
            user_id=user.id,
            access_token=user.plaid_token,
        )
```

### 2. Database (Snapshot Storage)

Use `svc-infra.db` to store historical snapshots.

**Example Schema** (SQLAlchemy):
```python
from svc_infra.db import Base
from sqlalchemy import Column, Integer, String, Float, DateTime

class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    total_net_worth = Column(Float, nullable=False)
    total_assets = Column(Float, nullable=False)
    total_liabilities = Column(Float, nullable=False)
    change_from_previous = Column(Float)
    change_percentage = Column(Float)
    
    # Asset breakdown (6 categories)
    cash = Column(Float, default=0.0)
    investments = Column(Float, default=0.0)
    crypto = Column(Float, default=0.0)
    real_estate = Column(Float, default=0.0)
    vehicles = Column(Float, default=0.0)
    other_assets = Column(Float, default=0.0)
    
    # Liability breakdown (6 categories)
    credit_cards = Column(Float, default=0.0)
    mortgages = Column(Float, default=0.0)
    auto_loans = Column(Float, default=0.0)
    student_loans = Column(Float, default=0.0)
    personal_loans = Column(Float, default=0.0)
    lines_of_credit = Column(Float, default=0.0)
```

**Migration** (Alembic):
```bash
# Create migration
poetry run python -m svc_infra.db revision --autogenerate -m "Add net_worth_snapshots table"

# Apply migration
poetry run python -m svc_infra.db upgrade head
```

### 3. Cache (1-Hour TTL)

Use `svc-infra.cache` to cache current net worth (reduce API calls to providers).

**Example**:
```python
from svc_infra.cache import cache_read, cache_write

@cache_read(prefix="net_worth", suffix="current", ttl=3600)  # 1 hour
async def get_current_net_worth(user_id: str, access_token: str):
    # Calculate net worth (expensive API calls)
    result = await tracker.calculate_net_worth(user_id, access_token)
    return result

# Subsequent calls within 1 hour will use cached value
```

### 4. Webhooks (Change Alerts)

Use `svc-infra.webhooks` to trigger webhooks on significant changes.

**Example**:
```python
from svc_infra.webhooks import trigger_webhook

# After snapshot creation
if detect_significant_change(current_net_worth, previous_net_worth):
    await trigger_webhook(
        event="net_worth.significant_change",
        user_id=user_id,
        payload={
            "current_net_worth": current_net_worth,
            "previous_net_worth": previous_net_worth,
            "change_amount": current_net_worth - previous_net_worth,
            "change_percentage": calculate_change(current_net_worth, previous_net_worth)[1],
        },
    )
```

---

## Charting Examples

### Line Chart (Net Worth Over Time)

**Library**: Chart.js, Recharts, D3.js

**Data Source**: `GET /net-worth/snapshots?days=90`

**Example** (Chart.js):
```javascript
// Fetch data
const response = await fetch('/net-worth/snapshots?user_id=user_123&days=90');
const data = await response.json();

// Prepare chart data
const labels = data.snapshots.map(s => s.date);
const netWorthData = data.snapshots.map(s => s.net_worth);

// Create line chart
new Chart(ctx, {
  type: 'line',
  data: {
    labels: labels,
    datasets: [{
      label: 'Net Worth',
      data: netWorthData,
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  },
  options: {
    scales: {
      y: {
        ticks: {
          callback: function(value) {
            return '$' + value.toLocaleString();
          }
        }
      }
    }
  }
});
```

**Result**: Line chart showing net worth trend ($56k → $58k → $60k over 90 days).

---

### Pie Chart (Asset Allocation)

**Library**: Chart.js, Recharts

**Data Source**: `GET /net-worth/breakdown`

**Example** (Chart.js):
```javascript
// Fetch data
const response = await fetch('/net-worth/breakdown?user_id=user_123&access_token=token');
const data = await response.json();

// Prepare chart data
const labels = ['Cash', 'Investments', 'Crypto', 'Real Estate', 'Vehicles', 'Other'];
const values = [
  data.assets.cash.amount,
  data.assets.investments.amount,
  data.assets.crypto.amount,
  data.assets.real_estate.amount,
  data.assets.vehicles.amount,
  data.assets.other.amount,
];

// Create pie chart
new Chart(ctx, {
  type: 'pie',
  data: {
    labels: labels,
    datasets: [{
      data: values,
      backgroundColor: [
        'rgb(255, 99, 132)',
        'rgb(54, 162, 235)',
        'rgb(255, 205, 86)',
        'rgb(75, 192, 192)',
        'rgb(153, 102, 255)',
        'rgb(201, 203, 207)',
      ]
    }]
  }
});
```

**Result**: Pie chart showing asset allocation (Cash 15.4%, Investments 76.9%, Crypto 7.7%).

---

## Advanced Usage

### Multi-Currency Support (V2 Planned)

```python
from fin_infra.markets import easy_market

# Setup exchange rate provider
market = easy_market(provider="alphavantage")

# Create tracker with multi-currency support
tracker = easy_net_worth(
    banking=banking,
    brokerage=brokerage,
    market=market,  # For exchange rates
    base_currency="USD",  # Convert all to USD
)

# Accounts in EUR, GBP, JPY will be converted to USD
```

### Custom Asset Categories (V2 Planned)

```python
from fin_infra.net_worth import AssetCategory

# Add custom category
class CustomAssetCategory(AssetCategory):
    NFT = "nft"  # NFT collectibles
    DOMAIN = "domain"  # Domain names

# Use custom category
AssetDetail(
    account_id="acct_nft",
    provider="opensea",
    account_type=CustomAssetCategory.NFT,
    name="Bored Ape #1234",
    balance=100000.0,  # Floor price
    currency="ETH",
)
```

### Goal Tracking (V2 with LLM)

```python
# Set retirement goal
goal = {
    "type": "retirement",
    "target_amount": 2000000.0,  # $2M
    "target_date": "2050-01-01",
    "current_age": 30,
    "retirement_age": 65,
}

# Get LLM-generated progress report
progress = await tracker.check_goal_progress(user_id, goal)
# "You're on track to reach $2M by 2050. Current savings rate: $1,500/month. 
#  To stay on track, maintain 7% investment returns and increase savings by $100/month."
```

---

## LLM Insights (V2)

> **AI-powered financial insights, conversation, and goal tracking**

### Overview

V2 adds LLM-powered capabilities using [ai-infra's CoreLLM](../../ai_infra/docs/llm.md) for:
- **Financial Insights** (4 types): Wealth trends, debt reduction plans, goal recommendations, asset allocation advice
- **Multi-turn Conversation**: Natural dialogue Q&A about finances (maintains context across turns)
- **Goal Tracking**: Validate goals, track progress, suggest course corrections

**Cost**: <$0.10/user/month with 95% cache hit rate (Google Gemini 2.0 Flash recommended)

### Design Choice: Natural Dialogue vs Structured Output

See [ADR-0021: LLM Insights Architecture](./adr/0021-net-worth-llm-insights.md) for full rationale.

**Key Decision**: Conversation uses `achat()` **WITHOUT** `output_schema` for natural dialogue, while insights/goals use `with_structured_output()` for predictable structure.

```python
# ✅ CONVERSATION: Natural dialogue (NO forced JSON)
response_text = await llm.achat(
    user_msg="How can I save more?",
    system="You are a helpful financial advisor...",
    # NO output_schema - allows natural, flexible responses
)

# ✅ INSIGHTS: Structured output (predictable schema)
structured = llm.with_structured_output(
    schema=WealthTrendAnalysis,  # Pydantic model
    method="json_mode",
)
result = await structured.ainvoke("Analyze trends...")
```

**Why?**
- **Conversation**: Multi-turn dialogue needs flexibility. Users ask follow-ups, context changes, forced JSON breaks natural flow.
- **Insights**: Single-shot analysis needs predictable fields for UI rendering (trend_percentage, risk_factors, etc.)

---

### Quick Start (LLM Features)

```python
from fin_infra.net_worth import easy_net_worth
from fin_infra.banking import easy_banking

# Setup providers
banking = easy_banking(provider="plaid", client_id="...", secret="...")

# Enable LLM features
tracker = easy_net_worth(
    banking=banking,
    base_currency="USD",
    enable_llm=True,  # ← Enable LLM insights
    llm_provider="google",  # Google Gemini (recommended)
    llm_api_key="...",  # Or set GOOGLE_API_KEY env
    llm_model="gemini-2.0-flash-exp",  # Cost-optimized model
)

# Generate insights
snapshot = await tracker.calculate_net_worth(user_id="user_123", access_token="...")
insights = await tracker.insights_generator.analyze_wealth_trends([snapshot])

print(f"Trend: {insights.summary}")
print(f"Change: {insights.change_percent:.1%}")
print(f"Drivers: {', '.join(insights.primary_drivers)}")
```

---

### Feature 1: Financial Insights (4 Types)

#### Wealth Trends Analysis

**Analyzes net worth changes over time (7-365 days) and identifies key drivers.**

```python
# Get 90 days of snapshots
snapshots = await tracker.get_snapshots(user_id="user_123", days=90)

# Analyze trends
trends = await tracker.insights_generator.analyze_wealth_trends(snapshots)

print(f"Period: {trends.period}")
print(f"Change: ${trends.change_amount:,.2f} ({trends.change_percent:.1%})")
print(f"Primary Drivers: {', '.join(trends.primary_drivers)}")
print(f"Risk Factors: {', '.join(trends.risk_factors)}")
print(f"Recommendations: {', '.join(trends.recommendations)}")
print(f"Confidence: {trends.confidence:.0%}")
```

**Example Output**:
```
Period: 3 months
Change: +$5,000 (+10.5%)
Primary Drivers: Investment growth, Reduced credit card debt
Risk Factors: Market volatility, Variable income
Recommendations: Continue debt payoff, Maintain emergency fund
Confidence: 85%
```

**API Endpoint**: `GET /net-worth/insights?type=wealth_trends&days=90`

**Cache**: 24h TTL (one generation per day)

---

#### Debt Reduction Plan

**Prioritizes debts by APR and generates payoff strategy (avalanche method).**

```python
debts = [
    {"type": "credit_card", "balance": 5000, "apr": 0.22, "min_payment": 150},
    {"type": "student_loan", "balance": 15000, "apr": 0.04, "min_payment": 200},
    {"type": "auto_loan", "balance": 8000, "apr": 0.06, "min_payment": 300},
]

plan = await tracker.insights_generator.generate_debt_reduction_plan(snapshots)

print(f"Priority: {plan.priority_order}")  # ['credit_card', 'auto_loan', 'student_loan']
print(f"Total Interest: ${plan.total_interest_without_plan:,.2f}")
print(f"Savings: ${plan.interest_saved:,.2f}")
print(f"Payoff Timeline: {plan.estimated_payoff_months} months")
```

**Why Avalanche?**
- Minimizes total interest paid
- Mathematically optimal (pays highest APR first)
- See [ADR-0021](./adr/0021-net-worth-llm-insights.md) for comparison vs snowball method

**API Endpoint**: `GET /net-worth/insights?type=debt_reduction`

**Cost**: ~$0.002/generation (500 input + 300 output tokens)

---

#### Goal Recommendations

**Suggests personalized financial goals based on age, income, net worth.**

```python
goals = await tracker.insights_generator.recommend_financial_goals(snapshots)

for goal in goals.recommended_goals:
    print(f"Goal: {goal.goal_type}")
    print(f"Target: ${goal.target_amount:,.2f} by {goal.target_date}")
    print(f"Monthly: ${goal.required_monthly_savings:,.2f}")
    print(f"Rationale: {goal.rationale}")
    print()
```

**Example Goals**:
- **Retirement**: $2M by age 65 (save $1,500/month)
- **Home Purchase**: $100K down payment by 2028 (save $2,000/month)
- **Debt-Free**: Pay off $20K by 2027 (pay $700/month)
- **Emergency Fund**: 6 months expenses ($18K) by 2026

**API Endpoint**: `GET /net-worth/insights?type=goal_recommendations`

---

#### Asset Allocation Advice

**Analyzes portfolio allocation and suggests rebalancing.**

```python
allocation = await tracker.insights_generator.suggest_asset_allocation(snapshots)

print(f"Current: {allocation.current_allocation}")
# {'cash': 0.20, 'stocks': 0.70, 'bonds': 0.10}

print(f"Recommended: {allocation.recommended_allocation}")
# {'cash': 0.10, 'stocks': 0.65, 'bonds': 0.20, 'real_estate': 0.05}

print(f"Rationale: {allocation.rationale}")
print(f"Rebalancing Steps: {', '.join(allocation.rebalancing_steps)}")
```

**Considers**:
- Age (more conservative as you age)
- Risk tolerance (inferred from current allocation)
- Diversification (avoid concentration risk)
- Modern portfolio theory principles

**API Endpoint**: `GET /net-worth/insights?type=asset_allocation`

---

### Feature 2: Multi-turn Conversation

**Natural language Q&A about finances with context retention.**

```python
# First question
response1 = await tracker.conversation.ask(
    user_id="user_123",
    question="How can I save $10,000 in 2 years?",
    session_id="session_456",  # Track conversation
    current_net_worth=50000.0,
    goals=[],
)

print(f"Answer: {response1.answer}")
print(f"Follow-ups: {', '.join(response1.follow_up_questions)}")
print(f"Confidence: {response1.confidence:.0%}")

# Follow-up question (uses context)
response2 = await tracker.conversation.ask(
    user_id="user_123",
    question="What if I want to save it in 1 year instead?",
    session_id="session_456",  # Same session - maintains context
    current_net_worth=50000.0,
    goals=[],
)

print(f"Answer: {response2.answer}")  # References previous conversation
```

**Example Dialogue**:
```
User: How can I save $10,000 in 2 years?
Bot:  To save $10,000 in 2 years, you'd need to set aside approximately $417 per month.
      Based on your current net worth of $50,000, this seems achievable if you...
      [detailed advice with context]
      
      Follow-up questions:
      - What if I want to save more aggressively?
      - Should I cut my spending or increase my income?
      
      Confidence: 85%

User: What if I want to save it in 1 year instead?
Bot:  For a 1-year timeline, you'd need to save $833 per month - double your previous target.
      This is more aggressive but possible if you... [references previous context]
```

**Key Features**:
- **Context Retention**: Remembers previous turns (10-turn limit)
- **Natural Dialogue**: Uses `achat()` WITHOUT `output_schema` (no forced JSON)
- **Safety Filters**: Blocks sensitive questions (SSN, passwords, account numbers)
- **Follow-up Questions**: Suggests relevant next questions
- **Confidence Scores**: 0.0-1.0 (based on data quality and context)

**API Endpoint**: `POST /net-worth/conversation`

**Request**:
```json
{
  "user_id": "user_123",
  "question": "How can I save more?",
  "session_id": "session_456",
  "access_token": "plaid_token"
}
```

**Response**:
```json
{
  "answer": "Based on your current spending...",
  "follow_up_questions": [
    "Should I focus on reducing expenses or increasing income?",
    "What's a realistic savings rate for my situation?"
  ],
  "confidence": 0.85,
  "sources": ["net_worth_snapshot", "conversation_history"]
}
```

**Cache**: 24h TTL for conversation context

**Cost**: ~$0.002/conversation (600 input + 400 output tokens)

---

### Feature 3: Goal Tracking

**Validate financial goals, track progress, suggest course corrections.**

#### Goal Validation (LLM-Enhanced)

```python
# Define goal
goal = {
    "type": "retirement",
    "target_amount": 2000000.0,
    "target_age": 65,
    "current_age": 35,
}

# Get current snapshot
snapshot = await tracker.calculate_net_worth(user_id="user_123", access_token="...")

# Validate with LLM
validation = await tracker.goal_tracker.validate_goal(goal, snapshot)

print(f"Feasibility: {validation.feasibility}")  # 'feasible', 'challenging', 'unrealistic'
print(f"Required Monthly: ${validation.required_monthly_savings:,.2f}")
print(f"Timeline: {validation.projected_completion_date}")
print(f"Current Progress: {validation.current_progress:.1%}")
print(f"Alternative Paths: {', '.join(validation.alternative_paths)}")
print(f"Recommendations: {', '.join(validation.recommendations)}")
```

**LLM Context Around Local Math**:
- ✅ Local functions calculate required savings, timelines (accurate math)
- ✅ LLM provides context, alternatives, recommendations (creative reasoning)
- ❌ LLM does NOT calculate numbers (prevents hallucination)

**Example**:
```python
# Local calculation (accurate)
required_savings = calculate_retirement_goal(
    target_amount=2000000.0,
    current_savings=50000.0,
    years_remaining=30,
    expected_return=0.07,
)  # Returns $1,492.37/month

# LLM adds context
validation = GoalValidation(
    feasibility="feasible",
    required_monthly_savings=1492.37,  # From local calc
    recommendations=[
        "Max out 401k contributions ($22,500/year)",
        "Consider Roth IRA ($6,500/year)",
        "Invest in index funds (target 7% return)",
    ],
    confidence=0.85,
)
```

**API Endpoint**: `POST /net-worth/goals`

**Cost**: ~$0.0009/validation (400 input + 300 output tokens)

---

#### Goal Progress Tracking

```python
# Track progress weekly
progress = await tracker.goal_tracker.track_progress(goal, current_net_worth=75000.0)

print(f"Progress: {progress.progress_percentage:.1%}")
print(f"On Track: {progress.on_track}")
print(f"Required vs Actual: ${progress.required_monthly_savings:,.2f} vs ${progress.actual_monthly_savings:,.2f}")
print(f"Estimated Completion: {progress.estimated_completion_date}")
print(f"Recommendations: {', '.join(progress.recommendations)}")
```

**Weekly Check-ins**: Compares actual progress vs target trajectory

**API Endpoint**: `GET /net-worth/goals/{goal_id}/progress`

**Cost**: ~$0.0009/week = $0.0036/user/month (4 check-ins)

---

### Cost Analysis

#### Pricing Comparison (Per 1K Tokens)

| Provider | Input | Output | Total (avg) | Notes |
|----------|-------|--------|-------------|-------|
| **Google Gemini 2.0 Flash** | $0.00035 | $0.0014 | ~$0.0009 | ✅ **Recommended** (best cost/performance) |
| OpenAI GPT-4o mini | $0.00015 | $0.0006 | ~$0.0004 | Cheaper but less capable |
| OpenAI GPT-4o | $0.0025 | $0.010 | ~$0.006 | 6x more expensive |
| Anthropic Claude 3.5 Sonnet | $0.003 | $0.015 | ~$0.009 | 10x more expensive |

#### Per-User Monthly Costs (Google Gemini 2.0 Flash)

| Feature | Frequency | Tokens (avg) | Cost/Call | Monthly Cost |
|---------|-----------|--------------|-----------|--------------|
| **Insights** | 1/day | 800 (500 in + 300 out) | $0.0006 | $0.018 |
| **Conversation** | 10/month | 1000 (600 in + 400 out) | $0.0008 | $0.008 |
| **Goal Validation** | 1/month | 700 (400 in + 300 out) | $0.0006 | $0.0006 |
| **Goal Progress** | 4/month | 700 (400 in + 300 out) | $0.0006 | $0.0024 |
| **Total** | | | | **$0.029/month** |

**With Cache (95% hit rate)**: $0.029 × 5% = **$0.0015/user/month** ✅

**Target**: <$0.10/user/month (well under target)

#### Cost Optimization Strategies

1. **Cache Aggressively**:
   - Insights: 24h TTL (one generation per day)
   - Conversation: 24h context cache
   - Goal validation: Cache identical goals

2. **Use Cost-Efficient Models**:
   - ✅ Google Gemini 2.0 Flash (recommended)
   - ✅ OpenAI GPT-4o mini (alternative)
   - ❌ Avoid GPT-4o, Claude 3.5 (overkill for this use case)

3. **Prompt Optimization**:
   - Keep prompts concise (<500 tokens)
   - Use structured output to reduce verbose responses
   - Limit conversation history (10 turns max)

4. **Measure Production Costs**:
   ```bash
   # Simulate 1000 users for 30 days
   GOOGLE_API_KEY=your_key poetry run python examples/scripts/measure_llm_costs.py \
     --users 1000 --days 30 --feature all
   ```

See [examples/scripts/measure_llm_costs.py](../../examples/scripts/measure_llm_costs.py) for detailed cost measurement script.

---

### Configuration

#### Environment Variables

```bash
# LLM Provider (required if enable_llm=True)
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key  # Alternative

# Cache (recommended for cost optimization)
REDIS_URL=redis://localhost:6379/0
CACHE_PREFIX=fin_infra
CACHE_VERSION=1.0

# Conversation Settings
CONVERSATION_CONTEXT_TTL=86400  # 24 hours
CONVERSATION_MAX_TURNS=10  # Limit context size

# Insights Settings
INSIGHTS_CACHE_TTL=86400  # 24 hours
INSIGHTS_MIN_DAYS=7  # Minimum days for trends
INSIGHTS_MAX_DAYS=365  # Maximum days for trends
```

#### Programmatic Configuration

```python
tracker = easy_net_worth(
    banking=banking,
    
    # LLM Configuration
    enable_llm=True,
    llm_provider="google",  # 'google', 'openai', 'anthropic'
    llm_api_key="...",  # Or use env var
    llm_model="gemini-2.0-flash-exp",
    
    # Cache Configuration
    cache_url="redis://localhost:6379/0",
    cache_ttl=86400,  # 24 hours
    
    # Conversation Settings
    conversation_max_turns=10,
    conversation_context_ttl=86400,
    
    # Insights Settings
    insights_cache_ttl=86400,
    insights_min_days=7,
    insights_max_days=365,
    
    # Goal Settings
    goal_progress_frequency="weekly",  # 'daily', 'weekly', 'monthly'
)
```

---

### Migration Guide (V1 → V2)

#### V1 (Calculation Only)

```python
# V1: Basic net worth calculation
tracker = easy_net_worth(banking=banking)

result = await tracker.calculate_net_worth(
    user_id="user_123",
    access_token="plaid_token",
)

print(f"Net Worth: ${result['total_net_worth']:,.2f}")
```

#### V2 (With LLM Insights)

```python
# V2: Add LLM features (backward compatible)
tracker = easy_net_worth(
    banking=banking,
    enable_llm=True,  # ← Add this line
    llm_provider="google",
    llm_api_key=os.getenv("GOOGLE_API_KEY"),
)

# Existing code works unchanged
result = await tracker.calculate_net_worth(
    user_id="user_123",
    access_token="plaid_token",
)

# NEW: Generate insights
snapshots = await tracker.get_snapshots(user_id="user_123", days=90)
insights = await tracker.insights_generator.analyze_wealth_trends(snapshots)

# NEW: Ask questions
response = await tracker.conversation.ask(
    user_id="user_123",
    question="How can I save more?",
    session_id="session_456",
    current_net_worth=result['total_net_worth'],
    goals=[],
)

# NEW: Validate goals
validation = await tracker.goal_tracker.validate_goal(goal, result)
```

**Backward Compatibility**: V1 code works unchanged. LLM features are opt-in via `enable_llm=True`.

---

### Troubleshooting (V2 LLM Features)

#### Issue: LLM insights return 503 error

**Cause**: LLM not enabled or API key missing.

**Solution**: Check `enable_llm=True` and API key is set.

```python
# ❌ WRONG: LLM not enabled
tracker = easy_net_worth(banking=banking)  # enable_llm defaults to False

# ✅ CORRECT: Enable LLM
tracker = easy_net_worth(
    banking=banking,
    enable_llm=True,
    llm_api_key=os.getenv("GOOGLE_API_KEY"),
)
```

---

#### Issue: Conversation loses context after 10 turns

**Cause**: Context window limit (intentional, prevents runaway costs).

**Solution**: Increase `conversation_max_turns` or start new session.

```python
tracker = easy_net_worth(
    banking=banking,
    enable_llm=True,
    conversation_max_turns=20,  # Default is 10
)
```

---

#### Issue: Goal validation returns unrealistic numbers

**Cause**: LLM hallucinating numbers instead of using local calculations.

**Solution**: Verify local calculation functions are called (not LLM).

```python
# ✅ CORRECT: Local calculation
required_savings = calculate_retirement_goal(...)  # Accurate math

# LLM only provides context
validation = await tracker.goal_tracker.validate_goal(goal, snapshot)
# Uses required_savings from local calc, adds LLM recommendations
```

---

#### Issue: High LLM costs

**Cause**: Cache misconfigured or hit rate too low.

**Solution**: 
1. Verify Redis is running and cache is enabled
2. Measure actual costs with simulation script
3. Increase cache TTL for insights (24h recommended)

```bash
# Measure costs
GOOGLE_API_KEY=your_key poetry run python examples/scripts/measure_llm_costs.py \
  --users 1000 --days 30

# Expected output:
# Cache Hit Rate: 95%+
# Cost/User/Month: <$0.10
```

---

#### Issue: Insights are too generic

**Cause**: Insufficient context in LLM prompts.

**Solution**: See quality review guide for improvement strategies.

- [docs/testing/llm-quality-review.md](./testing/llm-quality-review.md)
- Target: 4.0+ average rating from 20 test users

---

#### Issue: Conversation blocks legitimate questions

**Cause**: Over-aggressive safety filters.

**Solution**: Review safety filter logic in `conversation/planning.py:_is_safe_question()`.

Safety filters currently block:
- SSN, social security, tax ID
- Password, PIN, account number, routing number
- Credit card, CVV, security code
- Driver license, passport

If legitimate question is blocked, adjust filter patterns or add exception.

---

## Troubleshooting

**Cause**: Non-USD accounts are skipped in V1.

**Solution**: Ensure all accounts use `currency="USD"`.

```python
# ❌ WRONG: EUR account skipped
AssetDetail(currency="EUR", balance=5000.0)

# ✅ CORRECT: Manually convert to USD
AssetDetail(currency="USD", balance=5500.0)  # 5000 EUR * 1.1 rate
```

---

### Issue: Net worth doesn't include investment gains

**Cause**: Using `balance` instead of `market_value` for investments.

**Solution**: Ensure brokerage provider returns `market_value`.

```python
# ❌ WRONG: Uses cost basis ($40k)
AssetDetail(
    account_type=AssetCategory.INVESTMENTS,
    balance=40000.0,  # Cost basis
)

# ✅ CORRECT: Uses market value ($50k)
AssetDetail(
    account_type=AssetCategory.INVESTMENTS,
    balance=40000.0,  # Cost basis
    market_value=50000.0,  # Current value (USES THIS)
)
```

---

### Issue: Snapshots not created automatically

**Cause**: svc-infra jobs not configured.

**Solution**: Add daily job for snapshot creation.

```python
from svc_infra.jobs import easy_jobs

worker, scheduler = easy_jobs(app)

@scheduler.add_task(interval=86400)  # 24 hours
async def create_snapshots():
    # Create snapshots for all users
    pass
```

---

## Related Documentation

### Core Integrations
- [Banking Integration](./banking.md) - Plaid, Teller adapters for account balances
- [Brokerage Integration](./brokerage.md) - Alpaca adapter for stock holdings
- [Crypto Integration](./crypto.md) - CCXT, CoinGecko for crypto balances
- [Market Data](./market-data.md) - Alpha Vantage for stock quotes, exchange rates

### Financial Planning
- [Goal Management](./goals.md) - Track net worth milestones and wealth goals
- [Budget Management](./budgets.md) - Link net worth to budget savings categories
- [Analytics](./analytics.md) - Net worth trends, growth projections, and insights

### LLM Features (V2)
- [ADR-0021: LLM Insights Architecture](./adr/0021-net-worth-llm-insights.md) - Design decisions for V2
- [LLM Quality Review Guide](./testing/llm-quality-review.md) - Manual testing process (20 users, 4.0+ target)
- [Cost Measurement Script](../../examples/scripts/measure_llm_costs.py) - Simulate production costs

### Architecture
- [ADR-0020: Net Worth Architecture](./adr/0020-net-worth-architecture.md) - V1 design decisions

---

## License

MIT License - see [LICENSE](../../LICENSE)
