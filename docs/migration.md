# Migration Guide

This guide documents breaking changes and migration paths between versions of fin-infra.

## Version Compatibility

| fin-infra | Python | svc-infra | ai-infra | Notes |
|-----------|--------|-----------|----------|-------|
| 1.0.x | 3.11+ | >=1.0.0 | >=1.0.0 | Stable API, production ready |
| 0.1.x | 3.11+ | >=0.1.0 | >=0.1.0 | Legacy (deprecated) |

## Migrating to 1.0.0

### No Breaking Changes

v1.0.0 is API-compatible with 0.1.x. This release marks API stability:

- All documented APIs are now considered stable
- Breaking changes will follow semantic versioning (major version bumps)
- Deprecated features will have 2+ minor version warning period

### What's New in 1.0.0

- **Enhanced documentation**: Comprehensive API reference with mkdocstrings
- **Experimental APIs marked**: See `docs/reference/experimental.md`
- **Improved test coverage**: 70%+ coverage on all modules

### Deprecated Aliases

The following will be removed in v2.0.0:

```python
# Deprecated
from fin_infra.markets import StockMarketData

# Use instead
from fin_infra.markets import MarketData
```

### Recommended Upgrades

```python
# Use the normalized providers for consistent API
from fin_infra.banking import easy_banking
from fin_infra.brokerage import easy_brokerage
from fin_infra.markets import easy_market
```

## Migrating to 0.1.x

### From Direct Provider SDKs

If you're migrating from direct Plaid/Alpaca SDK usage:

#### Banking (from Plaid SDK)

```python
# Before (direct Plaid)
from plaid.api import plaid_api
from plaid.model import AccountsGetRequest

client = plaid_api.PlaidApi(configuration)
request = AccountsGetRequest(access_token=token)
response = client.accounts_get(request)
accounts = response["accounts"]

# After (fin-infra)
from fin_infra.banking import easy_banking

banking = easy_banking(provider="plaid")
accounts = await banking.get_accounts(token)
# Returns normalized Account models
```

#### Brokerage (from Alpaca SDK)

```python
# Before (direct Alpaca)
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest

client = TradingClient(api_key, secret_key)
order = client.submit_order(
    MarketOrderRequest(symbol="AAPL", qty=10, side="buy", ...)
)

# After (fin-infra)
from fin_infra.brokerage import easy_brokerage

brokerage = easy_brokerage(provider="alpaca")
order = await brokerage.submit_order(
    symbol="AAPL",
    quantity=Decimal("10"),
    side="buy",
    order_type="market",
    client_order_id=str(uuid.uuid4()),  # Required for idempotency
)
```

#### Market Data (from Yahoo Finance)

```python
# Before (direct yfinance)
import yfinance as yf

ticker = yf.Ticker("AAPL")
quote = ticker.info

# After (fin-infra)
from fin_infra.markets import easy_market

market = easy_market(provider="yahoo")
quote = market.quote("AAPL")
# Returns normalized Quote model
```

## Critical Migration Notes

### Money Handling

**fin-infra uses Decimal for all money values:**

```python
# Before (float - WRONG)
total = sum(float(txn.amount) for txn in transactions)

# After (Decimal - CORRECT)
from decimal import Decimal
total = sum(Decimal(str(txn.amount)) for txn in transactions)
```

### Idempotency Keys

**All order submissions require idempotency keys:**

```python
# Before (optional - dangerous)
order = await broker.submit_order(symbol, qty)

# After (required)
import uuid
order = await brokerage.submit_order(
    symbol=symbol,
    quantity=qty,
    client_order_id=str(uuid.uuid4()),  # REQUIRED
)
```

### Provider Configuration

**Credentials now auto-detected from environment:**

```python
# Before (explicit config)
banking = PlaidClient(
    client_id="...",
    secret="...",
    environment="sandbox",
)

# After (auto-detect from env)
# Set PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENVIRONMENT
banking = easy_banking(provider="plaid")  # Auto-configures
```

## Planned Breaking Changes (0.2.x)

### Async-First API

```python
# 0.1.x (sync market data)
quote = market.quote("AAPL")

# 0.2.x (planned - async everywhere)
quote = await market.quote("AAPL")
```

### Model Renames

```python
# 0.1.x
from fin_infra.models import Account, Transaction

# 0.2.x (planned)
from fin_infra.models.banking import BankAccount
from fin_infra.models.transactions import BankTransaction
```

## Deprecation Notices

### 0.1.50+

- `banking.easy_banking()` moved to `fin_infra.banking.easy_banking()`
- Old model locations deprecated

### 0.1.100+

- Sync market data methods deprecated (use async)
- Float amounts in models trigger warnings

## Getting Help

- Check the [error handling guide](error-handling.md) for exception changes
- Open an issue for migration questions
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines
