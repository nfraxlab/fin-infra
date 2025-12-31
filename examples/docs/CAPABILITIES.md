# Complete Capabilities Reference

Comprehensive technical documentation for all 20+ fin-infra capabilities.

## Table of Contents

###  Banking & Accounts
- [Banking Integration](#banking-integration)

###  Markets & Trading
- [Market Data (Stocks/ETFs)](#market-data)
- [Crypto Data](#crypto-data)
- [Brokerage Integration](#brokerage-integration)

###  Credit & Identity
- [Credit Scores](#credit-scores)

###  Tax & Compliance
- [Tax Data](#tax-data)

### 🧠 Financial Intelligence
- [Analytics](#analytics)
- [Categorization](#categorization)
- [Recurring Detection](#recurring-detection)
- [Insights Feed](#insights-feed)

###  Planning & Tracking
- [Budgets](#budgets)
- [Goals](#goals)
- [Net Worth Tracking](#net-worth-tracking)

### 📄 Documents & Security
- [Documents](#documents)
- [Security](#security)

### 🛠 Utilities
- [Normalization](#normalization)
- [Cashflows](#cashflows)
- [Conversation (AI Chat)](#conversation)

---

## Banking Integration

**Provider**: Plaid (Teller, MX planned)  
**Prefix**: `/banking`  
**Auth**: Public (token-based)  
**Router**: `public_router`

### Overview

Connect to 10,000+ financial institutions to aggregate accounts, transactions, and balances. Supports checking, savings, credit cards, loans, and investment accounts.

### Endpoints

#### 1. Create Link Token
```
GET /banking/link
```

Generates a Plaid Link token for frontend integration.

**Response:**
```json
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

#### 2. Exchange Public Token
```
POST /banking/exchange
```

Exchanges Plaid public token for access token after Link flow.

**Request:**
```json
{
  "public_token": "public-sandbox-xyz789..."
}
```

**Response:**
```json
{
  "access_token": "access-sandbox-def456...",
  "item_id": "item123"
}
```

#### 3. Get Accounts
```
GET /banking/accounts?access_token={token}
```

Retrieves all linked accounts.

**Response:**
```json
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
    }
  ]
}
```

#### 4. Get Balances
```
GET /banking/balances?access_token={token}
```

Get real-time account balances only (faster than full accounts call).

#### 5. Get Transactions
```
GET /banking/transactions?access_token={token}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

Fetch historical transactions with optional date range.

**Response:**
```json
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

### Configuration

```bash
# Plaid (sandbox for testing, production for real data)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox  # or development, production
```

### Use Cases

- **Personal Finance Apps**: Aggregate all user accounts (Mint, YNAB)
- **Lending Platforms**: Verify income and assets
- **Wealth Management**: Track net worth across institutions
- **Budgeting Tools**: Analyze spending patterns

### Rate Limits

- **Sandbox**: Unlimited
- **Development**: 100 calls/day
- **Production**: Based on plan (typically 500-5000/month included)

### Troubleshooting

**Error: "Provider not configured"**
- Set `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` in `.env`
- Restart server after configuration

**Error: "Invalid access token"**
- Access tokens expire after 90 days (Plaid sandbox)
- Create new link token and re-link account

---

## Market Data

**Provider**: Alpha Vantage (default), Yahoo Finance, Polygon  
**Prefix**: `/market`  
**Auth**: Public  
**Router**: `public_router`

### Overview

Real-time and historical stock market data for equities, ETFs, and indices.

### Endpoints

#### 1. Get Quote
```
GET /market/quote/{symbol}
```

Real-time or delayed quote for a stock.

**Response:**
```json
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

#### 2. Batch Quotes
```
GET /market/quotes?symbols=AAPL,GOOGL,MSFT
```

Get multiple quotes in one call (more efficient).

#### 3. Historical Data
```
GET /market/history/{symbol}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

OHLCV (Open/High/Low/Close/Volume) historical data.

**Response:**
```json
{
  "symbol": "AAPL",
  "data": [
    {
      "date": "2024-01-31",
      "open": 180.20,
      "high": 183.00,
      "low": 179.50,
      "close": 182.50,
      "volume": 52341234
    }
  ]
}
```

#### 4. Search Symbols
```
GET /market/search?q=apple
```

Search for stocks by name or symbol.

### Configuration

```bash
# Alpha Vantage (free tier available)
ALPHA_VANTAGE_API_KEY=your_api_key

# Yahoo Finance (no API key needed, rate limited)
# Auto-fallback if Alpha Vantage not configured

# Polygon (premium, real-time data)
POLYGON_API_KEY=your_api_key
```

### Use Cases

- **Investment Tracking**: Monitor portfolio performance
- **Trading Platforms**: Real-time quotes for order execution
- **Robo-Advisors**: Portfolio rebalancing
- **Financial Education**: Teach market concepts with real data

### Rate Limits

- **Alpha Vantage Free**: 5 calls/min, 100/day
- **Yahoo Finance**: ~2000 calls/hour (unofficial)
- **Polygon**: Based on plan (5/min free, unlimited paid)

### Caching

- Quotes cached for 1 minute
- Historical data cached for 24 hours

---

## Crypto Data

**Provider**: CoinGecko (default), CCXT  
**Prefix**: `/crypto`  
**Auth**: Public  
**Router**: `public_router`

### Overview

Real-time cryptocurrency prices, market cap, volume, and historical data for 10,000+ coins.

### Endpoints

#### 1. Get Crypto Quote
```
GET /crypto/quote/{symbol}
```

**Response:**
```json
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

#### 2. Batch Crypto Quotes
```
GET /crypto/quotes?symbols=BTC,ETH,SOL
```

#### 3. Crypto Historical Data
```
GET /crypto/history/{symbol}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

### Configuration

```bash
# CoinGecko (free tier available)
COINGECKO_API_KEY=your_api_key  # Optional for free tier

# CCXT (exchange-specific data)
CCXT_EXCHANGE=binance  # or coinbase, kraken, etc.
```

### Use Cases

- **Crypto Portfolios**: Track holdings value
- **Trading Bots**: Get real-time prices for strategy execution
- **Tax Reporting**: Calculate crypto gains/losses
- **DeFi Dashboards**: Monitor token prices

### Rate Limits

- **CoinGecko Free**: 50 calls/min
- **CoinGecko Pro**: 500 calls/min
- **CCXT**: Exchange-specific (usually 1200/min)

---

## Brokerage Integration

**Provider**: Alpaca (default), Interactive Brokers, SnapTrade (planned)  
**Prefix**: `/brokerage`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Connect to brokerage accounts for paper trading (testing) and live trading (production).

### Endpoints

#### 1. Get Account Info
```
GET /brokerage/account
```

**Response:**
```json
{
  "account_id": "abc123",
  "buying_power": 100000.00,
  "cash": 100000.00,
  "portfolio_value": 100000.00,
  "status": "ACTIVE"
}
```

#### 2. Get Positions
```
GET /brokerage/positions
```

Current holdings in the account.

#### 3. Place Order
```
POST /brokerage/orders
```

**Request:**
```json
{
  "symbol": "AAPL",
  "qty": 10,
  "side": "buy",
  "type": "market",
  "time_in_force": "day"
}
```

#### 4. Get Orders
```
GET /brokerage/orders
```

List all orders (open, filled, cancelled).

### Configuration

```bash
# Alpaca (paper trading for testing)
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
# ALPACA_BASE_URL=https://api.alpaca.markets  # Live trading
```

### Use Cases

- **Robo-Advisors**: Automated portfolio management
- **Trading Apps**: User-directed trading interfaces
- **Algo Trading**: Algorithmic strategy execution
- **Backtesting**: Test strategies with paper trading

---

## Credit Scores

**Provider**: Experian, Equifax (planned), TransUnion (planned)  
**Prefix**: `/credit`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Fetch credit scores and reports from major bureaus.

### Endpoints

#### 1. Get Credit Score
```
GET /credit/score
```

**Response:**
```json
{
  "score": 750,
  "bureau": "Experian",
  "date": "2024-01-15",
  "factors": [
    "Payment history: Excellent",
    "Credit utilization: 15%"
  ]
}
```

#### 2. Get Credit Report
```
GET /credit/report
```

Full credit report with accounts, inquiries, public records.

### Configuration

```bash
EXPERIAN_API_KEY=your_api_key
EXPERIAN_CLIENT_SECRET=your_client_secret
```

### Use Cases

- **Credit Monitoring Apps**: Track score changes
- **Lending Platforms**: Assess creditworthiness
- **Financial Planning**: Improve credit score strategies

---

## Tax Data

**Provider**: IRS, TaxBit (crypto), custom parsers  
**Prefix**: `/tax`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Tax form management, crypto gains calculation, and document parsing.

### Endpoints

#### 1. Upload Tax Document
```
POST /tax/documents
```

Upload W-2, 1099, etc. with OCR parsing.

#### 2. Get Tax Forms
```
GET /tax/documents
```

List all uploaded tax forms.

#### 3. Calculate Crypto Gains
```
POST /tax/crypto-gains
```

**Request:**
```json
{
  "transactions": [
    {"date": "2023-01-15", "type": "buy", "amount": 0.5, "price": 40000},
    {"date": "2024-01-15", "type": "sell", "amount": 0.5, "price": 43000}
  ]
}
```

**Response:**
```json
{
  "short_term_gain": 1500.00,
  "long_term_gain": 0.00,
  "total_gain": 1500.00
}
```

### Use Cases

- **Tax Preparation**: Organize documents
- **Crypto Tax**: Calculate gains for IRS reporting
- **Financial Planning**: Estimate tax liability

---

## Analytics

**Provider**: Internal (LLM-enhanced)  
**Prefix**: `/analytics`  
**Auth**: Public (utility endpoints)  
**Router**: `public_router`

### Overview

Financial insights, cash flow analysis, savings rate, spending patterns.

### Endpoints

#### 1. Cash Flow Analysis
```
GET /analytics/cash-flow/{user_id}
```

#### 2. Savings Rate
```
GET /analytics/savings-rate/{user_id}
```

#### 3. Spending Insights
```
GET /analytics/spending-insights/{user_id}
```

#### 4. AI Financial Advice
```
GET /analytics/advice/{user_id}
```

Uses ai-infra LLM to generate personalized advice.

### Configuration

```bash
# AI-powered insights require ai-infra configuration
GOOGLE_GENAI_API_KEY=your_api_key  # For Gemini
# Or configure other LLM providers via ai-infra
```

### Use Cases

- **Personal Finance Apps**: Automated insights dashboard
- **Wealth Management**: Client reports
- **Budgeting Tools**: Spending analysis
- **Financial Coaching**: Personalized recommendations

---

## Categorization

**Provider**: Internal (rule-based + LLM)  
**Prefix**: `/categorize`  
**Auth**: Public  
**Router**: `public_router`

### Overview

Categorize transactions using merchant names, amounts, and ML models.

### Endpoints

#### 1. Categorize Single Transaction
```
POST /categorize
```

**Request:**
```json
{
  "description": "STARBUCKS COFFEE",
  "amount": 5.75
}
```

**Response:**
```json
{
  "category": "Food and Drink > Restaurants > Coffee Shop",
  "category_id": "13005031",
  "confidence": 0.95,
  "method": "rule_based"
}
```

#### 2. Batch Categorization
```
POST /categorize/batch
```

**Request:**
```json
{
  "transactions": [
    {"description": "UBER RIDE", "amount": 15.50},
    {"description": "WHOLE FOODS", "amount": 125.30}
  ]
}
```

### Use Cases

- **Budgeting**: Automatic category assignment
- **Expense Tracking**: Organize spending
- **Tax Prep**: Identify deductible expenses
- **Analytics**: Spending breakdown by category

---

## Recurring Detection

**Provider**: Internal (pattern matching)  
**Prefix**: `/recurring`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Detect subscriptions, bills, and recurring payments automatically.

### Endpoints

#### 1. Detect Patterns
```
POST /recurring/detect
```

**Request:**
```json
{
  "user_id": "user_123",
  "transactions": [
    {"date": "2024-01-15", "amount": 15.99, "description": "NETFLIX"},
    {"date": "2024-02-15", "amount": 15.99, "description": "NETFLIX"}
  ]
}
```

**Response:**
```json
{
  "patterns": [
    {
      "pattern_id": "rec_123",
      "merchant": "NETFLIX",
      "frequency": "monthly",
      "amount": 15.99,
      "confidence": 0.98,
      "next_expected_date": "2024-03-15"
    }
  ]
}
```

### Use Cases

- **Subscription Management**: Track all recurring charges
- **Budget Planning**: Predict future expenses
- **Expense Alerts**: Notify on unexpected charges

---

## Insights Feed

**Provider**: Internal (aggregates all insights)  
**Prefix**: `/insights`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Unified feed of financial insights from all capabilities.

### Endpoints

#### 1. Get Insights Feed
```
GET /insights?include_read=false
```

**Response:**
```json
{
  "insights": [
    {
      "id": "insight_123",
      "type": "spending_spike",
      "title": "Dining spending up 25%",
      "description": "You spent $450 on dining this month, 25% more than average",
      "priority": "medium",
      "actionable": true,
      "actions": ["Review dining budget", "Meal prep more often"],
      "read": false,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### 2. Mark Insight as Read
```
POST /insights/mark-read/{insight_id}
```

### Use Cases

- **Dashboard**: Central insights view
- **Notifications**: Alert users to important changes
- **Financial Health Score**: Aggregate insights for scoring

---

## Budgets

**Provider**: Internal  
**Prefix**: `/budgets`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Create, track, and manage budgets with category breakdowns and alerts.

### Endpoints

#### 1. Create Budget
```
POST /budgets
```

#### 2. Get Budget
```
GET /budgets/{budget_id}
```

#### 3. Get Budget Status
```
GET /budgets/{budget_id}/status
```

#### 4. Update Budget
```
PATCH /budgets/{budget_id}
```

#### 5. Delete Budget
```
DELETE /budgets/{budget_id}
```

#### 6. List User Budgets
```
GET /budgets/user/{user_id}
```

### Use Cases

- **Budgeting Apps**: Core feature
- **Expense Tracking**: Monitor spending against limits
- **Financial Coaching**: Set and track budget goals

---

## Goals

**Provider**: Internal  
**Prefix**: `/goals`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Financial goal setting, tracking, and milestone management.

### Endpoints

#### 1. Create Goal
```
POST /goals
```

#### 2. Get Goal
```
GET /goals/{goal_id}
```

#### 3. Update Goal Progress
```
PATCH /goals/{goal_id}
```

#### 4. Delete Goal
```
DELETE /goals/{goal_id}
```

#### 5. List User Goals
```
GET /goals/user/{user_id}
```

### Use Cases

- **Savings Goals**: Emergency fund, vacation, down payment
- **Investment Goals**: Retirement, education fund
- **Debt Payoff**: Track progress toward debt-free

---

## Net Worth Tracking

**Provider**: Internal (aggregates accounts)  
**Prefix**: `/net-worth`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Aggregate assets and liabilities for net worth calculation and tracking.

### Endpoints

#### 1. Get Net Worth Snapshot
```
GET /net-worth/{user_id}
```

#### 2. Get Net Worth History
```
GET /net-worth/{user_id}/history?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

#### 3. Update Net Worth Snapshot
```
POST /net-worth/{user_id}/snapshot
```

### Use Cases

- **Wealth Tracking**: Monitor progress over time
- **Financial Planning**: Assess current financial health
- **Goal Setting**: Set net worth targets

---

## Documents

**Provider**: Internal (OCR + AI)  
**Prefix**: `/documents`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

Upload, store, and analyze financial documents with OCR and AI.

### Endpoints

#### 1. Upload Document
```
POST /documents/upload
```

#### 2. List Documents
```
GET /documents
```

#### 3. Get Document
```
GET /documents/{document_id}
```

#### 4. Analyze Document (AI)
```
POST /documents/{document_id}/analyze
```

### Use Cases

- **Tax Prep**: Store W-2, 1099 forms
- **Receipts**: Organize expense receipts
- **Contracts**: Store loan agreements, leases

---

## Security

**Provider**: Internal  
**Prefix**: `/security`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

PII detection, encryption helpers, audit logging.

### Endpoints

#### 1. Detect PII
```
POST /security/detect-pii
```

#### 2. Get Audit Logs
```
GET /security/audit-logs
```

### Use Cases

- **Compliance**: GDPR, CCPA compliance
- **Security**: Detect sensitive data leaks
- **Audit**: Track data access

---

## Normalization

**Provider**: Internal (symbol resolution, currency conversion)  
**Prefix**: `/normalize`  
**Auth**: Public  
**Router**: `public_router`

### Overview

Resolve stock symbols (ticker <-> CUSIP <-> ISIN) and convert currencies.

### Endpoints

#### 1. Resolve Symbol
```
GET /normalize/symbol/{identifier}
```

#### 2. Convert Currency
```
GET /normalize/convert?from=USD&to=EUR&amount=100
```

### Use Cases

- **Multi-Asset Portfolios**: Normalize symbol formats
- **International**: Convert currencies for consolidated views

---

## Cashflows

**Provider**: Internal (numpy-financial)  
**Prefix**: `/cashflows`  
**Auth**: Public  
**Router**: `public_router`

### Overview

Financial calculations: NPV, IRR, loan payments, future value, present value.

### Endpoints

#### 1. NPV (Net Present Value)
```
POST /cashflows/npv
```

#### 2. IRR (Internal Rate of Return)
```
POST /cashflows/irr
```

#### 3. PMT (Loan Payment)
```
POST /cashflows/pmt
```

#### 4. FV (Future Value)
```
POST /cashflows/fv
```

#### 5. PV (Present Value)
```
POST /cashflows/pv
```

### Use Cases

- **Loan Calculators**: Mortgage, auto loan calculators
- **Investment Analysis**: Evaluate investment returns
- **Financial Planning**: Retirement savings projections

---

## Conversation

**Provider**: ai-infra (LLM-powered)  
**Prefix**: `/chat`  
**Auth**: Protected (`user_router`)  
**Router**: `user_router`

### Overview

AI-powered financial planning conversation with safety filters.

### Endpoints

#### 1. Ask Question
```
POST /chat/ask
```

#### 2. Get Conversation History
```
GET /chat/history
```

#### 3. Clear History
```
DELETE /chat/history
```

### Configuration

```bash
# Requires ai-infra LLM configuration
GOOGLE_GENAI_API_KEY=your_api_key  # For Gemini
# Or configure other LLM providers
```

### Use Cases

- **Financial Advice**: Personalized recommendations
- **Education**: Learn financial concepts
- **Planning**: Interactive financial planning

### Safety

- Filters sensitive questions (SSN, passwords, account numbers)
- Includes "not a substitute for certified advisor" disclaimer
- All conversations logged for compliance

---

## Next Steps

- **Try examples**: See [USAGE.md](../USAGE.md) for code examples
- **Configure providers**: Read [PROVIDERS.md](PROVIDERS.md) for setup
- **Setup database**: Check [DATABASE.md](DATABASE.md) for schema

---

**Questions?** Open an issue or check the main [README.md](../README.md).
