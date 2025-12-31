# Cryptocurrency Market Data Integration

fin-infra provides unified access to cryptocurrency market data through multiple providers, with consistent data models and zero-configuration setup.

## Supported Providers

### Cryptocurrency Data
- **CoinGecko** (default): Free API with no key required, 10-30 req/min
- **CCXT**: Multi-exchange support (Coming soon)
- **CryptoCompare**: Professional-grade data (Coming soon)

## Quick Start

### Zero-Config Setup
```python
from fin_infra.crypto import easy_crypto

# No API key required for CoinGecko free tier!
crypto = easy_crypto()

# Get real-time ticker
ticker = crypto.ticker("BTC/USDT")
print(f"{ticker.symbol}: ${ticker.price}")

# Get OHLCV candles
candles = crypto.ohlcv("ETH/USDT", timeframe="1h", limit=24)
for candle in candles:
    print(f"{candle.ts}: ${candle.close}")
```

### Explicit Provider
```python
# Specify provider explicitly
crypto = easy_crypto(provider="coingecko")
```

## Core Operations

### 1. Get Ticker (Current Price)
```python
from fin_infra.crypto import easy_crypto

crypto = easy_crypto()

# Single ticker
ticker = crypto.ticker("BTC/USDT")

print(f"Symbol: {ticker.symbol}")
print(f"Price: ${ticker.price}")
print(f"Timestamp: {ticker.as_of}")
```

**Supported Symbol Formats:**
- `"BTC/USDT"` - Standard format
- `"BTC-USDT"` - Alternative format (automatically converted)
- `"ETH/USD"` - Works with any quote currency

### 2. Get OHLCV Candles
```python
# Hourly candles
candles = crypto.ohlcv("BTC/USDT", timeframe="1h", limit=24)

# Daily candles
candles = crypto.ohlcv("ETH/USD", timeframe="1d", limit=30)

# Process candles
for candle in candles:
    print(f"{candle.ts}: O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} V:{candle.volume}")
```

**Supported Timeframes:**
- `"1m"` - 1 minute
- `"5m"` - 5 minutes
- `"15m"` - 15 minutes
- `"30m"` - 30 minutes
- `"1h"` - 1 hour
- `"4h"` - 4 hours
- `"1d"` - 1 day (default)
- `"1w"` - 1 week

## Data Models

### Quote (Ticker)
```python
from fin_infra.models import Quote

ticker = Quote(
    symbol="BTC/USDT",
    price=Decimal("45000.00"),
    as_of=datetime.now(timezone.utc)
)
```

### Candle (OHLCV)
```python
from fin_infra.models import Candle

candle = Candle(
    ts=1704067200000,  # Unix timestamp in milliseconds
    open=Decimal("45000.00"),
    high=Decimal("46000.00"),
    low=Decimal("44500.00"),
    close=Decimal("45800.00"),
    volume=Decimal("1234.56")
)
```

## FastAPI Integration

### Easy Add Crypto Data (One-Liner Setup)
```python
from fin_infra.crypto import add_crypto_data

# [OK] Mount complete crypto API with one call
crypto_provider = add_crypto_data(
    app,
    provider="coingecko",  # optional, defaults to coingecko
    prefix="/crypto"       # default: "/crypto"
)

# Auto-generated routes (using svc-infra dual routers):
# GET  /crypto/ticker/{symbol}     - Get real-time ticker for a crypto pair
# GET  /crypto/ohlcv/{symbol}      - Get OHLCV candles with timeframe and limit

# Landing page card automatically registered at /crypto/docs
# OpenAPI schema available at /crypto/openapi.json
```

**What `add_crypto_data()` Does:**
- [OK] Initializes crypto provider (CoinGecko) with environment config
- [OK] Mounts 2 crypto endpoints with proper request/response models
- [OK] Uses `public_router()` from svc-infra (public crypto data, no auth)
- [OK] Registers landing page documentation card
- [OK] Stores provider instance on `app.state.crypto_provider`
- [OK] Returns provider for programmatic access
- [OK] Handles provider errors with proper HTTP status codes

### Basic Setup (Using svc-infra)
```python
from fastapi import FastAPI, HTTPException
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.cache import init_cache
from fin_infra.crypto import easy_crypto

# Backend from svc-infra
app = easy_service_app(name="CryptoAPI", release="production")
init_cache(url="redis://localhost")

# Financial provider from fin-infra
crypto = easy_crypto()

@app.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    """Fetch real-time crypto ticker"""
    try:
        ticker = crypto.ticker(symbol)
        return {
            "symbol": ticker.symbol,
            "price": float(ticker.price),
            "timestamp": ticker.as_of.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/ohlcv/{symbol}")
async def get_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Fetch OHLCV candles"""
    candles = crypto.ohlcv(symbol, timeframe=timeframe, limit=limit)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": [
            {
                "timestamp": c.ts,
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
crypto_cache = resource("crypto", "symbol")

@app.get("/ticker/{symbol}")
@crypto_cache.cache_read(ttl=60, suffix="ticker")  # 60s cache
async def get_ticker_cached(symbol: str):
    """Cached ticker fetch (60s TTL)"""
    ticker = crypto.ticker(symbol)
    return {"symbol": ticker.symbol, "price": float(ticker.price)}

@app.get("/ohlcv/{symbol}")
@crypto_cache.cache_read(ttl=300, suffix="ohlcv")  # 5 min cache
async def get_ohlcv_cached(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Cached OHLCV fetch (5min TTL)"""
    candles = crypto.ohlcv(symbol, timeframe=timeframe, limit=limit)
    return {"symbol": symbol, "count": len(candles)}
```

## Integration Examples

### Complete Production App (fin-infra + svc-infra)
```python
from fastapi import FastAPI, HTTPException, Query
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.logging import setup_logging
from svc_infra.cache import init_cache, resource
from svc_infra.obs import add_observability
from fin_infra.crypto import add_crypto_data, easy_crypto

# 1. Setup logging (svc-infra)
setup_logging(level="INFO", fmt="json")

# 2. Create service app (svc-infra)
app = easy_service_app(
    name="CryptoDataAPI",
    release="production",
    api_version="v1"
)

# 3. Initialize cache (svc-infra)
init_cache(url="redis://localhost:6379", prefix="cryptoapi", version="v1")

# 4. Add observability (svc-infra)
shutdown_obs = add_observability(
    app,
    metrics_path="/metrics",
    skip_metric_paths=["/health", "/metrics"]
)

# 5. Add crypto data (fin-infra) - One-liner!
crypto_provider = add_crypto_data(app, provider="coingecko", prefix="/crypto")

# 6. Custom cached routes using crypto provider
crypto_cache = resource("crypto", "symbol")

@app.get("/portfolio/crypto")
@crypto_cache.cache_read(ttl=30, suffix="portfolio")  # 30s cache
async def crypto_portfolio(symbols: str = Query(..., description="Comma-separated")):
    """Calculate crypto portfolio value (cached 30s)"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    total_value = 0
    tickers = []

    for symbol in symbol_list:
        try:
            # Normalize symbol format (add /USDT if no quote currency)
            if "/" not in symbol and "-" not in symbol:
                symbol = f"{symbol}/USDT"

            ticker = crypto_provider.ticker(symbol)
            tickers.append({
                "symbol": ticker.symbol,
                "price": float(ticker.price),
            })
            total_value += float(ticker.price)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching {symbol}: {str(e)}")

    return {
        "symbols": symbol_list,
        "tickers": tickers,
        "total_value_usdt": total_value
    }

@app.get("/alerts/price")
async def price_alert(symbol: str, target_price: float):
    """Check if crypto reached target price"""
    ticker = crypto_provider.ticker(symbol)
    current_price = float(ticker.price)

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
# No API key required for CoinGecko!
export REDIS_URL="redis://localhost:6379"

# Start server
uvicorn main:app --reload

# API available at:
# - Docs: http://localhost:8000/docs
# - Crypto card: http://localhost:8000/crypto/docs
# - Crypto endpoints: http://localhost:8000/crypto/*
# - Custom endpoints: http://localhost:8000/portfolio/crypto?symbols=BTC,ETH,SOL
```

### Minimal Example (Just Crypto Data)
```python
from fastapi import FastAPI
from fin_infra.crypto import add_crypto_data

app = FastAPI(title="Crypto Data API")

# One-liner setup - NO API KEY REQUIRED!
add_crypto_data(app, provider="coingecko")

# That's it! 2 endpoints ready to use:
# GET /crypto/ticker/{symbol}
# GET /crypto/ohlcv/{symbol}?timeframe=1h&limit=100
```

### Programmatic Usage (No FastAPI)
```python
from fin_infra.crypto import easy_crypto

# Initialize provider (no API key needed!)
crypto = easy_crypto()

# Use directly in scripts, background jobs, CLI tools
symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]

for symbol in symbols:
    ticker = crypto.ticker(symbol)
    print(f"{symbol}: ${ticker.price:.2f}")

# Historical analysis
candles = crypto.ohlcv("BTC/USDT", timeframe="1h", limit=24)
print(f"24h high: ${max(float(c.high) for c in candles):.2f}")
print(f"24h low: ${min(float(c.low) for c in candles):.2f}")
print(f"24h change: ${float(candles[-1].close - candles[0].open):.2f}")
```

### With Background Jobs (svc-infra)
```python
from svc_infra.jobs.easy import easy_jobs
from fin_infra.crypto import easy_crypto

# Setup jobs (svc-infra)
worker, scheduler = easy_jobs(app, redis_url="redis://localhost:6379")

# Crypto provider
crypto = easy_crypto()

@worker.task
async def update_crypto_data(symbols: list[str]):
    """Background job to update crypto data"""
    tickers = []
    for symbol in symbols:
        try:
            ticker = crypto.ticker(symbol)
            tickers.append({
                "symbol": ticker.symbol,
                "price": float(ticker.price),
                "timestamp": ticker.as_of
            })
            # Store in database
            await db.save_ticker(ticker)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    return {"updated": len(tickers), "tickers": tickers}

# Schedule updates every minute (crypto markets 24/7)
@scheduler.scheduled_job("interval", minutes=1)
async def frequent_update():
    """Update crypto data every minute"""
    watchlist = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]
    await update_crypto_data.kiq(watchlist)

# Hourly OHLCV snapshot
@scheduler.scheduled_job("cron", minute=0)  # Every hour
async def hourly_candles():
    """Store hourly candles for trend analysis"""
    symbols = await db.get_all_tracked_crypto()

    for symbol in symbols:
        candles = crypto.ohlcv(symbol, timeframe="1h", limit=1)
        if candles:
            await db.save_candle(symbol, candles[0])
```

## Rate Limiting & Caching

### CoinGecko Free Tier Limits
- **Rate Limit**: 10-30 requests per minute
- **No API Key**: Required for free tier
- **Data Delay**: Real-time for most endpoints

### Recommended Caching Strategy
```python
from svc_infra.cache import init_cache, resource

# Initialize cache
init_cache(url="redis://localhost:6379", prefix="crypto", version="v1")

# Define caching strategy
crypto_cache = resource("crypto", "symbol")

# Ticker: 60s TTL (crypto markets move fast)
@crypto_cache.cache_read(ttl=60, suffix="ticker")
def get_ticker(symbol: str):
    return crypto.ticker(symbol)

# OHLCV: 5min TTL (historical data changes less frequently)
@crypto_cache.cache_read(ttl=300, suffix="ohlcv")
def get_ohlcv(symbol: str, timeframe: str, limit: int):
    return crypto.ohlcv(symbol, timeframe=timeframe, limit=limit)
```

## Error Handling

### Common Errors
```python
from fin_infra.crypto import easy_crypto

crypto = easy_crypto()

try:
    ticker = crypto.ticker("INVALID/SYMBOL")
except Exception as e:
    print(f"Error: {e}")
    # Handle: symbol not found, network error, rate limit, etc.
```

### Production Error Handling
```python
from fastapi import HTTPException
from fin_infra.crypto import easy_crypto

crypto = easy_crypto()

@app.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    try:
        ticker = crypto.ticker(symbol)
        return {"symbol": ticker.symbol, "price": float(ticker.price)}
    except ValueError as e:
        # Invalid symbol format
        raise HTTPException(status_code=400, detail=f"Invalid symbol: {str(e)}")
    except Exception as e:
        # Network or provider error
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
```

## Best Practices

1. **Caching**: Always enable caching to respect rate limits (60s for tickers, 5min for OHLCV)
2. **Symbol Normalization**: Support both `/` and `-` separators (e.g., "BTC/USDT" or "BTC-USDT")
3. **Rate Limiting**: Don't exceed 10-30 req/min for CoinGecko free tier
4. **Error Handling**: Handle network errors, invalid symbols, and rate limits gracefully
5. **24/7 Markets**: Crypto markets never close - design accordingly
6. **Timeframes**: Use appropriate timeframes (1h for day trading, 1d for longer analysis)

## Testing

```python
import pytest
from fin_infra.crypto import easy_crypto

def test_get_ticker():
    crypto = easy_crypto()
    ticker = crypto.ticker("BTC/USDT")

    assert ticker.symbol == "BTC/USDT"
    assert ticker.price > 0

@pytest.mark.acceptance
def test_real_crypto_data():
    crypto = easy_crypto()
    ticker = crypto.ticker("BTC/USDT")

    # Test against real API
    assert ticker is not None
    assert ticker.price > 1000  # BTC should be > $1000
```

## Provider Comparison

| Provider | API Key | Rate Limit | Data Delay | Multi-Exchange |
|----------|---------|------------|------------|----------------|
| CoinGecko | No | 10-30 req/min | Real-time | No |
| CCXT | Varies | Varies | Real-time | Yes (50+ exchanges) |
| CryptoCompare | Yes | 100 req/hour (free) | Real-time | Yes |

## Real-Time vs Delayed Data

### CoinGecko (Default)
- **Ticker data**: Real-time aggregated across exchanges
- **OHLCV candles**: Real-time for most pairs
- **Best for**: Portfolio tracking, price alerts, general market data

### Future: CCXT Integration
- **Direct exchange data**: Real-time from specific exchanges
- **Trading data**: Orderbook depth, recent trades
- **Best for**: Trading bots, arbitrage, exchange-specific strategies

## Next Steps

- [Banking Integration](banking.md) - Connect bank accounts
- [Market Data (Equities)](market-data.md) - Stock market data
- [Brokerage Integration](brokerage.md) - Trade execution
- [Cashflows & Calculations](cashflows.md) - Financial calculations
