# Quickstart

> From zero to financial data in 5 minutes.

## 1. Install

```bash
pip install fin-infra
```

With Plaid banking:

```bash
pip install fin-infra[plaid]
```

## 2. Set Your API Keys

```bash
export ALPHAVANTAGE_API_KEY="your-key"
```

Or create a `.env` file:

```bash
ALPHAVANTAGE_API_KEY=your-key
PLAID_CLIENT_ID=your-client-id
PLAID_SECRET=your-secret
```

## 3. Get a Stock Quote

```python
from fin_infra.markets import easy_market

market = easy_market(provider="alphavantage")
quote = market.quote("AAPL")

print(f"Apple: ${quote.price}")
print(f"Change: {quote.change_percent}%")
```

Done. You're fetching real market data.

---

## 4. Get Crypto Prices

```python
from fin_infra.markets import easy_market

market = easy_market(provider="alphavantage")
btc = market.crypto_quote("BTC", "USD")

print(f"Bitcoin: ${btc.price:,.2f}")
```

---

## 5. Connect Plaid Sandbox

```python
from fin_infra.banking import easy_banking

# Use Plaid sandbox for testing
banking = easy_banking(
    provider="plaid",
    environment="sandbox",
)

# Create a sandbox access token (for testing only)
access_token = await banking.create_sandbox_token(
    institution_id="ins_109508",  # Chase sandbox
    products=["transactions", "auth"],
)

# Get accounts
accounts = await banking.get_accounts(access_token)
for account in accounts:
    print(f"{account.name}: ${account.balance:,.2f}")
```

---

## 6. Categorize Transactions

```python
from fin_infra.categorization import easy_categorization

categorizer = easy_categorization()

# Categorize by merchant name
category = categorizer.categorize("STARBUCKS #12345 SAN FRANCISCO")
print(f"Category: {category.name}")  # "Food & Drink"
print(f"Subcategory: {category.subcategory}")  # "Coffee Shops"
```

---

## Complete Example

```python
from fin_infra.markets import easy_market
from fin_infra.categorization import easy_categorization

# Get market data
market = easy_market(provider="alphavantage")

# Stock quotes
for symbol in ["AAPL", "GOOGL", "MSFT"]:
    quote = market.quote(symbol)
    print(f"{symbol}: ${quote.price} ({quote.change_percent:+.2f}%)")

# Categorize transactions
categorizer = easy_categorization()
transactions = [
    "AMAZON.COM*123456",
    "UBER *TRIP",
    "NETFLIX.COM",
]

for tx in transactions:
    cat = categorizer.categorize(tx)
    print(f"{tx} -> {cat.name}")
```

---

## Next Steps

- [Getting Started](getting-started.md) - Full guide with all features
- [Market Data](market-data.md) - Stocks, crypto, forex
- [Banking](banking/plaid.md) - Plaid, Teller integration
- [Categorization](categorization.md) - Transaction categorization
- [Net Worth](net-worth.md) - Track assets and liabilities
