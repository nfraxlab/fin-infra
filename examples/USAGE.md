# Usage Guide

Detailed examples for each fin-infra capability with copy-paste code snippets.

## Table of Contents

###  Provider Integrations
- [Banking Integration](#banking-integration)
- [Market Data](#market-data)
- [Crypto Data](#crypto-data)
- [Credit Scores](#credit-scores)
- [Brokerage](#brokerage)
- [Tax Data](#tax-data)

### 🧠 Financial Intelligence
- [Analytics](#analytics)
- [Categorization](#categorization)
- [Recurring Detection](#recurring-detection)
- [Insights Feed](#insights-feed)

###  Financial Planning
- [Budgets](#budgets)
- [Goals](#goals)
- [Net Worth Tracking](#net-worth-tracking)

### 📄 Document & Compliance
- [Documents](#documents)
- [Security](#security)
- [Compliance](#compliance)

### 🛠 Utilities
- [Normalization](#normalization)
- [Cashflows](#cashflows)
- [Conversation](#conversation)

---

## Banking Integration

### Get Link Token (Plaid)

```bash
curl http://localhost:8001/banking/link

# Response:
{
  "link_token": "link-sandbox-abc123...",
  "expiration": "2024-01-15T10:30:00Z",
  "instructions": "Use Plaid Link with this token",
  "sandbox_credentials": {
    "username": "user_good",
    "password": "pass_good"
  }
}
```

### Exchange Public Token

After user completes Plaid Link flow:

```bash
curl -X POST http://localhost:8001/banking/exchange \
  -H "Content-Type: application/json" \
  -d '{
    "public_token": "public-sandbox-xyz789..."
  }'

# Response:
{
  "access_token": "access-sandbox-def456...",
  "item_id": "item123"
}
```

### Get Accounts

```bash
curl "http://localhost:8001/banking/accounts?access_token=access-sandbox-def456..."

# Response:
{
  "accounts": [
    {
      "account_id": "acc_123",
      "name": "Plaid Checking",
      "type": "depository",
      "subtype": "checking",
      "balance": {
        "available": 10000.50,
        "current": 10500.75
      }
    },
    {
      "account_id": "acc_124",
      "name": "Plaid Savings",
      "type": "depository",
      "subtype": "savings",
      "balance": {
        "available": 25000.00,
        "current": 25000.00
      }
    }
  ]
}
```

### Get Transactions

```bash
curl "http://localhost:8001/banking/transactions?access_token=access-sandbox-def456...&start_date=2024-01-01&end_date=2024-01-31"

# Response:
{
  "transactions": [
    {
      "transaction_id": "txn_123",
      "account_id": "acc_123",
      "amount": -5.75,
      "date": "2024-01-15",
      "name": "Starbucks",
      "merchant_name": "Starbucks",
      "category": ["Food and Drink", "Restaurants", "Coffee Shop"]
    }
  ],
  "total_transactions": 1
}
```

---

## Market Data

### Get Stock Quote

```bash
curl http://localhost:8001/market/quote/AAPL

# Response:
{
  "symbol": "AAPL",
  "price": 182.50,
  "change": 2.30,
  "change_percent": 1.28,
  "volume": 52341234,
  "open": 180.20,
  "high": 183.00,
  "low": 179.50,
  "previous_close": 180.20,
  "timestamp": "2024-01-15T16:00:00Z"
}
```

### Get Multiple Quotes

```bash
curl "http://localhost:8001/market/quotes?symbols=AAPL,GOOGL,MSFT"

# Response:
{
  "quotes": [
    {"symbol": "AAPL", "price": 182.50, ...},
    {"symbol": "GOOGL", "price": 142.30, ...},
    {"symbol": "MSFT", "price": 375.80, ...}
  ]
}
```

### Get Historical Data

```bash
curl "http://localhost:8001/market/history/AAPL?start_date=2024-01-01&end_date=2024-01-31"

# Response:
{
  "symbol": "AAPL",
  "data": [
    {"date": "2024-01-31", "close": 182.50, "volume": 52341234},
    {"date": "2024-01-30", "close": 180.20, "volume": 48932145}
  ]
}
```

---

## Crypto Data

### Get Crypto Quote

```bash
curl http://localhost:8001/crypto/quote/BTC

# Response:
{
  "symbol": "BTC",
  "name": "Bitcoin",
  "price": 43250.50,
  "change_24h": 1250.30,
  "change_percent_24h": 2.98,
  "market_cap": 845231234567,
  "volume_24h": 28431234567,
  "high_24h": 43500.00,
  "low_24h": 41800.00
}
```

### Get Multiple Crypto Quotes

```bash
curl "http://localhost:8001/crypto/quotes?symbols=BTC,ETH,SOL"

# Response:
{
  "quotes": [
    {"symbol": "BTC", "price": 43250.50, ...},
    {"symbol": "ETH", "price": 2315.75, ...},
    {"symbol": "SOL", "price": 105.23, ...}
  ]
}
```

---

## Investments

### Get Investment Holdings

```bash
curl http://localhost:8001/investments/holdings

# Response:
{
  "holdings": [
    {
      "account_id": "acc_401k_123",
      "account_name": "Vanguard 401(k)",
      "security": {
        "ticker_symbol": "VFIAX",
        "name": "Vanguard 500 Index Fund Admiral",
        "type": "mutual_fund",
        "close_price": 425.67
      },
      "quantity": 234.567,
      "institution_value": 99876.54,
      "cost_basis": 85000.00,
      "unrealized_gain_loss": 14876.54,
      "unrealized_gain_loss_percent": 17.50
    }
  ],
  "total_value": 117419.54,
  "total_cost_basis": 100000.00,
  "total_unrealized_gain_loss": 17419.54
}
```

### Get Asset Allocation

```bash
curl http://localhost:8001/investments/allocation

# Response:
{
  "allocation_by_asset_class": [
    {
      "asset_class": "equity",
      "value": 70493.72,
      "percentage": 60.0
    },
    {
      "asset_class": "mutual_fund",
      "value": 35246.86,
      "percentage": 30.0
    },
    {
      "asset_class": "bond",
      "value": 11748.95,
      "percentage": 10.0
    }
  ],
  "total_value": 117419.54
}
```

### Get Investment Accounts

```bash
curl http://localhost:8001/investments/accounts

# Response:
{
  "accounts": [
    {
      "account_id": "acc_401k_123",
      "name": "Vanguard 401(k)",
      "type": "investment",
      "subtype": "401k",
      "total_value": 99876.54,
      "total_cost_basis": 85000.00,
      "total_unrealized_gain_loss": 14876.54,
      "holdings_count": 5
    },
    {
      "account_id": "acc_ira_456",
      "name": "Fidelity Roth IRA",
      "type": "investment",
      "subtype": "roth_ira",
      "total_value": 17543.00,
      "total_cost_basis": 15000.00,
      "total_unrealized_gain_loss": 2543.00,
      "holdings_count": 3
    }
  ],
  "total_value": 117419.54
}
```

**Note**: Configure `PLAID_CLIENT_ID` and `PLAID_SECRET` (for 401k/IRA) or `SNAPTRADE_CLIENT_ID` and `SNAPTRADE_CONSUMER_KEY` (for retail brokerages) in `.env` for real holdings data.

---

## Analytics

### Cash Flow Analysis

```bash
curl http://localhost:8001/analytics/cash-flow/user_123

# Response:
{
  "user_id": "user_123",
  "period": "2024-01",
  "income": 5000.00,
  "expenses": 3500.00,
  "net_cash_flow": 1500.00,
  "categories": {
    "Food and Drink": -450.00,
    "Transportation": -200.00,
    "Shopping": -300.00
  }
}
```

### Savings Rate

```bash
curl http://localhost:8001/analytics/savings-rate/user_123

# Response:
{
  "user_id": "user_123",
  "period": "2024-01",
  "income": 5000.00,
  "savings": 1500.00,
  "savings_rate": 0.30,
  "savings_rate_percent": 30.0,
  "target_rate": 0.20,
  "ahead_of_target": true
}
```

### Spending Insights

```bash
curl http://localhost:8001/analytics/spending-insights/user_123

# Response:
{
  "user_id": "user_123",
  "insights": [
    {
      "category": "Food and Drink",
      "amount": 450.00,
      "vs_average": 1.25,
      "trend": "increasing",
      "message": "Spending 25% more than average on dining"
    }
  ]
}
```

### AI-Powered Financial Advice

```bash
curl http://localhost:8001/analytics/advice/user_123

# Response:
{
  "advice": "Based on your spending patterns, consider reducing dining expenses by $150/month to reach your savings goal faster.",
  "confidence": 0.85,
  "actionable_steps": [
    "Meal prep 3 times per week",
    "Limit dining out to 2x per week",
    "Use grocery delivery to avoid impulse purchases"
  ]
}
```

---

## Categorization

### Categorize Single Transaction

```bash
curl -X POST http://localhost:8001/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "description": "STARBUCKS COFFEE",
    "amount": 5.75
  }'

# Response:
{
  "category": "Food and Drink > Restaurants > Coffee Shop",
  "category_id": "13005031",
  "confidence": 0.95,
  "method": "rule_based"
}
```

### Batch Categorization

```bash
curl -X POST http://localhost:8001/categorize/batch \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {"description": "UBER RIDE", "amount": 15.50},
      {"description": "WHOLE FOODS", "amount": 125.30},
      {"description": "NETFLIX", "amount": 15.99}
    ]
  }'

# Response:
{
  "results": [
    {"category": "Transportation > Taxi", "confidence": 0.92},
    {"category": "Food and Drink > Groceries", "confidence": 0.88},
    {"category": "Entertainment > Streaming Services", "confidence": 0.95}
  ]
}
```

---

## Recurring Detection

### Detect Recurring Patterns

```bash
curl -X POST http://localhost:8001/recurring/detect \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "transactions": [
      {"date": "2024-01-15", "amount": 15.99, "description": "NETFLIX"},
      {"date": "2024-02-15", "amount": 15.99, "description": "NETFLIX"},
      {"date": "2024-03-15", "amount": 15.99, "description": "NETFLIX"}
    ]
  }'

# Response:
{
  "patterns": [
    {
      "pattern_id": "rec_123",
      "merchant": "NETFLIX",
      "frequency": "monthly",
      "amount": 15.99,
      "variance": 0.0,
      "confidence": 0.98,
      "next_expected_date": "2024-04-15"
    }
  ]
}
```

---

## Budgets

### Create Budget

```bash
curl -X POST http://localhost:8001/budgets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "name": "Monthly Budget",
    "type": "monthly",
    "start_date": "2024-01-01",
    "categories": {
      "Food and Drink": 500.00,
      "Transportation": 200.00,
      "Shopping": 300.00
    }
  }'

# Response:
{
  "budget_id": "bdg_123",
  "name": "Monthly Budget",
  "total_budget": 1000.00,
  "categories": {...},
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Get Budget Status

```bash
curl http://localhost:8001/budgets/bdg_123/status

# Response:
{
  "budget_id": "bdg_123",
  "period": "2024-01",
  "total_budget": 1000.00,
  "total_spent": 750.00,
  "remaining": 250.00,
  "utilization": 0.75,
  "categories": {
    "Food and Drink": {
      "budget": 500.00,
      "spent": 450.00,
      "remaining": 50.00,
      "status": "on_track"
    },
    "Transportation": {
      "budget": 200.00,
      "spent": 200.00,
      "remaining": 0.00,
      "status": "at_limit"
    },
    "Shopping": {
      "budget": 300.00,
      "spent": 100.00,
      "remaining": 200.00,
      "status": "under_budget"
    }
  }
}
```

---

## Goals

### Create Financial Goal

```bash
curl -X POST http://localhost:8001/goals \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "name": "Emergency Fund",
    "target_amount": 10000.00,
    "current_amount": 2500.00,
    "target_date": "2024-12-31",
    "priority": "high"
  }'

# Response:
{
  "goal_id": "goal_123",
  "name": "Emergency Fund",
  "target_amount": 10000.00,
  "current_amount": 2500.00,
  "progress_percent": 25.0,
  "monthly_contribution_needed": 750.00,
  "on_track": true
}
```

### Update Goal Progress

```bash
curl -X PATCH http://localhost:8001/goals/goal_123 \
  -H "Content-Type: application/json" \
  -d '{
    "current_amount": 3000.00
  }'

# Response:
{
  "goal_id": "goal_123",
  "progress_percent": 30.0,
  "monthly_contribution_needed": 700.00,
  "on_track": true
}
```

---

## Net Worth Tracking

### Get Net Worth Snapshot

```bash
curl http://localhost:8001/net-worth/user_123

# Response:
{
  "user_id": "user_123",
  "total_assets": 75000.00,
  "total_liabilities": 25000.00,
  "net_worth": 50000.00,
  "assets": {
    "checking": 10000.00,
    "savings": 25000.00,
    "investment": 35000.00,
    "retirement": 5000.00
  },
  "liabilities": {
    "credit_card": 2000.00,
    "student_loan": 20000.00,
    "auto_loan": 3000.00
  },
  "change_30d": 2500.00,
  "change_percent_30d": 5.26
}
```

### Get Net Worth History

```bash
curl "http://localhost:8001/net-worth/user_123/history?start_date=2024-01-01&end_date=2024-01-31"

# Response:
{
  "user_id": "user_123",
  "snapshots": [
    {"date": "2024-01-31", "net_worth": 50000.00},
    {"date": "2024-01-30", "net_worth": 49800.00},
    {"date": "2024-01-29", "net_worth": 49500.00}
  ]
}
```

---

## Cashflows

### Calculate NPV

```bash
curl -X POST http://localhost:8001/cashflows/npv \
  -H "Content-Type: application/json" \
  -d '{
    "rate": 0.08,
    "cashflows": [-10000, 3000, 4000, 5000]
  }'

# Response:
{
  "npv": 1234.56
}
```

### Calculate IRR

```bash
curl -X POST http://localhost:8001/cashflows/irr \
  -H "Content-Type: application/json" \
  -d '{
    "cashflows": [-10000, 3000, 4000, 5000]
  }'

# Response:
{
  "irr": 0.123
}
```

### Calculate Loan Payment

```bash
curl -X POST http://localhost:8001/cashflows/pmt \
  -H "Content-Type: application/json" \
  -d '{
    "rate": 0.004167,
    "nper": 360,
    "pv": 200000
  }'

# Response:
{
  "pmt": -1073.64
}
```

### Calculate Future Value

```bash
curl -X POST http://localhost:8001/cashflows/fv \
  -H "Content-Type: application/json" \
  -d '{
    "rate": 0.005833,
    "nper": 120,
    "pmt": -500
  }'

# Response:
{
  "fv": 86920.42
}
```

---

## Conversation

### Ask Financial Question

```bash
curl -X POST http://localhost:8001/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How can I save more money each month?",
    "net_worth": 50000.0
  }'

# Response:
{
  "answer": "Based on your net worth of $50,000, here are personalized strategies to increase your monthly savings:\n\n1. Track all expenses for 30 days to identify unnecessary spending\n2. Implement the 50/30/20 rule: 50% needs, 30% wants, 20% savings\n3. Automate savings transfers right after payday\n4. Review and cancel unused subscriptions\n5. Consider a high-yield savings account for better returns\n\nStart with tracking expenses this month to establish a baseline.",
  "follow_up_questions": [
    "What's your current monthly income?",
    "Do you have any high-interest debt?",
    "What are your short-term financial goals?"
  ],
  "conversation_id": "conv_123",
  "disclaimer": "This is AI-generated advice and not a substitute for a certified financial advisor."
}
```

### Get Conversation History

```bash
curl http://localhost:8001/chat/history

# Response:
{
  "exchanges": [
    {
      "question": "How can I save more money?",
      "answer": "...",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## Normalization

### Resolve Symbol

```bash
curl http://localhost:8001/normalize/symbol/AAPL

# Response:
{
  "ticker": "AAPL",
  "cusip": "037833100",
  "isin": "US0378331005",
  "name": "Apple Inc.",
  "exchange": "NASDAQ",
  "type": "stock"
}
```

### Convert Currency

```bash
curl "http://localhost:8001/normalize/convert?from=USD&to=EUR&amount=100"

# Response:
{
  "from_currency": "USD",
  "to_currency": "EUR",
  "amount": 100.00,
  "converted_amount": 92.50,
  "rate": 0.925,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Programming Examples

### Python Client Example

```python
import httpx
import asyncio

async def get_stock_quote(symbol: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8001/market/quote/{symbol}"
        )
        return response.json()

# Usage
quote = asyncio.run(get_stock_quote("AAPL"))
print(f"AAPL: ${quote['price']}")
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function getStockQuote(symbol) {
  const response = await axios.get(
    `http://localhost:8001/market/quote/${symbol}`
  );
  return response.data;
}

// Usage
getStockQuote('AAPL').then(quote => {
  console.log(`AAPL: $${quote.price}`);
});
```

### cURL with Authentication (Future)

Once authentication is enabled:

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.access_token')

# Use token in requests
curl http://localhost:8001/budgets \
  -H "Authorization: Bearer $TOKEN"
```

---

## Best Practices

### Error Handling

All endpoints return standard error responses:

```json
{
  "detail": "Provider not configured",
  "error_code": "PROVIDER_NOT_CONFIGURED",
  "suggestions": [
    "Set PLAID_CLIENT_ID in .env",
    "Restart server after configuration"
  ]
}
```

### Rate Limiting

Be mindful of provider rate limits:

- **Alpha Vantage Free**: 5 calls/min, 100/day
- **CoinGecko Free**: 50 calls/min
- **Plaid Sandbox**: Unlimited

### Caching

Expensive operations are cached:

- Market quotes: 1 minute
- Analytics: 24 hours
- Normalizations: 7 days

### Production Considerations

1. **Use environment variables** for all credentials
2. **Enable Redis** for distributed caching
3. **Set APP_ENV=prod** for production logging
4. **Use PostgreSQL** instead of SQLite
5. **Enable authentication** before deployment
6. **Monitor costs** with provider dashboards

---

## Next Steps

- **Explore [docs/CAPABILITIES.md](docs/CAPABILITIES.md)** for complete feature reference
- **Read [docs/PROVIDERS.md](docs/PROVIDERS.md)** for provider setup
- **Check [docs/DATABASE.md](docs/DATABASE.md)** for database configuration
- **Review main.py** for implementation details

---

**Need help?** Open an issue on GitHub or check the documentation in [docs/](docs/).
