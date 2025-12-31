# fin-infra

**Financial data infrastructure for fintech apps.**

[![PyPI](https://img.shields.io/pypi/v/fin-infra.svg)](https://pypi.org/project/fin-infra/)
[![CI](https://github.com/nfraxlab/fin-infra/actions/workflows/ci.yml/badge.svg)](https://github.com/nfraxlab/fin-infra/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/fin-infra.svg)](https://pypi.org/project/fin-infra/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

Banking, investments, market data, credit scores, and financial calculations in one toolkit.

### Key Features

- **Banking** - Plaid/Teller integration, accounts, transactions
- **Investments** - Holdings, portfolio data, real P/L with cost basis
- **Market Data** - Stocks, crypto, forex quotes and history
- **Credit** - Credit scores and monitoring
- **Analytics** - Cash flow, savings rate, spending insights
- **Cashflows** - NPV, IRR, loan amortization calculations

## Why fin-infra?

Building a fintech app means integrating Plaid, pulling market data, calculating portfolio returns, categorizing transactions... and doing it all securely.

**fin-infra** gives you production-ready financial infrastructure:

```python
from fin_infra.banking import easy_banking
from fin_infra.markets import easy_market

# Connect to banks via Plaid
banking = easy_banking()
accounts = await banking.get_accounts(access_token)
transactions = await banking.get_transactions(account_id)

# Get market data
market = easy_market()
quote = market.quote("AAPL")
```

## Quick Install

```bash
pip install fin-infra
```

## What's Included

| Feature | What You Get | One-liner |
|---------|-------------|-----------|
| **Banking** | Plaid/Teller integration, accounts, transactions | `easy_banking()` |
| **Investments** | Holdings, portfolio data, real P/L with cost basis | `easy_investments()` |
| **Market Data** | Stocks, crypto, forex quotes and history | `easy_market()` |
| **Credit** | Credit scores and monitoring | `easy_credit()` |
| **Analytics** | Cash flow, savings rate, spending insights | Built-in |
| **Budgets** | Multi-type budget tracking with templates | Scaffold included |
| **Goals** | Financial goal tracking with milestones | Scaffold included |
| **Cashflows** | NPV, IRR, loan amortization calculations | `npv()`, `irr()` |

## 30-Second Examples

### Connect Bank Accounts

```python
from fin_infra.banking import easy_banking

banking = easy_banking(provider="plaid")

# Get linked accounts
accounts = await banking.get_accounts(access_token)
for acc in accounts:
    print(f"{acc.name}: ${acc.balance}")

# Get transactions
transactions = await banking.get_transactions(account_id)
```

### Portfolio Holdings with Real P/L

```python
from fin_infra.investments import easy_investments

investments = easy_investments(provider="plaid")

# Get holdings with cost basis
holdings = await investments.get_holdings(access_token)
for h in holdings:
    print(f"{h.symbol}: {h.quantity} shares, P/L: ${h.unrealized_gain}")

# Asset allocation
allocation = await investments.get_allocation(access_token)
print(allocation)  # {"stocks": 60, "bonds": 30, "cash": 10}
```

### Real-Time Market Data

```python
from fin_infra.markets import easy_market, easy_crypto

# Stock quotes
market = easy_market()
quote = market.quote("AAPL")
print(f"AAPL: ${quote.price} ({quote.change_percent}%)")

# Crypto
crypto = easy_crypto()
btc = crypto.ticker("BTC/USDT")
print(f"BTC: ${btc.price}")
```

### Credit Scores

```python
from fin_infra.credit import easy_credit

credit = easy_credit()
score = await credit.get_credit_score(user_id)
print(f"Credit Score: {score.value} ({score.rating})")
```

### Financial Calculations

```python
from fin_infra.cashflows import npv, irr, loan_payment

# Net Present Value
cashflows = [-100000, 30000, 30000, 30000, 30000]
value = npv(rate=0.08, cashflows=cashflows)
print(f"NPV: ${value:,.2f}")

# Internal Rate of Return
rate = irr(cashflows)
print(f"IRR: {rate:.2%}")

# Loan payments
monthly = loan_payment(principal=250000, rate=0.065, years=30)
print(f"Monthly payment: ${monthly:,.2f}")
```

## FastAPI Integration

Use with [svc-infra](https://github.com/nfraxlab/svc-infra) for a complete backend:

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.banking import add_banking
from fin_infra.investments import add_investments
from fin_infra.markets import add_market_data

# Create app with svc-infra (auth, database, etc.)
app = easy_service_app(name="FinanceAPI", release="1.0.0")

# Add financial capabilities
add_banking(app, provider="plaid")
add_investments(app, provider="plaid")
add_market_data(app, provider="alphavantage")

# Automatic endpoints:
# GET  /banking/accounts
# GET  /banking/transactions
# GET  /investments/holdings
# GET  /investments/allocation
# GET  /market/quote/{symbol}
```

## Supported Providers

| Category | Providers |
|----------|-----------|
| **Banking** | Plaid, Teller |
| **Investments** | Plaid |
| **Market Data** | Alpha Vantage, Yahoo Finance |
| **Crypto** | CoinGecko, Binance |
| **Credit** | Experian |

## Scaffold Models

Generate production-ready models for your app:

```bash
# Generate budget models
fin-infra scaffold budgets --dest-dir app/models/ --include-tenant

# Generate goal tracking
fin-infra scaffold goals --dest-dir app/models/

# Generate net worth snapshots
fin-infra scaffold net-worth --dest-dir app/models/
```

**What you get:**
- SQLAlchemy models with proper indexes
- Pydantic schemas (Create, Read, Update)
- Repository pattern with async CRUD
- Type hints throughout

**Wire CRUD in one call:**

```python
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget

add_sql_resources(app, [
    SqlResource(
        model=Budget,
        prefix="/budgets",
        search_fields=["name", "description"],
    )
])
# Creates: POST, GET, PATCH, DELETE /budgets/*
```

## Configuration

```bash
# Banking (Plaid)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox  # or development, production

# Market Data
ALPHAVANTAGE_API_KEY=your_api_key

# Credit (Experian)
EXPERIAN_CLIENT_ID=your_client_id
EXPERIAN_CLIENT_SECRET=your_secret
```

## Documentation

| Module | Description |
|--------|-------------|
| **Data Integration** | |
| [Banking](docs/banking.md) | Account aggregation, transactions |
| [Investments](docs/investments.md) | Holdings, portfolio, P/L |
| [Market Data](docs/market-data.md) | Stocks, crypto, forex |
| [Credit](docs/credit.md) | Credit scores and reports |
| **Analytics** | |
| [Analytics](docs/analytics.md) | Cash flow, savings rate, insights |
| [Net Worth](docs/net-worth.md) | Net worth tracking |
| [Cashflows](docs/cashflows.md) | NPV, IRR, loan calculations |
| **Features** | |
| [Budgets](docs/budgets.md) | Budget management |
| [Goals](docs/goals.md) | Financial goal tracking |
| [Insights](docs/insights.md) | AI-powered insights |
| [Categorization](docs/categorization.md) | Transaction categorization |
| **Infrastructure** | |
| [Persistence](docs/persistence.md) | Scaffold workflow |
| [API Guide](docs/api.md) | Building fintech APIs |
| [Compliance](docs/compliance.md) | GLBA, FCRA, PCI-DSS |

## Architecture

fin-infra is the **financial data layer**. Use with **svc-infra** for backend infrastructure:

```
Your App
    |
    +-- fin-infra (financial data)
    |       Banking, investments, market data, credit
    |
    +-- svc-infra (backend infrastructure)
            Auth, database, API framework, jobs, billing
```

This separation keeps financial logic clean and portable.

## Running Examples

```bash
git clone https://github.com/nfraxlab/fin-infra.git
cd fin-infra
poetry install

# Market data (no auth needed)
poetry run python -c "
from fin_infra.markets import easy_market
market = easy_market()
print(market.quote('AAPL'))
"

# Run all tests
poetry run pytest -q
```

## Related Packages

fin-infra is part of the **nfrax** infrastructure suite:

| Package | Purpose |
|---------|---------|
| **[fin-infra](https://github.com/nfraxlab/fin-infra)** | Financial infrastructure (banking, portfolio, insights) |
| **[svc-infra](https://github.com/nfraxlab/svc-infra)** | Backend infrastructure (auth, billing, jobs, webhooks) |
| **[ai-infra](https://github.com/nfraxlab/ai-infra)** | AI/LLM infrastructure (agents, tools, RAG, MCP) |

## License

MIT License - use it for anything.

---

<div align="center">

**Built by [nfraxlab](https://github.com/nfraxlab)**

[Star us on GitHub](https://github.com/nfraxlab/fin-infra) | [View on PyPI](https://pypi.org/project/fin-infra/)

</div>
