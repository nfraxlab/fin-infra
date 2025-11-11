# Cryptocurrency Module

**Status**: ✅ Production-ready (Phase 3)  
**Module**: `fin_infra.crypto`  
**Dependencies**: svc-infra (cache, API), ai-infra (LLM for insights)

---

## Overview

The cryptocurrency module provides market data, portfolio tracking, and AI-powered insights for crypto assets. It supports multiple market data providers (CoinGecko, Yahoo Finance, CCXT) and integrates with ai-infra's CoreLLM for intelligent portfolio analysis.

### Key Features

- **Market Data**: Real-time quotes, historical prices, and market cap information
- **Multi-Provider Support**: CoinGecko (primary), Yahoo Finance, CCXT (exchanges)
- **Portfolio Insights**: AI-powered recommendations using ai-infra CoreLLM
- **Symbol Normalization**: Automatic conversion between different symbol formats
- **Caching**: Intelligent caching with svc-infra (60s TTL for quotes)
- **REST API**: FastAPI integration with dual routers

### Use Cases

- **Crypto Investment Apps** (Coinbase, Crypto.com): Portfolio tracking, market data
- **Personal Finance Apps** (Mint, YNAB): Crypto holdings integration
- **Tax Platforms** (TurboTax, TaxBit): Crypto gains/losses calculation
- **Wealth Management**: Multi-asset portfolios (stocks + crypto + bonds)
- **Trading Bots**: Real-time market data for automated trading

---

## Quick Start

### 1. Basic Market Data

```python
from fin_infra.crypto import easy_crypto

# Create crypto provider (CoinGecko by default)
crypto = easy_crypto()

# Get real-time quote
ticker = crypto.ticker("BTC/USDT")
print(f"Bitcoin Price: ${ticker.last:,.2f}")
print(f"24h Change: {ticker.percentage_change:.2%}")

# Get historical prices
history = crypto.history("ETH/USDT", days=30)
print(f"Ethereum 30-day history: {len(history)} data points")

# Search for coins
results = crypto.search("bitcoin")
print(f"Found: {results[0]['name']} ({results[0]['symbol']})")
```

### 2. Portfolio Insights (AI-Powered)

```python
from fin_infra.crypto.insights import generate_crypto_insights, CryptoHolding
from ai_infra.llm import CoreLLM
from decimal import Decimal

# Define portfolio holdings
holdings = [
    CryptoHolding(
        symbol="BTC",
        quantity=Decimal("0.5"),
        market_value=Decimal("25000"),
        cost_basis=Decimal("20000"),
    ),
    CryptoHolding(
        symbol="ETH",
        quantity=Decimal("10"),
        market_value=Decimal("15000"),
        cost_basis=Decimal("12000"),
    ),
]

# Generate insights (with AI)
llm = CoreLLM()
insights = await generate_crypto_insights(
    user_id="user_123",
    holdings=holdings,
    llm=llm,
    total_portfolio_value=Decimal("100000"),  # Total portfolio (all assets)
)

# Display insights
for insight in insights:
    print(f"[{insight.priority}] {insight.title}")
    print(f"  {insight.description}")
    if insight.action:
        print(f"  ➡️ {insight.action}")
```

### 3. FastAPI Integration

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.crypto import add_crypto_data

# Create app
app = easy_service_app(name="CryptoAPI")

# Add crypto endpoints (one-liner!)
crypto = add_crypto_data(app, prefix="/crypto", cache_ttl=60)

# Access at:
# - GET /crypto/quote/{symbol}         # Real-time quote
# - GET /crypto/history/{symbol}       # Historical prices
# - GET /crypto/search?q=bitcoin       # Search coins
# - POST /crypto/insights              # AI-powered insights
```

---

## Market Data API

### `easy_crypto()`

**Zero-config setup** for crypto market data provider.

```python
from fin_infra.crypto import easy_crypto

crypto = easy_crypto(
    provider="coingecko",  # Optional: defaults to coingecko
    api_key=None,          # Optional: for CoinGecko Pro (auto-detected from env)
)
```

**Auto-Detection**:
1. If `COINGECKO_API_KEY` environment variable is set → CoinGecko Pro
2. Otherwise → CoinGecko Free (no key needed, rate limits apply)

### `ticker(symbol: str) -> Ticker`

Get real-time market quote for a cryptocurrency.

```python
ticker = crypto.ticker("BTC/USDT")

print(f"Symbol: {ticker.symbol}")
print(f"Last Price: ${ticker.last:,.2f}")
print(f"Bid: ${ticker.bid:,.2f}")
print(f"Ask: ${ticker.ask:,.2f}")
print(f"Volume: {ticker.volume:,.0f}")
print(f"24h Change: {ticker.percentage_change:,.2%}")
print(f"Timestamp: {ticker.timestamp}")
```

**Ticker Model**:
```python
Ticker(
    symbol: str,
    last: Decimal,
    bid: Decimal | None,
    ask: Decimal | None,
    volume: Decimal | None,
    percentage_change: Decimal | None,
    timestamp: datetime,
)
```

**Symbol Formats**:
- `"BTC/USDT"` (base/quote, recommended)
- `"BTC"` (defaults to USD quote)
- `"bitcoin"` (CoinGecko ID)

### `history(symbol: str, days: int = 30) -> list[HistoricalPrice]`

Get historical price data.

```python
history = crypto.history("ETH/USDT", days=90)

for point in history[:5]:  # First 5 days
    print(f"{point.date}: ${point.close:,.2f} (vol: {point.volume:,.0f})")
```

**HistoricalPrice Model**:
```python
HistoricalPrice(
    date: datetime,
    open: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal | None,
)
```

### `search(query: str, limit: int = 10) -> list[dict]`

Search for cryptocurrencies by name or symbol.

```python
results = crypto.search("ethereum", limit=5)

for coin in results:
    print(f"{coin['name']} ({coin['symbol']})")
    print(f"  ID: {coin['id']}")
    print(f"  Market Cap Rank: {coin.get('market_cap_rank', 'N/A')}")
```

**Result Fields**:
- `id`: CoinGecko ID (e.g., "bitcoin")
- `name`: Full name (e.g., "Bitcoin")
- `symbol`: Ticker symbol (e.g., "BTC")
- `market_cap_rank`: Ranking by market cap (optional)

---

## Portfolio Insights (AI-Powered)

**Status**: ✅ Production-ready (Phase 3)  
**Module**: `fin_infra.crypto.insights`  
**Dependencies**: ai-infra (CoreLLM)

### Overview

Generate personalized cryptocurrency portfolio insights using ai-infra's CoreLLM. Combines **rule-based patterns** (allocation, performance) with **AI-powered recommendations** (risk assessment, strategic advice).

### API Reference

#### `generate_crypto_insights()`

```python
from fin_infra.crypto.insights import generate_crypto_insights, CryptoHolding
from ai_infra.llm import CoreLLM
from decimal import Decimal

insights = await generate_crypto_insights(
    user_id="user_123",
    holdings=[
        CryptoHolding(
            symbol="BTC",
            quantity=Decimal("1.5"),
            market_value=Decimal("75000"),
            cost_basis=Decimal("60000"),
        ),
        CryptoHolding(
            symbol="ETH",
            quantity=Decimal("20"),
            market_value=Decimal("30000"),
            cost_basis=Decimal("25000"),
        ),
    ],
    llm=CoreLLM(),  # Optional: enables AI insights
    total_portfolio_value=Decimal("200000"),  # Optional: for allocation %
)

for insight in insights:
    print(f"[{insight.priority}] {insight.category}: {insight.title}")
    print(f"  {insight.description}")
```

**Parameters**:
- `user_id` (str): User identifier
- `holdings` (list[CryptoHolding]): Portfolio holdings (required)
- `llm` (CoreLLM | None): ai-infra LLM instance (optional, enables AI insights)
- `total_portfolio_value` (Decimal | None): Total portfolio value across all assets (optional)

**Returns**: `list[CryptoInsight]` sorted by priority (high → medium → low)

### `CryptoHolding` Model

```python
CryptoHolding(
    symbol: str,                      # Crypto symbol (e.g., "BTC", "ETH")
    quantity: Decimal,                # Amount held
    market_value: Decimal,            # Current market value
    cost_basis: Decimal,              # Original purchase price
    average_cost: Decimal | None = None,  # Average cost per unit (optional)
)
```

**Example**:
```python
holding = CryptoHolding(
    symbol="BTC",
    quantity=Decimal("0.5"),
    market_value=Decimal("25000"),    # Current value
    cost_basis=Decimal("20000"),      # Original cost
    average_cost=Decimal("40000"),    # $20,000 / 0.5 BTC = $40k per BTC
)
```

### `CryptoInsight` Model

```python
CryptoInsight(
    id: str,                          # Unique identifier
    user_id: str,                     # User identifier
    symbol: str | None,               # Crypto symbol (None for portfolio-wide insights)
    category: str,                    # "allocation", "risk", "opportunity", "performance"
    priority: str,                    # "high", "medium", "low"
    title: str,                       # Short headline (max 100 chars)
    description: str,                 # Detailed explanation (max 500 chars)
    action: str | None,               # Recommended action (max 200 chars, optional)
    value: Decimal | None,            # Associated numeric value (optional)
    metadata: dict | None,            # Additional context (optional)
    created_at: datetime,             # Creation timestamp
)
```

### Insight Categories

1. **Allocation** (Rule-Based):
   - Concentration risk (e.g., "BTC is 70% of crypto holdings")
   - Diversification opportunities
   - Portfolio-wide allocation % (crypto vs total portfolio)

2. **Performance** (Rule-Based):
   - Unrealized gains/losses
   - Top performers
   - Underperformers

3. **Risk** (AI-Powered):
   - Volatility warnings
   - Emergency fund recommendations
   - Risk tolerance assessment

4. **Opportunity** (AI-Powered):
   - Rebalancing suggestions
   - Profit-taking opportunities
   - Dollar-cost averaging recommendations

### Rule-Based Insights

**Generated automatically** without LLM (fast, deterministic):

#### Allocation Insights

```python
# Example: Bitcoin concentration
Insight:
  Priority: MEDIUM
  Category: allocation
  Title: "Bitcoin Dominates Crypto Holdings"
  Description: "BTC represents 65% of your crypto portfolio. Consider diversifying."
  Action: "Explore adding ETH or other altcoins to reduce single-asset risk."
```

**Logic**:
- If any holding > 50% of crypto portfolio → concentration warning
- If crypto < 5% of total portfolio → "Low crypto exposure, consider increasing"
- If crypto > 30% of total portfolio → "High crypto exposure, ensure emergency fund"

#### Performance Insights

```python
# Example: Top performer
Insight:
  Priority: MEDIUM
  Category: performance
  Title: "Ethereum Outperforming (+25%)"
  Description: "ETH has gained 25% since purchase. Current value: $30,000."
  Action: "Consider taking partial profits while maintaining long-term exposure."
```

**Logic**:
- If unrealized gain > 20% → profit-taking opportunity
- If unrealized loss > 20% → tax-loss harvesting opportunity
- If gain > 50% → strong performer highlight

### AI-Powered Insights

**Generated with CoreLLM** (intelligent, personalized):

#### AI Prompt Context

The LLM receives:
- Portfolio composition (symbols, quantities, values)
- Total crypto value and allocation percentage
- Unrealized gains/losses per holding
- Financial disclaimers and safety constraints

**Example Prompt** (sent to LLM):
```
You are a cryptocurrency portfolio advisor. Based on this portfolio:

Holdings:
- BTC: 1.5 units, $75,000 value, +$15,000 gain (25%)
- ETH: 20 units, $30,000 value, +$5,000 gain (20%)

Total crypto value: $105,000 (15% of $700,000 total portfolio)

Provide ONE actionable insight (max 200 words):
- Focus on risk management, diversification, or profit-taking
- Use simple language
- Do NOT recommend specific coins to buy
- Mention "Not financial advice - consult a certified advisor"

Provide your insight:
```

**Example AI Response**:
```
Your crypto allocation (15% of portfolio) is aggressive but manageable. 
Both BTC and ETH have strong gains—consider rebalancing to lock in 
some profits while maintaining long-term exposure. Ensure you have 
6+ months emergency fund in stable assets before increasing crypto 
exposure. Not financial advice—consult a certified financial advisor.
```

### Mocking LLM Calls in Tests

**CRITICAL**: Never call real LLM APIs in unit tests. Always mock CoreLLM.

```python
# tests/unit/crypto/test_insights.py
from unittest.mock import AsyncMock, Mock
from ai_infra.llm import CoreLLM

def test_generate_crypto_insights_with_llm():
    """Test AI-powered insights with mocked LLM."""
    # Create mock LLM
    mock_llm = Mock(spec=CoreLLM)
    mock_response = Mock()
    mock_response.content = "Your crypto portfolio is well-diversified..."
    mock_llm.achat = AsyncMock(return_value=mock_response)
    
    # Generate insights
    insights = await generate_crypto_insights(
        user_id="user_123",
        holdings=[...],
        llm=mock_llm,
    )
    
    # Verify LLM was called
    mock_llm.achat.assert_called_once()
    
    # Verify AI insight in results
    ai_insights = [i for i in insights if "AI Portfolio Analysis" in i.title]
    assert len(ai_insights) == 1
```

**Key Points**:
- Use `unittest.mock.Mock(spec=CoreLLM)` to create type-safe mock
- Mock `achat` method with `AsyncMock(return_value=mock_response)`
- Mock response should have `.content` attribute (string)
- Verify LLM call with `assert_called_once()`

### Cost Considerations

**LLM Usage**: Each `generate_crypto_insights()` call with LLM makes **1 API request**

**Estimated Costs** (with GPT-4):
- Prompt: ~500 tokens ($0.015/1K tokens) = $0.0075
- Response: ~200 tokens ($0.03/1K tokens) = $0.006
- **Total**: ~$0.014 per insights generation

**Optimization Strategies**:
1. **Cache AI insights**: 24h TTL (crypto insights change slowly)
   ```python
   from svc_infra.cache import cache_read
   
   @cache_read(suffix="crypto_insights", ttl=86400)  # 24 hours
   async def get_cached_insights(user_id: str):
       return await generate_crypto_insights(...)
   ```

2. **Use cheaper models**: Gemini Flash (10x cheaper than GPT-4)
   ```python
   llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")
   ```

3. **Batch users**: Generate insights in nightly jobs, not per-request

**Target**: <$0.10/user/month with caching (7 insights generations per month × $0.014)

### Safety & Disclaimers

**Mandatory Disclaimers** (included in all AI prompts):
- "Not financial advice - consult a certified financial advisor"
- No specific coin buy recommendations
- Risk warnings for high-volatility assets

**PII Protection**:
- Never send user names, emails, or account numbers to LLM
- Only send: holdings (symbols, values), portfolio aggregates

**Compliance Logging**:
- All LLM calls logged via svc-infra structured logging
- Includes user_id, timestamp, prompt hash (not full prompt)

---

## Integration Examples

### Example 1: Dashboard Widget

**Use Case**: Show crypto holdings with AI insights

```python
from fin_infra.crypto import easy_crypto
from fin_infra.crypto.insights import generate_crypto_insights, CryptoHolding
from ai_infra.llm import CoreLLM

# Fetch real-time prices
crypto = easy_crypto()
btc_price = crypto.ticker("BTC/USDT").last
eth_price = crypto.ticker("ETH/USDT").last

# Calculate holdings
holdings = [
    CryptoHolding(
        symbol="BTC",
        quantity=Decimal("0.5"),
        market_value=btc_price * Decimal("0.5"),
        cost_basis=Decimal("20000"),
    ),
    CryptoHolding(
        symbol="ETH",
        quantity=Decimal("10"),
        market_value=eth_price * Decimal("10"),
        cost_basis=Decimal("12000"),
    ),
]

# Generate insights
llm = CoreLLM()
insights = await generate_crypto_insights(
    user_id="user_123",
    holdings=holdings,
    llm=llm,
)

# Display top 3 insights
for insight in insights[:3]:
    print(f"💡 {insight.title}: {insight.description}")
```

### Example 2: Tax Reporting Integration

**Use Case**: Calculate crypto gains for tax reporting

```python
from fin_infra.crypto.insights import CryptoHolding
from decimal import Decimal

holdings = [...]  # User's crypto holdings

total_gains = Decimal("0")
for holding in holdings:
    gain = holding.market_value - holding.cost_basis
    total_gains += gain
    
    print(f"{holding.symbol}: ${gain:,.2f} gain")

print(f"Total Crypto Gains: ${total_gains:,.2f}")
```

### Example 3: Multi-Asset Portfolio

**Use Case**: Crypto + stocks portfolio with unified insights

```python
from fin_infra.insights import aggregate_insights
from fin_infra.crypto.insights import CryptoHolding

# Crypto holdings
crypto_holdings = [
    CryptoHolding(symbol="BTC", quantity=Decimal("1"), market_value=Decimal("50000"), cost_basis=Decimal("40000")),
]

# Aggregate with other financial data
feed = aggregate_insights(
    user_id="user_123",
    crypto_holdings=crypto_holdings,
    goals=goals,
    budgets=budgets,
    # ... other sources
)

# Crypto insights appear in unified feed with other insights
for insight in feed.insights:
    if insight.category == "portfolio" and "crypto" in insight.description.lower():
        print(f"🪙 {insight.title}")
```

---

## Production Considerations

### Caching Strategy

```python
from svc_infra.cache import cache_read, resource

# Define crypto resource
crypto_resource = resource("crypto", "symbol")

# Cache quotes (60s TTL)
@crypto_resource.cache_read(suffix="quote", ttl=60)
def get_quote(symbol: str):
    crypto = easy_crypto()
    return crypto.ticker(symbol)

# Cache insights (24h TTL)
@crypto_resource.cache_read(suffix="insights", ttl=86400)
async def get_insights(user_id: str):
    return await generate_crypto_insights(...)
```

### Rate Limiting

**CoinGecko Free Tier**:
- 10-30 calls/minute
- No API key required
- Shared IP rate limits

**CoinGecko Pro**:
- 500 calls/minute
- Requires API key: `COINGECKO_API_KEY=your_key`
- Per-key rate limits

**Handling Rate Limits**:
```python
from svc_infra.http import retry_with_backoff

@retry_with_backoff(max_retries=3, backoff_factor=2)
def fetch_ticker(symbol: str):
    return crypto.ticker(symbol)
```

### Error Handling

```python
from fin_infra.crypto import easy_crypto
from fin_infra.crypto.insights import generate_crypto_insights

try:
    crypto = easy_crypto()
    ticker = crypto.ticker("INVALID_SYMBOL")
except ValueError as e:
    logger.error(f"Invalid symbol: {e}")
    # Return fallback data or error response

try:
    insights = await generate_crypto_insights(user_id="user_123", holdings=[], llm=llm)
except Exception as e:
    logger.error(f"Failed to generate insights: {e}")
    # Fallback to rule-based insights only (no LLM)
    insights = await generate_crypto_insights(user_id="user_123", holdings=[], llm=None)
```

### Monitoring

```python
from svc_infra.logging import setup_logging

setup_logging()

# Logs are automatically structured
crypto = easy_crypto()
ticker = crypto.ticker("BTC/USDT")
# Log output:
# INFO: Fetched BTC/USDT ticker: $50,000 (+2.5%)

insights = await generate_crypto_insights(...)
# Log output:
# INFO: Generated 5 crypto insights for user_123 (3 rule-based, 2 AI-powered)
```

---

## Testing

### Unit Tests (Crypto Insights)

```python
# tests/unit/crypto/test_insights.py
from fin_infra.crypto.insights import generate_crypto_insights, CryptoHolding
from decimal import Decimal

@pytest.mark.asyncio
async def test_allocation_insights():
    """Test rule-based allocation insights."""
    holdings = [
        CryptoHolding(symbol="BTC", quantity=Decimal("1"), market_value=Decimal("65000"), cost_basis=Decimal("50000")),
        CryptoHolding(symbol="ETH", quantity=Decimal("10"), market_value=Decimal("35000"), cost_basis=Decimal("30000")),
    ]
    
    insights = await generate_crypto_insights(user_id="user_123", holdings=holdings)
    
    # Should generate concentration warning (BTC is 65%)
    allocation_insights = [i for i in insights if i.category == "allocation"]
    assert len(allocation_insights) > 0
    assert "BTC" in allocation_insights[0].description

@pytest.mark.asyncio
async def test_ai_insights_with_mock_llm():
    """Test AI-powered insights with mocked LLM."""
    from unittest.mock import AsyncMock, Mock
    
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "Your crypto portfolio is well-diversified..."
    mock_llm.achat = AsyncMock(return_value=mock_response)
    
    holdings = [...]
    insights = await generate_crypto_insights(user_id="user_123", holdings=holdings, llm=mock_llm)
    
    # Verify LLM was called
    mock_llm.achat.assert_called_once()
    
    # Verify AI insight in results
    ai_insights = [i for i in insights if "AI" in i.title]
    assert len(ai_insights) == 1
```

### Integration Tests (Market Data)

```python
# tests/integration/test_crypto_api.py
from fin_infra.crypto import easy_crypto

def test_coingecko_ticker():
    """Test CoinGecko real API (rate limit: 10/min)."""
    crypto = easy_crypto(provider="coingecko")
    ticker = crypto.ticker("BTC/USDT")
    
    assert ticker.symbol == "BTC/USDT"
    assert ticker.last > 0
    assert ticker.timestamp is not None

@pytest.mark.slow
def test_crypto_insights_end_to_end():
    """Test full insights generation with real LLM (skip in CI)."""
    from ai_infra.llm import CoreLLM
    
    llm = CoreLLM()
    holdings = [...]
    
    insights = await generate_crypto_insights(user_id="test_user", holdings=holdings, llm=llm)
    
    assert len(insights) > 0
    assert any("AI" in i.title for i in insights)  # At least one AI insight
```

---

## FAQ

**Q: Do I need an API key for CoinGecko?**  
A: No for free tier (10-30 calls/min). Yes for Pro tier (500 calls/min). Set `COINGECKO_API_KEY` env var for Pro.

**Q: What's the difference between rule-based and AI insights?**  
A: Rule-based insights are deterministic patterns (concentration, gains). AI insights are LLM-generated recommendations (risk assessment, strategic advice). Both are valuable.

**Q: How do I reduce LLM costs?**  
A: (1) Cache insights with 24h TTL, (2) Use cheaper models (Gemini Flash), (3) Generate insights in nightly jobs, not per-request.

**Q: Can I use crypto module without ai-infra?**  
A: Yes! Market data works without ai-infra. Insights work without LLM (rule-based only). Pass `llm=None` to skip AI insights.

**Q: How accurate are crypto prices?**  
A: CoinGecko aggregates prices from multiple exchanges. Prices are delayed ~1-2 minutes. For real-time trading, use exchange-specific APIs (CCXT).

**Q: Can I track crypto in multiple accounts?**  
A: Yes. Create separate `CryptoHolding` objects per account and aggregate them in insights.

**Q: How do I handle unknown symbols?**  
A: Use `search()` to find correct symbol format. CoinGecko uses IDs like "bitcoin", not tickers like "BTC".

**Q: What about crypto tax reporting?**  
A: See `tax.md` for crypto-specific tax calculations (FIFO/LIFO, capital gains).

---

## Related Documentation

- **[Insights Feed](./insights.md)**: Unified insights aggregation (includes crypto)
- **[Analytics](./analytics.md)**: Portfolio rebalancing with crypto
- **[Tax](./tax.md)**: Crypto tax calculations and reporting
- **[Market Data](./markets.md)**: Stock market data (similar patterns)
- **[ai-infra LLM](../../ai-infra/docs/llm.md)**: CoreLLM usage guide
- **[svc-infra Cache](../../svc-infra/docs/cache.md)**: Caching strategies

---

**Last Updated**: 2025-01-27  
**Module Version**: Phase 3 (Production-ready)  
**Test Coverage**: 16 unit tests (insights), 8 integration tests (market data)
