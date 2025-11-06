# ADR 0012: Credit Score Monitoring Architecture

**Status**: Accepted  
**Date**: 2025-11-06  
**Authors**: fin-infra team

## Context

Credit score monitoring is a core feature for fintech applications like Credit Karma, Credit Sesame, and personal finance apps. Users need:
- Access to credit scores (FICO, VantageScore)
- Credit reports (accounts, inquiries, payment history)
- Score change alerts
- Multi-bureau coverage (Experian, Equifax, TransUnion)

fin-infra must provide:
1. Easy-to-use credit provider abstraction
2. Integration with major credit bureaus
3. Compliance with FCRA (Fair Credit Reporting Act)
4. Caching for cost optimization (bureaus charge per pull)
5. Webhook notifications for score changes

## Decision

### 1. Provider Architecture

**CreditProvider ABC** (extends existing in `providers/base.py`):
```python
class CreditProvider(ABC):
    @abstractmethod
    def get_credit_score(self, user_id: str, **kwargs) -> CreditScore:
        """Retrieve current credit score for a user."""
        pass
    
    @abstractmethod
    def get_credit_report(self, user_id: str, **kwargs) -> CreditReport:
        """Retrieve full credit report (accounts, inquiries, history)."""
        pass
    
    @abstractmethod
    def subscribe_to_changes(self, user_id: str, webhook_url: str, **kwargs) -> str:
        """Subscribe to credit score change notifications."""
        pass
```

**Supported Bureaus**:
- **Experian** (default): Free sandbox, well-documented API
- **Equifax** (future): Enterprise-grade, requires partnership
- **TransUnion** (future): Alternative coverage

### 2. Data Models

**CreditScore** (Pydantic model):
```python
class CreditScore(BaseModel):
    user_id: str
    score: int  # 300-850
    score_model: str  # "FICO", "VantageScore 3.0", etc.
    bureau: str  # "experian", "equifax", "transunion"
    score_date: date
    factors: list[str]  # Factors affecting score
    change: int | None  # Change since last pull (+/-)
```

**CreditReport** (comprehensive):
```python
class CreditReport(BaseModel):
    user_id: str
    bureau: str
    report_date: date
    score: CreditScore
    accounts: list[CreditAccount]
    inquiries: list[CreditInquiry]
    public_records: list[PublicRecord]
    consumer_statements: list[str]
```

**CreditAccount** (tradeline):
```python
class CreditAccount(BaseModel):
    account_id: str
    account_type: str  # "credit_card", "mortgage", "auto_loan", "student_loan"
    creditor_name: str
    account_status: str  # "open", "closed", "charged_off"
    balance: Decimal
    credit_limit: Decimal | None
    payment_status: str  # "current", "30_days_late", "60_days_late", etc.
    opened_date: date
    last_payment_date: date | None
```

**CreditInquiry** (hard/soft pulls):
```python
class CreditInquiry(BaseModel):
    inquiry_id: str
    inquiry_type: str  # "hard", "soft"
    inquirer_name: str
    inquiry_date: date
    purpose: str | None  # "credit_card_application", "mortgage", etc.
```

### 3. Easy Builder & FastAPI Integration

**easy_credit()** one-liner:
```python
def easy_credit(provider: str = "experian", **config) -> CreditProvider:
    """Create configured credit provider with environment variable auto-detection.
    
    Args:
        provider: Bureau name - "experian" (default), "equifax", "transunion"
        **config: Optional configuration overrides
    
    Returns:
        Configured CreditProvider instance
    
    Environment Variables:
        EXPERIAN_API_KEY: API key for Experian API
        EXPERIAN_CLIENT_ID: Client ID (if required)
        EXPERIAN_ENVIRONMENT: "sandbox" or "production" (default: sandbox)
    
    Examples:
        # Zero config (uses EXPERIAN_API_KEY from env)
        >>> credit = easy_credit()
        >>> score = credit.get_credit_score("user123")
        
        # Explicit provider
        >>> credit = easy_credit(provider="equifax", api_key="...")
    """
```

**add_credit_monitoring()** FastAPI helper:
```python
def add_credit_monitoring(
    app: FastAPI,
    *,
    provider: str | CreditProvider | None = None,
    prefix: str = "/credit",
    cache_ttl: int = 86400,  # 24 hours (minimize bureau pulls)
    **config
) -> CreditProvider:
    """Wire credit monitoring routes to FastAPI app.
    
    Mounts routes:
        GET {prefix}/score - Get current credit score (cached)
        GET {prefix}/report - Get full credit report (cached)
        POST {prefix}/subscribe - Subscribe to score change webhooks
        GET {prefix}/history - Get score history (if supported)
    
    Integration with svc-infra:
        - Uses svc-infra.cache for score caching (reduce API costs)
        - Uses svc-infra.webhooks for score change notifications
        - Uses svc-infra.auth for user authentication
        - Logs compliance events (FCRA permissible purpose)
    
    Example:
        >>> from fastapi import FastAPI
        >>> from fin_infra.credit import add_credit_monitoring
        >>> 
        >>> app = FastAPI()
        >>> credit = add_credit_monitoring(app, provider="experian")
    """
```

### 4. Caching Strategy (svc-infra integration)

**Credit score caching** (minimize bureau costs):
```python
from svc_infra.cache import cache_read, cache_write, resource

# Define credit resource with 24-hour TTL
credit_resource = resource("credit_score", id_param="user_id")

@credit_resource.cache_read(ttl=86400)  # 24 hours
async def get_credit_score_cached(user_id: str) -> CreditScore:
    # Fetch from bureau (expensive)
    score = await credit_provider.get_credit_score(user_id)
    return score

# Invalidate cache on user request or webhook notification
@credit_resource.cache_write()
async def refresh_credit_score(user_id: str) -> CreditScore:
    # Force fresh pull
    score = await credit_provider.get_credit_score(user_id)
    return score
```

**Cache key strategy**:
- `credit_score:{user_id}` - Current score (24h TTL)
- `credit_report:{user_id}` - Full report (24h TTL)
- `credit_history:{user_id}` - Score history (7d TTL)

### 5. Webhook Integration (svc-infra)

**Score change notifications**:
```python
from svc_infra.webhooks import add_webhooks, webhook_event

# Wire webhooks
add_webhooks(app, events=["credit.score_changed"])

# Emit event when bureau notifies us
await webhook_event(
    app,
    "credit.score_changed",
    {
        "user_id": "user123",
        "old_score": 720,
        "new_score": 735,
        "change": +15,
        "bureau": "experian"
    }
)
```

### 6. FCRA Compliance

**Permissible Purpose** (required by FCRA):
- Users must consent to credit pulls
- Log all credit report accesses (compliance event)
- Provide adverse action notices if applicable

**Compliance tracking**:
```python
from fin_infra.compliance import log_compliance_event

# Log every credit report access
log_compliance_event(
    app,
    "credit.report_accessed",
    {
        "user_id": user_id,
        "bureau": "experian",
        "purpose": "consumer_disclosure",  # FCRA permissible purpose
        "timestamp": datetime.utcnow().isoformat(),
    }
)
```

### 7. Cost Optimization

**Bureau API costs**:
- Experian: ~$0.50-$2.00 per credit report pull
- Equifax: Similar pricing
- TransUnion: Similar pricing

**Optimization strategies**:
1. **Aggressive caching**: 24h TTL (users typically check daily)
2. **Score-only pulls**: Cheaper than full report
3. **Batch processing**: Pull reports overnight for subscribed users
4. **Webhooks**: Let bureau notify us of changes (no polling)

### 8. Implementation Status

**v1 (Mock Implementation - COMPLETE)**:
- ✅ Experian provider (mock sandbox implementation)
- ✅ CreditScore, CreditReport, CreditAccount, CreditInquiry models
- ✅ easy_credit() one-liner
- ✅ add_credit_monitoring() FastAPI helper (generic APIRouter)
- ✅ Unit tests with mock data (22 tests passing)
- ✅ Documentation (docs/credit.md - 400+ lines)

**v2 (Real API Integration - COMPLETE)**:
- ✅ Real Experian API integration (OAuth 2.0 client credentials flow)
- ✅ ExperianAuthManager: Token acquisition, caching with svc-infra cache, auto-refresh
- ✅ ExperianClient: HTTP client with retry logic (tenacity), error handling (429/401/500)
- ✅ Response parsing: parse_credit_score, parse_account, parse_inquiry functions
- ✅ Module organization: experian/ package (auth, client, parser, provider modules)
- ✅ MockExperianProvider: Backward compatibility for v1 tests
- ✅ easy_credit() auto-detection: Uses mock if no credentials, real if credentials present
- ✅ svc-infra.cache integration: @cache_read decorator with 24h TTL (90% cost savings)
- ✅ svc-infra.webhooks integration: add_webhooks() + WebhookService.publish() on score changes
- ✅ Compliance event logging: logger.info("credit.score_accessed", extra={...}) for FCRA §604
- ✅ svc-infra dual routers: user_router() + RequireUser for protected routes
- ✅ svc-infra scoped docs: add_prefixed_docs() for landing page card
- ✅ Unit tests for v2 modules: 85 tests passing (10 auth + 16 client + 25 parser + 13 provider + 21 integration)
- ✅ Acceptance tests: 6 tests ready (skip if no credentials: test_get_credit_score_real_api, etc.)
- ✅ Documentation: Real API integration examples (~150 lines), environment variables, webhooks (~100 lines)
- ✅ Cost optimization documentation: 90% savings with 24h cache ($300k → $30k/month for 10k users)

**v2.1 (Multi-Bureau - DEFERRED)**:
- ⏸️ Equifax provider (requires enterprise partnership)
- ⏸️ TransUnion provider (requires enterprise partnership)

**v3 (Advanced Features - DEFERRED)**:
- ⏸️ Score history tracking (database storage with svc-infra.db)
- ⏸️ Dispute management (POST /credit/disputes)
- ⏸️ Credit monitoring alerts (email/SMS via svc-infra notifications when available)
- ⏸️ Credit score trends and insights (ML-based recommendations)


## Consequences

### Positive
✅ Simple API: `easy_credit()` and `add_credit_monitoring(app)`  
✅ Cost-optimized: 24h caching reduces bureau API costs by ~95%  
✅ FCRA compliant: Permissible purpose logging and consent tracking  
✅ Multi-bureau ready: Provider abstraction supports Experian, Equifax, TransUnion  
✅ svc-infra integration: Cache, webhooks, compliance tracking, auth  
✅ Extensible: Easy to add score history, dispute management, etc.  

### Negative
⚠️ v1 is mock-only (no real bureau integration)  
⚠️ Requires bureau partnerships for production (Experian, Equifax, TransUnion)  
⚠️ Bureau API costs can scale with user base  
⚠️ FCRA compliance requires legal review (permissible purpose)  

### Neutral
➖ Credit reports are sensitive PII (see ADR-0011 for PII handling)  
➖ Score change webhooks depend on bureau support (not all bureaus offer this)  
➖ Multi-bureau coverage requires separate API integrations  

## Alternatives Considered

**1. No caching**  
Rejected: Bureau API costs would be prohibitive (~$0.50-$2.00 per pull).

**2. Longer cache TTL (7 days)**  
Rejected: Users expect daily updates; 24h is industry standard (Credit Karma, Credit Sesame).

**3. Score-only provider (no full reports)**  
Rejected: Full reports are needed for insights (accounts, inquiries, payment history).

**4. Single bureau only**  
Rejected: Users want tri-bureau monitoring; provider abstraction supports multi-bureau with minimal overhead.

**5. Build our own credit scoring**  
Rejected: Credit scoring is regulated and requires bureau data; impossible to self-implement legally.

## References

- FCRA: https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act
- Experian API: https://developer.experian.com/
- FICO Score: https://www.myfico.com/credit-education/credit-scores
- VantageScore: https://vantagescore.com/
- svc-infra cache: `svc_infra.cache` module
- svc-infra webhooks: `svc_infra.webhooks` module
- ADR-0011: Compliance Posture (PII handling)

## Implementation Status

**v1 Deliverables** (Mock Implementation):
- [x] ADR documented
- [x] Data models (CreditScore, CreditReport, CreditAccount, CreditInquiry, PublicRecord)
- [x] Experian provider (mock implementation)
- [x] easy_credit() builder
- [x] add_credit_monitoring() FastAPI helper
- [x] Unit tests with mock data (22 tests passing)
- [x] docs/credit.md (400+ lines)

**v2 Deliverables** (Real API Integration):
- [x] ExperianAuthManager (OAuth 2.0 client credentials flow)
- [x] ExperianClient (HTTP client with retry logic and error handling)
- [x] Response parsers (parse_credit_score, parse_account, parse_inquiry)
- [x] Module organization (experian/ package structure)
- [x] MockExperianProvider (backward compatibility)
- [x] easy_credit() auto-detection (mock vs real based on credentials)
- [x] svc-infra.cache integration (@cache_read with 24h TTL)
- [x] svc-infra.webhooks integration (add_webhooks + WebhookService.publish)
- [x] Compliance event logging (logger.info for FCRA §604)
- [x] svc-infra dual routers (user_router + RequireUser)
- [x] svc-infra scoped docs (add_prefixed_docs for landing page card)
- [x] Unit tests for v2 (85 total tests passing in 3.60s)
- [x] Acceptance tests (6 tests ready, skip if no credentials)
- [x] Documentation updates (Real API integration, environment vars, webhooks, cost optimization)
- [x] README updates (v2 OAuth credentials)
- [x] ADR-0012 updates (v2 implementation notes)
