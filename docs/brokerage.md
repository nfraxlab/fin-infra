# Brokerage Integration

fin-infra provides unified interfaces for connecting to brokerage accounts for automated trading, portfolio management, and position tracking. The brokerage integration supports **paper trading** (sandbox) and **live trading** with built-in safety mechanisms.

## [!] Important Disclaimers

**TRADING INVOLVES SUBSTANTIAL RISK**: This software is provided for educational and development purposes. Real trading involves risk of loss. Paper trading results DO NOT guarantee real trading success.

**PAPER TRADING FIRST**: Always test with paper trading before using live mode. fin-infra defaults to paper trading mode for safety.

**NOT FINANCIAL ADVICE**: This library does not provide investment advice. You are responsible for all trading decisions and their consequences.

**REGULATORY COMPLIANCE**: Ensure your trading application complies with all applicable regulations (SEC, FINRA, etc.) in your jurisdiction.

## Supported Providers

### Current
- **Alpaca** ([OK] Implemented)
  - Commission-free trading API
  - Full paper trading environment
  - Real-time market data
  - Order management (market, limit, stop, stop-limit)
  - Position tracking
  - Portfolio history

### Coming Soon
- **Interactive Brokers**: Institutional-grade API (research pending)
- **TD Ameritrade**: thinkorswim API (research pending)

## Quick Setup

### Zero-Config (Paper Trading)
```python
from fin_infra.brokerage import easy_brokerage

# Defaults to paper trading mode (safe for testing)
# Reads ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY from environment
brokerage = easy_brokerage()

# Verify it is in paper mode
print(f"Mode: {brokerage.mode}")  # Output: "paper"
```

### Explicit Configuration
```python
from fin_infra.brokerage import easy_brokerage

# Paper trading (explicit)
brokerage = easy_brokerage(
    provider="alpaca",
    mode="paper",
    api_key="YOUR_PAPER_API_KEY",
    api_secret="YOUR_PAPER_SECRET_KEY"
)

# Live trading (requires explicit mode="live")
# WARNING: This uses real money!
brokerage = easy_brokerage(
    provider="alpaca",
    mode="live",  # Must explicitly set to "live"
    api_key="YOUR_LIVE_API_KEY",
    api_secret="YOUR_LIVE_SECRET_KEY"
)
```

### Environment Variables
```bash
# Paper trading credentials (default)
export ALPACA_PAPER_API_KEY="your_paper_api_key"
export ALPACA_PAPER_SECRET_KEY="your_paper_secret_key"

# Live trading credentials (opt-in)
export ALPACA_LIVE_API_KEY="your_live_api_key"
export ALPACA_LIVE_SECRET_KEY="your_live_secret_key"
```

## FastAPI Integration

### Basic Setup
```python
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.logging import setup_logging
from fin_infra.brokerage import add_brokerage

# Setup backend (svc-infra)
setup_logging()
app = easy_service_app(name="TradingAPI")

# Wire brokerage provider (fin-infra)
# Defaults to paper trading mode
brokerage = add_brokerage(app)

# Routes automatically mounted at /brokerage/*
# - GET /brokerage/account
# - GET /brokerage/positions
# - GET /brokerage/positions/{symbol}
# - DELETE /brokerage/positions/{symbol}
# - POST /brokerage/orders
# - GET /brokerage/orders
# - GET /brokerage/orders/{order_id}
# - DELETE /brokerage/orders/{order_id}
# - GET /brokerage/portfolio/history
```

### Custom Prefix
```python
brokerage = add_brokerage(app, prefix="/api/v1/trading")

# Routes now at /api/v1/trading/*
```

### With Provider Instance
```python
from fin_infra.brokerage import easy_brokerage, add_brokerage

# Create provider with custom config
brokerage_provider = easy_brokerage(
    provider="alpaca",
    mode="paper",  # Always start with paper!
    timeout=30
)

# Wire to FastAPI
brokerage = add_brokerage(app, provider=brokerage_provider)
```

## Next Steps

- [Market Data Integration](market-data.md) - Get real-time quotes for trading decisions
- [Banking Integration](banking.md) - Link bank accounts for funding
- [Crypto Data Integration](crypto-data.md) - Trade cryptocurrencies

## Support & Resources

- **Alpaca Docs**: https://alpaca.markets/docs/
- **Paper Trading Signup**: https://alpaca.markets/docs/trading/paper-trading/
- **API Reference**: https://alpaca.markets/docs/api-references/trading-api/
- **Alpaca Community**: https://forum.alpaca.markets/

## Core Operations

### 1. Get Account Information
```python
# Get account details (buying power, equity, cash)
account = brokerage.get_account()

print(f"Account ID: {account['id']}")
print(f"Account Number: {account['account_number']}")
print(f"Status: {account['status']}")
print(f"Buying Power: ${account['buying_power']}")
print(f"Cash: ${account['cash']}")
print(f"Portfolio Value: ${account['portfolio_value']}")
print(f"Equity: ${account['equity']}")
print(f"Pattern Day Trader: {account['pattern_day_trader']}")
```

### 2. Submit Orders

#### Market Order (Buy)
```python
order = brokerage.submit_order(
    symbol="AAPL",
    qty=10,
    side="buy",
    type="market",
    time_in_force="day"
)

print(f"Order ID: {order['id']}")
print(f"Client Order ID: {order['client_order_id']}")  # Auto-generated UUID for idempotency
print(f"Status: {order['status']}")  # new, accepted, filled, etc.
print(f"Filled: {order['filled_qty']} shares")
```

> **Idempotency**: Every order automatically gets a unique `client_order_id` (UUID) if not provided. This prevents duplicate orders on network retries. You can also provide your own:
>
> ```python
> order = brokerage.submit_order(
>     symbol="AAPL", qty=10, side="buy", type="market",
>     time_in_force="day",
>     client_order_id="my-unique-id-123"  # Your own idempotency key
> )
> ```

#### Limit Order (Sell)
```python
order = brokerage.submit_order(
    symbol="TSLA",
    qty=5,
    side="sell",
    type="limit",
    limit_price=250.00,
    time_in_force="gtc"  # good-til-canceled
)
```

#### Stop Loss Order
```python
order = brokerage.submit_order(
    symbol="MSFT",
    qty=20,
    side="sell",
    type="stop",
    stop_price=380.00,
    time_in_force="day"
)
```

#### Stop-Limit Order
```python
order = brokerage.submit_order(
    symbol="GOOGL",
    qty=3,
    side="buy",
    type="stop_limit",
    limit_price=145.00,
    stop_price=143.00,
    time_in_force="day"
)
```

### 3. Manage Orders

#### List Orders
```python
# Get all orders
orders = brokerage.list_orders()

# Filter by status
open_orders = brokerage.list_orders(status="open")
filled_orders = brokerage.list_orders(status="filled")

# Limit results
recent_orders = brokerage.list_orders(limit=10)

for order in orders:
    print(f"{order['symbol']}: {order['side']} {order['qty']} @ {order['type']}")
    print(f"  Status: {order['status']}")
    print(f"  Filled: {order['filled_qty']}/{order['qty']}")
```

#### Get Order Details
```python
order = brokerage.get_order(order_id="some-order-id")

print(f"Symbol: {order['symbol']}")
print(f"Type: {order['type']}")
print(f"Side: {order['side']}")
print(f"Qty: {order['qty']}")
print(f"Filled: {order['filled_qty']}")
print(f"Status: {order['status']}")
print(f"Submitted: {order['submitted_at']}")
if order['filled_at']:
    print(f"Filled: {order['filled_at']}")
if order['filled_avg_price']:
    print(f"Avg Fill Price: ${order['filled_avg_price']}")
```

#### Cancel Order
```python
# Cancel a pending order
brokerage.cancel_order(order_id="some-order-id")

# Cancel returns None on success, raises exception on error
```

### 4. Manage Positions

#### List All Positions
```python
positions = brokerage.positions()

for position in positions:
    print(f"{position['symbol']}: {position['qty']} shares")
    print(f"  Entry: ${position['avg_entry_price']}")
    print(f"  Current: ${position['current_price']}")
    print(f"  P&L: ${position['unrealized_pl']} ({position['unrealized_plpc']}%)")
    print(f"  Market Value: ${position['market_value']}")
```

#### Get Position for Symbol
```python
position = brokerage.get_position(symbol="AAPL")

print(f"Symbol: {position['symbol']}")
print(f"Qty: {position['qty']}")
print(f"Side: {position['side']}")  # long or short
print(f"Avg Entry: ${position['avg_entry_price']}")
print(f"Current: ${position['current_price']}")
print(f"Cost Basis: ${position['cost_basis']}")
print(f"Market Value: ${position['market_value']}")
print(f"Unrealized P&L: ${position['unrealized_pl']}")
print(f"Unrealized P&L %: {position['unrealized_plpc']}%")
```

#### Close Position
```python
# Close entire position (market order to exit)
order = brokerage.close_position(symbol="TSLA")

print(f"Closing order: {order['id']}")
print(f"Status: {order['status']}")
```

### 5. Portfolio History
```python
# Get portfolio value history
history = brokerage.get_portfolio_history(
    period="1M",  # 1D, 1W, 1M, 3M, 1A, all
    timeframe="1D"  # 5Min, 15Min, 1H, 1D
)

print(f"Timeframes: {len(history['timestamp'])} data points")
print(f"Base Value: ${history['base_value']}")

for i, (timestamp, equity) in enumerate(zip(history['timestamp'], history['equity'])):
    profit_loss = history['profit_loss'][i]
    profit_loss_pct = history['profit_loss_pct'][i]
    print(f"{timestamp}: ${equity} (P&L: ${profit_loss}, {profit_loss_pct}%)")
```

## Paper Trading vs Live Trading

### Paper Trading (Default)
- **Safe testing environment** with simulated trading
- **No real money** at risk
- **Same API** as live trading
- **Full order types** supported (market, limit, stop, stop-limit)
- **Real-time market data** (delayed 15 minutes for some exchanges)
- **Resets available** (contact Alpaca support to reset paper account)

### Live Trading (Opt-In)
- **Real money** and real trades
- **Must explicitly set** `mode="live"`
- **Requires live API credentials** (separate from paper)
- **Regulatory compliance** required (pattern day trader rules, etc.)
- **Cannot be undone** - all orders are real

### Safety Checklist Before Going Live
- [ ] Thoroughly tested with paper trading
- [ ] Risk management implemented (stop losses, position limits)
- [ ] Error handling for all API calls
- [ ] Monitoring and alerting configured
- [ ] Regulatory compliance verified
- [ ] Account properly funded
- [ ] Trading plan documented
- [ ] Backup and recovery procedures in place

## Error Handling

### Common Errors
```python
from httpx import HTTPStatusError

try:
    order = brokerage.submit_order(
        symbol="AAPL",
        qty=1000000,  # Too large
        side="buy",
        type="market",
        time_in_force="day"
    )
except HTTPStatusError as e:
    if e.response.status_code == 403:
        print("Insufficient buying power")
    elif e.response.status_code == 422:
        print("Invalid order parameters")
    else:
        print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Retry Logic (svc-infra integration)
```python
from fin_infra.brokerage import easy_brokerage

# Brokerage provider already uses httpx with retries
brokerage = easy_brokerage(mode="paper")

# API calls automatically retry on transient errors
# (network issues, 5xx errors, timeouts)
positions = brokerage.positions()  # Retries up to 3 times
```

## Rate Limits

### Alpaca Rate Limits
- **Paper Trading**: 200 requests per minute
- **Live Trading**: 200 requests per minute
- **Market Data**: Separate limits (see market data docs)

### Handling Rate Limits
```python
from time import sleep

def submit_orders_with_throttle(orders_to_submit):
    """Submit multiple orders with rate limit handling."""
    for order_params in orders_to_submit:
        try:
            order = brokerage.submit_order(**order_params)
            print(f"Order submitted: {order['id']}")
        except HTTPStatusError as e:
            if e.response.status_code == 429:
                print("Rate limit hit, waiting 60 seconds...")
                sleep(60)
                order = brokerage.submit_order(**order_params)
            else:
                raise

        # Small delay between orders
        sleep(0.3)  # 200 req/min = ~3 req/sec max
```

## Testing

### Unit Tests (Mock Provider)
```python
import pytest
from unittest.mock import Mock
from fin_infra.brokerage import add_brokerage
from fastapi import FastAPI
from fastapi.testclient import TestClient

def test_submit_order_endpoint():
    """Test order submission via API."""
    app = FastAPI()

    # Create mock provider
    mock_provider = Mock()
    mock_provider.submit_order.return_value = {
        "id": "test-order-123",
        "symbol": "AAPL",
        "status": "accepted"
    }

    # Wire to app
    add_brokerage(app, provider=mock_provider)
    client = TestClient(app)

    # Submit order
    response = client.post("/brokerage/orders", json={
        "symbol": "AAPL",
        "qty": 10,
        "side": "buy",
        "type": "market",
        "time_in_force": "day"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-order-123"
    assert data["symbol"] == "AAPL"
```

### Integration Tests (Paper Trading)
```python
import pytest
import os
from fin_infra.brokerage import easy_brokerage

@pytest.mark.skipif(
    not os.getenv("ALPACA_PAPER_API_KEY"),
    reason="Requires Alpaca paper trading credentials"
)
def test_real_paper_trading():
    """Test with real Alpaca paper trading API."""
    brokerage = easy_brokerage(mode="paper")

    # Get account
    account = brokerage.get_account()
    assert account['status'] == 'ACTIVE'
    assert float(account['buying_power']) > 0

    # Submit market order
    order = brokerage.submit_order(
        symbol="AAPL",
        qty=1,
        side="buy",
        type="market",
        time_in_force="day"
    )
    assert order['symbol'] == 'AAPL'
    assert order['status'] in ['accepted', 'new', 'filled']

    # Cancel if not filled
    if order['status'] != 'filled':
        brokerage.cancel_order(order['id'])
```

## Production Best Practices

1. **Always Start with Paper**: Test all logic thoroughly before live trading
2. **Implement Stop Losses**: Protect against unexpected price movements
3. **Position Sizing**: Never risk more than you can afford to lose
4. **Error Handling**: Wrap all API calls in try/except blocks
5. **Monitoring**: Set up alerts for failed orders and unusual activity
6. **Compliance**: Ensure regulatory compliance (PDT rules, etc.)
7. **Logging**: Log all trades for audit trail
8. **Rate Limiting**: Respect API rate limits to avoid throttling
9. **Idempotency**: Use client_order_id to prevent duplicate orders
10. **Testing**: Continuous testing in paper mode even after going live
