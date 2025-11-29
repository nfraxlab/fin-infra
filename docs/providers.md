# Provider System

fin-infra uses a **provider registry** for dynamic loading and configuration of financial data providers. This allows you to switch between providers (e.g., Plaid vs Teller for banking) without changing your code.

## Quick Start

### Using the Registry

```python
from fin_infra.providers import resolve

# Load default banking provider (Plaid)
banking = resolve("banking")

# Load specific provider
banking = resolve("banking", "teller", api_key="your_key")

# Load market data provider
market = resolve("market", "alphavantage", api_key="your_key")

# Load crypto provider (CoinGecko doesn't need API key)
crypto = resolve("crypto", "coingecko")
```

### Listing Available Providers

```python
from fin_infra.providers import list_providers

# List all providers
all_providers = list_providers()
# ['banking:plaid', 'banking:teller', 'market:alphavantage', ...]

# List providers for a domain
banking_providers = list_providers(domain="banking")
# ['banking:plaid', 'banking:teller', 'banking:mx']

market_providers = list_providers(domain="market")
# ['market:alphavantage', 'market:yahoo', 'market:polygon']
```

## Available Providers

### Banking Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **Plaid** | `banking:plaid` | Account aggregation, transactions, identity | Sandbox only |
| **Teller** | `banking:teller` | Bank connections, transactions | Limited |
| **MX** | `banking:mx` | Account aggregation, statements | Sandbox |

**Default**: `plaid`

```python
# Use default
banking = resolve("banking")

# Or specify explicitly
banking = resolve("banking", "plaid", client_id="...", secret="...")
banking = resolve("banking", "teller", api_key="...")
```

### Market Data Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **Alpha Vantage** | `market:alphavantage` | Stocks, quotes, candles | 5 req/min, 500/day |
| **Yahoo Finance** | `market:yahoo` | Stocks, indices, ETFs | Unlimited (no key) |
| **Polygon** | `market:polygon` | Real-time data, options | Limited |

**Default**: `alphavantage`

```python
# Alpha Vantage (needs API key)
market = resolve("market", "alphavantage", api_key="...")

# Yahoo Finance (free, no API key)
market = resolve("market", "yahoo")
```

### Crypto Data Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **CoinGecko** | `crypto:coingecko` | Prices, market data | 10-30 req/min |
| **CCXT** | `crypto:ccxt` | Multi-exchange support | Varies by exchange |
| **CryptoCompare** | `crypto:cryptocompare` | Historical data | Limited |

**Default**: `coingecko`

```python
# CoinGecko (no API key needed)
crypto = resolve("crypto", "coingecko")

# CCXT for exchange-specific data
crypto = resolve("crypto", "ccxt", exchange="binance")
```

### Brokerage Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **Alpaca** | `brokerage:alpaca` | Paper/live trading, US stocks | Paper trading free |
| **Interactive Brokers** | `brokerage:ib` | Global markets, options | Paid |
| **TD Ameritrade** | `brokerage:tdameritrade` | US stocks, options | Varies |

**Default**: `alpaca`

```python
# Alpaca paper trading
brokerage = resolve("brokerage", "alpaca", 
                   api_key="...", 
                   api_secret="...",
                   paper=True)  # Safe default
```

### Credit Score Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **Experian** | `credit:experian` | Credit scores, reports | Sandbox |
| **Equifax** | `credit:equifax` | Credit monitoring | Sandbox |
| **TransUnion** | `credit:transunion` | Credit reports | Sandbox |

**Default**: `experian`

```python
credit = resolve("credit", "experian", api_key="...")
```

### Identity Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **Stripe Identity** | `identity:stripe` | KYC verification | Limited |

**Default**: `stripe`

```python
identity = resolve("identity", "stripe", api_key="...")
```

### Tax Data Providers

| Provider | Key | Features | Free Tier |
|----------|-----|----------|-----------|
| **TaxBit** | `tax:taxbit` | Crypto tax reporting | Limited |
| **IRS** | `tax:irs` | Tax transcript retrieval | Free |

**Default**: `taxbit`

```python
tax = resolve("tax", "taxbit", api_key="...")
```

## Provider Interfaces

All providers implement domain-specific ABCs:

### BankingProvider

```python
from fin_infra.providers import BankingProvider

class BankingProvider(ABC):
    @abstractmethod
    def create_link_token(self, user_id: str) -> str: ...
    
    @abstractmethod
    def exchange_public_token(self, public_token: str) -> dict: ...
    
    @abstractmethod
    def accounts(self, access_token: str) -> list[dict]: ...
```

### MarketDataProvider

```python
from fin_infra.providers import MarketDataProvider

class MarketDataProvider(ABC):
    @abstractmethod
    def quote(self, symbol: str) -> Quote: ...
    
    @abstractmethod
    def history(self, symbol: str, *, period: str = "1mo", interval: str = "1d") -> Sequence[Candle]: ...
```

### CryptoDataProvider

```python
from fin_infra.providers import CryptoDataProvider

class CryptoDataProvider(ABC):
    @abstractmethod
    def ticker(self, symbol_pair: str) -> Quote: ...
    
    @abstractmethod
    def ohlcv(self, symbol_pair: str, timeframe: str = "1d", limit: int = 100) -> Sequence[Candle]: ...
```

### BrokerageProvider

```python
from fin_infra.providers import BrokerageProvider

class BrokerageProvider(ABC):
    @abstractmethod
    def submit_order(self, symbol: str, qty: float, side: str, type_: str, time_in_force: str) -> dict: ...
    
    @abstractmethod
    def positions(self) -> Iterable[dict]: ...
```

### CreditProvider

```python
from fin_infra.providers import CreditProvider

class CreditProvider(ABC):
    @abstractmethod
    def get_credit_score(self, user_id: str, **kwargs) -> dict | None: ...
```

### TaxProvider

```python
from fin_infra.providers import TaxProvider

class TaxProvider(ABC):
    @abstractmethod
    def get_tax_forms(self, user_id: str, tax_year: int, **kwargs) -> list[dict]: ...
    
    @abstractmethod
    def get_tax_document(self, document_id: str, **kwargs) -> dict: ...
    
    @abstractmethod
    def calculate_crypto_gains(self, transactions: list[dict], **kwargs) -> dict: ...
```

## Advanced Usage

### Custom Provider Configuration

```python
from fin_infra.providers import ProviderRegistry

# Create custom registry
registry = ProviderRegistry()

# Resolve with custom config
banking = registry.resolve(
    "banking",
    "plaid",
    client_id="your_id",
    secret="your_secret",
    environment="sandbox"
)

# Cache is automatic - second call reuses instance
banking2 = registry.resolve("banking", "plaid")
assert banking is banking2  # Same instance

# Clear cache if needed
registry.clear_cache()
```

### Environment Variables

Providers automatically read from environment variables:

```bash
# Banking
export PLAID_CLIENT_ID=your_client_id
export PLAID_SECRET=your_secret
export PLAID_ENV=sandbox

# Market data
export ALPHAVANTAGE_API_KEY=your_key

# Brokerage
export ALPACA_API_KEY=your_key
export ALPACA_API_SECRET=your_secret
export ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

Then use without explicit config:

```python
from fin_infra.settings import get_settings

settings = get_settings()
banking = resolve("banking", "plaid", 
                 client_id=settings.plaid_client_id,
                 secret=settings.plaid_secret)
```

### Provider Switching

Switch providers dynamically (e.g., for A/B testing, failover):

```python
def get_market_provider(feature_flags: dict):
    """Select provider based on feature flags."""
    provider_name = feature_flags.get("market_provider", "alphavantage")
    return resolve("market", provider_name)

# Production
market = get_market_provider({"market_provider": "polygon"})

# Fallback to free tier
market = get_market_provider({"market_provider": "yahoo"})
```

### Error Handling

```python
from fin_infra.providers import ProviderNotFoundError, resolve

try:
    provider = resolve("banking", "unknown_provider")
except ProviderNotFoundError as e:
    print(f"Provider not found: {e}")
    # Fallback to default
    provider = resolve("banking")
```

## Integration with Easy Builders

The registry powers all `easy_*()` functions:

```python
# These use the registry internally:
from fin_infra.banking import easy_banking
from fin_infra.markets import easy_market

banking = easy_banking(provider="plaid")
# Equivalent to: resolve("banking", "plaid")

market = easy_market(provider="alphavantage")
# Equivalent to: resolve("market", "alphavantage")
```

## Best Practices

1. **Use defaults for development**: `resolve("banking")` uses sensible defaults
2. **Explicit in production**: `resolve("banking", "plaid", client_id=..., secret=...)`
3. **Environment variables**: Store credentials in env vars, not code
4. **Provider switching**: Use feature flags to switch providers without deployment
5. **Error handling**: Always catch `ProviderNotFoundError` for robustness
6. **Caching**: Registry caches instances automatically for performance

## Next Steps

- **Banking**: [banking.md](banking.md) for account aggregation
- **Market Data**: [market-data.md](market-data.md) for stock quotes
- **Credit**: [credit.md](credit.md) for credit scores
