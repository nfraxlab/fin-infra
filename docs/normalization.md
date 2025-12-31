# Data Normalization & Symbol Resolution

**Status**: Production Ready  
**Category**: Financial Data Integration  
**Dependencies**: svc-infra (cache, http)

---

## Overview

The normalization module provides **symbol resolution** and **currency conversion** for financial applications. Convert between ticker formats (AAPL → CUSIP → ISIN), normalize provider-specific symbols, and handle multi-currency portfolios.

### What It Does

- **Symbol Resolution**: Ticker <-> CUSIP <-> ISIN conversions
- **Provider Normalization**: Yahoo's `BTC-USD` → CoinGecko's `bitcoin` → Alpaca's `BTCUSD` → `BTC`
- **Currency Conversion**: USD → EUR with live exchange rates
- **Metadata Enrichment**: Ticker → company name, sector, exchange
- **Batch Operations**: Resolve multiple symbols efficiently

###Quick Start

```python
from fin_infra.normalization import easy_normalization

# One-liner setup
resolver, converter = easy_normalization()

# Convert between identifier types
ticker = await resolver.to_ticker("037833100")  # CUSIP → AAPL
cusip = await resolver.to_cusip("AAPL")        # AAPL → 037833100
isin = await resolver.to_isin("AAPL")          # AAPL → US0378331005

# Normalize provider symbols
btc = await resolver.normalize("BTC-USD", "yahoo")      # → BTC
btc = await resolver.normalize("bitcoin", "coingecko")  # → BTC
btc = await resolver.normalize("BTCUSD", "alpaca")      # → BTC

# Currency conversion
eur = await converter.convert(100, "USD", "EUR")  # → 92.0
rate = await converter.get_rate("USD", "EUR")     # → 0.92
```

### Key Use Cases

1. **Multi-Provider Portfolios**: Aggregate positions from different brokerages with consistent symbols
2. **Global Finance Apps**: Support portfolios with mixed currencies (USD, EUR, GBP, etc.)
3. **Compliance Reporting**: Convert tickers to CUSIPs/ISINs for regulatory filings
4. **Data Integration**: Normalize symbols when pulling from multiple market data providers
5. **Backtesting**: Use historical exchange rates for portfolio analysis

---

## Symbol Resolution

### Convert Between Identifier Types

```python
from fin_infra.normalization import easy_normalization

resolver, _ = easy_normalization()

# Ticker → CUSIP
cusip = await resolver.to_cusip("AAPL")
# → "037833100"

# Ticker → ISIN
isin = await resolver.to_isin("TSLA")
# → "US88160R1014"

# CUSIP → Ticker
ticker = await resolver.to_ticker("037833100")
# → "AAPL"

# ISIN → Ticker
ticker = await resolver.to_ticker("US88160R1014")
# → "TSLA"

# Exchange-qualified symbols
ticker = await resolver.to_ticker("NASDAQ:AAPL")
# → "AAPL"
```

### Provider Symbol Normalization

Different providers use different symbol formats. The resolver normalizes them:

```python
# Yahoo Finance: Uses dashes for crypto
yahoo_btc = await resolver.normalize("BTC-USD", "yahoo")
# → "BTC"

# CoinGecko: Uses full names
coingecko_btc = await resolver.normalize("bitcoin", "coingecko")
# → "BTC"

# Alpaca: No separators
alpaca_btc = await resolver.normalize("BTCUSD", "alpaca")
# → "BTC"

# All normalize to the same standard ticker: BTC
```

### Supported Providers

| Provider | Symbol Format | Example | Normalized |
|----------|---------------|---------|------------|
| **Yahoo Finance** | Ticker with dashes | `BTC-USD`, `ETH-USD` | `BTC`, `ETH` |
| **CoinGecko** | Full names (lowercase) | `bitcoin`, `ethereum` | `BTC`, `ETH` |
| **Alpaca** | No separators | `BTCUSD`, `ETHUSD` | `BTC`, `ETH` |
| **Alpha Vantage** | Standard tickers | `AAPL`, `TSLA` | `AAPL`, `TSLA` |
| **Plaid** | Account IDs (pass-through) | N/A | N/A |

### Get Company Metadata

```python
metadata = await resolver.get_metadata("AAPL")

print(metadata.ticker)      # "AAPL"
print(metadata.name)        # "Apple Inc."
print(metadata.exchange)    # "NASDAQ"
print(metadata.cusip)       # "037833100"
print(metadata.isin)        # "US0378331005"
print(metadata.sector)      # "Technology"
print(metadata.industry)    # "Consumer Electronics"
print(metadata.asset_type)  # "stock"
```

### Batch Resolution

Resolve multiple symbols in one call:

```python
symbols = ["037833100", "US88160R1014", "AAPL", "NASDAQ:GOOGL"]
results = await resolver.resolve_batch(symbols)

print(results)
# {
#     "037833100": "AAPL",
#     "US88160R1014": "TSLA",
#     "AAPL": "AAPL",
#     "NASDAQ:GOOGL": "GOOGL"
# }
```

### Custom Symbol Mappings

Add custom symbols not in the pre-cached list:

```python
resolver.add_mapping(
    ticker="CUSTOM",
    cusip="999999999",
    isin="US9999999999",
    metadata={
        "name": "Custom Company Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "asset_type": "stock"
    }
)

# Now resolves like any other symbol
cusip = await resolver.to_cusip("CUSTOM")
# → "999999999"
```

---

## Currency Conversion

### Basic Conversion

```python
from fin_infra.normalization import easy_normalization

_, converter = easy_normalization()

# Convert amount
eur = await converter.convert(100, "USD", "EUR")
# → 92.0 (live exchange rate)

# Get exchange rate only
rate = await converter.get_rate("USD", "EUR")
# → 0.92
```

### Detailed Conversion

Get conversion with full details:

```python
result = await converter.convert_with_details(100, "USD", "EUR")

print(result.amount)       # 100.0
print(result.from_currency) # "USD"
print(result.to_currency)  # "EUR"
print(result.converted)    # 92.0
print(result.rate)         # 0.92
print(result.date)         # None (current rate)
```

### Historical Rates

Get rates for a specific date (paid tier required):

```python
from datetime import date

# Historical rate
historical_rate = await converter.get_rate(
    "USD",
    "EUR",
    date=date(2023, 1, 1)
)

# Convert with historical rate
historical_eur = await converter.convert(
    100,
    "USD",
    "EUR",
    date=date(2023, 1, 1)
)
```

### All Rates for a Currency

Get all exchange rates at once:

```python
rates = await converter.get_rates("USD")

print(rates["EUR"])  # 0.92
print(rates["GBP"])  # 0.79
print(rates["JPY"])  # 149.50
print(rates["CAD"])  # 1.35
# ... 160+ currencies
```

### Batch Conversion

Convert multiple amounts to a single target currency:

```python
amounts = {
    "USD": 100.0,
    "EUR": 90.0,
    "GBP": 80.0,
    "JPY": 15000.0
}

# Convert all to USD
usd_amounts = await converter.batch_convert(amounts, "USD")

print(usd_amounts)
# {
#     "USD": 100.0,
#     "EUR": 97.8,
#     "GBP": 101.3,
#     "JPY": 100.3
# }

total_usd = sum(usd_amounts.values())
# → 399.4 USD
```

### Supported Currencies

160+ currencies including:
- **Major Fiat**: USD, EUR, GBP, JPY, CAD, AUD, CHF, CNY
- **Crypto**: BTC, ETH, BNB, XRP, ADA, DOGE, SOL
- **Emerging**: INR, BRL, MXN, ZAR, TRY

```python
currencies = await converter.supported_currencies()
print(len(currencies))  # 160+
print("BTC" in currencies)  # True
print("ETH" in currencies)  # True
```

---

## Integration Examples

### Multi-Provider Portfolio Aggregation

```python
from fin_infra.brokerage import easy_brokerage
from fin_infra.markets import easy_market
from fin_infra.normalization import easy_normalization

resolver, converter = easy_normalization()

# Get positions from brokerage
brokerage = easy_brokerage(mode="paper")
positions = await brokerage.positions()

total_value_usd = 0.0
portfolio_summary = []

for position in positions:
    # Normalize symbol to standard ticker
    ticker = await resolver.normalize(position.symbol, provider="alpaca")

    # Get current quote
    market = easy_market()
    quote = market.quote(ticker)

    # Convert to USD if needed
    if position.currency != "USD":
        value_usd = await converter.convert(
            position.market_value,
            position.currency,
            "USD"
        )
    else:
        value_usd = position.market_value

    total_value_usd += value_usd

    portfolio_summary.append({
        "ticker": ticker,
        "shares": position.qty,
        "price": quote.price,
        "value_usd": value_usd,
    })

print(f"Total Portfolio Value: ${total_value_usd:,.2f} USD")
for item in portfolio_summary:
    print(f"  {item['ticker']}: {item['shares']} shares @ ${item['price']} = ${item['value_usd']:,.2f}")
```

### Symbol Lookup API

```python
from fastapi import FastAPI, HTTPException
from fin_infra.normalization import easy_normalization, SymbolNotFoundError

app = FastAPI()
resolver, converter = easy_normalization()

@app.get("/symbols/{identifier}")
async def resolve_symbol(identifier: str):
    """Resolve any identifier to full symbol information."""
    try:
        ticker = await resolver.to_ticker(identifier)
        metadata = await resolver.get_metadata(ticker)

        try:
            cusip = await resolver.to_cusip(ticker)
        except SymbolNotFoundError:
            cusip = None

        try:
            isin = await resolver.to_isin(ticker)
        except SymbolNotFoundError:
            isin = None

        return {
            "input": identifier,
            "ticker": ticker,
            "cusip": cusip,
            "isin": isin,
            "name": metadata.name,
            "exchange": metadata.exchange,
            "sector": metadata.sector,
            "asset_type": metadata.asset_type,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/currencies/convert")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str
):
    """Convert amount between currencies."""
    result = await converter.convert_with_details(
        amount, from_currency, to_currency
    )
    return {
        "amount": result.amount,
        "from": result.from_currency,
        "to": result.to_currency,
        "rate": result.rate,
        "converted": result.converted,
    }
```

### Historical Backtesting

```python
from datetime import date
from fin_infra.markets import easy_market
from fin_infra.normalization import easy_normalization

resolver, converter = easy_normalization()
market = easy_market()

# Portfolio on Jan 1, 2023
portfolio = [
    {"ticker": "AAPL", "shares": 100},
    {"ticker": "TSLA", "shares": 50},
    {"ticker": "GOOGL", "shares": 25},
]

# Calculate value in EUR on that date
backtest_date = date(2023, 1, 1)
total_eur = 0.0

for holding in portfolio:
    # Get historical price (simplified - would use historical API)
    quote = market.quote(holding["ticker"])
    value_usd = quote.price * holding["shares"]

    # Convert to EUR using historical rate
    value_eur = await converter.convert(
        value_usd,
        "USD",
        "EUR",
        date=backtest_date
    )
    total_eur += value_eur

    print(f"{holding['ticker']}: €{value_eur:,.2f}")

print(f"\nTotal Portfolio Value (Jan 1, 2023): €{total_eur:,.2f}")
```

### Cross-Provider Symbol Resolution

```python
from fin_infra.markets import easy_market
from fin_infra.crypto import easy_crypto
from fin_infra.normalization import easy_normalization

resolver, _ = easy_normalization()

# Get BTC price from multiple providers
yahoo_symbol = "BTC-USD"      # Yahoo Finance format
coingecko_symbol = "bitcoin"  # CoinGecko format

# Normalize both to standard ticker
yahoo_ticker = await resolver.normalize(yahoo_symbol, "yahoo")
coingecko_ticker = await resolver.normalize(coingecko_symbol, "coingecko")

# Both resolve to "BTC"
assert yahoo_ticker == coingecko_ticker == "BTC"

# Now fetch from both providers with normalized symbol
market = easy_market(provider="yahoo")
crypto = easy_crypto(provider="coingecko")

yahoo_price = market.quote(yahoo_symbol).price
coingecko_price = crypto.ticker(coingecko_symbol)["price"]

print(f"BTC Price (Yahoo): ${yahoo_price:,.2f}")
print(f"BTC Price (CoinGecko): ${coingecko_price:,.2f}")
```

---

## Configuration

### Environment Variables

```bash
# Currency conversion API key (optional, increases rate limit)
EXCHANGE_RATE_API_KEY=your_key_here

# Symbol resolution (future: OpenFIGI API for more symbols)
# OPENFIGI_API_KEY=your_key_here  # Coming soon
```

### API Rate Limits

**exchangerate-api.io** (currency conversion):
- **Free tier**: 1,500 requests/month (no API key required)
- **Paid tier**: $10/month for 100,000 requests

**Static mappings** (pre-cached):
- Top 50 US stocks by market cap
- Common crypto symbols (BTC, ETH, etc.)
- No API calls needed for cached symbols

### Caching with svc-infra

Integrate with svc-infra cache for better performance:

```python
from svc_infra.cache import init_cache, cache_read
from fin_infra.normalization import easy_normalization

# Initialize svc-infra cache
init_cache(url="redis://localhost", prefix="fin", version="v1")

resolver, converter = easy_normalization()

# Cache symbol resolutions (24 hours)
@cache_read(key="symbol:cusip:{cusip}", ttl=86400)
async def cached_cusip_to_ticker(cusip: str) -> str:
    return await resolver.to_ticker(cusip)

# Cache exchange rates (5 minutes)
@cache_read(key="fx:{from_currency}:{to_currency}", ttl=300)
async def cached_exchange_rate(from_currency: str, to_currency: str) -> float:
    return await converter.get_rate(from_currency, to_currency)
```

---

## Error Handling

### Symbol Resolution Errors

```python
from fin_infra.normalization import SymbolNotFoundError

try:
    cusip = await resolver.to_cusip("UNKNOWN")
except SymbolNotFoundError as e:
    print(f"Symbol not found: {e}")
    # Fallback: use original symbol
    cusip = "UNKNOWN"
```

### Currency Conversion Errors

```python
from fin_infra.normalization import CurrencyNotSupportedError
from fin_infra.normalization.providers.exchangerate import ExchangeRateAPIError

try:
    result = await converter.convert(100, "USD", "EUR")
except CurrencyNotSupportedError:
    print("Currency not supported")
except ExchangeRateAPIError as e:
    print(f"API error: {e}")
    # Fallback: use cached rate or return original amount
```

### Graceful Degradation

```python
async def safe_convert(amount, from_curr, to_curr):
    """Convert with fallback to original amount on error."""
    try:
        return await converter.convert(amount, from_curr, to_curr)
    except (CurrencyNotSupportedError, ExchangeRateAPIError) as e:
        logger.warning(f"Conversion failed, returning original: {e}")
        return amount  # Return original on error
```

---

## Best Practices

### [OK] DO

- **Use easy_normalization() once**: It returns singletons, reuse them throughout your app
- **Cache exchange rates**: Use svc-infra cache (TTL: 5-15 minutes)
- **Cache symbol mappings**: Use svc-infra cache (TTL: 24 hours)
- **Batch operations**: Use `resolve_batch()` and `batch_convert()` for efficiency
- **Handle errors gracefully**: Provide fallbacks for unknown symbols/currencies
- **Normalize early**: Convert provider symbols to standard tickers at ingestion
- **Use custom mappings**: Add symbols not in pre-cached list with `add_mapping()`

### [X] DON'T

- **Don't query APIs excessively**: Use caching to reduce API calls
- **Don't assume all symbols resolve**: Handle SymbolNotFoundError
- **Don't bypass normalization**: Always normalize provider-specific symbols
- **Don't forget rate limits**: Free tier is 1,500 requests/month
- **Don't cache rates too long**: Exchange rates change frequently (5-15 min TTL)
- **Don't cache symbols too short**: Symbol mappings rarely change (24 hour TTL)

---

## Related Documentation

- [Banking Provider Guide](./banking.md)
- [Market Data Guide](./market-data.md)
- [Crypto Data Guide](./crypto-data.md)
- [Brokerage Guide](./brokerage.md)
- [Caching & Rate Limits Guide](./caching-rate-limits-retries.md)
- [svc-infra Cache Documentation](../../../../svc-infra/src/svc_infra/cache/)

---

## API Reference

### SymbolResolver

| Method | Description | Example |
|--------|-------------|---------|
| `to_ticker(identifier)` | Convert any ID to ticker | `"037833100"` → `"AAPL"` |
| `to_cusip(ticker)` | Convert ticker to CUSIP | `"AAPL"` → `"037833100"` |
| `to_isin(ticker)` | Convert ticker to ISIN | `"AAPL"` → `"US0378331005"` |
| `normalize(symbol, provider)` | Normalize provider symbol | `("BTC-USD", "yahoo")` → `"BTC"` |
| `get_metadata(ticker)` | Get company metadata | `"AAPL"` → `SymbolMetadata(...)` |
| `resolve_batch(symbols)` | Batch resolve symbols | `["AAPL", "037833100"]` → `{...}` |
| `add_mapping(...)` | Add custom symbol | Manual symbol override |

### CurrencyConverter

| Method | Description | Example |
|--------|-------------|---------|
| `convert(amount, from, to)` | Convert amount | `(100, "USD", "EUR")` → `92.0` |
| `get_rate(from, to)` | Get exchange rate | `("USD", "EUR")` → `0.92` |
| `get_rates(base)` | Get all rates | `"USD"` → `{"EUR": 0.92, ...}` |
| `convert_with_details(...)` | Convert with metadata | Returns `CurrencyConversionResult` |
| `supported_currencies()` | List currencies | Returns `["USD", "EUR", ...]` |
| `batch_convert(amounts, to)` | Batch convert | `{...}` → `{...}` |

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Aliikhatami94/fin-infra/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Aliikhatami94/fin-infra/discussions)
- **Exchange Rate API**: [exchangerate-api.io](https://www.exchangerate-api.com/)
