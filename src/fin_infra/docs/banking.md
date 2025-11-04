# Banking Integration Guide

fin-infra provides unified interfaces for connecting to users' bank accounts, fetching transactions, balances, and identity information through various banking aggregation providers.

## 📋 Table of Contents
- [Supported Providers](#supported-providers)
- [Quick Start](#quick-start)
- [Provider Comparison](#provider-comparison)
- [Authentication](#authentication)
- [Environment Variables](#environment-variables)
- [Core Operations](#core-operations)
- [FastAPI Integration](#fastapi-integration)
- [Security & PII](#security--pii)
- [Rate Limits](#rate-limits)
- [Troubleshooting](#troubleshooting)

## Supported Providers

### ✅ Production Ready
- **Teller** (Default) - Certificate-based mTLS authentication, free tier (100 connections/month)
- **Plaid** (Alternate) - Industry standard, OAuth-based, sandbox free

### 🚧 Coming Soon
- **MX** - Enterprise-grade aggregation
- **Finicity** - Mastercard-backed aggregation

## Quick Start

### Zero Configuration (Recommended)
```python
from fin_infra.banking import easy_banking

# Auto-detects provider and credentials from environment
banking = easy_banking()

# Use immediately
accounts = banking.accounts(access_token="user_token")
transactions = banking.transactions(
    access_token="user_token",
    start_date="2025-01-01",
    end_date="2025-01-31"
)
```

### Explicit Provider
```python
# Use Teller (default)
banking = easy_banking(provider="teller")

# Use Plaid
banking = easy_banking(provider="plaid")
```

### Manual Configuration
```python
from fin_infra.providers.banking.teller_client import TellerClient

# Teller with certificates
teller = TellerClient(
    cert_path="./teller_certificate.pem",
    key_path="./teller_private_key.pem",
    environment="sandbox"  # or "production"
)
```

## Provider Comparison

| Feature | Teller | Plaid | MX |
|---------|--------|-------|-----|
| **Pricing** | ✅ Free 100 conn/mo<br>$0.25 after | ❌ $0.10-0.30/conn/mo<br>Min: $100-500/mo | 💰 Enterprise only<br>Contact sales |
| **Auth Method** | 🔐 mTLS Certificates | 🔑 OAuth (client_id + secret) | 🔑 OAuth |
| **Coverage** | 🇺🇸 US-only (4,000+ banks) | 🌍 US, CA, UK, EU (12,000+) | 🌍 16,000+ institutions |
| **Setup Time** | ⚡ 5-10 minutes | ⚡ 10-15 minutes | 🐌 Days (sales process) |
| **Best For** | MVP, startups, US-only | Production, international | Enterprise
## Authentication

### Teller (Certificate-Based mTLS)

**Why certificates instead of API keys?**
- 🔐 **Mutual TLS (mTLS)**: Both client and server verify each other's identity
- ✅ **More secure**: Compromised API keys = full access; compromised cert = server can revoke
- 🚫 **No secrets in URLs**: Certificates never appear in logs/URLs
- 🎯 **Defense in depth**: Certificate + private key required (two-factor at infrastructure level)

**Setup Steps:**

1. **Generate Certificate Signing Request (CSR)**
   ```bash
   cd ~/secure-certs  # Outside git repo!
   openssl req -new -newkey rsa:2048 -nodes \
     -keyout teller_private_key.pem \
     -out teller_request.csr
   ```

2. **Submit CSR to Teller**
   - Login to Teller dashboard → API Settings → Upload CSR
   - Download signed certificate: `teller_certificate.pem`

3. **Store Certificates Securely**
   ```bash
   # Development: Project root (gitignored)
   cp teller_certificate.pem /path/to/fin-infra/
   cp teller_private_key.pem /path/to/fin-infra/
   
   # Production: Environment variables pointing to secure storage
   export TELLER_CERTIFICATE_PATH="/run/secrets/teller.pem"
   export TELLER_PRIVATE_KEY_PATH="/run/secrets/teller.key"
   ```

4. **Configure Environment**
   ```bash
   # .env (never commit!)
   TELLER_CERTIFICATE_PATH=./teller_certificate.pem
   TELLER_PRIVATE_KEY_PATH=./teller_private_key.pem
   TELLER_ENVIRONMENT=sandbox  # or production
   ```

⚠️ **SECURITY CRITICAL**: Never commit `.pem` or `.key` files to git! See [SECURITY.md](../../SECURITY.md) for emergency procedures if certificates are leaked.

### Plaid (OAuth API Keys)

**Setup Steps:**

1. **Get Credentials**
   - Sign up at [plaid.com/dashboard](https://plaid.com/dashboard)
   - Create application → Copy client_id and secret

2. **Configure Environment**
   ```bash
   # .env (never commit!)
   PLAID_CLIENT_ID=your_client_id
   PLAID_SECRET=your_secret
   PLAID_ENVIRONMENT=sandbox  # sandbox, development, production
   ```

3. **Initialize**
   ```python
   from fin_infra.banking import easy_banking
   
   plaid = easy_banking(provider="plaid")
   ```

## Environment Variables

### Teller (Default Provider)
```bash
TELLER_CERTIFICATE_PATH=./teller_certificate.pem  # Path to signed certificate
TELLER_PRIVATE_KEY_PATH=./teller_private_key.pem  # Path to private key
TELLER_ENVIRONMENT=sandbox                        # sandbox | production
```

### Plaid (Alternate Provider)
```bash
PLAID_CLIENT_ID=your_client_id_here
PLAID_SECRET=your_secret_here
PLAID_ENVIRONMENT=sandbox  # sandbox | development | production
```

### Auto-Detection Logic
`easy_banking()` checks in order:
1. `TELLER_CERTIFICATE_PATH` exists → Use Teller
2. `PLAID_CLIENT_ID` set → Use Plaid
3. Fallback: Error (no credentials found)

## Core Operations

### 1. Fetch Accounts
```python
from fin_infra.banking import easy_banking

banking = easy_banking()

# Get all accounts for user
accounts = banking.accounts(access_token="user_access_token")

for account in accounts:
    print(f"{account.name}: {account.balance} {account.currency}")
    print(f"Type: {account.type}")  # checking, savings, credit_card, etc.
    print(f"Institution: {account.institution_name}")
```

**Response Model:**
```python
from fin_infra.models import BankAccount

# Pydantic model with validation
account = BankAccount(
    id="acc_123",
    name="My Checking",
    official_name="Premium Checking Account",
    type="depository",
    subtype="checking",
    balance=5432.10,
    currency="USD",
    institution_id="ins_001",
    institution_name="Chase Bank"
)
```

### 2. Fetch Transactions
```python
from datetime import date, timedelta

banking = easy_banking()

# Last 30 days
end_date = date.today()
start_date = end_date - timedelta(days=30)

transactions = banking.transactions(
    access_token="user_access_token",
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat()
)

for txn in transactions:
    print(f"{txn.date}: {txn.description} - ${txn.amount}")
    print(f"Category: {txn.category}")
    print(f"Merchant: {txn.merchant_name}")
```

**Response Model:**
```python
from fin_infra.models import Transaction

txn = Transaction(
    id="txn_123",
    account_id="acc_123",
    amount=-45.67,  # Negative = debit, Positive = credit
    date="2025-01-15",
    description="STARBUCKS #12345",
    merchant_name="Starbucks",
    category="Food & Drink",
    pending=False,
    currency="USD"
)
```

### 3. Fetch Identity (PII)
```python
# ⚠️ Handle PII carefully - see Security section
identity = banking.identity(access_token="user_access_token")

for owner in identity.owners:
    print(f"Name: {owner.name}")
    print(f"Email: {owner.email}")
    print(f"Phone: {owner.phone}")
    print(f"Address: {owner.address}")
```

### 4. Fetch Balances (Quick Update)
```python
# Lightweight call for balance updates only
balances = banking.balances(access_token="user_access_token")

for bal in balances:
    print(f"Account {bal.account_id}: ${bal.current}")
    print(f"Available: ${bal.available}")
```

## FastAPI Integration

### Basic Setup (Using svc-infra)
```python
from fastapi import FastAPI, Depends, HTTPException
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.cache import init_cache
from fin_infra.banking import easy_banking

# Backend from svc-infra
app = easy_service_app(name="BankingAPI")
init_cache(url="redis://localhost")

# Financial provider from fin-infra
banking = easy_banking()

@app.get("/accounts")
async def get_accounts(access_token: str):
    """Fetch user's bank accounts"""
    try:
        accounts = banking.accounts(access_token=access_token)
        return {"accounts": accounts}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/transactions")
async def get_transactions(
    access_token: str,
    start_date: str,
    end_date: str
):
    """Fetch user's transactions"""
    txns = banking.transactions(
        access_token=access_token,
        start_date=start_date,
        end_date=end_date
    )
    return {"transactions": txns}
```

### With Caching (svc-infra)
```python
from svc_infra.cache import cache_read, cache_write, resource

# Define cached resource
bank = resource("bank_account", "user_id")

@app.get("/accounts/{user_id}")
@bank.cache_read(ttl=300, suffix="accounts")  # 5 min cache
async def get_cached_accounts(user_id: str, access_token: str):
    """Cached account fetch"""
    return banking.accounts(access_token=access_token)

@app.post("/accounts/{user_id}/refresh")
@bank.cache_write(tags=["accounts"], recache=[...])
async def refresh_accounts(user_id: str, access_token: str):
    """Invalidate cache and refresh"""
    return banking.accounts(access_token=access_token)
```

### With Auth (svc-infra)
```python
from svc_infra.api.fastapi.auth.add import add_auth_users
from svc_infra.api.fastapi.auth.dependencies import get_current_user

# Add auth to app
add_auth_users(app, ...)

@app.get("/me/accounts")
async def my_accounts(user = Depends(get_current_user)):
    """Get current user's accounts"""
    # Retrieve access_token from user's encrypted storage
    access_token = decrypt_token(user.bank_token_encrypted)
    return banking.accounts(access_token=access_token)
```

### Easy Add Banking (Coming Soon)
```python
from fin_infra.banking import add_banking

# One-liner to mount routes (future feature)
add_banking(
    app,
    provider="teller",
    mount_path="/api/v1/banking",
    require_auth=True
)
# Auto-generates: /accounts, /transactions, /balances, /identity
```

## Security & PII

### PII Classification
| Data Type | PII Level | GDPR/CCPA | Storage Rules |
|-----------|-----------|-----------|---------------|
| Account ID | Low | ✅ OK | Database OK |
| Account Name | Low | ✅ OK | Database OK |
| Balance | Medium | ⚠️ Sensitive | Encrypt at rest |
| Transactions | Medium | ⚠️ Sensitive | Encrypt at rest |
| Identity (name, email) | High | 🔴 Highly Sensitive | Encrypt + audit log |
| SSN, tax IDs | Critical | 🔴 Highly Sensitive | Never store (pass-through only) |

### Storage Best Practices

**✅ DO:**
```python
from svc_infra.security import encrypt_field, decrypt_field

# Encrypt before storing
encrypted_token = encrypt_field(access_token, key=app_encryption_key)
await db.execute(
    "INSERT INTO user_tokens (user_id, token_encrypted) VALUES (?, ?)",
    (user_id, encrypted_token)
)

# Decrypt when using
encrypted = await db.fetchone("SELECT token_encrypted FROM user_tokens WHERE user_id = ?", (user_id,))
access_token = decrypt_field(encrypted[0], key=app_encryption_key)
```

**❌ DON'T:**
```python
# Never store plaintext tokens/PII
await db.execute(
    "INSERT INTO users (user_id, access_token, ssn) VALUES (?, ?, ?)",
    (user_id, access_token, ssn)  # ❌ SECURITY VIOLATION
)
```

### Access Token Storage
- **Encrypt at rest**: Use svc-infra's `encrypt_field()`
- **Short TTLs**: Teller tokens expire after 60 days, Plaid varies
- **Rotation**: Implement token refresh flows
- **Audit logging**: Log all token access (who, when, why)

### Certificate Security (Teller)
- **Never commit**: `.pem` and `.key` files MUST NOT be in git
- **Production storage**: 
  - Kubernetes: Use sealed secrets or external secret managers (AWS Secrets Manager, Vault)
  - Docker: Mount volumes with restricted permissions (chmod 600)
  - Railway/Heroku: Environment variables pointing to secure storage
- **Emergency procedures**: See [SECURITY.md](../../SECURITY.md) for leak response

### Compliance Helpers (svc-infra)
```python
from svc_infra.data.add import add_data_lifecycle

# Auto-expire PII per retention policies
add_data_lifecycle(
    app,
    retention_policies={
        "transactions": 90,  # days
        "identity": 30
    },
    anonymization_rules={...}
)
```

## Rate Limits

### Provider Limits
| Provider | Rate Limit | Overage |
|----------|------------|---------|
| Teller | None documented | Contact support |
| Plaid | Varies by tier (typically 100-500 req/min) | 429 errors |

### svc-infra Rate Limiting
```python
from svc_infra.api.fastapi.middlewares.rate_limit import SimpleRateLimit

# Protect banking endpoints
app.add_middleware(
    SimpleRateLimit,
    limit=100,  # requests
    window=60,  # seconds
    paths=["/api/v1/banking/*"]
)
```

### Retry Logic (svc-infra)
```python
from svc_infra.http import with_retries

# Auto-retry on 429/500 errors
@with_retries(max_attempts=3, backoff=2.0)
async def fetch_accounts_with_retry(access_token: str):
    return banking.accounts(access_token=access_token)
```

## Troubleshooting

### Certificate Errors (Teller)
**Problem**: `SSLError: certificate verify failed`

**Solutions**:
1. Check certificate paths are correct:
   ```bash
   ls -la teller_certificate.pem teller_private_key.pem
   ```
2. Verify certificate is not expired:
   ```bash
   openssl x509 -in teller_certificate.pem -noout -dates
   ```
3. Ensure private key matches certificate:
   ```bash
   diff <(openssl x509 -in teller_certificate.pem -pubkey -noout) \
        <(openssl rsa -in teller_private_key.pem -pubout 2>/dev/null)
   ```

### Missing Environment Variables
**Problem**: `ValueError: No banking provider credentials found`

**Solution**: Check .env file is loaded
```python
# Acceptance tests auto-load .env via conftest.py
# For manual scripts:
from dotenv import load_dotenv
load_dotenv()
```

### API Errors
**Problem**: `401 Unauthorized`

**Teller**: Certificate not accepted → Re-upload CSR in dashboard
**Plaid**: Wrong environment → Check `PLAID_ENVIRONMENT` matches token (sandbox tokens won't work in production)

**Problem**: `400 Bad Request - Invalid access token`

**Solutions**:
1. Token expired → Refresh using provider's token refresh flow
2. Token revoked → User must re-authenticate
3. Wrong provider → Ensure token from Teller isn't used with Plaid client

### Debugging
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

# See all HTTP requests/responses
banking = easy_banking()
accounts = banking.accounts(access_token="...")  # Watch console for details
```

### Common Patterns

**Multi-provider fallback**:
```python
from fin_infra.banking import easy_banking

# Try Teller first, fallback to Plaid
try:
    banking = easy_banking(provider="teller")
except ValueError:
    banking = easy_banking(provider="plaid")
```

**Sandbox vs Production**:
```python
import os

env = os.getenv("APP_ENV", "development")

if env == "production":
    os.environ["TELLER_ENVIRONMENT"] = "production"
    os.environ["PLAID_ENVIRONMENT"] = "production"
else:
    os.environ["TELLER_ENVIRONMENT"] = "sandbox"
    os.environ["PLAID_ENVIRONMENT"] = "sandbox"

banking = easy_banking()  # Auto-uses correct environment
```

## Additional Resources

- [SECURITY.md](../../SECURITY.md) - Certificate handling and emergency procedures
- [.env.example](../../../.env.example) - Complete environment variable reference
- [svc-infra docs](https://github.com/yourusername/svc-infra) - Backend framework documentation
- [Teller API Docs](https://teller.io/docs) - Official Teller documentation
- [Plaid API Docs](https://plaid.com/docs) - Official Plaid documentation
```

### Transaction
```python
from fin_infra.models.transactions import Transaction

class Transaction:
    transaction_id: str
    account_id: str
    amount: Decimal
    date: date
    name: str
    merchant_name: str | None
    category: list[str]
    pending: bool
    iso_currency_code: str
```

## Webhooks

Handle real-time updates from banking providers:

```python
from fastapi import FastAPI, Request
from fin_infra.banking.webhooks import verify_plaid_webhook

app = FastAPI()

@app.post("/webhooks/plaid")
async def plaid_webhook(request: Request):
    payload = await request.json()
    
    # Verify webhook signature
    if not verify_plaid_webhook(request.headers, payload):
        return {"error": "Invalid signature"}
    
    webhook_type = payload.get("webhook_type")
    webhook_code = payload.get("webhook_code")
    
    if webhook_type == "TRANSACTIONS":
        if webhook_code == "INITIAL_UPDATE":
            # Initial transaction data available
            pass
        elif webhook_code == "DEFAULT_UPDATE":
            # New transaction data available
            pass
        elif webhook_code == "HISTORICAL_UPDATE":
            # Historical transaction data available
            pass
    
    return {"status": "received"}
```

## Error Handling

```python
from fin_infra.banking.exceptions import (
    BankingProviderError,
    InvalidCredentialsError,
    ItemLoginRequiredError,
    RateLimitError
)

try:
    accounts = await banking.get_accounts(access_token)
except ItemLoginRequiredError:
    # User needs to re-authenticate with their bank
    link_token = await banking.create_link_token(
        user_id="user_123",
        access_token=access_token,  # Update mode
    )
except RateLimitError:
    # Implement exponential backoff
    pass
except BankingProviderError as e:
    # Handle general provider errors
    print(f"Error: {e.message}")
```

## Best Practices

1. **Secure Token Storage**: Store access tokens encrypted in your database
2. **Rate Limiting**: Implement rate limiting for API calls
3. **Webhook Handling**: Use webhooks for real-time updates instead of polling
4. **Error Recovery**: Implement retry logic with exponential backoff
5. **User Communication**: Clearly communicate when re-authentication is needed
6. **Data Retention**: Follow provider guidelines for data retention and deletion

## Testing

```python
import pytest
from fin_infra.banking import easy_banking

@pytest.mark.asyncio
async def test_get_accounts():
    banking = easy_banking()
    
    # Use sandbox credentials
    access_token = "access-sandbox-xxx"
    accounts = await banking.get_accounts(access_token)
    
    assert len(accounts) > 0
    assert accounts[0].account_id is not None
```

## Next Steps

- [Market Data Integration](market-data.md)
- [Credit Score Integration](credit.md)
- [Brokerage Integration](brokerage.md)
