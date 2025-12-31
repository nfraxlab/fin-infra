# Caching, Rate Limiting & Retries

This guide shows how to use **svc-infra** infrastructure modules with **fin-infra** financial providers for caching, rate limiting, and HTTP retries.

> **Critical**: fin-infra does NOT implement its own caching, rate limiting, or retry logic. Always use svc-infra modules for these cross-cutting concerns.

## Table of Contents

1. [Caching Financial Data](#caching-financial-data)
2. [Rate Limiting Provider Calls](#rate-limiting-provider-calls)
3. [HTTP Retries for Provider APIs](#http-retries-for-provider-apis)
4. [Complete Integration Example](#complete-integration-example)
5. [Provider-Specific Patterns](#provider-specific-patterns)

---

## Caching Financial Data

### Quick Start

```python
from svc_infra.cache import init_cache, cache_read, cache_write
from fin_infra.markets import easy_market

# 1. Initialize cache (do this once at app startup)
init_cache(
    url="redis://localhost:6379/0",
    prefix="finapp",
    version="v1"
)

# 2. Use providers as normal - cache manually where needed
market = easy_market()
```

### Cache Initialization

**Sync initialization** (for scripts):
```python
from svc_infra.cache import init_cache

init_cache(
    url="redis://localhost:6379/0",  # Redis backend
    prefix="myapp",                   # Key prefix
    version="v1"                      # Cache version
)
```

**Async initialization** (for FastAPI apps):
```python
from svc_infra.cache import init_cache_async

@app.on_event("startup")
async def startup():
    await init_cache_async(
        url="redis://localhost:6379/0",
        prefix="finapp",
        version="v1"
    )
```

### Caching Market Data Quotes

```python
from svc_infra.cache.decorators import cache_read
from fin_infra.markets import easy_market

market = easy_market()

# Cache quotes for 5 minutes
@cache_read(key="quote:{symbol}", ttl=300)
async def get_cached_quote(symbol: str):
    """Get quote with 5-minute cache."""
    return market.quote(symbol)

# Usage
quote = await get_cached_quote("AAPL")  # First call: API request
quote = await get_cached_quote("AAPL")  # Second call: cached (fast!)
```

### Caching Banking Accounts

```python
from svc_infra.cache.decorators import cache_read, cache_write, invalidate_tags
from fin_infra.banking import easy_banking

banking = easy_banking()

# Cache account list for 10 minutes, tag for invalidation
@cache_read(
    key="banking:accounts:{access_token}",
    ttl=600,
    tags=["banking:accounts"]
)
async def get_cached_accounts(access_token: str):
    """Get accounts with 10-minute cache."""
    return banking.get_accounts(access_token)

# Invalidate when account data changes
async def on_account_updated():
    """Called when account data is updated externally."""
    await invalidate_tags(["banking:accounts"])
```

### Caching Crypto Prices

```python
from svc_infra.cache.decorators import cache_read
from fin_infra.crypto import easy_crypto

crypto = easy_crypto()

# Short TTL for volatile crypto prices
@cache_read(key="crypto:price:{symbol}", ttl=60)
async def get_cached_crypto_price(symbol: str):
    """Get crypto price with 1-minute cache."""
    return crypto.ticker(symbol)
```

### Cache Tags for Bulk Invalidation

```python
from svc_infra.cache.decorators import cache_read, invalidate_tags

# Tag multiple related caches
@cache_read(
    key="user:{user_id}:portfolio",
    ttl=300,
    tags=lambda user_id: [f"user:{user_id}", "portfolios"]
)
async def get_user_portfolio(user_id: int):
    return fetch_portfolio(user_id)

# Invalidate all portfolios at once
await invalidate_tags(["portfolios"])

# Invalidate specific user's data
await invalidate_tags([f"user:{user_id}"])
```

### Resource-Based Caching

```python
from svc_infra.cache.resources import resource

# Define a resource for user-specific market data
user_market = resource(name="user_market", id_param="user_id")

@user_market.cache_read(suffix="watchlist", ttl=600)
async def get_user_watchlist(user_id: int):
    # Key becomes: "user_market:{user_id}:watchlist"
    return fetch_watchlist(user_id)

@user_market.cache_write(tags=["watchlists"])
async def update_user_watchlist(user_id: int, symbols: list[str]):
    # Invalidates cache automatically
    return save_watchlist(user_id, symbols)
```

---

## Rate Limiting Provider Calls

### Application-Level Rate Limiting

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.api.fastapi.middleware.ratelimit import SimpleRateLimitMiddleware
from svc_infra.api.fastapi.middleware.ratelimit_store import RedisRateLimitStore
from fin_infra.markets import add_market_data

# Create app with rate limiting
app = easy_service_app(name="FinanceAPI")

# Add Redis-backed rate limiter
rate_limit_store = RedisRateLimitStore(redis_url="redis://localhost:6379/1")
app.add_middleware(
    SimpleRateLimitMiddleware,
    store=rate_limit_store,
    default_limit=100,      # 100 requests
    default_window=60       # per 60 seconds
)

# Wire financial providers
market = add_market_data(app)
```

### Route-Specific Rate Limits

```python
from fastapi import FastAPI, Depends
from svc_infra.api.fastapi.dependencies.ratelimit import RateLimiter
from fin_infra.markets import easy_market

app = FastAPI()
market = easy_market()

# Different limits for different endpoints
@app.get(
    "/quote/{symbol}",
    dependencies=[Depends(RateLimiter(limit=10, window=60))]  # 10/min
)
async def get_quote(symbol: str):
    return market.quote(symbol)

@app.get(
    "/history/{symbol}",
    dependencies=[Depends(RateLimiter(limit=5, window=60))]  # 5/min (expensive)
)
async def get_history(symbol: str):
    return market.history(symbol)
```

### User-Specific Rate Limits

```python
from svc_infra.api.fastapi.dependencies.ratelimit import RateLimiter
from svc_infra.api.fastapi.auth.dependencies import RequireUser

@app.get(
    "/banking/accounts",
    dependencies=[Depends(RequireUser())]
)
async def get_accounts(
    user=Depends(RequireUser()),
    rate_limit=Depends(RateLimiter(
        limit=50,
        window=60,
        key_func=lambda req: f"user:{req.state.user.id}"  # Per-user limit
    ))
):
    banking = easy_banking()
    return banking.get_accounts(user.provider_token)
```

### Provider Quota Tracking

```python
from svc_infra.cache import cache_read
from fin_infra.markets import easy_market

market = easy_market()

async def check_provider_quota(provider: str) -> dict:
    """Check remaining API quota for a provider."""
    # This would be provider-specific
    if provider == "alphavantage":
        # Alpha Vantage: 25 requests per day (free tier)
        key = f"quota:{provider}:daily"
        current = await get_from_cache(key) or 0
        return {
            "provider": provider,
            "limit": 25,
            "remaining": max(0, 25 - current),
            "resets_at": "midnight UTC"
        }
    return {"provider": provider, "limit": "unknown"}

@app.get("/admin/quotas")
async def get_quotas():
    """Check quota status for all providers."""
    return {
        "alphavantage": await check_provider_quota("alphavantage"),
        "plaid": await check_provider_quota("plaid"),
        "alpaca": await check_provider_quota("alpaca"),
    }
```

---

## HTTP Retries for Provider APIs

### Automatic Retries with svc-infra HTTP Client

```python
from svc_infra.http import new_async_httpx_client, make_timeout
import httpx

# Create HTTP client with retries built-in
async with new_async_httpx_client(
    timeout=make_timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
    follow_redirects=True
) as client:
    # Automatically retries on network errors, 5xx responses
    response = await client.get("https://api.example.com/data")
    data = response.json()
```

### Custom Retry Logic for Providers

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import httpx

@retry(
    stop=stop_after_attempt(3),                    # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=1, max=10),  # Exponential backoff
    retry=retry_if_exception_type((
        httpx.NetworkError,
        httpx.TimeoutException,
        httpx.HTTPStatusError
    ))
)
async def fetch_with_retry(url: str):
    """Fetch URL with automatic retries."""
    async with new_async_httpx_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Provider-Specific Retry Strategies

```python
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_result

# Alpha Vantage: Retry on rate limit with longer wait
@retry(
    stop=stop_after_attempt(5),
    wait=wait_fixed(60),  # Wait 60s between retries
    retry=retry_if_result(lambda r: "rate limit" in str(r).lower())
)
async def fetch_alphavantage_quote(symbol: str):
    """Fetch from Alpha Vantage with rate limit handling."""
    from fin_infra.markets import easy_market
    market = easy_market(provider="alphavantage")
    return market.quote(symbol)

# Plaid: Retry on specific error codes
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2),
    retry=retry_if_exception_type(httpx.HTTPStatusError)
)
async def fetch_plaid_accounts(access_token: str):
    """Fetch from Plaid with retry on HTTP errors."""
    from fin_infra.banking import easy_banking
    banking = easy_banking(provider="plaid")
    return banking.get_accounts(access_token)
```

### Circuit Breaker Pattern

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    """Simple circuit breaker for provider APIs."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half-open"
            else:
                raise Exception(f"Circuit breaker OPEN for provider")

        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            self.state = "closed"
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise

# Usage
alphavantage_breaker = CircuitBreaker(failure_threshold=5, timeout=300)

async def get_quote_with_breaker(symbol: str):
    """Get quote with circuit breaker protection."""
    market = easy_market()
    return await alphavantage_breaker.call(market.quote, symbol)
```

---

## Complete Integration Example

### Full Production Setup

```python
from fastapi import FastAPI, Depends
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.api.fastapi.middleware.ratelimit import SimpleRateLimitMiddleware
from svc_infra.api.fastapi.middleware.ratelimit_store import RedisRateLimitStore
from svc_infra.api.fastapi.dependencies.ratelimit import RateLimiter
from svc_infra.cache import init_cache_async, cache_read
from svc_infra.http import new_async_httpx_client
from svc_infra.logging import setup_logging
from svc_infra.obs import add_observability
from fin_infra.markets import easy_market, add_market_data
from fin_infra.banking import add_banking
from fin_infra.brokerage import add_brokerage

# Setup logging
setup_logging(level="INFO")

# Create app
app = easy_service_app(name="FinanceAPI")

# Initialize infrastructure
@app.on_event("startup")
async def startup():
    # 1. Cache
    await init_cache_async(
        url="redis://localhost:6379/0",
        prefix="finapi",
        version="v1"
    )

    # 2. Rate limiting
    rate_limit_store = RedisRateLimitStore(redis_url="redis://localhost:6379/1")
    app.add_middleware(
        SimpleRateLimitMiddleware,
        store=rate_limit_store,
        default_limit=100,
        default_window=60
    )

    # 3. Observability
    add_observability(app)

# Wire financial providers
market = add_market_data(app, prefix="/market")
banking = add_banking(app, prefix="/banking")
brokerage = add_brokerage(app, prefix="/brokerage", mode="paper")

# Cached endpoint with rate limiting
@app.get(
    "/quote/{symbol}",
    dependencies=[Depends(RateLimiter(limit=10, window=60))]
)
@cache_read(key="quote:{symbol}", ttl=300)
async def get_quote(symbol: str):
    """Get stock quote (cached 5min, rate limited 10/min)."""
    return market.quote(symbol)

# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Provider-Specific Patterns

### Banking (Plaid/Teller)
```python
# Cache accounts for 10 minutes (account data changes slowly)
@cache_read(key="banking:accounts:{token}", ttl=600, tags=["banking"])
async def get_accounts(token: str):
    banking = easy_banking()
    return banking.get_accounts(token)

# Cache transactions for 5 minutes (more dynamic)
@cache_read(key="banking:transactions:{account_id}", ttl=300)
async def get_transactions(account_id: str, token: str):
    banking = easy_banking()
    return banking.get_transactions(account_id, token)

# Rate limit: 50 requests/minute per user
@app.get("/banking/accounts", dependencies=[
    Depends(RateLimiter(limit=50, window=60, key_func=lambda r: r.state.user.id))
])
```

### Market Data (Alpha Vantage/Yahoo)
```python
# Cache quotes for 5 minutes (market data updates frequently)
@cache_read(key="market:quote:{symbol}", ttl=300)
async def get_quote(symbol: str):
    market = easy_market()
    return market.quote(symbol)

# Cache historical data for 1 hour (less volatile)
@cache_read(key="market:history:{symbol}:{period}", ttl=3600)
async def get_history(symbol: str, period: str = "1mo"):
    market = easy_market()
    return market.history(symbol, period=period)

# Rate limit: Alpha Vantage free tier = 25 requests/day
# Use aggressive caching + queue for batch requests
```

### Crypto Data (CoinGecko)
```python
# Cache crypto prices for 1 minute (very volatile)
@cache_read(key="crypto:ticker:{symbol}", ttl=60)
async def get_crypto_ticker(symbol: str):
    crypto = easy_crypto()
    return crypto.ticker(symbol)

# Rate limit: CoinGecko free = 10-50 requests/minute
@app.get("/crypto/ticker/{symbol}", dependencies=[
    Depends(RateLimiter(limit=10, window=60))
])
```

### Brokerage (Alpaca)
```python
# DON'T cache: Account info (buying power changes with trades)
async def get_account():
    broker = easy_brokerage(mode="paper")
    return broker.get_account()  # No cache!

# DON'T cache: Positions (change with every trade)
async def get_positions():
    broker = easy_brokerage(mode="paper")
    return broker.positions()  # No cache!

# Cache portfolio history for 5 minutes (less critical for real-time)
@cache_read(key="brokerage:history:{period}", ttl=300)
async def get_portfolio_history(period: str = "1W"):
    broker = easy_brokerage(mode="paper")
    return broker.get_portfolio_history(period=period)

# Rate limit: Alpaca = 200 requests/minute
@app.post("/brokerage/orders", dependencies=[
    Depends(RateLimiter(limit=200, window=60))
])
```

---

## Best Practices

### [OK] DO
- **Use svc-infra cache for all caching** (never implement custom cache)
- **Cache slow/expensive provider calls** (market data, account lists)
- **Use short TTLs for volatile data** (crypto prices: 1min, stocks: 5min)
- **Use long TTLs for static data** (symbol metadata: 1 day)
- **Tag related caches for bulk invalidation** (all user data, all portfolios)
- **Rate limit aggressively** to protect provider quotas
- **Use circuit breakers** for unreliable providers
- **Monitor cache hit rates** via svc-infra observability

### [X] DON'T
- **DON'T cache trading account balances** (changes with every trade)
- **DON'T cache real-time positions** (critical for trading decisions)
- **DON'T cache sensitive PII** without encryption
- **DON'T cache provider tokens** (use secure storage)
- **DON'T bypass rate limits** (risks account suspension)
- **DON'T implement custom retry logic** (use svc-infra/tenacity)
- **DON'T cache across user boundaries** (always include user_id in keys)

---

## Related Documentation

- [svc-infra Cache Documentation](../../svc-infra/src/svc_infra/cache/)
- [svc-infra Rate Limiting](../../svc-infra/src/svc_infra/api/fastapi/middleware/ratelimit.py)
- [svc-infra HTTP Client](../../svc-infra/src/svc_infra/http/)
- [Banking Provider Guide](./banking.md)
- [Market Data Guide](./market-data.md)
- [Crypto Data Guide](./crypto-data.md)
- [Brokerage Guide](./brokerage.md)
