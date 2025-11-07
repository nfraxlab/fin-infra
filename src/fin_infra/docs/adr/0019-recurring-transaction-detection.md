# ADR-0019: Recurring Transaction Detection Architecture

**Status**: Accepted  
**Date**: 2025-11-06  
**Deciders**: Development Team  
**Related**: ADR-0018 (Transaction Categorization)  

## Context

Users need automatic detection of recurring transactions (subscriptions, bills, memberships) to:
1. **Track spending**: Know total monthly recurring costs ($200/month subscriptions adds up)
2. **Avoid surprises**: Predict upcoming charges (rent due in 3 days)
3. **Identify waste**: Find unused subscriptions (Netflix + Hulu + Disney+ = $45/month)
4. **Budget planning**: Allocate funds for fixed expenses vs variable spending

**Requirements**:
- Detect 90%+ of true recurring transactions (high recall)
- False positive rate <5% (high precision)
- Processing time <100ms per 100 transactions (real-time capable)
- Confidence scoring (0.0-1.0) for user review
- Support multiple cadences (monthly, bi-weekly, quarterly, annual)
- Handle variable amounts (utilities, phone bills with seasonal variance)

**Constraints**:
- No training data available initially (no ML until V2)
- Must work with existing transaction data (merchant name, amount, date)
- Must integrate with svc-infra (jobs, cache, webhooks)

## Decision

Implement **3-layer hybrid pattern detection architecture**:

### Layer 1: Fixed Amount Subscriptions (85% coverage)
- **Pattern**: Same merchant + same amount (±2% or ±$0.50) + regular cadence
- **Examples**: Netflix $15.99, Spotify $9.99, Gym $49.99
- **Algorithm**: Group by normalized merchant → detect amount consistency + date clustering
- **Confidence**: 0.90-1.00 (high confidence due to strict matching)
- **Performance**: O(n) per merchant group, <10ms per 100 transactions

### Layer 2: Variable Amount Bills (10% coverage)
- **Pattern**: Same merchant + amount within range + regular cadence
- **Examples**: Electric $45-85, Phone $60-90, Water $30-45
- **Algorithm**: Group by merchant → calculate mean ± 2*std_dev → detect date clustering
- **Confidence**: 0.70-0.90 (medium confidence due to variance)
- **Performance**: O(n) per merchant group, <20ms per 100 transactions

### Layer 3: Irregular/Annual Subscriptions (5% coverage)
- **Pattern**: Same merchant + same amount + long cadence (90+ days)
- **Examples**: Amazon Prime annual $139, Insurance semi-annual $450
- **Algorithm**: Group by merchant → detect quarterly/annual spacing (min 2 occurrences)
- **Confidence**: 0.60-0.80 (lower confidence due to infrequency)
- **Performance**: O(n) per merchant group, <10ms per 100 transactions

### Multi-Factor Confidence Scoring

```python
def calculate_confidence(pattern: RecurringPattern) -> float:
    # Base confidence by pattern type
    base = {
        "fixed": 0.90,
        "variable": 0.70,
        "irregular": 0.60
    }[pattern.pattern_type]
    
    # Adjustments
    confidence = base
    confidence += min(0.10, (pattern.occurrence_count - 3) * 0.05)  # More occurrences = higher
    confidence += 0.05 if pattern.date_std_dev < 2 else 0  # Date consistency bonus
    confidence -= 0.10 if pattern.date_std_dev > 5 else 0  # Date variance penalty
    confidence += 0.05 if pattern.amount_variance_pct < 0.01 else 0  # Amount consistency bonus
    confidence -= 0.10 if pattern.amount_variance_pct > 0.10 else 0  # Amount variance penalty
    confidence -= 0.05 if is_generic_merchant(pattern.merchant) else 0  # Generic name penalty
    
    return max(0.0, min(1.0, confidence))
```

### Merchant Normalization Pipeline

```python
def normalize_merchant(raw_name: str) -> str:
    # 1. Lowercase
    name = raw_name.lower()
    # 2. Remove special chars
    name = re.sub(r'[^a-z0-9\s]', '', name)
    # 3. Remove store/transaction numbers
    name = re.sub(r'\s*#?\d{4,}', '', name)
    # 4. Remove legal entities (inc, llc, corp)
    name = re.sub(r'\b(inc|llc|corp|ltd|co)\b', '', name)
    # 5. Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name
```

**Fuzzy Matching** (RapidFuzz):
- Group similar merchants (80%+ similarity)
- "NETFLIX.COM" + "Netflix Inc" → "netflix" canonical
- "Starbucks #123" + "Starbucks #456" → "starbucks" canonical

### Data Models (Pydantic V2)

```python
class CadenceType(str, Enum):
    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

class PatternType(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    IRREGULAR = "irregular"

class RecurringPattern(BaseModel):
    """Detected recurring pattern."""
    merchant_name: str
    normalized_merchant: str
    pattern_type: PatternType
    cadence: CadenceType
    
    # Amount info
    amount: float | None = None  # For fixed patterns
    amount_range: tuple[float, float] | None = None  # For variable patterns
    amount_variance_pct: float
    
    # Date info
    occurrence_count: int
    first_date: datetime
    last_date: datetime
    next_expected_date: datetime
    date_std_dev: float
    
    # Confidence
    confidence: float
    reasoning: str | None = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "merchant_name": "NETFLIX.COM",
            "normalized_merchant": "netflix",
            "pattern_type": "fixed",
            "cadence": "monthly",
            "amount": 15.99,
            "amount_range": None,
            "amount_variance_pct": 0.0,
            "occurrence_count": 12,
            "first_date": "2024-01-15T00:00:00Z",
            "last_date": "2024-12-15T00:00:00Z",
            "next_expected_date": "2025-01-15T00:00:00Z",
            "date_std_dev": 0.5,
            "confidence": 0.98,
            "reasoning": "Fixed amount $15.99 charged monthly on 15th (±0 days variance)"
        }
    })

class SubscriptionDetection(BaseModel):
    """User-facing subscription detection result."""
    pattern: RecurringPattern
    historical_transactions: list[str]  # Transaction IDs
    detected_at: datetime
    user_confirmed: bool = False
    user_id: str | None = None

class BillPrediction(BaseModel):
    """Predicted future bill."""
    merchant_name: str
    expected_date: datetime
    expected_amount: float | None = None  # None for variable
    expected_range: tuple[float, float] | None = None
    confidence: float
    cadence: CadenceType
```

### Integration with svc-infra

**1. Jobs (Daily Detection)**:
```python
from svc_infra.jobs import easy_jobs

worker, scheduler = easy_jobs(driver="redis")

# Daily detection job (2 AM)
scheduler.add_task(
    name="detect_recurring_transactions",
    interval_seconds=86400,  # 24 hours
    func=detect_and_cache_recurring
)

async def detect_and_cache_recurring():
    """Detect recurring patterns for all users, cache results."""
    users = get_active_users()
    for user in users:
        transactions = get_user_transactions(user.id, days=365)
        patterns = detect_recurring(transactions)
        cache_user_subscriptions(user.id, patterns, ttl=86400)  # 24h TTL
```

**2. Cache (Detection Results)**:
```python
from svc_infra.cache import cache_read, cache_write, resource

# Resource-based caching
subscriptions = resource("subscriptions", "user_id")

@subscriptions.cache_read(ttl=86400)  # 24h TTL
def get_user_subscriptions(user_id: str) -> list[RecurringPattern]:
    """Get cached subscriptions or detect."""
    transactions = get_user_transactions(user_id, days=365)
    return detect_recurring(transactions)

@subscriptions.cache_write(tags=["subscriptions:{user_id}"])
def update_user_subscriptions(user_id: str, patterns: list[RecurringPattern]):
    """Cache detected patterns."""
    return patterns
```

**3. Webhooks (Change Alerts)**:
```python
from svc_infra.webhooks import add_webhooks

add_webhooks(app, secret="webhook-secret-key")

async def notify_subscription_changes(user_id: str, changes: list[dict]):
    """Send webhook when subscriptions change."""
    webhook_payload = {
        "event": "subscriptions.changed",
        "user_id": user_id,
        "changes": changes,
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_webhook(user_id, webhook_payload)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.dual.protected import user_router

router = user_router(prefix="/recurring", tags=["Recurring Detection"])

@router.post("/detect")
async def detect_recurring_patterns(request: DetectionRequest, user=RequireUser()):
    """Detect recurring patterns in transaction history."""
    transactions = get_user_transactions(user.id, days=request.days)
    patterns = detect_recurring(transactions)
    return {"patterns": patterns, "count": len(patterns)}

@router.get("/subscriptions")
async def get_subscriptions(user=RequireUser()):
    """Get detected subscriptions (cached)."""
    patterns = get_user_subscriptions(user.id)
    return {"subscriptions": patterns}

@router.get("/predictions")
async def get_bill_predictions(days: int = 30, user=RequireUser()):
    """Predict upcoming bills."""
    patterns = get_user_subscriptions(user.id)
    predictions = predict_next_charges(patterns, days=days)
    return {"predictions": predictions}

def add_recurring_detection(app: FastAPI, prefix="/recurring", **config):
    """One-call integration."""
    app.include_router(router, include_in_schema=True)
    add_prefixed_docs(app, prefix=prefix, title="Recurring Detection")
    return RecurringDetector(**config)
```

## Consequences

### Positive

1. **High Accuracy**: 85%+ expected (90%+ for fixed, 70%+ for variable)
2. **Fast**: <100ms per 100 transactions (real-time capable)
3. **Deterministic**: Rule-based, explainable reasoning
4. **No Training Data**: Works immediately without ML training
5. **Extensible**: Can add ML layer in V2 for edge cases
6. **User-Friendly**: Confidence scores guide user review

### Negative

1. **Rigid Thresholds**: Hard-coded 2%, ±7 days may miss edge cases
2. **No Learning**: Doesn't improve from user feedback (until V2 ML)
3. **Merchant Variants**: May struggle with complex name variations
4. **Cold Start**: Requires 3+ occurrences (misses new subscriptions)

### Neutral

1. **Complexity**: 3 layers adds code complexity vs single approach
2. **Maintenance**: Thresholds may need tuning per use case
3. **Testing**: Requires 150+ labeled test cases for validation

## Alternatives Considered

### Alternative 1: Pure ML Approach (Rejected)
**Pros**: Learns patterns, handles edge cases, improves over time  
**Cons**: Requires 10k+ labeled transactions, slower (10-50ms), black box, model drift  
**Decision**: Rejected for V1 due to lack of training data; consider for V2

### Alternative 2: Simple Threshold Matching (Rejected)
**Pros**: Simplest implementation, fastest (<1ms)  
**Cons**: Low accuracy (70-75%), high false positives (10%+), no variable amount support  
**Decision**: Rejected due to insufficient accuracy

### Alternative 3: Statistical Only (No Fuzzy Matching) (Rejected)
**Pros**: Simpler, no external dependencies (RapidFuzz)  
**Cons**: Misses merchant name variants (10-15% recall loss)  
**Decision**: Rejected; fuzzy matching critical for grouping variants

## Implementation Plan

### Phase 1: Core Detection Engine (Days 1-2)
- Implement merchant normalization pipeline
- Implement Layer 1 (fixed amount detection)
- Implement Layer 2 (variable amount detection)
- Implement Layer 3 (irregular detection)
- Implement confidence scoring

### Phase 2: Integration (Day 3)
- Create easy_recurring_detection() builder
- Create add_recurring_detection(app) FastAPI integration
- Integrate svc-infra.jobs for daily detection
- Integrate svc-infra.cache for result caching

### Phase 3: Testing (Day 4)
- Create 150+ labeled test cases
- Unit tests for each layer
- Integration tests for API endpoints
- Accuracy validation (target 85%+)

### Phase 4: Documentation (Day 5)
- docs/recurring-detection.md comprehensive guide
- API reference with examples
- Configuration tuning guide

## Success Metrics

1. **Accuracy**: 85%+ overall (95% fixed, 70% variable, 75% irregular)
2. **False Positives**: <5%
3. **Performance**: <100ms per 100 transactions
4. **Coverage**: 90%+ of true recurring transactions detected
5. **User Satisfaction**: 80%+ of shown subscriptions confirmed

## References

- Research: docs/research/recurring-transaction-detection.md
- Similar systems: Plaid, Mint, Personal Capital (80-85% accuracy benchmarks)
- Academic: "Recurring Transaction Detection" (Stanford, 2019) - 90% accuracy with ML
- Tools: RapidFuzz (fuzzy matching), scikit-learn (V2 ML)
