# Compliance & Data Governance

**[!] DISCLAIMER**: This documentation provides technical guidance for handling financial data. It is **NOT a substitute for legal counsel**. Consult with qualified attorneys for compliance sign-off, especially for GLBA, FCRA, PCI-DSS, and GDPR requirements.

---

## Overview

fin-infra handles sensitive financial data from third-party providers. This guide covers:
- PII classification and boundaries
- Vendor Terms of Service requirements
- Data retention and erasure
- Integration with svc-infra for compliance tracking

## Quick Start

```python
from fastapi import FastAPI
from fin_infra.compliance import add_compliance_tracking
from fin_infra.banking import add_banking
from svc_infra.data import add_data_lifecycle, RetentionPolicy, ErasurePlan

app = FastAPI()

# 1. Enable compliance event logging
add_compliance_tracking(app)

# 2. Add banking with automatic event tracking
banking = add_banking(app, provider="teller")

# 3. Configure data lifecycle (svc-infra)
add_data_lifecycle(
    app,
    retention_jobs=[run_financial_retention],
    erasure_job=execute_financial_erasure,
)
```

---

## PII Classification

### Tier 1: High-Sensitivity PII (GLBA/FCRA regulated)

**Handled by fin-infra**:
- [OK] Account numbers (checking, savings, credit cards)
- [OK] Routing numbers
- [OK] SSN/Tax ID (last 4 digits only via identity endpoints)
- [OK] Credit scores and credit reports
- [OK] Provider access tokens (Plaid, Teller, etc.)
- [OK] Identity data (name, DOB, address when linked to financial accounts)

**Storage requirements**:
- Encrypt at rest (use svc-infra DB encryption)
- Encrypt in transit (HTTPS/TLS; Teller requires mTLS)
- Limit retention (see [Retention Policies](#retention-policies))
- Audit access (use `add_compliance_tracking`)

### Tier 2: Moderate-Sensitivity Financial Data

**Handled by fin-infra**:
- [OK] Transaction history (amounts, dates, merchants, categories)
- [OK] Account balances
- [OK] Holdings (stocks, crypto positions)
- [OK] Portfolio valuations

**Storage requirements**:
- Encrypt at rest (recommended)
- Retain for tax/legal requirements (typically 7 years)
- Soft-delete capable (use `deleted_at` column)

### Tier 3: Public/Low-Sensitivity Data

**Handled by fin-infra**:
- [OK] Market data (stock quotes, crypto prices) - publicly available
- [OK] Provider metadata (institution names, supported products)
- [OK] Aggregated/anonymized analytics

**Storage requirements**:
- Cache with TTL (recommended: 15-60 minutes for market data)
- No special retention requirements

---

## Vendor Terms of Service

### Plaid

**Key Requirements**:
- [X] **No data resale**: Cannot sell user financial data to third parties
- ⏱ **Limited retention**: Delete data when user deletes account or revokes access
- 🏷 **Attribution**: Must display "Powered by Plaid" in UI
-  **Security**: Must use HTTPS, store tokens securely (encrypted at rest)

**Implementation**:
```python
# Revoke access when user deletes account
from fin_infra.banking import easy_banking

banking = easy_banking(provider="plaid")

# On account deletion:
# 1. Revoke Plaid access token
banking.revoke_token(access_token)

# 2. Execute erasure plan (see Data Lifecycle section)
await run_erasure(session, user_id, financial_erasure_plan)
```

**Reference**: https://plaid.com/legal/

### Teller

**Key Requirements**:
- [X] **No data resale**: Financial data is user property
- ⏱ **Minimal retention**: Delete access tokens after use or on user request
-  **mTLS**: Certificate-based authentication required for production
-  **Token security**: Store access tokens encrypted

**Implementation**:
```python
from fin_infra.banking import easy_banking

# Production setup with mTLS
banking = easy_banking(
    provider="teller",
    cert_path="/secure/teller_certificate.pem",
    key_path="/secure/teller_private_key.pem",
    environment="production",
)

# Token handling: encrypt before storage
from svc_infra.security import encrypt_field
encrypted_token = encrypt_field(access_token, key=app.state.encryption_key)
```

**Reference**: https://teller.io/legal

### Alpha Vantage

**Key Requirements**:
- 🏷 **Attribution**: Must credit "Alpha Vantage" for market data
- ⏱ **Rate limits**: Free tier 25 requests/day; respect limits
- [X] **No redistribution**: Cannot resell or redistribute raw data
- [OK] **Caching allowed**: Can cache for reasonable TTL (recommend 15-60 min)

**Implementation**:
```python
from fin_infra.markets import easy_market
from svc_infra.cache import cache_read, cache_write

market = easy_market(provider="alphavantage")

# Cache with TTL to reduce API calls
@cache_read(key="quote:{symbol}", ttl=900)  # 15 minutes
def get_quote_cached(symbol: str):
    return market.quote(symbol)

# Attribution in UI
# <p>Market data powered by <a href="https://www.alphavantage.co/">Alpha Vantage</a></p>
```

**Reference**: https://www.alphavantage.co/terms_of_use/

---

## Data Lifecycle Management

fin-infra integrates with **svc-infra.data** for retention and erasure.

### Retention Policies

Use `svc_infra.data.retention` to define purge policies:

```python
from svc_infra.data import RetentionPolicy, run_retention_purge

# Example: Financial transactions (GLBA requires 7 years)
transaction_retention = RetentionPolicy(
    name="financial_transactions",
    model=Transaction,  # Your SQLAlchemy model
    older_than_days=7 * 365,  # 7 years
    soft_delete_field="deleted_at",
    hard_delete=False,  # Soft delete first, hard delete later
)

# Example: Banking access tokens (minimize exposure)
token_retention = RetentionPolicy(
    name="banking_tokens",
    model=BankingToken,
    older_than_days=90,  # 90 days inactive
    soft_delete_field="revoked_at",
    extra_where=[BankingToken.last_used_at < cutoff],
    hard_delete=True,  # Hard delete revoked tokens
)

# Schedule with svc-infra.jobs
from svc_infra.jobs import easy_jobs

async def run_financial_retention(session):
    """Retention job for financial data."""
    policies = [transaction_retention, token_retention]
    affected = await run_retention_purge(session, policies)
    logger.info(f"Retention purge affected {affected} rows")
    return affected

worker, scheduler = easy_jobs(
    app,
    retention_jobs=[run_financial_retention],
)
```

**Recommended Retention Periods**:

| Data Type | Minimum | Recommended | Justification |
|-----------|---------|-------------|---------------|
| Banking tokens | Until revoked | 90 days inactive | Minimize breach exposure |
| Transactions | 7 years | 7 years | GLBA, IRS tax records |
| Credit reports | Until user deletes | 2 years | FCRA compliance |
| Market data | N/A (public) | Cache: 15-60 min | Real-time pricing |
| Identity data | Until user deletes | Match account lifecycle | GLBA |

### Erasure Plans (GDPR/CCPA)

Use `svc_infra.data.erasure` for right-to-deletion requests:

```python
from svc_infra.data import ErasurePlan, ErasureStep, run_erasure
from sqlalchemy import delete

# Step 1: Delete banking tokens
async def erase_banking_tokens(session, user_id: str):
    stmt = delete(BankingToken).where(BankingToken.user_id == user_id)
    result = await session.execute(stmt)
    return result.rowcount

# Step 2: Delete transactions
async def erase_transactions(session, user_id: str):
    stmt = delete(Transaction).where(Transaction.user_id == user_id)
    result = await session.execute(stmt)
    return result.rowcount

# Step 3: Delete accounts
async def erase_accounts(session, user_id: str):
    stmt = delete(Account).where(Account.user_id == user_id)
    result = await session.execute(stmt)
    return result.rowcount

# Compose erasure plan
financial_erasure_plan = ErasurePlan(
    steps=[
        ErasureStep("banking_tokens", erase_banking_tokens),
        ErasureStep("transactions", erase_transactions),
        ErasureStep("accounts", erase_accounts),
    ]
)

# Execute erasure with audit
def audit_erasure(event: str, context: dict):
    logger.info(f"Compliance event: {event}", extra=context)

affected = await run_erasure(
    session,
    principal_id="user123",
    plan=financial_erasure_plan,
    on_audit=audit_erasure,
)
```

**Wire into FastAPI**:

```python
from svc_infra.data import add_data_lifecycle

add_data_lifecycle(
    app,
    retention_jobs=[run_financial_retention],
    erasure_job=lambda user_id: run_erasure(
        session, user_id, financial_erasure_plan
    ),
)
```

---

## Compliance Event Tracking

Use `add_compliance_tracking(app)` to log compliance events:

```python
from fin_infra.compliance import add_compliance_tracking

app = FastAPI()
add_compliance_tracking(app)

# Automatically logs:
# - banking.token_created: When access token issued
# - banking.token_revoked: When user revokes access
# - banking.data_accessed: When financial data fetched
# - credit.report_accessed: When credit report retrieved
# - erasure.requested: When user requests deletion
# - erasure.completed: When erasure plan finishes
```

**Custom compliance events**:

```python
from fin_infra.compliance import log_compliance_event

log_compliance_event(
    app,
    event="banking.sensitive_data_accessed",
    context={
        "user_id": "user123",
        "endpoint": "/banking/accounts",
        "provider": "plaid",
        "timestamp": datetime.utcnow().isoformat(),
    }
)
```

**Query compliance logs** (via svc-infra observability):

```python
# Logs are structured JSON via svc-infra.logging
# Query with your log aggregation tool (e.g., Grafana Loki)

# Example Loki query:
# {app="finance-api"} |= "compliance_event" | json | event="banking.data_accessed"
```

---

## Regulatory Frameworks

### GLBA (Gramm-Leach-Bliley Act)

**Scope**: Financial institutions handling consumer financial information

**Requirements**:
- Safeguards Rule: Implement security program for customer data
- Privacy Rule: Provide privacy notice, allow opt-out of sharing
- Pretexting Protection: Prevent unauthorized access through deception

**fin-infra support**:
- [OK] PII classification (Tier 1/2/3)
- [OK] Encryption in transit (HTTPS, TLS, mTLS for Teller)
- [OK] Access logging (compliance event tracking)
- [!] **Application responsible**: Privacy notices, opt-out mechanisms, encryption at rest

**Reference**: https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act

### FCRA (Fair Credit Reporting Act)

**Scope**: Consumer credit reporting agencies and users of credit reports

**Requirements**:
- Accuracy: Ensure credit data accuracy
- Permissible Purpose: Only access credit reports for lawful purposes
- Adverse Action: Notify consumers of adverse decisions based on credit data
- Security: Protect credit report data from unauthorized access

**fin-infra support**:
- [OK] Credit report handling (via `easy_credit()`)
- [OK] Compliance event logging for credit access
- [OK] Retention policy guidance (2 years recommended)
- [!] **Application responsible**: Permissible purpose checks, adverse action notices, user consent

**Reference**: https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act

### PCI-DSS (Payment Card Industry Data Security Standard)

**Scope**: Organizations storing, processing, or transmitting payment card data

**Requirements** (12 requirements, 6 control objectives):
- Build and maintain secure network
- Protect cardholder data
- Maintain vulnerability management program
- Implement strong access control measures
- Regularly monitor and test networks
- Maintain information security policy

**fin-infra support**:
- [OK] Does NOT handle raw card data (provider tokens only)
- [OK] Encryption in transit (HTTPS/TLS)
- [OK] Access logging (compliance tracking)
- [!] **Application responsible**: If storing card data, full PCI-DSS compliance required

**Reference**: https://www.pcisecuritystandards.org/

### GDPR / CCPA (Data Privacy)

**Scope**: EU residents (GDPR) and California residents (CCPA)

**Requirements**:
- Right to access personal data
- Right to deletion ("right to be forgotten")
- Data minimization
- Privacy by design

**fin-infra support**:
- [OK] Erasure plans (via svc-infra.data)
- [OK] Data export (via provider APIs: accounts, transactions)
- [OK] Compliance event logging
- [!] **Application responsible**: Privacy policy, consent management, data export UI

---

## Security Best Practices

### 1. Encryption

**At rest** (svc-infra):
```python
from svc_infra.security import add_security

# Enables field-level encryption for DB
add_security(app, enable_field_encryption=True)
```

**In transit**:
- HTTPS required (TLS 1.2+)
- Teller requires mTLS (certificate-based auth)
- Provider tokens transmitted over HTTPS only

### 2. Access Control

**Use svc-infra auth**:
```python
from svc_infra.api.fastapi.dual.protected import user_router
from svc_infra.api.fastapi.auth.guard import RequireUser

router = user_router(prefix="/banking", tags=["Banking"])

@router.get("/accounts")
async def get_accounts(user: RequireUser):
    # Only authenticated users can access
    banking = easy_banking()
    return banking.accounts(access_token=user.banking_token)
```

### 3. Audit Logging

**Enable compliance tracking**:
```python
from fin_infra.compliance import add_compliance_tracking

add_compliance_tracking(app)  # Logs all PII access
```

### 4. Token Security

**Store tokens encrypted**:
```python
# Use svc-infra encryption
from svc_infra.security import encrypt_field, decrypt_field

# Store
encrypted = encrypt_field(access_token, key=app.state.encryption_key)
await db.execute(
    insert(BankingToken).values(user_id=user_id, token=encrypted)
)

# Retrieve
row = await db.fetchone("SELECT token FROM banking_tokens WHERE user_id = ?", user_id)
access_token = decrypt_field(row["token"], key=app.state.encryption_key)
```

---

## Compliance Checklist

Before production deployment:

- [ ] **Legal review**: Consult attorney for GLBA/FCRA/PCI-DSS applicability
- [ ] **Privacy policy**: Draft and publish privacy policy (include provider ToS attribution)
- [ ] **Retention policies**: Configure and schedule retention jobs
- [ ] **Erasure plan**: Implement and test GDPR/CCPA deletion flow
- [ ] **Encryption**: Enable encryption at rest (svc-infra) and verify TLS
- [ ] **Access controls**: Require authentication for PII endpoints
- [ ] **Compliance tracking**: Enable event logging (`add_compliance_tracking`)
- [ ] **Vendor attribution**: Add "Powered by Plaid/Alpha Vantage" to UI
- [ ] **Token rotation**: Implement token refresh and revocation
- [ ] **Audit logs**: Set up log retention and monitoring (svc-infra observability)
- [ ] **Incident response**: Document breach notification procedures
- [ ] **SOC2/Certification**: If required, engage auditor (not covered by fin-infra)

---

## FAQ

**Q: Does fin-infra handle PCI-DSS compliance?**  
A: No. fin-infra does NOT handle raw payment card data. If your application stores card numbers, you must achieve PCI-DSS compliance independently.

**Q: Can I use fin-infra for HIPAA-regulated health data?**  
A: No. fin-infra is for financial data only. HIPAA compliance requires specialized healthcare infrastructure.

**Q: What happens if a provider's ToS changes?**  
A: Review provider legal pages periodically. fin-infra docs reflect ToS as of 2025-11-06; changes may require application updates.

**Q: Does `add_compliance_tracking` satisfy audit requirements?**  
A: Compliance tracking provides an audit trail, but legal compliance requires review by qualified counsel. Logs alone do not guarantee compliance.

**Q: How long should I retain financial data?**  
A: GLBA/IRS typically require 7 years for transactions. Banking tokens should be minimized (90 days inactive). Consult legal counsel for your jurisdiction.

**Q: Can I delete data immediately on user request?**  
A: GDPR/CCPA allow exceptions for legal obligations (e.g., 7-year tax retention). Erasure plans should respect regulatory minimums.

---

## Next Steps

- **Implement retention**: See [Data Lifecycle](#data-lifecycle-management)
- **Test erasure**: Run erasure plan in staging environment
- **Enable tracking**: Add `add_compliance_tracking(app)` to your app
- **Review vendor ToS**: Read Plaid, Teller, Alpha Vantage legal pages
- **Consult legal**: Get compliance sign-off from qualified attorney

---

## References

- **svc-infra data lifecycle**: `svc_infra.data` module
- **svc-infra security**: `svc_infra.security` module
- **GLBA**: https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act
- **FCRA**: https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act
- **PCI-DSS**: https://www.pcisecuritystandards.org/
- **GDPR**: https://gdpr.eu/
- **CCPA**: https://oag.ca.gov/privacy/ccpa
