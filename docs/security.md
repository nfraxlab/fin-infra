# Financial Security Guide

**Production-ready security for financial applications**

<parameter name="guide"/>

## Overview

The `fin-infra` security module provides comprehensive protection for sensitive financial data:

1. **PII Masking**: Automatically detect and mask financial PII in logs (SSN, account numbers, cards)
2. **Token Encryption**: Encrypt provider API tokens at rest (Plaid, Alpaca, Alpha Vantage)
3. **Audit Logging**: Track all PII access for compliance (SOC 2, GDPR, GLBA)

### Key Features

- [OK] **Automatic PII Detection**: Regex + context + validation (Luhn for cards, ABA for routing)
- [OK] **Zero Configuration**: One-line `add_financial_security(app)` setup
- [OK] **Compliance-Ready**: Meets PCI-DSS, SOC 2, GDPR, GLBA, CCPA requirements
- [OK] **Provider-Agnostic**: Works with all financial providers (Plaid, Alpaca, etc.)
- [OK] **Key Rotation**: Support multiple encryption keys for zero-downtime rotation
- [OK] **Reuses svc-infra**: Extends existing auth/logging without duplication
- [OK] **Decimal Precision**: All money values use `Decimal` to prevent floating-point errors

---

## Quick Start

### 1. Install Dependencies

```bash
poetry add cryptography  # For token encryption
```

### 2. Generate Encryption Key

```python
from fin_infra.security import generate_encryption_key

# Generate once, store securely (environment variable or KMS)
key = generate_encryption_key()
print(f"PROVIDER_TOKEN_ENCRYPTION_KEY={key.decode()}")
```

### 3. Configure Application

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.logging import setup_logging
from fin_infra.security import add_financial_security

# Create app
app = easy_service_app(name="FinanceAPI")

# Setup base logging (svc-infra)
setup_logging(level="INFO")

# Add financial security (fin-infra)
encryption = add_financial_security(
    app,
    encryption_key=None,  # Uses PROVIDER_TOKEN_ENCRYPTION_KEY env var
    enable_pii_filter=True,
    enable_audit_log=True,
)

# Now all logs are PII-safe and tokens can be encrypted
```

### 4. Verify PII Masking

```python
import logging

logger = logging.getLogger(__name__)

# Before: Logs expose PII [X]
logger.info("Processing SSN: 123-45-6789")
# Output: Processing SSN: 123-45-6789  (PII LEAKED!)

# After: PII automatically masked [OK]
logger.info("Processing SSN: 123-45-6789")
# Output: Processing SSN: ***-**-6789  (PII SAFE!)
```

---

## Financial Precision

**Critical**: All financial amounts MUST use `Decimal`, never `float`. Floating-point arithmetic causes rounding errors that compound in financial calculations.

```python
from decimal import Decimal
from fin_infra.models import Transaction, Account

# [OK] CORRECT: Use Decimal for all money values
tx = Transaction(
    id="tx-1",
    account_id="acct-1",
    amount=Decimal("123.45"),  # Precise
    date="2024-01-01",
    description="Purchase"
)

# [X] WRONG: Float causes precision errors
# 0.1 + 0.2 == 0.30000000000000004 in float!

# fin-infra models automatically coerce float to Decimal for safety,
# but you should always use Decimal explicitly in your code.
```

**Why this matters**: `$0.01 + $0.02 = $0.03` fails with float (`0.030000000000000004`). Over millions of transactions, these errors compound into significant discrepancies.

---

## PII Masking

### Supported PII Types

| PII Type | Pattern | Masked Format | Example |
|----------|---------|---------------|---------|
| **SSN** | `123-45-6789` | `***-**-6789` | Last 4 digits visible |
| **SSN (no dash)** | `123456789` | `*****6789` | Last 4 digits visible |
| **Account Number** | `1234567890` | `******7890` | Last 4 digits visible |
| **Routing Number** | `021000021` | `******021` | Last 3 digits visible |
| **Credit Card** | `4111 1111 1111 1111` | `**** **** **** 1111` | Last 4 digits visible |
| **CVV** | `123` | `***` | Fully masked |
| **Tax ID (EIN)** | `12-3456789` | `**-****789` | Last 3 digits visible |
| **Email** | `user@example.com` | `u***@example.com` | Optional |
| **Phone** | `(555) 123-4567` | `***-***-4567` | Optional |

### How It Works

The PII filter uses **three layers of validation**:

1. **Regex Pattern**: Match potential PII format
2. **Context Keywords**: Verify nearby text contains PII-related keywords
3. **Checksum Validation**: Validate card numbers (Luhn) and routing numbers (ABA)

This prevents false positives (e.g., order IDs that happen to be 9 digits).

### Usage Examples

#### Basic Logging

```python
import logging
from fin_infra.security import FinancialPIIFilter

# Add filter to logger
logger = logging.getLogger(__name__)
logger.addFilter(FinancialPIIFilter())

# All PII automatically masked
logger.info("User SSN: 123-45-6789")
# Output: User SSN: ***-**-6789

logger.info("Account: 1234567890, Routing: 021000021")
# Output: Account: ******7890, Routing: ******021

logger.info("Card: 4111 1111 1111 1111, CVV: 123")
# Output: Card: **** **** **** 1111, CVV: ***
```

#### Mask Emails and Phones (Optional)

```python
# Enable email/phone masking (disabled by default)
pii_filter = FinancialPIIFilter(
    mask_emails=True,
    mask_phones=True
)
logger.addFilter(pii_filter)

logger.info("Contact: user@example.com, Phone: (555) 123-4567")
# Output: Contact: u***@example.com, Phone: ***-***-4567
```

#### Custom Masking

```python
from fin_infra.security.pii_patterns import SSN_PATTERN

# Mask SSN in custom text
text = "User SSN is 123-45-6789"
masked = SSN_PATTERN.sub(lambda m: f"***-**-{m.group()[-4:]}", text)
print(masked)
# Output: User SSN is ***-**-6789
```

---

## Provider Token Encryption

### Why Encrypt Tokens?

Financial provider tokens (Plaid access tokens, Alpaca API keys, etc.) are **sensitive credentials** that must be protected:

- **Plaid access tokens**: Access user's bank accounts
- **Alpaca API keys**: Execute trades in user's brokerage account
- **Alpha Vantage keys**: Access paid market data tier

If tokens leak (database breach, logs, backups), attackers can:
- Access user's financial accounts
- Execute unauthorized trades
- Steal market data API quota

### Encryption Algorithm

- **Algorithm**: Fernet (symmetric encryption with AES-128-CBC + HMAC)
- **Key Size**: 32 bytes (base64-encoded)
- **Context Binding**: Tokens bound to user_id + provider (prevents reuse)
- **Key Rotation**: Support multiple active keys for zero-downtime rotation

### Usage Examples

#### Generate Encryption Key (One-Time)

```bash
# Generate key (run once, store securely)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output (example): OqiPX5ZwLQ7OMfTlVNH9Xw2fRqH2Q9-vSX7VxXqPz0M=

# Store in environment variable
export PROVIDER_TOKEN_ENCRYPTION_KEY=OqiPX5ZwLQ7OMfTlVNH9Xw2fRqH2Q9-vSX7VxXqPz0M=
```

#### Encrypt/Decrypt Tokens

```python
from fin_infra.security import ProviderTokenEncryption

# Initialize encryption (reads PROVIDER_TOKEN_ENCRYPTION_KEY from env)
encryption = ProviderTokenEncryption()

# Encrypt Plaid token
plaid_token = "access-sandbox-abc123"
context = {"user_id": "user123", "provider": "plaid"}

encrypted = encryption.encrypt(plaid_token, context=context)
print(f"Encrypted: {encrypted[:50]}...")
# Output: Encrypted: gAAAAABmXYZ1234567890abcdefghijklmnopqrstuvwxyz...

# Decrypt token
decrypted = encryption.decrypt(encrypted, context=context)
assert decrypted == plaid_token
```

#### Store Encrypted Tokens in Database

```python
from sqlalchemy.ext.asyncio import AsyncSession
from fin_infra.security import store_provider_token, get_provider_token

# Store encrypted token
await store_provider_token(
    db=db,
    user_id="user123",
    provider="plaid",
    token="access-sandbox-abc123",
    encryption=encryption,
    expires_at=None  # Optional expiration
)

# Retrieve decrypted token
token = await get_provider_token(
    db=db,
    user_id="user123",
    provider="plaid",
    encryption=encryption
)
```

#### Context Verification (Prevents Token Reuse)

```python
# Encrypt with context
encrypted = encryption.encrypt(
    "access-token",
    context={"user_id": "user123", "provider": "plaid"}
)

# Decrypt with WRONG context -> ValueError
try:
    encryption.decrypt(
        encrypted,
        context={"user_id": "user456", "provider": "plaid"}  # Wrong user!
    )
except ValueError as e:
    print(f"Error: {e}")
    # Output: Error: Context mismatch. Token may have been tampered with...
```

#### Key Rotation (Zero Downtime)

```python
# Generate new key
new_key = Fernet.generate_key()

# Re-encrypt token with new key
re_encrypted = encryption.rotate_key(
    encrypted_token=old_encrypted,
    new_key=new_key,
    context={"user_id": "user123", "provider": "plaid"}
)

# Decrypt with new key
new_encryption = ProviderTokenEncryption(key=new_key)
token = new_encryption.decrypt(re_encrypted, context=...)
```

---

## PII Access Audit Logging

### Why Audit PII Access?

Compliance regulations (SOC 2, GDPR, GLBA) require tracking who accessed sensitive data:

- **SOC 2**: Demonstrate access controls
- **GDPR**: Track personal data access (Article 30)
- **GLBA**: Financial privacy safeguards

### Usage Examples

#### Log PII Access

```python
from fin_infra.security import log_pii_access

# Log when user views SSN
await log_pii_access(
    user_id="admin123",
    pii_type="ssn",
    action="read",
    resource="user:user456",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    success=True
)
```

#### Retrieve Audit Logs

```python
from fin_infra.security import get_audit_logs

# Get all PII access logs
all_logs = get_audit_logs(limit=100)

# Filter by user
user_logs = get_audit_logs(user_id="admin123")

# Filter by PII type
ssn_logs = get_audit_logs(pii_type="ssn")

# Filter by action
read_logs = get_audit_logs(action="read")
```

#### Audit Log in FastAPI Endpoint

```python
from fastapi import FastAPI, Depends, Request
from fin_infra.security import log_pii_access

@app.get("/users/{user_id}/ssn")
async def get_user_ssn(
    user_id: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Get user's SSN (admin only)."""

    # Log PII access
    await log_pii_access(
        user_id=current_user.id,
        pii_type="ssn",
        action="read",
        resource=f"user:{user_id}",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    # Retrieve SSN (from encrypted storage)
    ssn = await get_user_ssn(user_id)

    return {"ssn": ssn}
```

---

## Integration with Providers

### Plaid (Banking)

```python
from fin_infra.banking import easy_banking
from fin_infra.security import store_provider_token, get_provider_token

@app.post("/banking/link")
async def link_bank_account(
    public_token: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    encryption = Depends(lambda: app.state.provider_token_encryption)
):
    """Exchange Plaid public token and store encrypted."""
    banking = easy_banking(provider="plaid")

    # Exchange public token
    result = await banking.exchange_public_token(public_token)
    access_token = result["access_token"]

    # Store encrypted
    await store_provider_token(
        db, user_id, "plaid", access_token, encryption
    )

    return {"status": "linked"}

@app.get("/banking/accounts")
async def get_accounts(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    encryption = Depends(lambda: app.state.provider_token_encryption)
):
    """Get banking accounts using encrypted token."""
    # Retrieve decrypted token
    access_token = await get_provider_token(db, user_id, "plaid", encryption)

    banking = easy_banking(provider="plaid")
    accounts = await banking.get_accounts(access_token)

    return accounts
```

### Alpaca (Brokerage)

```python
from fin_infra.brokerage import easy_brokerage
from fin_infra.security import store_provider_token, get_provider_token

@app.post("/brokerage/link")
async def link_brokerage(
    api_key: str,
    api_secret: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    encryption = Depends(lambda: app.state.provider_token_encryption)
):
    """Store encrypted Alpaca credentials."""
    # Encrypt API key and secret separately
    await store_provider_token(db, user_id, "alpaca_key", api_key, encryption)
    await store_provider_token(db, user_id, "alpaca_secret", api_secret, encryption)

    return {"status": "linked"}

@app.post("/brokerage/buy")
async def buy_stock(
    symbol: str,
    quantity: int,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    encryption = Depends(lambda: app.state.provider_token_encryption)
):
    """Execute buy order using encrypted credentials."""
    # Retrieve decrypted credentials
    api_key = await get_provider_token(db, user_id, "alpaca_key", encryption)
    api_secret = await get_provider_token(db, user_id, "alpaca_secret", encryption)

    brokerage = easy_brokerage(
        provider="alpaca",
        api_key=api_key,
        api_secret=api_secret
    )

    order = await brokerage.buy(symbol, quantity)
    return order
```

---

## Configuration

### Environment Variables

```bash
# Required: Encryption key for provider tokens
PROVIDER_TOKEN_ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# Optional: PII filter settings
FINANCIAL_PII_FILTER_ENABLED=true
FINANCIAL_AUDIT_LOG_ENABLED=true
FINANCIAL_PII_MASK_EMAILS=false
FINANCIAL_PII_MASK_PHONES=false

# Optional: Audit log retention
FINANCIAL_PII_RETENTION_DAYS=90
```

### Programmatic Configuration

```python
from fin_infra.security import add_financial_security

# Custom configuration
encryption = add_financial_security(
    app,
    encryption_key=custom_key,  # Override env var
    enable_pii_filter=True,
    enable_audit_log=True,
    mask_emails=False,  # Don't mask emails
    mask_phones=False   # Don't mask phones
)
```

---

## Best Practices

### Security

1. **Store Encryption Key Securely**:
   - [X] Don't: Hardcode in source code
   - [X] Don't: Commit to Git
   - [OK] Do: Use environment variables (development)
   - [OK] Do: Use KMS (production): AWS KMS, Google Cloud KMS, Azure Key Vault

2. **Rotate Keys Regularly**:
   - [OK] Rotate encryption keys every 90 days
   - [OK] Support multiple active keys for zero-downtime rotation
   - [OK] Re-encrypt tokens after key rotation

3. **Audit PII Access**:
   - [OK] Log every PII read/write/delete
   - [OK] Include user_id, IP address, timestamp
   - [OK] Retain logs for compliance period (90 days minimum)

### Compliance

1. **PCI-DSS (Credit Cards)**:
   - [OK] Never log full card numbers (last 4 only)
   - [OK] Never log CVV codes (fully masked)
   - [OK] Encrypt card tokens at rest

2. **SOC 2 (Security Controls)**:
   - [OK] Audit all PII access
   - [OK] Encrypt sensitive data at rest and in transit
   - [OK] Implement least privilege access

3. **GDPR (Data Privacy)**:
   - [OK] Track personal data access (audit logs)
   - [OK] Support data deletion (delete tokens)
   - [OK] Minimize data retention

### Performance

1. **PII Filter Overhead**:
   - Regex matching on every log message (~1-2ms per message)
   - Use structured logging to reduce overhead
   - Disable email/phone masking if not needed

2. **Encryption Overhead**:
   - Fernet encryption: ~0.5ms per token
   - Cache decrypted tokens in memory (short TTL)
   - Use batch operations when possible

---

## Compliance Reference

### PCI-DSS Requirements

| Requirement | Implementation |
|-------------|----------------|
| **3.2**: Mask PAN when displayed | [OK] `**** **** **** 1111` |
| **3.3**: Mask PAN in logs | [OK] Automatic PII filter |
| **3.4**: Render PAN unreadable | [OK] Token encryption |
| **3.5**: Protect keys | [OK] KMS integration |
| **10.2**: Implement audit trails | [OK] PII access logging |

### SOC 2 Controls

| Control | Implementation |
|---------|----------------|
| **CC6.1**: Logical access | [OK] svc-infra auth + audit logs |
| **CC6.6**: Encryption | [OK] Token encryption at rest |
| **CC6.7**: Transmission security | [OK] HTTPS for provider APIs |
| **CC7.2**: Monitoring | [OK] PII access audit logs |

### GDPR Articles

| Article | Implementation |
|---------|----------------|
| **Article 5**: Data minimization | [OK] Encrypt tokens, mask PII |
| **Article 17**: Right to erasure | [OK] Delete provider tokens |
| **Article 30**: Records of processing | [OK] PII access audit logs |
| **Article 32**: Security measures | [OK] Encryption + masking |

---

## API Reference

### `add_financial_security()`

Configure financial security for FastAPI application.

**Signature**:
```python
def add_financial_security(
    app: FastAPI,
    encryption_key: Optional[bytes] = None,
    enable_pii_filter: bool = True,
    enable_audit_log: bool = True,
    mask_emails: bool = False,
    mask_phones: bool = False
) -> ProviderTokenEncryption
```

**Parameters**:
- `app`: FastAPI application
- `encryption_key`: Token encryption key (uses env var if None)
- `enable_pii_filter`: Enable PII masking in logs
- `enable_audit_log`: Enable PII access audit logging
- `mask_emails`: Mask email addresses in logs
- `mask_phones`: Mask phone numbers in logs

**Returns**: Configured `ProviderTokenEncryption` instance

### `FinancialPIIFilter`

Logging filter that masks financial PII.

**Signature**:
```python
class FinancialPIIFilter(logging.Filter):
    def __init__(
        self,
        mask_emails: bool = False,
        mask_phones: bool = False
    )
```

**Methods**:
- `filter(record: logging.LogRecord) -> bool`: Mask PII in log record

### `ProviderTokenEncryption`

Encrypt/decrypt provider API tokens.

**Signature**:
```python
class ProviderTokenEncryption:
    def __init__(self, key: Optional[bytes] = None)

    def encrypt(
        self,
        token: str,
        context: Optional[Dict[str, Any]] = None,
        key_id: Optional[str] = None
    ) -> str

    def decrypt(
        self,
        encrypted_token: str,
        context: Optional[Dict[str, Any]] = None,
        verify_context: bool = True
    ) -> str

    def rotate_key(
        self,
        encrypted_token: str,
        new_key: bytes,
        context: Optional[Dict[str, Any]] = None
    ) -> str

    @staticmethod
    def generate_key() -> bytes
```

### `store_provider_token()`

Store encrypted provider token in database.

**Signature**:
```python
async def store_provider_token(
    db: AsyncSession,
    user_id: str,
    provider: str,
    token: str,
    encryption: ProviderTokenEncryption,
    expires_at: Optional[datetime] = None,
    key_id: Optional[str] = None
) -> ProviderTokenMetadata
```

### `get_provider_token()`

Retrieve and decrypt provider token from database.

**Signature**:
```python
async def get_provider_token(
    db: AsyncSession,
    user_id: str,
    provider: str,
    encryption: ProviderTokenEncryption
) -> str
```

### `log_pii_access()`

Log PII access for audit trail.

**Signature**:
```python
async def log_pii_access(
    user_id: str,
    pii_type: str,
    action: str,
    resource: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> PIIAccessLog
```

---

## Troubleshooting

### PII Not Masked

**Problem**: PII appears in logs unmasked

**Solutions**:
1. Verify PII filter is enabled: `app.state.financial_pii_filter_enabled`
2. Check context keywords: SSN needs "ssn" nearby in log message
3. Add context: Instead of `logger.info("123-45-6789")`, use `logger.info("SSN: 123-45-6789")`

### Token Decryption Fails

**Problem**: `ValueError: Invalid encrypted token`

**Solutions**:
1. Verify encryption key matches: `PROVIDER_TOKEN_ENCRYPTION_KEY` env var
2. Check context matches: `{"user_id": "...", "provider": "..."}` must match encryption
3. Verify token not corrupted: Re-encrypt if needed

### High Logging Overhead

**Problem**: PII filter slows down logging

**Solutions**:
1. Reduce log volume: Use structured logging, lower log level
2. Disable email/phone masking: `mask_emails=False, mask_phones=False`
3. Use sampling: Log every Nth message in high-volume paths

---

## Related Documentation

- [svc-infra Security](../../../../svc-infra/src/svc_infra/security/)
- [svc-infra Audit Logging](../../../../svc-infra/src/svc_infra/security/audit.py)
- [Banking Provider Guide](./banking.md)
- [Brokerage Provider Guide](./brokerage.md)

---

## Support

For security issues, please report privately:
- Email: security@yourcompany.com
- Slack: #security-alerts

For general questions:
- Slack: #fin-infra-support
- Docs: https://docs.yourcompany.com/fin-infra/security
