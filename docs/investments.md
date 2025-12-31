# Investments Module

> **READ-ONLY investment holdings, transactions, and portfolio data from external providers**

## Overview

The investments module provides **read-only access** to investment holdings, transactions, securities, and portfolio data from external providers like Plaid and SnapTrade. This module is designed for **viewing and analyzing** investment data, not for executing trades.

### What This Module Provides

- **Holdings Data**: Current positions, quantities, values, cost basis, and P/L
- **Transaction History**: Buys, sells, dividends, fees, and other investment transactions
- **Account Information**: Investment account details, balances, and metadata
- **Asset Allocation**: Portfolio breakdown by asset class (stocks, bonds, cash, etc.)
- **Securities Details**: Security identifiers, names, types, and market data
- **Real P/L Calculations**: Accurate profit/loss using actual cost basis

### Critical Distinction: Investments vs Brokerage

```
┌─────────────────────────────────────────────────────────────┐
│  Investments Module (READ-ONLY)                             │
│  • View holdings from external accounts (401k, IRA, etc.)   │
│  • Track portfolio performance                              │
│  • Calculate profit/loss                                    │
│  • Providers: Plaid, SnapTrade, Teller (aggregators)       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Brokerage Module (TRADING)                                 │
│  • Execute buy/sell orders                                  │
│  • Manage active trading positions                          │
│  • Place market/limit orders                                │
│  • Providers: Alpaca, Interactive Brokers (brokers)         │
└─────────────────────────────────────────────────────────────┘
```

> **For trading operations** (buy/sell orders, order management), see [Brokerage Integration](brokerage.md)

### Supported Providers

| Provider   | Status      | Coverage                          | Use Case                           |
|------------|-------------|-----------------------------------|------------------------------------|
| **Plaid**  | [OK] Current  | 12,000+ institutions (US)         | Production-ready, broad coverage   |
| **SnapTrade** | [OK] Current | 5,000+ institutions (US/Canada) | Alternative to Plaid              |
| **Teller** |  Future   | Limited coverage                  | Privacy-focused alternative        |
| **MX**     |  Future   | 16,000+ institutions (US)         | Broader coverage for edge cases    |

## Quick Start

### Programmatic Usage

```python
from fin_infra.investments import easy_investments

# Initialize Plaid provider
investments = easy_investments(provider="plaid")

# Fetch holdings for a user
holdings = await investments.get_holdings(
    access_token="access-sandbox-123..."
)

# Calculate portfolio metrics
from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings

metrics = portfolio_metrics_with_holdings(holdings)
print(f"Total value: ${metrics.total_value:,.2f}")
print(f"Total return: {metrics.total_return_percent:.2f}%")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fin_infra.investments import add_investments

app = FastAPI()

# Mount investment endpoints at /investments
provider = add_investments(app, prefix="/investments")

# Now available:
# GET /investments/holdings
# GET /investments/transactions
# GET /investments/accounts
# GET /investments/allocation
# GET /investments/securities
```

### cURL Examples

```bash
# Fetch holdings (Plaid)
curl -X POST http://localhost:8000/investments/holdings \
  -H "Content-Type: application/json" \
  -d '{"access_token": "access-sandbox-123..."}'

# Fetch holdings (SnapTrade)
curl -X POST http://localhost:8000/investments/holdings \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "user_secret": "secret123"
  }'

# Fetch transactions with date range
curl -X POST http://localhost:8000/investments/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "access-sandbox-123...",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'
```

### Zero-Config Setup

Set environment variables and the module auto-configures:

```bash
# Plaid configuration
export PLAID_CLIENT_ID=your_client_id
export PLAID_SECRET=your_secret
export PLAID_ENV=sandbox  # or production

# SnapTrade configuration (alternative)
export SNAPTRADE_CONSUMER_KEY=your_key
export SNAPTRADE_CLIENT_ID=your_client_id
```

```python
# Provider auto-detects from environment
investments = easy_investments()  # Uses Plaid if configured

# Or explicitly specify
investments = easy_investments(provider="plaid")
```

## API Reference

### GET /investments/holdings

Fetch current investment holdings across accounts.

**Request:**
```json
{
  "access_token": "access-sandbox-123...",  // Plaid
  "account_ids": ["acc1", "acc2"]           // Optional filter
}
```

**Response:**
```json
[
  {
    "account_id": "acc1",
    "security": {
      "security_id": "AAPL",
      "name": "Apple Inc.",
      "ticker_symbol": "AAPL",
      "type": "equity"
    },
    "quantity": 10.0,
    "institution_price": 150.00,
    "institution_value": 1500.00,
    "cost_basis": 1200.00,
    "iso_currency_code": "USD",
    "unrealized_gain_loss": 300.00,
    "unrealized_gain_loss_percent": 25.0
  }
]
```

**Filtering:**
```python
# All holdings
holdings = await investments.get_holdings(access_token=token)

# Specific accounts only
holdings = await investments.get_holdings(
    access_token=token,
    account_ids=["401k_account", "ira_account"]
)
```

### GET /investments/transactions

Fetch investment transactions (buys, sells, dividends, fees).

**Request:**
```json
{
  "access_token": "access-sandbox-123...",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "account_ids": ["acc1"]  // Optional
}
```

**Response:**
```json
[
  {
    "transaction_id": "txn123",
    "account_id": "acc1",
    "security": {
      "security_id": "AAPL",
      "ticker_symbol": "AAPL"
    },
    "type": "buy",
    "date": "2024-06-15",
    "quantity": 10.0,
    "price": 120.00,
    "amount": 1200.00,
    "fees": 0.0,
    "iso_currency_code": "USD"
  }
]
```

**Transaction Types:**
- `buy`: Purchase of security
- `sell`: Sale of security
- `dividend`: Dividend payment
- `interest`: Interest payment
- `fee`: Account or transaction fee
- `transfer`: Transfer between accounts
- `other`: Other transaction types

### GET /investments/accounts

Fetch investment account details and balances.

**Request:**
```json
{
  "access_token": "access-sandbox-123..."
}
```

**Response:**
```json
[
  {
    "account_id": "401k_account",
    "name": "Vanguard 401(k)",
    "type": "401k",
    "subtype": "retirement",
    "balances": {
      "current": 50000.00,
      "available": 50000.00,
      "iso_currency_code": "USD"
    }
  }
]
```

### GET /investments/allocation

Calculate asset allocation breakdown by asset class.

**Request:**
```json
{
  "access_token": "access-sandbox-123...",
  "account_ids": ["acc1", "acc2"]  // Optional
}
```

**Response:**
```json
[
  {
    "asset_class": "Stocks",
    "value": 35000.00,
    "percentage": 70.0
  },
  {
    "asset_class": "Bonds",
    "value": 10000.00,
    "percentage": 20.0
  },
  {
    "asset_class": "Cash",
    "value": 5000.00,
    "percentage": 10.0
  }
]
```

**Asset Class Mapping:**
- `equity` -> Stocks
- `etf` -> Stocks (most ETFs)
- `mutual_fund` -> Bonds (conservative)
- `bond` -> Bonds
- `cash` -> Cash
- `derivative` -> Other
- `other` -> Other

### GET /investments/securities

Fetch detailed security information.

**Request:**
```json
{
  "access_token": "access-sandbox-123...",
  "security_ids": ["AAPL", "GOOGL", "MSFT"]
}
```

**Response:**
```json
[
  {
    "security_id": "AAPL",
    "name": "Apple Inc.",
    "ticker_symbol": "AAPL",
    "type": "equity",
    "cusip": "037833100",
    "isin": "US0378331005",
    "sedol": "2046251"
  }
]
```

## Provider Comparison

### Plaid

**Status:** [OK] Production-ready

**Coverage:**
- 12,000+ institutions (US)
- Major brokerages: Vanguard, Fidelity, Charles Schwab, etc.
- 401(k) providers: ADP, Paychex, etc.

**Data Quality:**
- [OK] Cost basis: Available for most holdings
- [OK] Update frequency: Real-time to daily
- [OK] Transaction history: 2+ years
- [!] Limitations: Some 401(k)s have delayed updates

**Pricing:**
- Sandbox: Free
- Development: Free
- Production: Pay-per-use (contact Plaid)

**Authentication:**
- Link flow: User authenticates via Plaid Link
- Token: `access_token` required for API calls

### SnapTrade

**Status:** [OK] Production-ready

**Coverage:**
- 5,000+ institutions (US/Canada)
- Broader international coverage than Plaid
- Cryptocurrency exchanges

**Data Quality:**
- [OK] Cost basis: Available
- [OK] Update frequency: Real-time
- [OK] Trading: Supports order execution (brokerage)

**Pricing:**
- Sandbox: Free
- Production: Tiered pricing

**Authentication:**
- User ID + Secret: Per-user credentials
- OAuth: Available for some brokers

### Teller (Future)

**Status:**  Planned

**Coverage:**
- Limited (privacy-focused)
- Major banks and brokerages

**Key Features:**
- Privacy-first: No screen scraping
- Direct API connections
- Open banking standards

### MX (Future)

**Status:**  Planned

**Coverage:**
- 16,000+ institutions (US)
- Broader coverage for credit unions and regional banks

**Use Case:**
- Fill coverage gaps from Plaid
- Redundancy for critical accounts

## Multi-Provider Usage

### Using Multiple Providers

Combine Plaid and SnapTrade for maximum coverage:

```python
from fin_infra.investments import easy_investments

# Initialize both providers
plaid = easy_investments(provider="plaid")
snaptrade = easy_investments(provider="snaptrade")

# Fetch holdings from both
plaid_holdings = await plaid.get_holdings(access_token=plaid_token)
snaptrade_holdings = await snaptrade.get_holdings(
    user_id=st_user_id,
    user_secret=st_secret
)

# Combine for unified view
all_holdings = plaid_holdings + snaptrade_holdings
```

### Provider Fallback Strategy

```python
async def get_holdings_with_fallback(user_id: str) -> list[Holding]:
    """Fetch holdings with provider fallback."""

    # Try primary provider (Plaid)
    try:
        plaid_token = get_user_plaid_token(user_id)
        return await plaid.get_holdings(access_token=plaid_token)
    except Exception as e:
        logging.warning(f"Plaid failed: {e}")

    # Fall back to SnapTrade
    try:
        st_user_id, st_secret = get_snaptrade_creds(user_id)
        return await snaptrade.get_holdings(
            user_id=st_user_id,
            user_secret=st_secret
        )
    except Exception as e:
        logging.error(f"SnapTrade also failed: {e}")
        raise
```

### Credential Management

```python
# Store provider credentials per user
from sqlalchemy import Column, String, JSON

class UserInvestmentCredentials(Base):
    __tablename__ = "user_investment_credentials"

    user_id = Column(String, primary_key=True)
    provider = Column(String, primary_key=True)  # "plaid", "snaptrade"
    credentials = Column(JSON)  # Encrypted tokens/secrets

    # Example:
    # {
    #   "plaid": {"access_token": "access-sandbox-123..."},
    #   "snaptrade": {"user_id": "user123", "user_secret": "secret123"}
    # }
```

## Integration with Other Modules

### Banking Module: Shared Plaid Client

Reuse Plaid credentials across banking and investments:

```python
from fin_infra.banking import easy_banking
from fin_infra.investments import easy_investments

# Both use same Plaid client and credentials
banking = easy_banking(provider="plaid")
investments = easy_investments(provider="plaid")

# Same access_token for both
accounts = await banking.get_accounts(access_token=token)
holdings = await investments.get_holdings(access_token=token)

# Combined view: checking + savings + investments
total_net_worth = (
    sum(acc.balance for acc in accounts) +
    sum(h.institution_value for h in holdings)
)
```

### Analytics Module: Real P/L Calculations

Replace mock portfolio data with real holdings:

```python
from fin_infra.investments import easy_investments
from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings

# Fetch real holdings
investments = easy_investments(provider="plaid")
holdings = await investments.get_holdings(access_token=token)

# Calculate real P/L from holdings
metrics = portfolio_metrics_with_holdings(holdings)

print(f"Total value: ${metrics.total_value:,.2f}")
print(f"Total return: ${metrics.total_return:,.2f}")
print(f"Return %: {metrics.total_return_percent:.2f}%")

# Asset allocation
for allocation in metrics.allocation_by_asset_class:
    print(f"{allocation.asset_class}: {allocation.percentage:.1f}%")
```

**Benefits over mock data:**
- Accurate cost basis -> real P/L
- Real security types -> precise allocation
- Current market values -> live tracking

### Brokerage Module: Unified Portfolio View

Combine external holdings (Plaid) with active trading positions (Alpaca):

```python
from fin_infra.investments import easy_investments
from fin_infra.brokerage import easy_brokerage

# External holdings (401k, IRA, taxable accounts)
plaid_investments = easy_investments(provider="plaid")
external_holdings = await plaid_investments.get_holdings(plaid_token)

# Active trading positions (brokerage account)
alpaca_broker = easy_brokerage(provider="alpaca")
trading_positions = await alpaca_broker.positions()

# Unified portfolio view
total_portfolio = {
    "external_accounts": {
        "total_value": sum(h.institution_value for h in external_holdings),
        "holdings": external_holdings,
    },
    "trading_account": {
        "total_value": sum(p.market_value for p in trading_positions),
        "positions": trading_positions,
    },
    "net_total": (
        sum(h.institution_value for h in external_holdings) +
        sum(p.market_value for p in trading_positions)
    ),
}
```

### Market Data Module: Real-Time Portfolio Value

Combine holdings with live quotes:

```python
from fin_infra.investments import easy_investments
from fin_infra.market_data import easy_market_data

# Fetch holdings
investments = easy_investments(provider="plaid")
holdings = await investments.get_holdings(access_token=token)

# Get live quotes for all securities
market_data = easy_market_data(provider="alpha_vantage")
tickers = [h.security.ticker_symbol for h in holdings]
quotes = await market_data.get_quotes(tickers)

# Calculate live portfolio value
live_value = sum(
    h.quantity * quotes[h.security.ticker_symbol].price
    for h in holdings
    if h.security.ticker_symbol in quotes
)

print(f"Live portfolio value: ${live_value:,.2f}")
```

## Use Cases

### Personal Finance: Track Performance

```python
from fin_infra.investments import easy_investments
from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings

async def get_portfolio_summary(user_id: str):
    """Generate portfolio summary for user."""

    # Fetch holdings
    investments = easy_investments()
    token = get_user_plaid_token(user_id)
    holdings = await investments.get_holdings(access_token=token)

    # Calculate metrics
    metrics = portfolio_metrics_with_holdings(holdings)

    return {
        "total_value": metrics.total_value,
        "total_return": metrics.total_return,
        "return_percent": metrics.total_return_percent,
        "allocation": [
            {"asset_class": a.asset_class, "percent": a.percentage}
            for a in metrics.allocation_by_asset_class
        ],
    }
```

### Robo-Advisor: Portfolio Rebalancing

```python
async def calculate_rebalancing_trades(user_id: str, target_allocation: dict):
    """Calculate trades needed to rebalance portfolio."""

    # Fetch current holdings
    investments = easy_investments()
    holdings = await investments.get_holdings(access_token=token)

    # Calculate current allocation
    metrics = portfolio_metrics_with_holdings(holdings)
    current_allocation = {
        a.asset_class: a.percentage
        for a in metrics.allocation_by_asset_class
    }

    # Calculate rebalancing trades
    trades = []
    for asset_class, target_pct in target_allocation.items():
        current_pct = current_allocation.get(asset_class, 0)
        diff_pct = target_pct - current_pct

        if abs(diff_pct) > 1.0:  # Rebalance if >1% off target
            trade_value = (diff_pct / 100) * metrics.total_value
            trades.append({
                "asset_class": asset_class,
                "action": "buy" if diff_pct > 0 else "sell",
                "amount": abs(trade_value),
            })

    return trades
```

### Wealth Management: Client Reporting

```python
from datetime import datetime, timedelta

async def generate_client_report(client_id: str) -> dict:
    """Generate monthly client report."""

    investments = easy_investments()
    token = get_client_plaid_token(client_id)

    # Current holdings
    holdings = await investments.get_holdings(access_token=token)
    metrics = portfolio_metrics_with_holdings(holdings)

    # Transaction history
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    transactions = await investments.get_transactions(
        access_token=token,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "client_id": client_id,
        "report_date": end_date,
        "portfolio": {
            "total_value": metrics.total_value,
            "total_return": metrics.total_return,
            "return_percent": metrics.total_return_percent,
        },
        "allocation": metrics.allocation_by_asset_class,
        "activity": {
            "buys": [t for t in transactions if t.type == "buy"],
            "sells": [t for t in transactions if t.type == "sell"],
            "dividends": [t for t in transactions if t.type == "dividend"],
        },
    }
```

### Tax Tools: Cost Basis Reporting

```python
async def generate_tax_report(user_id: str, tax_year: int) -> dict:
    """Generate tax report with cost basis and capital gains."""

    investments = easy_investments()
    token = get_user_plaid_token(user_id)

    # Fetch transactions for tax year
    transactions = await investments.get_transactions(
        access_token=token,
        start_date=f"{tax_year}-01-01",
        end_date=f"{tax_year}-12-31",
    )

    # Calculate realized gains
    realized_gains = []
    for txn in transactions:
        if txn.type == "sell":
            # Look up cost basis (simplified - real implementation would track lots)
            cost_basis = txn.quantity * txn.price  # Placeholder
            proceeds = txn.amount
            gain = proceeds - cost_basis

            realized_gains.append({
                "security": txn.security.ticker_symbol,
                "date": txn.date,
                "proceeds": proceeds,
                "cost_basis": cost_basis,
                "gain_loss": gain,
            })

    # Current unrealized gains
    holdings = await investments.get_holdings(access_token=token)
    unrealized_gains = sum(
        h.unrealized_gain_loss for h in holdings
        if h.unrealized_gain_loss
    )

    return {
        "tax_year": tax_year,
        "realized_gains": realized_gains,
        "total_realized": sum(g["gain_loss"] for g in realized_gains),
        "unrealized_gains": unrealized_gains,
    }
```

### Net Worth Tracking: Banking + Investments

```python
async def calculate_net_worth(user_id: str) -> dict:
    """Calculate total net worth from all accounts."""

    from fin_infra.banking import easy_banking
    from fin_infra.investments import easy_investments

    token = get_user_plaid_token(user_id)

    # Banking accounts (checking, savings, credit cards)
    banking = easy_banking(provider="plaid")
    bank_accounts = await banking.get_accounts(access_token=token)

    # Investment accounts
    investments = easy_investments(provider="plaid")
    holdings = await investments.get_holdings(access_token=token)

    # Calculate totals
    liquid_assets = sum(
        acc.balance for acc in bank_accounts
        if acc.type in ["depository"]
    )

    investment_assets = sum(
        h.institution_value for h in holdings
    )

    liabilities = sum(
        abs(acc.balance) for acc in bank_accounts
        if acc.type == "credit" and acc.balance < 0
    )

    return {
        "liquid_assets": liquid_assets,
        "investment_assets": investment_assets,
        "total_assets": liquid_assets + investment_assets,
        "liabilities": liabilities,
        "net_worth": liquid_assets + investment_assets - liabilities,
    }
```

## Data Persistence Patterns

### Optional: Applications Scaffold Models

The investments module returns Pydantic models. Applications can optionally persist data:

```python
from sqlalchemy import Column, String, Float, Date, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserHolding(Base):
    """Persist holdings for historical tracking."""
    __tablename__ = "user_holdings"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    account_id = Column(String)
    security_id = Column(String)
    snapshot_date = Column(Date, index=True)

    # Holdings data
    quantity = Column(Float)
    institution_price = Column(Float)
    institution_value = Column(Float)
    cost_basis = Column(Float, nullable=True)

    # Metadata
    security_data = Column(JSON)  # Full Security object
```

### Daily Snapshots for Day Change Tracking

Store daily snapshots to calculate day-over-day changes:

```python
from datetime import datetime, timedelta

async def store_daily_snapshot(user_id: str):
    """Store daily holdings snapshot."""

    investments = easy_investments()
    token = get_user_plaid_token(user_id)
    holdings = await investments.get_holdings(access_token=token)

    today = datetime.now().date()

    for holding in holdings:
        db.add(UserHolding(
            id=f"{user_id}_{holding.account_id}_{holding.security.security_id}_{today}",
            user_id=user_id,
            account_id=holding.account_id,
            security_id=holding.security.security_id,
            snapshot_date=today,
            quantity=float(holding.quantity),
            institution_price=float(holding.institution_price),
            institution_value=float(holding.institution_value),
            cost_basis=float(holding.cost_basis) if holding.cost_basis else None,
            security_data=holding.security.dict(),
        ))

    db.commit()

async def calculate_day_change(user_id: str):
    """Calculate day-over-day portfolio change."""
    from fin_infra.analytics.portfolio import calculate_day_change_with_snapshot

    # Fetch current holdings
    investments = easy_investments()
    token = get_user_plaid_token(user_id)
    current_holdings = await investments.get_holdings(access_token=token)

    # Load yesterday's snapshot
    yesterday = datetime.now().date() - timedelta(days=1)
    previous_snapshot = db.query(UserHolding).filter(
        UserHolding.user_id == user_id,
        UserHolding.snapshot_date == yesterday,
    ).all()

    # Convert to Holding objects
    previous_holdings = [
        Holding(
            account_id=snap.account_id,
            security=Security(**snap.security_data),
            quantity=snap.quantity,
            institution_price=snap.institution_price,
            institution_value=snap.institution_value,
            cost_basis=snap.cost_basis,
        )
        for snap in previous_snapshot
    ]

    # Calculate change
    return calculate_day_change_with_snapshot(current_holdings, previous_holdings)
```

### Time-Series for YTD/MTD Returns

```python
class PortfolioSnapshot(Base):
    """Time-series portfolio snapshots."""
    __tablename__ = "portfolio_snapshots"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    snapshot_date = Column(Date, index=True)

    total_value = Column(Float)
    total_cost_basis = Column(Float)
    total_return = Column(Float)
    total_return_percent = Column(Float)

    allocation = Column(JSON)  # Asset allocation breakdown

async def calculate_ytd_return(user_id: str):
    """Calculate year-to-date return."""
    from datetime import datetime

    # Current value
    investments = easy_investments()
    holdings = await investments.get_holdings(access_token=token)
    metrics = portfolio_metrics_with_holdings(holdings)
    current_value = metrics.total_value

    # Jan 1 value
    jan_1 = datetime(datetime.now().year, 1, 1).date()
    jan_1_snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.user_id == user_id,
        PortfolioSnapshot.snapshot_date == jan_1,
    ).first()

    if jan_1_snapshot:
        ytd_return = current_value - jan_1_snapshot.total_value
        ytd_return_percent = (ytd_return / jan_1_snapshot.total_value) * 100
        return {
            "ytd_return": ytd_return,
            "ytd_return_percent": ytd_return_percent,
        }

    return None
```

### Transaction History for Realized Gains

```python
class UserTransaction(Base):
    """Persist investment transactions."""
    __tablename__ = "user_transactions"

    transaction_id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    account_id = Column(String)
    security_id = Column(String)

    type = Column(String)  # buy, sell, dividend, etc.
    date = Column(Date, index=True)
    quantity = Column(Float)
    price = Column(Float)
    amount = Column(Float)
    fees = Column(Float)

async def calculate_realized_gains(user_id: str, year: int):
    """Calculate realized gains for tax year."""

    transactions = db.query(UserTransaction).filter(
        UserTransaction.user_id == user_id,
        UserTransaction.type.in_(["buy", "sell"]),
        UserTransaction.date.between(f"{year}-01-01", f"{year}-12-31"),
    ).all()

    # Calculate realized gains (simplified - real implementation uses tax lots)
    realized_gains = 0.0
    for txn in transactions:
        if txn.type == "sell":
            # Look up cost basis from buy transactions
            # ... tax lot matching logic ...
            pass

    return realized_gains
```

## Real P/L Calculations

### Current Value vs Cost Basis

The investments module provides **actual cost basis** from providers:

```python
holdings = await investments.get_holdings(access_token=token)

for holding in holdings:
    current_value = holding.institution_value
    cost_basis = holding.cost_basis

    if cost_basis:
        unrealized_gain = current_value - cost_basis
        unrealized_gain_percent = (unrealized_gain / cost_basis) * 100

        print(f"{holding.security.ticker_symbol}:")
        print(f"  Current: ${current_value:,.2f}")
        print(f"  Cost basis: ${cost_basis:,.2f}")
        print(f"  Gain/Loss: ${unrealized_gain:,.2f} ({unrealized_gain_percent:.2f}%)")
```

### Unrealized Gains/Losses

```python
from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings

holdings = await investments.get_holdings(access_token=token)
metrics = portfolio_metrics_with_holdings(holdings)

print(f"Total unrealized gain/loss: ${metrics.total_return:,.2f}")
print(f"Return %: {metrics.total_return_percent:.2f}%")
```

### Asset Allocation Breakdown

```python
metrics = portfolio_metrics_with_holdings(holdings)

print("Asset Allocation:")
for allocation in metrics.allocation_by_asset_class:
    print(f"  {allocation.asset_class}: ${allocation.value:,.2f} ({allocation.percentage:.1f}%)")

# Output:
# Asset Allocation:
#   Stocks: $35,000.00 (70.0%)
#   Bonds: $10,000.00 (20.0%)
#   Cash: $5,000.00 (10.0%)
```

### What Requires Historical Data

**Provided by holdings API:**
- [OK] Current value
- [OK] Cost basis
- [OK] Unrealized P/L
- [OK] Asset allocation

**Requires persistence (applications must implement):**
- ⏳ Day change (requires yesterday's snapshot)
- ⏳ YTD/MTD returns (requires Jan 1 / month start snapshot)
- ⏳ Historical performance (requires time-series data)
- ⏳ Realized gains (requires transaction history)

```python
# Day change - requires yesterday's snapshot
from fin_infra.analytics.portfolio import calculate_day_change_with_snapshot

current = await investments.get_holdings(access_token=token)
previous = load_snapshot_from_db(user_id, date=yesterday)

day_change = calculate_day_change_with_snapshot(current, previous)
print(f"Day change: ${day_change['day_change_dollars']:,.2f}")
```

## Troubleshooting

### Missing Cost Basis

**Issue:** Some holdings return `cost_basis=None`

**Causes:**
- Provider doesn't have cost basis data
- Account type doesn't track cost basis (e.g., some 401(k)s)
- Recent transfers (cost basis not yet updated)

**Solutions:**
```python
# Handle missing cost basis
holdings = await investments.get_holdings(access_token=token)

for holding in holdings:
    if holding.cost_basis is None:
        # Option 1: Skip P/L calculation
        print(f"{holding.security.ticker_symbol}: Cost basis unavailable")

        # Option 2: Estimate from recent transactions
        # ... look up buy transactions ...

        # Option 3: Use current value as baseline
        estimated_cost = holding.institution_value
```

### Stale Data

**Issue:** Holdings show outdated values

**Causes:**
- Provider update lag (some 401(k)s update weekly)
- Market closed (values from previous close)
- Cache on provider side

**Solutions:**
```python
# Force refresh via provider
holdings = await investments.get_holdings(
    access_token=token,
    force_refresh=True  # If provider supports
)

# Check data freshness
for holding in holdings:
    if holding.as_of_date:
        age = datetime.now().date() - holding.as_of_date
        if age.days > 1:
            print(f"Warning: {holding.security.ticker_symbol} data is {age.days} days old")
```

### Rate Limits

**Plaid:**
- Development: 100 requests/minute
- Production: 1000 requests/day (default)
- Solution: Cache holdings, use webhooks for updates

**SnapTrade:**
- Varies by plan
- Solution: Implement exponential backoff

```python
import asyncio
from functools import wraps

def rate_limit_retry(max_retries=3, base_delay=1.0):
    """Retry with exponential backoff on rate limit."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except HTTPException as e:
                    if e.status_code == 429:  # Rate limit
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                    else:
                        raise
            raise Exception(f"Rate limit exceeded after {max_retries} retries")
        return wrapper
    return decorator

@rate_limit_retry()
async def get_holdings_with_retry(token: str):
    return await investments.get_holdings(access_token=token)
```

### Plaid Sandbox Testing

**Sandbox credentials:**
```python
# Plaid sandbox environment
investments = easy_investments(
    provider="plaid",
    plaid_env="sandbox"  # or set PLAID_ENV=sandbox
)

# Sandbox test credentials (publicly available)
# Username: user_good
# Password: pass_good
# Institution: Platypus (ins_109508)

# After Plaid Link, use sandbox access token
holdings = await investments.get_holdings(
    access_token="access-sandbox-..."
)
```

### Data Quality Issues

**Issue:** Missing securities, incorrect types

**Causes:**
- Provider mapping issues
- New securities not in provider database
- Institution data quality

**Solutions:**
```python
# Validate security data
holdings = await investments.get_holdings(access_token=token)

for holding in holdings:
    if not holding.security.ticker_symbol:
        # Missing ticker - may be mutual fund or custom security
        print(f"Warning: No ticker for {holding.security.name}")

    if holding.security.type == "other":
        # Unknown security type - check security_id/cusip
        print(f"Unknown type: {holding.security.name} ({holding.security.security_id})")

# Enrich with market data module
from fin_infra.market_data import easy_market_data

market_data = easy_market_data()
for holding in holdings:
    if holding.security.ticker_symbol:
        quote = await market_data.get_quote(holding.security.ticker_symbol)
        # Use quote for real-time pricing
```

## Future Enhancements

### Day Change Tracking

**Status:**  Requires persistence layer

**Implementation:**
```python
# Applications must store daily snapshots
async def enable_day_change_tracking():
    """Store daily snapshots for day change calculations."""

    # Cron job: Daily at market close
    holdings = await investments.get_holdings(access_token=token)
    store_snapshot(user_id, date=today, holdings=holdings)

    # Calculate day change
    from fin_infra.analytics.portfolio import calculate_day_change_with_snapshot

    current = holdings
    previous = load_snapshot(user_id, date=yesterday)
    day_change = calculate_day_change_with_snapshot(current, previous)
```

### YTD/MTD Returns

**Status:**  Requires time-series persistence

**Implementation:**
```python
# Store monthly/yearly snapshots
async def calculate_ytd_return():
    """Calculate year-to-date return."""

    current_metrics = portfolio_metrics_with_holdings(current_holdings)
    jan_1_snapshot = load_snapshot(user_id, date=f"{year}-01-01")

    ytd_return = current_metrics.total_value - jan_1_snapshot.total_value
    ytd_return_percent = (ytd_return / jan_1_snapshot.total_value) * 100
```

### Historical Performance

**Status:**  Requires time-series database

**Features:**
- Multi-year performance charts
- Rolling returns (1yr, 3yr, 5yr)
- Performance vs benchmark (S&P 500)

### Tax Lot Tracking

**Status:**  Requires transaction history persistence

**Features:**
- FIFO/LIFO/Specific ID cost basis methods
- Short-term vs long-term capital gains
- Wash sale detection
- Tax-loss harvesting opportunities

**Implementation:**
```python
class TaxLot(Base):
    """Track tax lots for capital gains calculations."""
    __tablename__ = "tax_lots"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    security_id = Column(String)

    acquisition_date = Column(Date)
    quantity = Column(Float)
    cost_basis_per_share = Column(Float)
    total_cost_basis = Column(Float)

    disposal_date = Column(Date, nullable=True)
    disposal_price = Column(Float, nullable=True)
    realized_gain_loss = Column(Float, nullable=True)
```

### Dividend Tracking and Reinvestment

**Status:**  Requires transaction monitoring

**Features:**
- Track dividend payments
- Calculate dividend yield
- Monitor reinvestment (DRIP)
- Annual dividend income reporting

## Related Documentation

- [Brokerage Integration](brokerage.md) - Execute trades and manage orders
- [Banking Module](banking.md) - Bank accounts and transactions
- [Analytics Module](analytics.md) - Portfolio analytics and insights
- [Market Data](market-data.md) - Real-time quotes and market data
- [Categorization](categorization.md) - Transaction categorization
- [Persistence](persistence.md) - Data storage patterns

---

**Next Steps:**
1. Set up Plaid sandbox account for testing
2. Implement `easy_investments()` in your application
3. Test with sandbox credentials
4. Set up daily snapshot persistence (optional)
5. Integrate with analytics module for real P/L
6. Move to production with real Plaid credentials
