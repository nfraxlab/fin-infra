# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with fin-infra.

## Quick Diagnostics

Run this to check your environment:

```python
import os

checks = {
    "PLAID_CLIENT_ID": bool(os.getenv("PLAID_CLIENT_ID")),
    "PLAID_SECRET": bool(os.getenv("PLAID_SECRET")),
    "PLAID_ENV": os.getenv("PLAID_ENV", "sandbox"),
    "ALPACA_API_KEY": bool(os.getenv("ALPACA_API_KEY")),
    "POLYGON_API_KEY": bool(os.getenv("POLYGON_API_KEY")),
}

for name, value in checks.items():
    if isinstance(value, bool):
        status = "set" if value else "missing"
    else:
        status = value
    print(f"{name}: {status}")
```

---

## Plaid Connection Errors

### Symptoms

```
PlaidError: INVALID_ACCESS_TOKEN - The access token is invalid
PlaidError: ITEM_LOGIN_REQUIRED - User must re-authenticate
PlaidError: INSTITUTION_NOT_RESPONDING - Bank is temporarily unavailable
```

### Causes

1. Access token expired or revoked
2. User changed bank credentials
3. Institution experiencing issues
4. Wrong Plaid environment

### Solutions

**1. Handle ITEM_LOGIN_REQUIRED:**

```python
from fin_infra.banking import PlaidClient
from fin_infra.exceptions import PlaidError

async def get_accounts_safe(access_token: str):
    client = PlaidClient()

    try:
        accounts = await client.get_accounts(access_token)
        return accounts
    except PlaidError as e:
        if e.error_code == "ITEM_LOGIN_REQUIRED":
            # User needs to re-authenticate
            link_token = await client.create_link_token(
                user_id=user.id,
                access_token=access_token,  # Update mode
            )
            return {"requires_reauth": True, "link_token": link_token}
        raise
```

**2. Check Plaid environment:**

```python
import os

# Ensure you're using the right environment
plaid_env = os.getenv("PLAID_ENV", "sandbox")
print(f"Using Plaid environment: {plaid_env}")

# Sandbox: For testing with fake data
# Development: For testing with real credentials (100 items)
# Production: For production use
```

**3. Handle institution errors:**

```python
from fin_infra.banking import PlaidClient
from fin_infra.exceptions import InstitutionNotRespondingError

async def sync_with_retry(access_token: str, max_retries: int = 3):
    client = PlaidClient()

    for attempt in range(max_retries):
        try:
            return await client.sync_transactions(access_token)
        except InstitutionNotRespondingError:
            if attempt < max_retries - 1:
                # Wait and retry with exponential backoff
                await asyncio.sleep(60 * (2 ** attempt))
            else:
                raise
```

**4. Verify access token format:**

```python
# Plaid access tokens look like:
# access-sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# access-development-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# access-production-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

def validate_access_token(token: str) -> bool:
    import re
    pattern = r"^access-(sandbox|development|production)-[a-f0-9-]{36}$"
    return bool(re.match(pattern, token))
```

**5. Debug Plaid API calls:**

```python
import logging
logging.getLogger("fin_infra.banking").setLevel(logging.DEBUG)

# This will log:
# - API request/response details
# - Token validation steps
# - Error details from Plaid
```

---

## Market Data Rate Limits

### Symptoms

```
RateLimitExceededError: API rate limit exceeded. Retry after 60 seconds.
PolygonError: 429 Too Many Requests
AlphaVantageError: API call frequency limit reached
```

### Causes

1. Exceeding provider's request limits
2. Too many concurrent requests
3. Free tier limitations

### Solutions

**1. Understand provider limits:**

| Provider | Free Tier | Paid Tier |
|----------|-----------|-----------|
| Polygon.io | 5 req/min | Unlimited |
| Alpha Vantage | 5 req/min | 75 req/min |
| Yahoo Finance | ~2000/day | N/A |
| Alpaca | 200 req/min | Higher |

**2. Implement rate limiting:**

```python
import asyncio
from fin_infra.markets import MarketDataClient

client = MarketDataClient()
semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

async def get_quote_rate_limited(symbol: str):
    async with semaphore:
        result = await client.get_quote(symbol)
        await asyncio.sleep(0.2)  # 5 req/sec = 0.2s between requests
        return result

# Batch fetch with rate limiting
async def get_quotes_batch(symbols: list[str]):
    return await asyncio.gather(*[
        get_quote_rate_limited(s) for s in symbols
    ])
```

**3. Use caching for frequently accessed data:**

```python
from fin_infra.markets import MarketDataClient

client = MarketDataClient(
    cache_ttl=60,  # Cache quotes for 60 seconds
    cache_backend="redis",
)

# Subsequent calls within 60s use cached data
quote = await client.get_quote("AAPL")
```

**4. Handle rate limit errors gracefully:**

```python
from fin_infra.exceptions import RateLimitExceededError

async def get_quote_with_retry(symbol: str):
    for attempt in range(3):
        try:
            return await client.get_quote(symbol)
        except RateLimitExceededError as e:
            if attempt < 2:
                wait_time = e.retry_after or (60 * (attempt + 1))
                await asyncio.sleep(wait_time)
            else:
                raise

# Or use the built-in retry mechanism
client = MarketDataClient(
    max_retries=3,
    retry_on_rate_limit=True,
)
```

**5. Batch requests when possible:**

```python
# Instead of:
for symbol in symbols:
    quote = await client.get_quote(symbol)  # N requests

# Use batch API:
quotes = await client.get_quotes(symbols)  # 1 request
```

---

## Transaction Sync Failures

### Symptoms

```
TransactionSyncError: Failed to sync transactions
PlaidError: TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION
SyncTimeoutError: Transaction sync timed out after 300 seconds
```

### Causes

1. Large number of transactions to sync
2. Concurrent sync attempts
3. Institution slow to respond
4. Cursor corruption

### Solutions

**1. Handle large syncs with pagination:**

```python
from fin_infra.banking import PlaidClient

async def sync_all_transactions(access_token: str):
    client = PlaidClient()
    cursor = None
    all_added = []
    all_modified = []
    all_removed = []

    while True:
        result = await client.sync_transactions(
            access_token,
            cursor=cursor,
            count=500,  # Max per request
        )

        all_added.extend(result.added)
        all_modified.extend(result.modified)
        all_removed.extend(result.removed)

        if not result.has_more:
            break

        cursor = result.next_cursor

    return {
        "added": all_added,
        "modified": all_modified,
        "removed": all_removed,
    }
```

**2. Prevent concurrent syncs:**

```python
import asyncio
from fin_infra.banking import PlaidClient

# Use a lock per access token
sync_locks: dict[str, asyncio.Lock] = {}

async def sync_with_lock(access_token: str):
    if access_token not in sync_locks:
        sync_locks[access_token] = asyncio.Lock()

    async with sync_locks[access_token]:
        return await PlaidClient().sync_transactions(access_token)
```

**3. Handle cursor corruption:**

```python
from fin_infra.exceptions import TransactionSyncError

async def sync_with_reset(access_token: str, cursor: str | None = None):
    client = PlaidClient()

    try:
        return await client.sync_transactions(access_token, cursor=cursor)
    except TransactionSyncError as e:
        if "cursor" in str(e).lower():
            # Reset cursor and start fresh
            return await client.sync_transactions(access_token, cursor=None)
        raise
```

**4. Add timeout handling:**

```python
import asyncio

async def sync_with_timeout(access_token: str, timeout: float = 300.0):
    try:
        async with asyncio.timeout(timeout):
            return await sync_all_transactions(access_token)
    except asyncio.TimeoutError:
        # Log and queue for retry
        logger.warning(f"Sync timed out for {access_token[:8]}...")
        await queue_sync_retry(access_token)
        raise SyncTimeoutError("Transaction sync timed out")
```

---

## Categorization Accuracy Issues

### Symptoms

- Transactions categorized as "Uncategorized" or "Other"
- Wrong category assigned
- Low confidence scores

### Causes

1. Unknown merchant names
2. Ambiguous transaction descriptions
3. ML model not trained on similar data
4. Missing merchant context

### Solutions

**1. Check categorization method:**

```python
from fin_infra.categorization import categorize

result = await categorize("AMZN MKTP US*123ABC")

print(f"Category: {result.category}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Method: {result.method}")  # exact, regex, ml, llm

# If method is 'ml' with low confidence, consider using LLM
```

**2. Enable LLM fallback for low-confidence:**

```python
from fin_infra.categorization import easy_categorization

categorizer = easy_categorization(
    model="hybrid",
    enable_ml=True,
    enable_llm=True,
    confidence_threshold=0.7,  # Use LLM if ML confidence < 70%
    llm_provider="openai",
)

result = await categorizer.categorize("VENMO CASHOUT 12345")
```

**3. Add custom rules for common merchants:**

```python
from fin_infra.categorization import CategorizationEngine, CategoryRule

engine = CategorizationEngine()

# Add custom rules
engine.add_rule(CategoryRule(
    pattern=r"VENMO\s*(CASHOUT|PAYMENT)",
    category="Transfer",
    priority=100,  # Higher = checked first
))

engine.add_rule(CategoryRule(
    pattern=r"MY LOCAL COFFEE",
    category="Coffee Shops",
    priority=100,
))
```

**4. Provide more context:**

```python
from fin_infra.categorization import CategorizationRequest

# More context = better categorization
request = CategorizationRequest(
    description="AMZN MKTP US*123ABC",
    merchant_name="Amazon",
    amount=29.99,
    mcc="5411",  # Merchant category code if available
)

result = await categorizer.categorize(request)
```

**5. Batch categorize for efficiency:**

```python
from fin_infra.categorization import CategorizationEngine

engine = CategorizationEngine(enable_ml=True)

transactions = [
    {"description": "STARBUCKS #12345"},
    {"description": "UBER *TRIP HELP"},
    {"description": "AMAZON.COM*123456"},
]

# Batch is more efficient than one-by-one
results = await engine.categorize_batch([
    CategorizationRequest(description=t["description"])
    for t in transactions
])
```

**6. Debug categorization:**

```python
import logging
logging.getLogger("fin_infra.categorization").setLevel(logging.DEBUG)

# This will show:
# - Which rules were matched
# - ML model predictions and confidence
# - LLM prompts and responses (if enabled)
```

---

## Common Environment Issues

### Issue: "No module named 'fin_infra'"

```bash
pip install fin-infra
# or
poetry add fin-infra
```

### Issue: numpy-financial errors

```bash
# fin-infra requires numpy-financial for cashflow calculations
pip install numpy-financial
```

### Issue: ML categorization not working

```bash
# ML features require scikit-learn
pip install "fin-infra[ml]"
# or
pip install scikit-learn
```

### Issue: Slow first categorization

```python
# The ML model loads on first use. Pre-load it:
from fin_infra.categorization import CategorizationEngine

engine = CategorizationEngine(enable_ml=True)
await engine.warmup()  # Pre-load models
```

### Issue: Decimal precision errors

```python
from decimal import Decimal

# Always use Decimal for money, never float
amount = Decimal("19.99")  # Correct
amount = 19.99  # Wrong - float precision issues

# fin-infra models use Decimal internally
from fin_infra.models import Transaction
txn = Transaction(amount=Decimal("19.99"))
```

---

## Getting Help

If you're still stuck:

1. **Enable debug logging**: `logging.getLogger("fin_infra").setLevel(logging.DEBUG)`
2. **Check GitHub Issues**: [github.com/nfraxlab/fin-infra/issues](https://github.com/nfraxlab/fin-infra/issues)
3. **Open a new issue** with:
   - fin-infra version (`pip show fin-infra`)
   - Python version
   - Provider being used (Plaid, Alpaca, etc.)
   - Full error traceback
   - Sanitized example (remove real tokens/credentials)
