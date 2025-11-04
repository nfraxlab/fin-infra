# ADR-0004: Market Data Integration

## Status
Accepted

## Context
fin-infra needs stock/equity market data capabilities for fintech applications (portfolio tracking, investment analysis, financial dashboards). We need to provide:
- Real-time and historical quotes
- OHLCV candle data for charting
- Symbol search/lookup
- Company fundamentals (optional)
- Multiple provider support (free tier priority)

Key constraints:
- Free tier must work for MVPs (no upfront costs)
- Rate limits require caching strategy
- svc-infra provides ALL backend infrastructure (caching, HTTP retry, logging)
- fin-infra provides ONLY financial provider adapters

## Decision

### Provider Strategy
**Default: Alpha Vantage**
- Free tier: 5 requests/minute, 500/day
- API key required (free signup)
- Comprehensive data: quotes, historical, search, fundamentals
- Good for production with reasonable limits

**Alternate 1: Yahoo Finance**
- Completely free, no API key required
- No official API (uses unofficial libraries)
- Good for development/testing
- Zero-config capability

**Alternate 2: Polygon** (future)
- More generous free tier: 5 requests/minute
- Better data quality
- Defer until customer demand

### Data Models
Reuse existing models:
- `Quote`: symbol, price, as_of, currency
- `Candle`: ts (epoch ms), open, high, low, close, volume

Add optional models (defer to fast follow):
- `SymbolInfo`: symbol, name, type, exchange, currency
- `CompanyOverview`: market_cap, pe_ratio, dividend_yield, etc.

### Easy Builder Pattern
```python
from fin_infra.markets import easy_market

# Auto-detect from environment (checks ALPHA_VANTAGE_API_KEY, then falls back to Yahoo)
market = easy_market()

# Explicit provider
market = easy_market(provider="alphavantage")  # Requires API key
market = easy_market(provider="yahoo")         # No key needed
```

### FastAPI Integration
```python
from fin_infra.markets import add_market_data
from svc_infra.api.fastapi.ease import easy_service_app

app = easy_service_app(name="MarketAPI")

# Mount market data routes
add_market_data(
    app,
    provider="alphavantage",  # or None for auto-detect
    mount_path="/api/v1/market",
    require_auth=False  # Optional: use svc-infra auth
)
# Creates: GET /api/v1/market/quote/{symbol}
#          GET /api/v1/market/history/{symbol}
#          GET /api/v1/market/search?q={query}
```

### Caching Strategy (svc-infra)
Use svc-infra cache decorators for rate limit mitigation:
- Quotes: 60 second TTL (sufficient for most use cases)
- Historical data: 5 minute TTL (daily data doesn't change frequently)
- Search results: 1 hour TTL (symbol info rarely changes)

```python
from svc_infra.cache import cache_read, resource

# Define cached resource
market_quote = resource("market_quote", "symbol")

@market_quote.cache_read(ttl=60, suffix="latest")
def get_quote(symbol: str):
    return market.quote(symbol)
```

### Rate Limit Handling
1. **Client-side throttling**: Implement naive sleep-based throttling in providers
2. **HTTP retry**: Use svc-infra's `http_client_with_retry` for transient errors
3. **429 handling**: Catch rate limit errors, return cached data if available
4. **Fallback providers**: If Alpha Vantage exhausted, try Yahoo Finance

### Error Handling
- `ValueError`: Invalid symbol format
- `httpx.HTTPStatusError`: Provider API errors (log and re-raise)
- `httpx.TimeoutException`: Network timeouts (retry via svc-infra)
- Return empty list for history on errors (graceful degradation)

## Consequences

### Positive
- Zero-cost development (Yahoo Finance)
- Reasonable free tier for production (Alpha Vantage)
- Easy migration to paid providers later (Polygon, IEX)
- Proper separation: fin-infra handles provider APIs, svc-infra handles infrastructure
- Built-in caching reduces API calls by 90%+

### Negative
- Free tier rate limits require careful caching
- Yahoo Finance unofficial API may break
- Real-time data requires paid tiers (acceptable for MVP)
- Alpha Vantage 5 req/min is restrictive for batch operations

### Mitigations
- Implement robust caching (svc-infra)
- Support multiple providers for fallback
- Document rate limits clearly
- Provide batch quote endpoint with intelligent queuing

## Implementation Checklist
- [x] Existing: AlphaVantageMarketData class with quote() and history()
- [x] Existing: Quote and Candle models
- [ ] Enhance: Add error handling and rate limit logic to AlphaVantageMarketData
- [ ] New: YahooFinanceMarketData provider (zero config)
- [ ] New: easy_market() builder with auto-detection
- [ ] New: add_market_data() FastAPI integration helper
- [ ] New: Unit tests with mocked providers
- [ ] Existing: Acceptance test (enhance with more coverage)
- [ ] New: Documentation (docs/market-data.md)

## References
- Alpha Vantage API: https://www.alphavantage.co/documentation/
- Yahoo Finance (yfinance): https://pypi.org/project/yfinance/
- svc-infra caching: src/svc_infra/cache/
- svc-infra HTTP: src/svc_infra/http/
