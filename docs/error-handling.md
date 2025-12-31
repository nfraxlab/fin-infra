# Error Handling Guide

This guide documents exception hierarchies and error handling patterns in fin-infra.

## Exception Hierarchy

```
Exception
└── FinInfraError (base for all fin-infra exceptions)
    ├── ProviderError
    │   ├── ProviderNotFoundError
    │   ├── ProviderConfigError
    │   └── ProviderAPIError
    ├── BankingError
    │   ├── InvalidAccessTokenError
    │   ├── InstitutionNotFoundError
    │   ├── AccountNotFoundError
    │   └── TransactionSyncError
    ├── BrokerageError
    │   ├── OrderRejectedError
    │   ├── InsufficientFundsError
    │   ├── MarketClosedError
    │   └── PositionNotFoundError
    ├── MarketDataError
    │   ├── SymbolNotFoundError
    │   ├── QuoteUnavailableError
    │   └── RateLimitExceededError
    ├── CreditError
    │   ├── CreditPullFailedError
    │   └── ConsentRequiredError
    └── CalculationError
        ├── InvalidCashFlowError
        └── DivisionByZeroError
```

## Critical: Financial Error Handling

### Never Silently Fail on Money Operations

```python
# [X] WRONG - User's net worth is wrong
for asset in assets:
    if asset.currency != base_currency:
        continue  # Silent skip!
    total += asset.value

# [OK] CORRECT - Fail loudly or handle explicitly
for asset in assets:
    if asset.currency != base_currency:
        raise UnsupportedCurrencyError(f"Currency {asset.currency} not supported")
        # OR: converted = await convert_currency(asset, base_currency)
```

### Preserve Error Context for Auditing

```python
try:
    order = await submit_order(symbol, quantity)
except OrderRejectedError as e:
    # Log for audit trail
    audit_log.record(
        action="order_rejected",
        symbol=symbol,
        quantity=quantity,
        reason=str(e),
        timestamp=datetime.utcnow(),
    )
    raise
```

### Idempotency Errors

```python
from fin_infra.exceptions import DuplicateOrderError

try:
    order = await submit_order(symbol, qty, client_order_id)
except DuplicateOrderError:
    # Idempotency: return existing order instead of error
    order = await get_order_by_client_id(client_order_id)
    return order
```

## Provider-Specific Errors

### Plaid Errors

```python
from fin_infra.banking.exceptions import PlaidError

try:
    accounts = await banking.get_accounts(access_token)
except PlaidError as e:
    if e.error_code == "ITEM_LOGIN_REQUIRED":
        # User needs to re-authenticate
        return redirect_to_plaid_link()
    raise
```

### Brokerage Errors

```python
from fin_infra.brokerage.exceptions import (
    InsufficientFundsError,
    MarketClosedError,
)

try:
    order = await brokerage.submit_order(...)
except InsufficientFundsError:
    return {"error": "Not enough buying power"}
except MarketClosedError:
    return {"error": "Market is closed. Order queued."}
```

## HTTP Status Code Mapping

| Exception | HTTP Status |
|-----------|-------------|
| InvalidAccessTokenError | 401 |
| SymbolNotFoundError | 404 |
| InsufficientFundsError | 400 |
| RateLimitExceededError | 429 |
| ProviderAPIError | 502 |
| CalculationError | 500 |

## Best Practices

1. **Log all financial operations** for audit trail
2. **Never swallow exceptions** in money calculations
3. **Use Decimal** to avoid precision errors
4. **Add circuit breakers** for external API calls
5. **Validate idempotency keys** before operations
