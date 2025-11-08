# Analytics Module

> **Comprehensive financial analytics with cash flow, savings rate, spending insights, portfolio metrics, and growth projections**

## Overview

The analytics module provides production-ready financial analysis capabilities for fintech applications. It calculates key financial metrics, identifies spending patterns, analyzes portfolio performance, and projects future net worth scenarios.

### Key Features

- **Cash Flow Analysis**: Track income vs expenses with category breakdowns and period comparisons
- **Savings Rate**: Multiple calculation methods (gross, net, discretionary) with historical trends
- **Spending Insights**: Pattern detection, merchant analysis, anomaly detection, and trend identification
- **AI-Powered Advice**: LLM-generated personalized spending recommendations (via ai-infra)
- **Portfolio Analytics**: Performance metrics, asset allocation, and benchmark comparisons
- **Growth Projections**: Monte Carlo-style net worth forecasting with conservative/moderate/aggressive scenarios
- **REST API**: 7 endpoints for comprehensive financial analytics
- **Caching**: Intelligent caching with svc-infra (24h TTL for insights, 1h for real-time metrics)

### Use Cases

- **Personal Finance Apps** (Mint, YNAB, Personal Capital): Spending analysis, savings tracking, net worth projections
- **Investment Platforms** (Robinhood, Webull): Portfolio performance, benchmark comparisons, allocation analysis
- **Banking Apps** (Chime, Revolut): Cash flow insights, savings rate tracking, spending patterns
- **Wealth Management** (Betterment, Wealthfront): Long-term projections, portfolio optimization, financial planning
- **Budgeting Tools** (Simplifi, PocketGuard): Spending advice, anomaly detection, trend analysis
- **Business Accounting**: Cash flow management, expense analysis, financial forecasting

---

## Quick Start

### 1. Basic Setup (Programmatic)

```python
from fin_infra.analytics import easy_analytics

# Create analytics engine with sensible defaults
analytics = easy_analytics(
    default_period_days=30,  # 30-day analysis periods
    cache_ttl=3600,  # 1 hour cache for real-time metrics
)

# Calculate cash flow
cash_flow = await analytics.cash_flow(
    user_id="user_123",
    period_days=30,
)

print(f"Income: ${cash_flow.income_total:,.2f}")
print(f"Expenses: ${cash_flow.expense_total:,.2f}")
print(f"Net Cash Flow: ${cash_flow.net_cash_flow:,.2f}")

# Calculate savings rate
savings = await analytics.savings_rate(
    user_id="user_123",
    definition="net",  # net income after tax
    period="monthly",
)

print(f"Savings Rate: {savings.savings_rate:.1%}")
print(f"Trend: {savings.trend}")

# Get spending insights
insights = await analytics.spending_insights(
    user_id="user_123",
    period_days=30,
    include_trends=True,
)

print(f"Top Merchants: {insights.top_merchants[:3]}")
print(f"Total Spending: ${insights.total_spending:,.2f}")
print(f"Anomalies Detected: {len(insights.anomalies)}")

# Get AI-powered spending advice
advice = await analytics.spending_advice(
    user_id="user_123",
    period_days=30,
)

print(f"Key Observations: {advice.key_observations}")
print(f"Savings Opportunities: {advice.savings_opportunities}")
print(f"Estimated Monthly Savings: ${advice.estimated_monthly_savings:,.2f}")
```

### 2. FastAPI Integration

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.analytics import add_analytics, easy_analytics

# Create app (svc-infra)
app = easy_service_app(name="FinanceAPI")

# Add analytics endpoints (one-liner!)
analytics = add_analytics(app, prefix="/analytics")

# Access at:
# - GET  /analytics/cash-flow?user_id=...
# - GET  /analytics/savings-rate?user_id=...&period=monthly
# - GET  /analytics/spending-insights?user_id=...
# - GET  /analytics/spending-advice?user_id=...
# - GET  /analytics/portfolio?user_id=...
# - GET  /analytics/performance?user_id=...&benchmark=SPY
# - POST /analytics/forecast-net-worth (body: user_id, years, assumptions)

# Visit /docs for interactive API documentation
# Visit /analytics/docs for scoped analytics documentation
```

### 3. Custom Configuration

```python
from fin_infra.analytics import easy_analytics
from fin_infra.banking import easy_banking
from fin_infra.brokerage import easy_brokerage

# Setup data providers
banking = easy_banking(provider="plaid")
brokerage = easy_brokerage(provider="alpaca")

# Create analytics with custom providers
analytics = easy_analytics(
    banking_provider=banking,
    brokerage_provider=brokerage,
    categorization_provider=categorization,
    default_period_days=90,  # 90-day default analysis
    cache_ttl=7200,  # 2 hour cache
)

# All analytics calculations now use custom providers
cash_flow = await analytics.cash_flow(user_id="user_123")
```

---

## API Endpoints Reference

### 1. Cash Flow Analysis

**Endpoint**: `GET /analytics/cash-flow`

Analyzes income and expenses over a period with category breakdowns.

**Query Parameters**:
- `user_id` (required): User identifier
- `start_date` (optional): ISO 8601 date (default: 30 days ago)
- `end_date` (optional): ISO 8601 date (default: today)
- `period_days` (optional): Alternative to start/end dates

**Response**: `CashFlowAnalysis`
```json
{
  "income_total": 5700.0,
  "expense_total": 1650.0,
  "net_cash_flow": 4050.0,
  "income_by_source": {
    "Paycheck": 5000.0,
    "Side Hustle": 500.0,
    "Investment": 200.0
  },
  "expenses_by_category": {
    "Groceries": 600.0,
    "Restaurants": 400.0,
    "Entertainment": 150.0,
    "Transportation": 500.0
  },
  "period_start": "2025-10-08",
  "period_end": "2025-11-07"
}
```

**Example**:
```bash
curl "http://localhost:8000/analytics/cash-flow?user_id=user_123&period_days=30"
```

---

### 2. Savings Rate

**Endpoint**: `GET /analytics/savings-rate`

Calculates savings rate using multiple definitions (gross, net, discretionary).

**Query Parameters**:
- `user_id` (required): User identifier
- `definition` (optional): "gross", "net", or "discretionary" (default: "net")
- `period` (optional): "weekly", "monthly", "quarterly", "yearly" (default: "monthly")

**Response**: `SavingsRateData`
```json
{
  "savings_rate": 0.71,
  "savings_amount": 4050.0,
  "period": "monthly",
  "definition": "net",
  "trend": "increasing",
  "historical_rates": [0.65, 0.68, 0.71]
}
```

**Calculation Methods**:
- **GROSS**: (Income - Expenses) / Gross Income
- **NET**: (Income - Expenses) / Net Income (after tax)
- **DISCRETIONARY**: (Income - Expenses) / Discretionary Income (after necessities)

**Example**:
```bash
curl "http://localhost:8000/analytics/savings-rate?user_id=user_123&definition=net&period=monthly"
```

---

### 3. Spending Insights

**Endpoint**: `GET /analytics/spending-insights`

Analyzes spending patterns, identifies anomalies, and tracks trends by category.

**Query Parameters**:
- `user_id` (required): User identifier
- `period_days` (optional): Analysis period in days (default: 30)
- `include_trends` (optional): Include trend analysis (default: true)

**Response**: `SpendingInsight`
```json
{
  "top_merchants": [
    ["Whole Foods", 325.7],
    ["Uber", 180.5],
    ["Amazon", 150.2]
  ],
  "category_breakdown": {
    "Groceries": 325.7,
    "Transportation": 180.5,
    "Shopping": 302.3,
    "Restaurants": 80.5,
    "Entertainment": 25.98
  },
  "spending_trends": {
    "Groceries": "increasing",
    "Transportation": "stable",
    "Shopping": "increasing",
    "Restaurants": "decreasing",
    "Entertainment": "stable"
  },
  "anomalies": [
    {
      "category": "Shopping",
      "current_amount": 302.3,
      "average_amount": 241.84,
      "deviation_percent": 25.0,
      "description": "Shopping spending is 25.0% higher than usual"
    }
  ],
  "period_days": 30,
  "total_spending": 915.18
}
```

**Example**:
```bash
curl "http://localhost:8000/analytics/spending-insights?user_id=user_123&period_days=60&include_trends=true"
```

---

### 4. Spending Advice (AI-Powered)

**Endpoint**: `GET /analytics/spending-advice`

Generates personalized spending recommendations using LLM (via ai-infra).

**Query Parameters**:
- `user_id` (required): User identifier
- `period_days` (optional): Analysis period (default: 30)

**Response**: `PersonalizedSpendingAdvice`
```json
{
  "summary": "Your spending is well-controlled with strong savings. Focus on optimizing high-frequency small purchases.",
  "key_observations": [
    "Your highest spending category is Groceries at $325.70",
    "You have 5 recurring subscriptions totaling $45/month",
    "Shopping spending increased 25% this month ($302.30)"
  ],
  "savings_opportunities": [
    "Consider meal planning to reduce grocery expenses by ~$50/month",
    "Review subscriptions: 2 appear unused in the last 60 days",
    "Switch to annual payment for Netflix to save $20/year"
  ],
  "positive_habits": [
    "Consistent spending tracking",
    "Low restaurant spending ($80.50)",
    "No overdraft fees in the last 6 months"
  ],
  "alerts": [],
  "estimated_monthly_savings": 32.57
}
```

**Example**:
```bash
curl "http://localhost:8000/analytics/spending-advice?user_id=user_123"
```

**Note**: Uses ai-infra CoreLLM with cost tracking. Falls back to rule-based insights if LLM fails.

---

### 5. Portfolio Metrics

**Endpoint**: `GET /analytics/portfolio`

Calculates portfolio performance metrics and asset allocation.

**Query Parameters**:
- `user_id` (required): User identifier
- `accounts` (optional): Comma-separated account IDs to include (default: all)

**Response**: `PortfolioMetrics`
```json
{
  "total_value": 76500.0,
  "total_return": 8200.0,
  "total_return_percent": 12.01,
  "ytd_return": 5800.0,
  "ytd_return_percent": 8.21,
  "mtd_return": 1345.0,
  "mtd_return_percent": 1.79,
  "day_change": 425.0,
  "day_change_percent": 0.56,
  "allocation_by_asset_class": [
    {
      "asset_class": "Stocks",
      "value": 33305.0,
      "percentage": 43.34
    },
    {
      "asset_class": "Bonds",
      "value": 15300.0,
      "percentage": 20.0
    },
    {
      "asset_class": "Crypto",
      "value": 22895.0,
      "percentage": 29.93
    },
    {
      "asset_class": "Cash",
      "value": 5000.0,
      "percentage": 6.73
    }
  ]
}
```

**Example**:
```bash
curl "http://localhost:8000/analytics/portfolio?user_id=user_123"
curl "http://localhost:8000/analytics/portfolio?user_id=user_123&accounts=acc1,acc2"
```

---

### 6. Benchmark Comparison

**Endpoint**: `GET /analytics/performance`

Compares portfolio performance against market benchmarks (SPY, QQQ, etc.).

**Query Parameters**:
- `user_id` (required): User identifier
- `benchmark` (optional): Benchmark symbol (default: "SPY")
- `period` (optional): "1mo", "3mo", "6mo", "1y", "ytd" (default: "1y")
- `accounts` (optional): Comma-separated account IDs

**Response**: `BenchmarkComparison`
```json
{
  "portfolio_return": 12.01,
  "benchmark_return": 10.5,
  "alpha": 1.51,
  "beta": 1.15,
  "sharpe_ratio": 1.8,
  "max_drawdown": -8.2,
  "benchmark_name": "SPY",
  "period": "1y"
}
```

**Example**:
```bash
curl "http://localhost:8000/analytics/performance?user_id=user_123&benchmark=SPY&period=1y"
curl "http://localhost:8000/analytics/performance?user_id=user_123&benchmark=QQQ&period=6mo"
```

---

### 7. Net Worth Forecast

**Endpoint**: `POST /analytics/forecast-net-worth`

Projects future net worth with conservative/moderate/aggressive scenarios.

**Request Body**: `NetWorthForecastRequest`
```json
{
  "user_id": "user_123",
  "years": 30,
  "initial_net_worth": 50000.0,
  "annual_contribution": 12000.0,
  "conservative_return": 0.05,
  "moderate_return": 0.08,
  "aggressive_return": 0.11
}
```

**Response**: `GrowthProjection`
```json
{
  "current_net_worth": 50000.0,
  "years": 30,
  "monthly_contribution": 1000.0,
  "scenarios": [
    {
      "name": "Conservative",
      "expected_return": 0.05,
      "projected_values": [53000.0, 66650.0, ...],
      "final_value": 250000.0
    },
    {
      "name": "Moderate",
      "expected_return": 0.08,
      "projected_values": [54000.0, 70320.0, ...],
      "final_value": 450000.0
    },
    {
      "name": "Aggressive",
      "expected_return": 0.11,
      "projected_values": [55500.0, 75605.0, ...],
      "final_value": 750000.0
    }
  ],
  "assumptions": {
    "conservative_return": 0.05,
    "moderate_return": 0.08,
    "aggressive_return": 0.11,
    "contribution_growth": 0.02,
    "inflation": 0.025
  }
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/analytics/forecast-net-worth" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "years": 30,
    "initial_net_worth": 50000.0,
    "annual_contribution": 12000.0
  }'
```

---

## Configuration Options

### Analytics Engine Configuration

```python
from fin_infra.analytics import easy_analytics

analytics = easy_analytics(
    # Default analysis period
    default_period_days=30,  # 30, 60, 90 days typical
    
    # Cache TTL (seconds)
    cache_ttl=3600,  # 1 hour for real-time metrics
    # cache_ttl=86400,  # 24 hours for historical insights
    
    # Provider overrides
    banking_provider=custom_banking,
    brokerage_provider=custom_brokerage,
    categorization_provider=custom_categorization,
    
    # Savings rate defaults
    default_savings_definition="net",  # gross, net, discretionary
    historical_months=6,  # Trend analysis lookback
    
    # Portfolio defaults
    default_benchmark="SPY",  # S&P 500
    risk_free_rate=0.03,  # For Sharpe ratio
)
```

### FastAPI Integration Configuration

```python
from fin_infra.analytics import add_analytics

# Basic
analytics = add_analytics(app)

# Custom prefix
analytics = add_analytics(app, prefix="/api/analytics")

# Custom provider
custom_engine = easy_analytics(default_period_days=90)
analytics = add_analytics(app, provider=custom_engine)

# Disable OpenAPI schema (private endpoints)
analytics = add_analytics(app, include_in_schema=False)
```

### Environment Variables

The analytics module respects these environment variables:

```bash
# AI/LLM Configuration (for spending advice)
OPENAI_API_KEY=sk-...           # OpenAI for LLM advice
GOOGLE_GENAI_API_KEY=...        # Or Google Gemini
ANTHROPIC_API_KEY=...           # Or Anthropic Claude

# Provider Configuration (if using defaults)
PLAID_CLIENT_ID=...
PLAID_SECRET=...
ALPHA_VANTAGE_API_KEY=...
```

---

## Integration Patterns

### 1. With svc-infra (Backend Infrastructure)

```python
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.cache import init_cache
from svc_infra.obs import add_observability
from fin_infra.analytics import add_analytics

# Backend from svc-infra
app = easy_service_app(name="FinanceAPI")
init_cache(url="redis://localhost")
add_observability(app)

# Analytics from fin-infra
analytics = add_analytics(app)

# Complete system: backend + analytics
```

### 2. With ai-infra (LLM Infrastructure)

```python
from ai_infra.llm import CoreLLM
from ai_infra.conversation import FinancialPlanningConversation
from fin_infra.analytics import easy_analytics

# AI from ai-infra
llm = CoreLLM(provider="openai", model="gpt-4")

# Analytics from fin-infra
analytics = easy_analytics()

# Get spending advice (uses ai-infra LLM under the hood)
advice = await analytics.spending_advice(user_id="user_123")

# Multi-turn conversation with financial context
conversation = FinancialPlanningConversation(llm=llm)
response = await conversation.ask(
    user_id="user_123",
    question="How can I save more?",
    spending=await analytics.spending_insights(user_id="user_123"),
    net_worth=await analytics.portfolio(user_id="user_123"),
)
```

### 3. With Other fin-infra Modules

```python
from fin_infra.banking import add_banking
from fin_infra.brokerage import add_brokerage
from fin_infra.categorization import add_categorization
from fin_infra.net_worth import add_net_worth_tracking
from fin_infra.analytics import add_analytics

# Data providers
add_banking(app, provider="plaid")
add_brokerage(app, provider="alpaca")
add_categorization(app)

# Aggregation
add_net_worth_tracking(app)

# Analytics (uses banking, brokerage, categorization)
add_analytics(app)

# All capabilities integrated
```

### 4. Caching Strategy

```python
from svc_infra.cache import cache_read, cache_write, init_cache

# Initialize cache (svc-infra)
init_cache(url="redis://localhost", prefix="fin", version="1")

# Analytics respects cache automatically
analytics = easy_analytics(cache_ttl=3600)

# Real-time metrics: 1 hour cache
cash_flow = await analytics.cash_flow(user_id="user_123")  # 1h TTL

# Historical insights: 24 hour cache
advice = await analytics.spending_advice(user_id="user_123")  # 24h TTL

# Disable cache for specific call
cash_flow = await analytics.cash_flow(user_id="user_123", force_refresh=True)
```

---

## Calculation Methodologies

### Cash Flow Analysis

**Formula**:
```
Net Cash Flow = Total Income - Total Expenses
```

**Process**:
1. Fetch transactions from banking provider for period
2. Categorize transactions (income vs expense)
3. Group by category for breakdowns
4. Calculate totals and net flow

**Edge Cases**:
- Transfers between accounts: Excluded (not income/expense)
- Pending transactions: Excluded by default
- Refunds: Treated as negative expenses
- Cash deposits/withdrawals: Included if categorized

### Savings Rate Calculation

**GROSS Method**:
```
Savings Rate = (Income - Expenses) / Gross Income
```

**NET Method** (Recommended):
```
Savings Rate = (Income - Expenses) / Net Income (after tax)
```

**DISCRETIONARY Method**:
```
Savings Rate = (Income - Expenses) / Discretionary Income (after necessities)
```

**Trend Detection**:
- Calculate savings rate for last N months
- Use linear regression to determine trend
- Classify as: increasing, stable, decreasing

### Spending Insights

**Anomaly Detection**:
```
For each category:
  average = mean(last 6 months)
  current = current month
  deviation = (current - average) / average
  
  if deviation > 0.25:  # 25% higher
    flag as anomaly
```

**Trend Analysis**:
```
For each category:
  slope = linear_regression(last 6 months)
  
  if slope > 0.1:  trend = "increasing"
  elif slope < -0.1:  trend = "decreasing"
  else:  trend = "stable"
```

### Portfolio Performance

**Returns**:
```
Total Return % = (Current Value - Cost Basis) / Cost Basis
YTD Return % = (Current Value - Jan 1 Value) / Jan 1 Value
MTD Return % = (Current Value - Month Start Value) / Month Start Value
```

**Alpha & Beta**:
```
Beta = Covariance(Portfolio, Benchmark) / Variance(Benchmark)
Alpha = Portfolio Return - (Risk-Free Rate + Beta * Benchmark Return)
```

**Sharpe Ratio**:
```
Sharpe = (Portfolio Return - Risk-Free Rate) / Portfolio StdDev
```

### Growth Projections

**Compound Growth with Contributions**:
```
FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]

Where:
  FV = Future Value
  PV = Present Value (current net worth)
  r = Annual return rate
  n = Number of years
  PMT = Annual contribution
```

**Scenarios**:
- **Conservative**: 5% annual return + 2% contribution growth
- **Moderate**: 8% annual return + 2% contribution growth
- **Aggressive**: 11% annual return + 2% contribution growth

**Assumptions**:
- Inflation: 2.5% annually
- Contribution growth: 2% annually (salary increases)
- Returns: Pre-inflation (nominal returns)

---

## Generic Design Principles

### Multi-Application Support

The analytics module is designed to serve **any fintech application**:

1. **Personal Finance** (Mint, YNAB, Personal Capital)
   - Focus: Spending analysis, savings tracking, budget insights
   - Use: `spending_insights()`, `savings_rate()`, `spending_advice()`

2. **Investment Platforms** (Robinhood, Webull, E*TRADE)
   - Focus: Portfolio performance, benchmark comparisons
   - Use: `portfolio()`, `performance()`, `forecast_net_worth()`

3. **Banking Apps** (Chime, Revolut, N26)
   - Focus: Cash flow tracking, savings goals
   - Use: `cash_flow()`, `savings_rate()`

4. **Wealth Management** (Betterment, Wealthfront)
   - Focus: Long-term projections, financial planning
   - Use: `forecast_net_worth()`, `performance()`, `spending_advice()`

### Provider Abstraction

Analytics doesn't know about specific providers:

```python
# Analytics takes generic providers
analytics = easy_analytics(
    banking_provider=any_banking,      # Plaid, Teller, MX, etc.
    brokerage_provider=any_brokerage,  # Alpaca, IB, SnapTrade, etc.
)

# Each application chooses its providers
# Analytics works the same regardless
```

### Calculation Consistency

All calculations use **keyword-only arguments** for cache key stability:

```python
# ✅ CORRECT: Keyword-only (cache-friendly)
await analytics.cash_flow(
    user_id="user_123",
    period_days=30,
)

# ❌ WRONG: Positional args (breaks caching)
await analytics.cash_flow("user_123", 30)
```

### Data Privacy

Analytics never stores user data:

- Calculations are ephemeral (in-memory)
- Caching is opt-in (via svc-infra)
- No PII sent to LLMs without consent
- All data comes from providers (banking, brokerage)

---

## Performance & Caching

### Cache Strategy

| Metric | TTL | Reasoning |
|--------|-----|-----------|
| Cash flow | 1 hour | Real-time tracking |
| Savings rate | 1 hour | Daily changes |
| Spending insights | 24 hours | Stable patterns |
| Spending advice (LLM) | 24 hours | Expensive, slow-changing |
| Portfolio metrics | 1 hour | Market hours |
| Benchmark comparison | 1 hour | Market hours |
| Net worth forecast | 7 days | Assumptions rarely change |

### Cost Optimization

**LLM Usage** (Spending Advice):
- Target: <$0.10/user/month
- Strategy: 24h cache + fallback to rule-based
- Model: Gemini 2.0 Flash (cheapest with quality)
- Prompt tokens: ~500 (context) + 200 (instructions)
- Completion tokens: ~300 (structured output)
- Cost per call: ~$0.001

**API Rate Limits**:
- Banking providers: Cache 1h (60 req/user/day max)
- Market data: Cache 1h (60 req/symbol/day max)
- LLM: Cache 24h (<30 req/user/month)

### Scalability

Analytics is **stateless** and **horizontally scalable**:

- No database dependencies (reads from providers)
- Redis caching for multi-instance consistency
- Async/await for concurrent provider calls
- Each calculation ~200ms (uncached)

---

## Testing

### Unit Tests

```bash
# Run all analytics unit tests
pytest tests/unit/analytics/ -v

# Specific modules
pytest tests/unit/analytics/test_cash_flow.py -v
pytest tests/unit/analytics/test_spending.py -v
pytest tests/unit/analytics/test_portfolio.py -v
pytest tests/unit/analytics/test_projections.py -v

# Coverage report
pytest tests/unit/analytics/ --cov=src/fin_infra/analytics --cov-report=term-missing
```

### Integration Tests

```bash
# Test FastAPI endpoints with TestClient
pytest tests/integration/test_analytics_api.py -v

# Test all 7 endpoints
pytest tests/integration/test_analytics_api.py::test_cash_flow_endpoint -v
pytest tests/integration/test_analytics_api.py::test_savings_rate_endpoint -v
pytest tests/integration/test_analytics_api.py::test_spending_insights_endpoint -v
pytest tests/integration/test_analytics_api.py::test_spending_advice_endpoint -v
pytest tests/integration/test_analytics_api.py::test_portfolio_metrics_endpoint -v
pytest tests/integration/test_analytics_api.py::test_benchmark_comparison_endpoint -v
pytest tests/integration/test_analytics_api.py::test_forecast_net_worth_endpoint -v
```

### Acceptance Tests

```bash
# Test with real providers (requires API keys)
pytest tests/acceptance/test_analytics.py -m acceptance -v
```

---

## Troubleshooting

### Issue: Empty Results

**Symptom**: Analytics returns empty data or zeros

**Causes**:
1. No transactions in period → Shorten period or check provider
2. Provider authentication failed → Verify API keys
3. User has no accounts → Check banking/brokerage setup

**Fix**:
```python
# Debug provider connectivity
banking = easy_banking(provider="plaid")
accounts = await banking.get_accounts(user_id="user_123", token="...")
print(f"Found {len(accounts)} accounts")

transactions = await banking.get_transactions(
    user_id="user_123",
    token="...",
    start_date=datetime.now() - timedelta(days=30),
)
print(f"Found {len(transactions)} transactions")
```

### Issue: LLM Spending Advice Fails

**Symptom**: `spending_advice()` returns rule-based insights instead of LLM

**Causes**:
1. No LLM API key → Set `OPENAI_API_KEY` or `GOOGLE_GENAI_API_KEY`
2. Invalid model name → Check ai-infra CoreLLM supported models
3. Rate limit exceeded → Check LLM provider dashboard

**Fix**:
```python
# Enable LLM logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check ai-infra LLM setup
from ai_infra.llm import CoreLLM
llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")
response = await llm.achat(messages=[{"role": "user", "content": "test"}])
print(response)

# Verify spending advice
advice = await analytics.spending_advice(user_id="user_123")
print(f"Generated by: {'LLM' if 'LLM' in advice.summary else 'rule-based'}")
```

### Issue: Slow Performance

**Symptom**: Analytics calls take >5 seconds

**Causes**:
1. No caching enabled → Initialize svc-infra cache
2. Too many provider calls → Increase cache TTL
3. Large transaction volume → Reduce analysis period

**Fix**:
```python
# Enable caching
from svc_infra.cache import init_cache
init_cache(url="redis://localhost")

# Increase TTL
analytics = easy_analytics(cache_ttl=7200)  # 2 hours

# Monitor performance
import time
start = time.time()
result = await analytics.cash_flow(user_id="user_123")
print(f"Took {time.time() - start:.2f}s")
```

### Issue: Inaccurate Projections

**Symptom**: Net worth forecasts seem unrealistic

**Causes**:
1. Wrong initial net worth → Verify current balance
2. Unrealistic return assumptions → Use conservative rates
3. Missing contributions → Include monthly savings

**Fix**:
```python
# Use custom assumptions
projection = await analytics.forecast_net_worth(
    user_id="user_123",
    years=30,
    initial_net_worth=50000.0,  # Current verified balance
    annual_contribution=12000.0,  # Actual monthly savings * 12
    conservative_return=0.04,  # 4% (more conservative)
    moderate_return=0.07,  # 7%
    aggressive_return=0.10,  # 10%
)

# Validate against manual calculation
from fin_infra.cashflows import fv
manual_fv = fv(0.07, 30, -1000, -50000)  # 7%, 30yrs, $1k/mo, $50k PV
print(f"Manual: ${manual_fv:,.2f}")
print(f"Analytics: ${projection.scenarios[1].final_value:,.2f}")
```

---

## Migration Guide

### From Manual Calculations

**Before** (manual):
```python
# Calculate cash flow manually
income = sum(t.amount for t in transactions if t.amount > 0)
expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
net_flow = income - expenses
```

**After** (analytics module):
```python
# Use analytics module
from fin_infra.analytics import easy_analytics

analytics = easy_analytics()
cash_flow = await analytics.cash_flow(user_id="user_123", period_days=30)

# Much more: income_by_source, expenses_by_category, etc.
```

### From Custom Analytics Service

**Before** (custom service):
```python
class AnalyticsService:
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
    
    async def get_savings_rate(self, user_id):
        # 100+ lines of custom logic
        ...
```

**After** (fin-infra):
```python
from fin_infra.analytics import add_analytics

# One-liner
analytics = add_analytics(app)

# Done! All 7 endpoints with caching, validation, OpenAPI docs
```

---

## FAQ

**Q: Do I need ai-infra for analytics?**

A: Only for `spending_advice()` (LLM-powered recommendations). All other analytics work without ai-infra. If no LLM is configured, `spending_advice()` falls back to rule-based insights.

**Q: Can I use analytics without svc-infra?**

A: Yes! Analytics works standalone. Svc-infra provides optional caching, observability, and FastAPI integration.

**Q: How accurate are growth projections?**

A: Projections use standard financial formulas (compound interest with contributions). They're accurate **given the assumptions** but can't predict market returns. Use conservative scenario for planning.

**Q: Does analytics store my data?**

A: No. Analytics is ephemeral (reads from providers, calculates, returns). Caching is opt-in via svc-infra Redis.

**Q: Can I customize calculation logic?**

A: Yes. Subclass `AnalyticsEngine` and override specific methods:

```python
from fin_infra.analytics import AnalyticsEngine

class CustomAnalytics(AnalyticsEngine):
    async def cash_flow(self, user_id, **kwargs):
        # Custom logic
        result = await super().cash_flow(user_id, **kwargs)
        # Post-process
        return result

analytics = CustomAnalytics()
```

**Q: What's the difference between `spending_insights` and `spending_advice`?**

A: `spending_insights` provides **data** (patterns, trends, anomalies). `spending_advice` provides **recommendations** (what to do about it). Insights are rule-based and fast. Advice is LLM-generated and slower.

**Q: How do I test analytics in development?**

A: Use mock providers:

```python
from fin_infra.analytics import easy_analytics
from fin_infra.banking import MockBankingProvider

mock_banking = MockBankingProvider()
analytics = easy_analytics(banking_provider=mock_banking)

# Returns mock data for testing
cash_flow = await analytics.cash_flow(user_id="test_user")
```

---

## Related Documentation

- **[Categorization](./categorization.md)**: Transaction categorization (used by analytics)
- **[Net Worth Tracking](./net-worth.md)**: Net worth aggregation (used for projections)
- **[Banking](./banking.md)**: Banking provider setup (data source)
- **[Brokerage](./brokerage.md)**: Brokerage provider setup (portfolio data)
- **[Caching, Rate Limits, Retries](./caching-rate-limits-retries.md)**: Performance optimization

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Aliikhatami94/fin-infra/issues)
- **Documentation**: [fin-infra docs](https://github.com/Aliikhatami94/fin-infra/tree/main/src/fin_infra/docs)
- **Examples**: See `examples/demo_api/app.py` for complete integration

---

**Last Updated**: November 7, 2025  
**Module Version**: 1.0.0  
**Test Coverage**: 229 tests passing (207 unit, 22 integration)
