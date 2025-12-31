# Market Data Integration

fin-infra provides unified access to equity and cryptocurrency market data through multiple providers, with fallback support and consistent data models.

## Supported Providers

### Equity Markets
- **Alpha Vantage**: Free tier with rate limits
- **Yahoo Finance**: Via yahooquery
- **IEX Cloud**: Coming soon
- **Polygon.io**: Coming soon

### Cryptocurrency Markets
- **CoinGecko**: Free API with rate limits
- **CCXT**: Multi-exchange support (Binance, Coinbase, Kraken, etc.)
- **CoinMarketCap**: Coming soon

## Quick Setup

### Equity Market Data
```python
from fin_infra.markets import easy_market

# Auto-configured with default provider
market = easy_market()  # Uses Alpha Vantage by default

# Or specify provider
market = easy_market(provider="yahoo")
```

### Crypto Market Data
```python
from fin_infra.markets import easy_crypto

# Auto-configured with default provider
crypto = easy_crypto()  # Uses CoinGecko by default

# Or specify exchange via CCXT
crypto = easy_crypto(provider="ccxt", exchange="binance")
```

## Equity Market Operations

### 1. Get Real-Time Quote
```python
from fin_infra.models.quotes import Quote

quote = market.quote("AAPL")

print(f"Symbol: {quote.symbol}")
print(f"Price: ${quote.price}")
print(f"Change: {quote.change} ({quote.change_percent}%)")
print(f"Volume: {quote.volume}")
print(f"Market Cap: ${quote.market_cap}")
print(f"52-Week High: ${quote.high_52week}")
print(f"52-Week Low: ${quote.low_52week}")
```

### 2. Get Multiple Quotes
```python
quotes = market.quotes(["AAPL", "GOOGL", "MSFT", "TSLA"])

for quote in quotes:
    print(f"{quote.symbol}: ${quote.price}")
```

### 3. Historical Data
```python
from datetime import date, timedelta

# Get 1 month of daily data
historical = market.historical(
    symbol="AAPL",
    start_date=date.today() - timedelta(days=30),
    end_date=date.today(),
    interval="1d"  # 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
)

for candle in historical:
    print(f"{candle.timestamp}: O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close}")
```

### 4. Search Symbols
```python
results = market.search("apple")

for result in results:
    print(f"{result.symbol}: {result.name}")
    print(f"Exchange: {result.exchange}")
    print(f"Type: {result.asset_type}")
```

### 5. Company Information
```python
company = market.company_info("AAPL")

print(f"Name: {company.name}")
print(f"Description: {company.description}")
print(f"Industry: {company.industry}")
print(f"Sector: {company.sector}")
print(f"Website: {company.website}")
print(f"CEO: {company.ceo}")
```

## Cryptocurrency Operations

### 1. Get Crypto Price
```python
ticker = crypto.ticker("BTC/USDT")

print(f"Symbol: {ticker.symbol}")
print(f"Price: ${ticker.last}")
print(f"Bid: ${ticker.bid}")
print(f"Ask: ${ticker.ask}")
print(f"24h Volume: {ticker.volume}")
print(f"24h Change: {ticker.change_24h}%")
```

### 2. Get Multiple Tickers
```python
tickers = crypto.tickers(["BTC/USDT", "ETH/USDT", "SOL/USDT"])

for ticker in tickers:
    print(f"{ticker.symbol}: ${ticker.last}")
```

### 3. OHLCV Candles
```python
candles = crypto.candles(
    symbol="BTC/USDT",
    timeframe="1h",  # 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
    limit=100
)

for candle in candles:
    print(f"{candle.timestamp}: ${candle.close}")
```

### 4. Order Book
```python
orderbook = crypto.orderbook("BTC/USDT", limit=10)

print("Bids:")
for price, volume in orderbook.bids[:5]:
    print(f"  ${price} x {volume}")

print("Asks:")
for price, volume in orderbook.asks[:5]:
    print(f"  ${price} x {volume}")
```

### 5. Market List
```python
markets = crypto.list_markets()

for market in markets:
    print(f"{market.symbol}: {market.base}/{market.quote}")
```

## Data Models

### Quote
```python
from fin_infra.models.quotes import Quote

class Quote:
    symbol: str
    price: Decimal
    change: Decimal
    change_percent: Decimal
    volume: int
    market_cap: Decimal | None
    high_52week: Decimal | None
    low_52week: Decimal | None
    pe_ratio: Decimal | None
    dividend_yield: Decimal | None
```

### Candle (OHLCV)
```python
from fin_infra.models.candle import Candle

class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
```

## Rate Limiting & Caching

```python
from fin_infra.markets import easy_market
from fin_infra.cache import init_cache

# Initialize cache
init_cache(url="redis://localhost:6379", prefix="fininfra", version="v1")

# Market data calls are automatically cached
market = easy_market()

# First call hits API
quote1 = market.quote("AAPL")  # API call

# Second call within TTL returns cached data
quote2 = market.quote("AAPL")  # Cache hit
```

## Provider Fallback

```python
from fin_infra.markets import MarketDataAggregator

# Configure multiple providers with fallback
aggregator = MarketDataAggregator(
    providers=[
        ("alphavantage", {"api_key": "xxx"}),
        ("yahoo", {}),
        ("iex", {"api_key": "yyy"})
    ]
)

# Automatically falls back to next provider on error
quote = aggregator.quote("AAPL")
```

## Error Handling

```python
from fin_infra.markets.exceptions import (
    MarketDataError,
    SymbolNotFoundError,
    RateLimitError,
    ProviderError
)

try:
    quote = market.quote("INVALID_SYMBOL")
except SymbolNotFoundError:
    print("Symbol not found")
except RateLimitError:
    print("Rate limit exceeded, implement backoff")
except ProviderError as e:
    print(f"Provider error: {e.message}")
```

## Streaming Real-Time Data

```python
from fin_infra.markets import easy_market_stream

# WebSocket streaming (for supported providers)
async with easy_market_stream() as stream:
    await stream.subscribe(["AAPL", "GOOGL", "TSLA"])

    async for quote in stream:
        print(f"{quote.symbol}: ${quote.price}")
```

## FastAPI Integration

### Easy Add Market Data (One-Liner Setup)
```python
from fin_infra.markets import add_market_data

# [OK] Mount complete market data API with one call
market_provider = add_market_data(
    app,
    provider="alphavantage",  # or "yahoo" (optional, defaults to env)
    prefix="/market"          # default: "/market"
)

# Auto-generated routes (using svc-infra dual routers):
# GET  /market/quote/{symbol}     - Get real-time quote for a symbol
# GET  /market/history/{symbol}   - Get historical OHLCV candles
# GET  /market/search             - Search for symbols (query param)

# Landing page card automatically registered at /market/docs
# OpenAPI schema available at /market/openapi.json
```

**What `add_market_data()` Does:**
- [OK] Initializes market data provider (Alpha Vantage/Yahoo) with environment config
- [OK] Mounts all 3 market endpoints with proper request/response models
- [OK] Uses `public_router()` from svc-infra (public market data, no auth)
- [OK] Registers landing page documentation card
- [OK] Stores provider instance on `app.state.market_provider`
- [OK] Returns provider for programmatic access
- [OK] Handles provider errors with proper HTTP status codes

### Basic Setup (Using svc-infra)
```python
from fastapi import FastAPI, HTTPException, Query
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.cache import init_cache
from fin_infra.markets import easy_market

# Backend from svc-infra
app = easy_service_app(name="MarketAPI", release="production")
init_cache(url="redis://localhost")

# Financial provider from fin-infra
market = easy_market()

@app.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Fetch real-time stock quote"""
    try:
        quote = market.quote(symbol)
        return {
            "symbol": quote.symbol,
            "price": float(quote.price),
            "change": float(quote.change),
            "change_percent": float(quote.change_percent),
            "volume": quote.volume
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/history/{symbol}")
async def get_history(
    symbol: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD")
):
    """Fetch historical OHLCV data"""
    from datetime import date
    candles = market.history(
        symbol=symbol,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date)
    )
    return {
        "symbol": symbol,
        "candles": [
            {
                "timestamp": c.timestamp.isoformat(),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume)
            }
            for c in candles
        ]
    }
```

### With Caching (svc-infra)
```python
from svc_infra.cache import cache_read, resource

# Define cached resource
market_cache = resource("market", "symbol")

@app.get("/quote/{symbol}")
@market_cache.cache_read(ttl=60, suffix="quote")  # 60s cache
async def get_quote_cached(symbol: str):
    """Cached quote fetch (60s TTL)"""
    quote = market.quote(symbol)
    return {"symbol": quote.symbol, "price": float(quote.price)}

@app.get("/history/{symbol}")
@market_cache.cache_read(ttl=3600, suffix="history")  # 1 hour cache
async def get_history_cached(symbol: str, start_date: str, end_date: str):
    """Cached history fetch (1 hour TTL)"""
    from datetime import date
    candles = market.history(
        symbol=symbol,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date)
    )
    return {"symbol": symbol, "count": len(candles), "candles": candles}
```

## Integration Examples

### Complete Production App (fin-infra + svc-infra)
```python
from fastapi import FastAPI, HTTPException, Query
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.logging import setup_logging
from svc_infra.cache import init_cache, resource
from svc_infra.obs import add_observability
from fin_infra.markets import add_market_data, easy_market

# 1. Setup logging (svc-infra)
setup_logging(level="INFO", fmt="json")

# 2. Create service app (svc-infra)
app = easy_service_app(
    name="MarketDataAPI",
    release="production",
    api_version="v1"
)

# 3. Initialize cache (svc-infra)
init_cache(url="redis://localhost:6379", prefix="marketapi", version="v1")

# 4. Add observability (svc-infra)
shutdown_obs = add_observability(
    app,
    metrics_path="/metrics",
    skip_metric_paths=["/health", "/metrics"]
)

# 5. Add market data (fin-infra) - One-liner!
market_provider = add_market_data(app, provider="alphavantage", prefix="/market")

# 6. Custom cached routes using market provider
market_cache = resource("market", "symbol")

@app.get("/portfolio/value")
@market_cache.cache_read(ttl=30, suffix="portfolio")  # 30s cache
async def portfolio_value(symbols: str = Query(..., description="Comma-separated")):
    """Calculate portfolio value (cached 30s)"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    total_value = 0
    quotes = []

    for symbol in symbol_list:
        try:
            quote = market_provider.quote(symbol)
            quotes.append({
                "symbol": quote.symbol,
                "price": float(quote.price),
                "change_percent": float(quote.change_percent)
            })
            total_value += float(quote.price)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching {symbol}: {str(e)}")

    return {
        "symbols": symbol_list,
        "quotes": quotes,
        "total_value": total_value
    }

@app.get("/watchlist/alerts")
async def price_alerts(symbol: str, target_price: float):
    """Check if symbol reached target price"""
    quote = market_provider.quote(symbol)
    current_price = float(quote.price)

    if current_price >= target_price:
        return {
            "alert": True,
            "message": f"{symbol} reached target ${target_price}",
            "current_price": current_price,
            "target_price": target_price
        }
    else:
        return {
            "alert": False,
            "current_price": current_price,
            "target_price": target_price,
            "distance": target_price - current_price
        }

# 7. Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    shutdown_obs()
```

**Run it:**
```bash
# Set environment variables
export ALPHA_VANTAGE_API_KEY="your-api-key"
export REDIS_URL="redis://localhost:6379"

# Start server
uvicorn main:app --reload

# API available at:
# - Docs: http://localhost:8000/docs
# - Market card: http://localhost:8000/market/docs
# - Market endpoints: http://localhost:8000/market/*
# - Custom endpoints: http://localhost:8000/portfolio/value?symbols=AAPL,GOOGL,MSFT
```

### Minimal Example (Just Market Data)
```python
from fastapi import FastAPI
from fin_infra.markets import add_market_data

app = FastAPI(title="Market Data API")

# One-liner setup
add_market_data(app, provider="yahoo")  # Free, no API key!

# That's it! 3 endpoints ready to use:
# GET /market/quote/{symbol}
# GET /market/history/{symbol}
# GET /market/search?q=apple
```

### Programmatic Usage (No FastAPI)
```python
from fin_infra.markets import easy_market

# Initialize provider
market = easy_market(provider="yahoo")  # Free, no API key

# Use directly in scripts, background jobs, CLI tools
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]

for symbol in symbols:
    quote = market.quote(symbol)
    print(f"{symbol}: ${quote.price:.2f} ({quote.change_percent:+.2f}%)")

# Historical analysis
from datetime import date, timedelta
candles = market.history(
    symbol="AAPL",
    start_date=date.today() - timedelta(days=30),
    end_date=date.today()
)
print(f"30-day high: ${max(float(c.high) for c in candles):.2f}")
print(f"30-day low: ${min(float(c.low) for c in candles):.2f}")
```

### With Background Jobs (svc-infra)
```python
from svc_infra.jobs.easy import easy_jobs
from fin_infra.markets import easy_market

# Setup jobs (svc-infra)
worker, scheduler = easy_jobs(app, redis_url="redis://localhost:6379")

# Market provider
market = easy_market()

@worker.task
async def update_market_data(symbols: list[str]):
    """Background job to update market data"""
    quotes = []
    for symbol in symbols:
        try:
            quote = market.quote(symbol)
            quotes.append({
                "symbol": quote.symbol,
                "price": float(quote.price),
                "timestamp": quote.timestamp
            })
            # Store in database
            await db.save_quote(quote)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    return {"updated": len(quotes), "quotes": quotes}

# Schedule updates every 5 minutes during market hours
@scheduler.scheduled_job("cron", minute="*/5", hour="9-16", day_of_week="mon-fri")
async def market_hours_update():
    """Update market data every 5 minutes during trading hours"""
    watchlist = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    await update_market_data.kiq(watchlist)

# End of day summary
@scheduler.scheduled_job("cron", hour=16, minute=5, day_of_week="mon-fri")
async def end_of_day_summary():
    """Generate end-of-day market summary"""
    from datetime import date
    symbols = await db.get_all_tracked_symbols()

    for symbol in symbols:
        candles = market.history(
            symbol=symbol,
            start_date=date.today(),
            end_date=date.today()
        )
        # Calculate daily stats and send notifications
        await notify_subscribers(symbol, candles)
```

### Rate Limit Handling with Retry (svc-infra)
```python
from svc_infra.http import retry_with_backoff
from fin_infra.markets import easy_market

market = easy_market(provider="alphavantage")

@retry_with_backoff(max_attempts=3, backoff_factor=2.0)
async def fetch_quote_with_retry(symbol: str):
    """Fetch quote with automatic retry on rate limits"""
    try:
        return market.quote(symbol)
    except RateLimitError:
        # Backoff and retry automatically
        raise
    except Exception as e:
        # Other errors don't retry
        print(f"Error: {e}")
        return None

# Usage
quote = await fetch_quote_with_retry("AAPL")
```

## Best Practices

1. **Caching**: Always enable caching for market data to reduce API calls
2. **Rate Limiting**: Respect provider rate limits, implement exponential backoff
3. **Fallback Providers**: Configure multiple providers for reliability
4. **Symbol Normalization**: Normalize symbols before querying (e.g., "AAPL" not "aapl")
5. **Time Zones**: Always work with timezone-aware datetimes
6. **Data Validation**: Validate data ranges and handle missing data gracefully

## Testing

```python
import pytest
from fin_infra.markets import easy_market

def test_get_quote():
    market = easy_market()
    quote = market.quote("AAPL")

    assert quote.symbol == "AAPL"
    assert quote.price > 0
    assert quote.volume > 0

@pytest.mark.acceptance
def test_real_market_data():
    market = easy_market()
    quote = market.quote("AAPL")

    # Test against real API
    assert quote is not None
```

## Next Steps

- [Banking Integration](banking.md)
- [Brokerage Integration](brokerage.md)
- [Cashflows & Financial Calculations](cashflows.md)
