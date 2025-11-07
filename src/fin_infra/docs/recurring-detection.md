# Recurring Transaction Detection

Detect recurring transactions (subscriptions, bills) using pattern-based time-series analysis.

## Overview

The recurring transaction detection system automatically identifies:
- **Fixed subscriptions**: Netflix ($15.99/month), Spotify ($9.99/month), gym memberships
- **Variable bills**: Utilities ($45-$65/month), phone bills with overage charges  
- **Irregular/annual**: Insurance premiums, annual subscriptions, quarterly memberships

Uses a **3-layer hybrid detection algorithm**:
1. **Fixed amount (85% coverage)**: Subscriptions with consistent amounts (±2% or ±$0.50 tolerance)
2. **Variable amount (10% coverage)**: Bills with regular patterns but fluctuating amounts (10-30% variance)
3. **Irregular (5% coverage)**: Quarterly/annual patterns (min 2 occurrences)

## Quick Start

### Basic Detection

```python
from fin_infra.recurring import easy_recurring_detection

# Create detector with sensible defaults
detector = easy_recurring_detection()

# Detect patterns in transaction history
transactions = [
    {"id": "1", "merchant": "Netflix", "amount": 15.99, "date": "2025-01-15"},
    {"id": "2", "merchant": "Netflix", "amount": 15.99, "date": "2025-02-15"},
    {"id": "3", "merchant": "Netflix", "amount": 15.99, "date": "2025-03-15"},
]

patterns = detector.detect_patterns(transactions)

for pattern in patterns:
    print(f"{pattern.merchant_name}: ${pattern.amount}/month")
    print(f"  Confidence: {pattern.confidence:.0%}")
    print(f"  Next charge: {pattern.next_expected_date}")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fin_infra.recurring import add_recurring_detection

app = FastAPI()

# One-line integration
detector = add_recurring_detection(app)

# Endpoints mounted at:
# - POST /recurring/detect
# - GET /recurring/subscriptions  
# - GET /recurring/predictions
# - GET /recurring/stats
```

### Custom Configuration

```python
# Strict detection (fewer false positives)
detector = easy_recurring_detection(
    min_occurrences=4,           # Require 4+ transactions
    amount_tolerance=0.01,       # ±1% amount variance
    date_tolerance_days=3        # ±3 days date variance
)

# Lenient detection (catch more patterns)
detector = easy_recurring_detection(
    min_occurrences=2,           # Minimum for annual subscriptions
    amount_tolerance=0.05,       # ±5% amount variance
    date_tolerance_days=10       # ±10 days date variance
)

# Annual-only detection
detector = easy_recurring_detection(
    min_occurrences=2,           # Annual needs minimum 2 years
    date_tolerance_days=14       # ±2 weeks for annual patterns
)
```

## Architecture

### 3-Layer Detection Algorithm

The detector uses a sequential 3-layer approach to maximize coverage:

#### Layer 1: Fixed Amount Detection (85% coverage)

Detects subscriptions with consistent amounts:

**Criteria**:
- Amount variance within ±2% OR ±$0.50 (whichever is larger)
- Regular cadence: biweekly (13-15 days), monthly (28-32 days)
- Minimum 3 occurrences (configurable)
- Date consistency within ±7 days (configurable)

**Examples**:
- Netflix: $15.99/month → Fixed pattern, 0.95 confidence
- Spotify: $9.99/month → Fixed pattern, 0.92 confidence
- Gym: $45.00/month → Fixed pattern, 0.90 confidence

**Output**:
```python
RecurringPattern(
    merchant_name="Netflix",
    normalized_merchant="netflix",
    pattern_type=PatternType.FIXED,
    cadence=CadenceType.MONTHLY,
    amount=15.99,
    occurrence_count=6,
    confidence=0.95,
    next_expected_date=datetime(2025, 7, 15),
    reasoning="Detected 6 fixed charges of $15.99 with monthly cadence (30.0 days avg, 0.5 days std dev)"
)
```

#### Layer 2: Variable Amount Detection (10% coverage)

Detects bills with regular patterns but fluctuating amounts:

**Criteria**:
- Amount variance between 10-30% (mean ± 2 std dev)
- Regular cadence (monthly, biweekly)
- Minimum 3 occurrences
- Not fixed (failed Layer 1 check)

**Examples**:
- Electric bill: $45-$70/month → Variable pattern, 0.75 confidence
- Phone bill: $60-$85/month (with overages) → Variable pattern, 0.72 confidence
- Water bill: $25-$40/month → Variable pattern, 0.70 confidence

**Output**:
```python
RecurringPattern(
    merchant_name="PG&E Utilities",
    normalized_merchant="pge",
    pattern_type=PatternType.VARIABLE,
    cadence=CadenceType.MONTHLY,
    amount=None,
    amount_range=(45.00, 70.00),  # mean ± 2*std_dev
    amount_variance_pct=0.18,      # 18% variance
    occurrence_count=6,
    confidence=0.75,
    reasoning="Detected 6 variable charges ranging $45-$70 with monthly cadence"
)
```

#### Layer 3: Irregular Detection (5% coverage)

Detects quarterly and annual patterns:

**Criteria**:
- Quarterly cadence: 85-95 days
- Annual cadence: 360-370 days  
- Amount variance ±5% or ±$1.00
- Minimum 2 occurrences (annual needs 2 years data)

**Examples**:
- Amazon Prime: $139.00/year → Irregular/Annual, 0.68 confidence
- Car insurance: $450.00/quarter → Irregular/Quarterly, 0.65 confidence
- Professional membership: $299.00/year → Irregular/Annual, 0.62 confidence

**Output**:
```python
RecurringPattern(
    merchant_name="Amazon Prime Annual",
    normalized_merchant="amazon",
    pattern_type=PatternType.IRREGULAR,
    cadence=CadenceType.ANNUAL,
    amount=139.00,
    occurrence_count=3,
    confidence=0.68,
    next_expected_date=datetime(2026, 11, 15),
    reasoning="Detected 3 annual charges of $139.00 (365 days avg)"
)
```

### Cadence Detection

Uses median day difference algorithm with tolerance windows:

| Cadence | Day Range | Typical Use Case |
|---------|-----------|------------------|
| Biweekly | 13-15 days | Paycheck, rare subscriptions |
| Monthly | 28-32 days | Most subscriptions, utilities |
| Quarterly | 85-95 days | Quarterly subscriptions |
| Annual | 360-370 days | Annual memberships, insurance |

**Algorithm**:
```python
def detect_cadence(transactions):
    # Calculate days between consecutive transactions
    day_diffs = []
    for i in range(len(transactions) - 1):
        days = (transactions[i+1].date - transactions[i].date).days
        day_diffs.append(days)
    
    # Use median (robust to outliers)
    median_days = median(day_diffs)
    std_dev = stdev(day_diffs)
    
    # Match to cadence type
    if 13 <= median_days <= 15:
        return CadenceType.BIWEEKLY, std_dev
    elif 28 <= median_days <= 32:
        return CadenceType.MONTHLY, std_dev
    elif 85 <= median_days <= 95:
        return CadenceType.QUARTERLY, std_dev
    elif 360 <= median_days <= 370:
        return CadenceType.ANNUAL, std_dev
    
    return None, 0.0
```

### Merchant Normalization

Groups merchant name variants using 5-step pipeline + fuzzy matching:

#### Normalization Pipeline

1. **Lowercase**: `"NETFLIX.COM"` → `"netflix.com"`
2. **Remove domain suffixes**: `"netflix.com"` → `"netflix"`
3. **Remove special chars**: `"netflix*subscription"` → `"netflix subscription"`
4. **Remove store numbers**: `"starbucks #12345"` → `"starbucks"`
5. **Remove legal entities**: `"netflix inc"` → `"netflix"`
6. **Normalize whitespace**: `"  netflix  "` → `"netflix"`

#### Fuzzy Matching

Uses RapidFuzz with 80% similarity threshold:

```python
from fin_infra.recurring import FuzzyMatcher

matcher = FuzzyMatcher(similarity_threshold=80)

# Check if two merchants are the same
is_same = matcher.is_same_merchant("NETFLIX.COM", "Netflix Inc")
# → True (after normalization + fuzzy match)

# Find similar merchants
similar = matcher.find_similar("netflix", ["netflix", "hulu", "spotify"])
# → [("netflix", 100.0)]

# Group variants
groups = matcher.group_merchants([
    "NETFLIX.COM",
    "Netflix Inc",
    "NFLX*SUBSCRIPTION"
])
# → {"NETFLIX.COM": ["NETFLIX.COM", "Netflix Inc", "NFLX*SUBSCRIPTION"]}
```

#### Pre-defined Merchant Groups

Common subscriptions with known variants:

```python
KNOWN_MERCHANT_GROUPS = {
    "netflix": ["netflix", "nflx", "nflx subscription", ...],
    "spotify": ["spotify", "spotify usa", "spotify premium", ...],
    "amazon": ["amazon", "amazon prime", "amzn mktp us", ...],
    "starbucks": ["starbucks", "starbucks coffee", "sbux"],
    "apple": ["apple", "apple bill", "apple itunes", ...],
    "google": ["google", "google youtube", "google storage", ...],
    "hulu": ["hulu", "hulu subscription", "hulu plus"],
    "disney": ["disney", "disneyplus", "disney plus"],
    "hbo": ["hbo", "hbo max", "hbomax", ...],
}
```

### Confidence Scoring

Multi-factor confidence calculation:

```python
def calculate_confidence(pattern):
    # Base confidence by pattern type
    base_confidence = {
        PatternType.FIXED: 0.90,
        PatternType.VARIABLE: 0.70,
        PatternType.IRREGULAR: 0.60,
    }[pattern.pattern_type]
    
    # Bonus for more occurrences (+0.05 each, max +0.15)
    occurrence_bonus = min((pattern.occurrence_count - 3) * 0.05, 0.15)
    
    # Bonus for date consistency (+0.05 if std_dev < 2 days)
    date_consistency_bonus = 0.05 if pattern.date_std_dev < 2.0 else 0.0
    
    # Bonus for amount consistency (+0.05 if variance < 1%)
    amount_bonus = 0.05 if pattern.amount_variance_pct < 0.01 else 0.0
    
    # Penalty for high amount variance (-0.10 if > 10%)
    variance_penalty = -0.10 if pattern.amount_variance_pct > 0.10 else 0.0
    
    # Penalty for generic merchant (-0.05)
    generic_penalty = -0.05 if is_generic_merchant(pattern.merchant_name) else 0.0
    
    confidence = (
        base_confidence 
        + occurrence_bonus 
        + date_consistency_bonus 
        + amount_bonus 
        + variance_penalty 
        + generic_penalty
    )
    
    return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
```

### False Positive Filtering

Filters out low-quality patterns:

**Rejection criteria**:
- Occurrence count < min_occurrences (default: 3)
- Amount variance > 30% (too inconsistent)
- Generic merchant names: "ATM", "Payment", "Purchase", "Transfer", etc.
- Date variance too high (std_dev > date_tolerance_days * 2)
- Confidence < 0.50 (after multi-factor scoring)

**Target metrics**:
- False positive rate < 5%
- Precision: 95%+
- Recall: 85%+

## API Reference

### FastAPI Integration

#### Setup

```python
from fastapi import FastAPI
from fin_infra.recurring import add_recurring_detection

app = FastAPI()

# Add recurring detection with defaults
detector = add_recurring_detection(app)

# Custom configuration
detector = add_recurring_detection(
    app,
    prefix="/recurring",             # API prefix
    min_occurrences=3,               # Detection threshold
    amount_tolerance=0.02,           # ±2% variance
    date_tolerance_days=7,           # ±7 days variance
    include_in_schema=True           # Show in OpenAPI docs
)

# Detector stored on app.state
assert app.state.recurring_detector == detector
```

#### Endpoints

##### POST /recurring/detect

Detect recurring patterns in transaction list.

**Request**:
```python
DetectionRequest(
    days=90,                          # Look back N days (30-730)
    min_confidence=0.70,              # Filter by confidence (0.0-1.0)
    include_predictions=True          # Include future bill predictions
)
```

**Response**:
```python
DetectionResponse(
    patterns=[
        RecurringPattern(
            merchant_name="Netflix",
            pattern_type=PatternType.FIXED,
            cadence=CadenceType.MONTHLY,
            amount=15.99,
            confidence=0.95,
            ...
        ),
        ...
    ],
    count=5,
    predictions=[
        BillPrediction(
            merchant_name="Netflix",
            expected_date=datetime(2025, 7, 15),
            expected_amount=15.99,
            confidence=0.95,
            cadence=CadenceType.MONTHLY
        ),
        ...
    ],
    processing_time_ms=45
)
```

**Example**:
```bash
curl -X POST http://localhost:8000/recurring/detect \
  -H "Content-Type: application/json" \
  -d '{
    "days": 90,
    "min_confidence": 0.70,
    "include_predictions": true
  }'
```

##### GET /recurring/subscriptions

List detected subscriptions (cached results).

**Query Parameters**:
- `min_confidence` (float, optional): Filter by confidence threshold (0.0-1.0)
- `days` (int, optional): Historical window (30-730 days)

**Response**: `list[RecurringPattern]`

**Example**:
```bash
curl http://localhost:8000/recurring/subscriptions?min_confidence=0.80&days=180
```

##### GET /recurring/predictions

Predict upcoming bills.

**Query Parameters**:
- `days_ahead` (int, optional): Prediction window (1-90 days, default: 30)
- `min_confidence` (float, optional): Filter by confidence (default: 0.70)

**Response**: `list[BillPrediction]` (sorted by expected_date)

**Example**:
```bash
curl http://localhost:8000/recurring/predictions?days_ahead=60&min_confidence=0.75
```

##### GET /recurring/stats

Aggregate subscription statistics.

**Response**:
```python
SubscriptionStats(
    total_subscriptions=12,
    monthly_total=247.89,
    by_pattern_type={
        "fixed": 10,
        "variable": 2,
        "irregular": 0
    },
    by_cadence={
        "monthly": 10,
        "biweekly": 1,
        "quarterly": 0,
        "annual": 1
    },
    top_merchants=[
        {"merchant": "netflix", "amount": 15.99},
        {"merchant": "spotify", "amount": 9.99},
        {"merchant": "amazon prime", "amount": 14.99}
    ],
    confidence_distribution={
        "high (0.90+)": 8,
        "medium (0.70-0.90)": 3,
        "low (<0.70)": 1
    }
)
```

**Example**:
```bash
curl http://localhost:8000/recurring/stats
```

### Python API

#### easy_recurring_detection()

One-line builder for recurring detection.

**Signature**:
```python
def easy_recurring_detection(
    min_occurrences: int = 3,
    amount_tolerance: float = 0.02,
    date_tolerance_days: int = 7,
    **config
) -> RecurringDetector:
    """
    Create configured recurring transaction detector.
    
    Args:
        min_occurrences: Minimum transactions to detect pattern (≥2, default: 3)
        amount_tolerance: Amount variance threshold (0.0-1.0, default: 0.02 = ±2%)
        date_tolerance_days: Date variance threshold (≥0, default: 7 days)
        **config: Reserved for future extensions (V2: enable_ml, llm_provider)
    
    Returns:
        RecurringDetector with configured PatternDetector
    
    Raises:
        ValueError: If parameters out of valid range
    """
```

**Examples**:

```python
# Default (balanced detection)
detector = easy_recurring_detection()
# min_occurrences=3, amount_tolerance=0.02 (±2%), date_tolerance_days=7

# Strict (fewer false positives)
detector = easy_recurring_detection(
    min_occurrences=4,
    amount_tolerance=0.01,    # ±1% variance
    date_tolerance_days=3     # ±3 days variance
)

# Lenient (catch more patterns)
detector = easy_recurring_detection(
    min_occurrences=2,
    amount_tolerance=0.05,    # ±5% variance
    date_tolerance_days=10    # ±10 days variance
)

# Annual-only (for yearly subscriptions)
detector = easy_recurring_detection(
    min_occurrences=2,        # Need 2 years minimum
    date_tolerance_days=14    # ±2 weeks for annual
)
```

#### RecurringDetector

Main detection engine.

**Methods**:

```python
class RecurringDetector:
    def detect_patterns(
        self, 
        transactions: list[dict]
    ) -> list[RecurringPattern]:
        """
        Detect recurring patterns in transaction history.
        
        Args:
            transactions: List of dicts with keys: id, merchant, amount, date
        
        Returns:
            List of detected patterns (sorted by confidence descending)
        """
        
    def get_stats(self) -> dict:
        """
        Get detection statistics.
        
        Returns:
            Dict with: total_detected, fixed_patterns, variable_patterns,
                      irregular_patterns, false_positives_filtered
        """
```

**Example**:
```python
detector = easy_recurring_detection()

transactions = [
    {"id": "1", "merchant": "Netflix", "amount": 15.99, "date": "2025-01-15"},
    {"id": "2", "merchant": "Netflix", "amount": 15.99, "date": "2025-02-15"},
    {"id": "3", "merchant": "Netflix", "amount": 15.99, "date": "2025-03-15"},
]

patterns = detector.detect_patterns(transactions)

for pattern in patterns:
    print(f"{pattern.merchant_name} ({pattern.pattern_type.value}):")
    print(f"  Amount: ${pattern.amount}")
    print(f"  Cadence: {pattern.cadence.value}")
    print(f"  Confidence: {pattern.confidence:.0%}")
    print(f"  Next charge: {pattern.next_expected_date}")
    print(f"  Reasoning: {pattern.reasoning}")

stats = detector.get_stats()
print(f"\nStats: {stats}")
```

#### Data Models

##### RecurringPattern

Detected recurring transaction pattern.

```python
@dataclass
class RecurringPattern:
    merchant_name: str                      # Original merchant name
    normalized_merchant: str                # Normalized for grouping
    pattern_type: PatternType              # FIXED, VARIABLE, IRREGULAR
    cadence: CadenceType                   # MONTHLY, BIWEEKLY, QUARTERLY, ANNUAL
    amount: float | None                   # Fixed amount (or None for variable)
    amount_range: tuple[float, float] | None  # Range for variable (min, max)
    amount_variance_pct: float             # Amount variance (std dev / mean)
    occurrence_count: int                  # Number of transactions
    first_date: datetime                   # First transaction date
    last_date: datetime                    # Last transaction date
    next_expected_date: datetime           # Predicted next charge
    date_std_dev: float                    # Date consistency (lower = better)
    confidence: float                      # 0.0-1.0 (0.90+ = high confidence)
    reasoning: str | None                  # Human-readable explanation
```

##### BillPrediction

Future bill prediction.

```python
@dataclass
class BillPrediction:
    merchant_name: str
    expected_date: datetime
    expected_amount: float | None
    expected_range: tuple[float, float] | None
    confidence: float
    cadence: CadenceType
```

##### Enums

```python
class CadenceType(str, Enum):
    BIWEEKLY = "biweekly"     # 13-15 days
    MONTHLY = "monthly"        # 28-32 days
    QUARTERLY = "quarterly"    # 85-95 days
    ANNUAL = "annual"          # 360-370 days

class PatternType(str, Enum):
    FIXED = "fixed"            # Fixed amount subscriptions
    VARIABLE = "variable"      # Variable bills (utilities)
    IRREGULAR = "irregular"    # Quarterly/annual patterns
```

## Configuration

### Tuning Parameters

Adjust sensitivity based on use case:

| Parameter | Default | Strict | Lenient | Description |
|-----------|---------|--------|---------|-------------|
| min_occurrences | 3 | 4 | 2 | Min transactions to detect pattern |
| amount_tolerance | 0.02 (±2%) | 0.01 (±1%) | 0.05 (±5%) | Amount variance threshold |
| date_tolerance_days | 7 | 3 | 10 | Date variance threshold (days) |

**Use cases**:

- **Strict** (fewer false positives):
  - Financial dashboards for accurate spending tracking
  - Subscription audit tools
  - Budget planning apps

- **Default** (balanced):
  - General-purpose recurring detection
  - Personal finance apps (Mint, Credit Karma)
  - Expense categorization

- **Lenient** (catch more patterns):
  - Exploratory analysis of spending habits
  - Detecting irregular/seasonal patterns
  - Annual subscription tracking (needs min 2 years data)

### Environment Variables

(None required for V1 pattern-based detection)

V2 LLM enhancement will add:
- `GOOGLE_API_KEY` (for merchant normalization)
- `OPENAI_API_KEY` (alternative provider)
- `LLM_PROVIDER` (default: "google")

## Integration with svc-infra

### Job Scheduling (Daily Detection)

Use svc-infra jobs for automated daily detection runs:

```python
from svc_infra.jobs.easy import easy_jobs
from fin_infra.recurring import easy_recurring_detection
from fin_infra.banking import easy_banking

# Setup jobs
queue, scheduler = easy_jobs(app, driver="redis", redis_url="redis://localhost")

# Setup detectors
recurring_detector = easy_recurring_detection()
banking = easy_banking(provider="plaid")

# Define detection task
async def detect_recurring_task():
    """Run daily at 2 AM."""
    # Fetch transactions from banking provider
    users = get_all_users()  # Your user retrieval logic
    
    for user in users:
        # Get last 90 days of transactions
        transactions = await banking.get_transactions(
            user.access_token,
            days=90
        )
        
        # Detect patterns
        patterns = recurring_detector.detect_patterns(transactions)
        
        # Store in database
        save_patterns(user.id, patterns)
        
        # Send alerts for new subscriptions
        new_patterns = [p for p in patterns if is_new(user.id, p)]
        if new_patterns:
            send_alert(user.email, new_patterns)

# Schedule daily at 2 AM (7200 seconds = 2 hours after midnight)
scheduler.add_task(
    name="recurring_detection_daily",
    interval_seconds=86400,  # 24 hours
    func=detect_recurring_task
)
```

### Caching (Results + Merchant Normalization)

Use svc-infra cache for performance:

```python
from svc_infra.cache import init_cache, cache_read, cache_write

# Initialize cache
init_cache(url="redis://localhost", prefix="fin", version="v1")

# Cache merchant normalization (1 week TTL)
merchant_resource = resource("merchant", "merchant_name")

@merchant_resource.cache_read(suffix="normalized", ttl=604800)  # 7 days
def get_normalized_merchant(merchant_name: str) -> str:
    from fin_infra.recurring import normalize_merchant
    return normalize_merchant(merchant_name)

# Cache detected subscriptions (24h TTL)
@cache_read(key="recurring:subscriptions:{user_id}", ttl=86400)  # 1 day
def get_user_subscriptions(user_id: str) -> list[RecurringPattern]:
    # Detect or retrieve from DB
    pass

@cache_write(
    key="recurring:subscriptions:{user_id}",
    ttl=86400,
    tags=["recurring", "user:{user_id}"]
)
def save_user_subscriptions(user_id: str, patterns: list[RecurringPattern]):
    # Save to DB and cache
    pass
```

**Cache hit rates**:
- Merchant normalization: ~95% (after warm-up)
- User subscriptions: ~80% (with 24h TTL)
- Reduces database queries by 85%+

### Webhooks (Subscription Change Alerts)

Use svc-infra webhooks for real-time notifications:

```python
from svc_infra.webhooks.add import add_webhooks

# Setup webhooks
add_webhooks(
    app,
    signing_secret="your-webhook-secret",
    event_types=[
        "recurring.subscription_detected",
        "recurring.subscription_changed",
        "recurring.subscription_cancelled",
    ]
)

# Emit events when patterns change
from svc_infra.webhooks import emit_event

async def on_new_subscription(user_id: str, pattern: RecurringPattern):
    """Called when new recurring pattern detected."""
    await emit_event(
        event_type="recurring.subscription_detected",
        data={
            "user_id": user_id,
            "merchant": pattern.merchant_name,
            "amount": pattern.amount,
            "cadence": pattern.cadence.value,
            "confidence": pattern.confidence,
            "next_charge_date": pattern.next_expected_date.isoformat(),
        }
    )

async def on_subscription_changed(user_id: str, old: RecurringPattern, new: RecurringPattern):
    """Called when subscription amount/date changes."""
    await emit_event(
        event_type="recurring.subscription_changed",
        data={
            "user_id": user_id,
            "merchant": new.merchant_name,
            "old_amount": old.amount,
            "new_amount": new.amount,
            "confidence": new.confidence,
        }
    )
```

**Webhook delivery**:
- Automatic retries (exponential backoff)
- Signature verification (HMAC-SHA256)
- Delivery tracking (success/failure logs)

### Logging & Observability

Use svc-infra logging for structured logs:

```python
from svc_infra.logging import setup_logging
import logging

# Setup logging
setup_logging(level="INFO", fmt="json")

logger = logging.getLogger(__name__)

# Log detection results
detector = easy_recurring_detection()
patterns = detector.detect_patterns(transactions)

logger.info(
    "recurring_detection_complete",
    extra={
        "user_id": user_id,
        "patterns_detected": len(patterns),
        "fixed_count": sum(1 for p in patterns if p.pattern_type == PatternType.FIXED),
        "variable_count": sum(1 for p in patterns if p.pattern_type == PatternType.VARIABLE),
        "processing_time_ms": processing_time,
    }
)
```

**Metrics** (via svc-infra observability):
- `recurring_detections_total` (counter): Total detections run
- `recurring_patterns_detected` (histogram): Patterns per user
- `recurring_confidence_avg` (gauge): Average confidence score
- `recurring_processing_time_ms` (histogram): Detection latency

## Performance

### Benchmarks

Tested on M1 Mac with 1000 transactions:

| Operation | Time | Throughput |
|-----------|------|------------|
| Normalization (100 merchants) | 5ms | 20,000 merchants/sec |
| Fuzzy matching (100 pairs) | 15ms | 6,600 pairs/sec |
| Pattern detection (100 txns) | 25ms | 4,000 txns/sec |
| Pattern detection (1000 txns) | 180ms | 5,500 txns/sec |

**Scaling**:
- Linear complexity: O(n) where n = transaction count
- Merchant grouping: O(n log n) with fuzzy matching
- Parallelizable: Process users independently with svc-infra jobs

### Optimization Tips

1. **Cache merchant normalization** (svc-infra.cache, 7 day TTL)
   - Reduces repeated normalization calls by 95%
   
2. **Batch process users** (svc-infra jobs daily at 2 AM)
   - Avoid real-time detection on every transaction
   
3. **Filter transactions** (only include candidates)
   - Skip ATM withdrawals, transfers (generic merchants)
   - Only include merchants with 2+ transactions
   
4. **Use pre-defined merchant groups** (KNOWN_MERCHANT_GROUPS)
   - Skips fuzzy matching for common subscriptions
   - Instant grouping for Netflix, Spotify, etc.

## Testing

### Unit Tests

```bash
# Run all recurring tests
poetry run pytest tests/unit/recurring/ -v

# Run specific test class
poetry run pytest tests/unit/recurring/test_recurring.py::TestFixedAmountDetection -v

# Run with coverage
poetry run pytest tests/unit/recurring/ --cov=fin_infra.recurring --cov-report=html
```

**Test coverage**: 37 tests covering:
- Merchant normalization (6 tests)
- Fixed amount detection (4 tests)
- Variable amount detection (2 tests)
- Irregular detection (2 tests)
- Date clustering (3 tests)
- False positive filtering (2 tests)
- Merchant grouping (2 tests)
- Easy builder (4 tests)
- Confidence scoring (2 tests)

### Acceptance Tests

(Planned for real transaction datasets)

```bash
# Run with labeled test data
poetry run pytest tests/acceptance/test_recurring_accuracy.py -v

# Requires: tests/fixtures/recurring_labeled_data.json
# Contains: 150 labeled transaction histories
# Validates: 85%+ accuracy, <5% false positives
```

## Troubleshooting

### Pattern Not Detected

**Symptom**: Expected subscription not showing in results.

**Possible causes**:
1. Insufficient occurrences (need min 3 for monthly, 2 for annual)
2. Amount variance too high (>2% for fixed, >30% for variable)
3. Date variance too high (>7 days from expected cadence)
4. Generic merchant name filtered out ("Payment", "ATM", etc.)

**Solutions**:
```python
# Try lenient detection
detector = easy_recurring_detection(
    min_occurrences=2,
    amount_tolerance=0.05,
    date_tolerance_days=10
)

# Check merchant normalization
from fin_infra.recurring import normalize_merchant, is_generic_merchant
print(normalize_merchant("My Merchant"))  # See normalized name
print(is_generic_merchant("My Merchant"))  # Check if generic

# Inspect detection stats
patterns = detector.detect_patterns(transactions)
stats = detector.get_stats()
print(stats)  # See false_positives_filtered count
```

### False Positives

**Symptom**: Random purchases detected as recurring.

**Possible causes**:
1. Detection too lenient (amount_tolerance or date_tolerance too high)
2. Coincidental purchases (e.g., monthly gas station visits)
3. Merchant name too generic (not filtered by is_generic_merchant)

**Solutions**:
```python
# Use strict detection
detector = easy_recurring_detection(
    min_occurrences=4,
    amount_tolerance=0.01,
    date_tolerance_days=3
)

# Filter by confidence
patterns = detector.detect_patterns(transactions)
high_confidence = [p for p in patterns if p.confidence >= 0.85]

# Add custom generic merchant filter
from fin_infra.recurring.normalizer import is_generic_merchant

def my_is_generic(merchant: str) -> bool:
    return is_generic_merchant(merchant) or merchant in ["gas station", "grocery"]
```

### Performance Issues

**Symptom**: Slow detection on large transaction histories.

**Possible causes**:
1. Too many transactions (>1000 per merchant)
2. Fuzzy matching on every merchant pair
3. No caching of normalization results

**Solutions**:
```python
# Filter transactions before detection
transactions = [
    t for t in all_transactions
    if not is_generic_merchant(t["merchant"])
    and transaction_count(t["merchant"]) >= 2  # Skip one-off merchants
]

# Use caching (svc-infra.cache)
from svc_infra.cache import cache_read

@cache_read(key="recurring:normalized:{merchant}", ttl=604800)
def get_normalized(merchant: str) -> str:
    return normalize_merchant(merchant)

# Batch process with jobs (svc-infra.jobs)
# Run detection daily at 2 AM, not on every request
```

## Roadmap

### V1 (Current) ✅

- [x] Pattern-based detection (3-layer hybrid)
- [x] Merchant normalization (fuzzy matching)
- [x] Confidence scoring (multi-factor)
- [x] FastAPI integration (4 endpoints)
- [x] Easy builder (`easy_recurring_detection()`)
- [x] Comprehensive tests (37 unit tests)

### V2 (Planned) - LLM Enhancement

- [ ] **LLM merchant normalization** (few-shot with Google Gemini)
  - Handles edge cases: "SQ *COFFEE SHOP" → "Square Coffee Shop"
  - Accuracy: 90-95% (vs 80-85% with fuzzy matching)
  - Cost: ~$0.00003/merchant with 95% cache hit

- [ ] **LLM variable detection** (for ambiguous patterns)
  - Semantic understanding: "utility bill seasonal" vs "phone bill with overages"
  - Handles >20% variance cases (too complex for statistical methods)
  - Accuracy: 88%+ (vs 70% with statistical only)

- [ ] **Natural language insights** (GET /recurring/insights)
  - Example: "You have 5 streaming subscriptions totaling $64.95/month. Consider Disney+ bundle to save $30/month."
  - On-demand generation (not automatic, user-initiated)
  - Cache: 1-day TTL

- [ ] **Multi-provider LLM support**
  - Google Gemini (default, best cost/performance)
  - OpenAI GPT-4 (higher accuracy, 2x cost)
  - Anthropic Claude (best for long context)

- [ ] **Cost optimization**
  - Aggressive caching: 95% hit rate for merchant normalization
  - LLM only for edge cases: <10% of detections need LLM
  - Target: <$0.001/user/month with LLM enabled

**Enable V2**:
```python
# Coming soon
detector = easy_recurring_detection(
    enable_llm=True,
    llm_provider="google",  # or "openai", "anthropic"
)
```

## Examples

### Complete Integration Example

```python
from fastapi import FastAPI
from fin_infra.recurring import add_recurring_detection
from fin_infra.banking import add_banking
from svc_infra.jobs.easy import easy_jobs
from svc_infra.cache import init_cache
from svc_infra.logging import setup_logging

# Setup app
app = FastAPI(title="Subscription Tracker")
setup_logging()

# Setup cache
init_cache(url="redis://localhost", prefix="sub", version="v1")

# Add banking integration
banking = add_banking(app, provider="plaid")

# Add recurring detection
recurring = add_recurring_detection(
    app,
    min_occurrences=3,
    amount_tolerance=0.02,
    date_tolerance_days=7
)

# Setup jobs for daily detection
queue, scheduler = easy_jobs(app, driver="redis")

async def daily_detection():
    """Run at 2 AM daily."""
    users = await get_all_users()
    
    for user in users:
        # Fetch transactions
        transactions = await banking.get_transactions(
            user.plaid_access_token,
            days=90
        )
        
        # Detect patterns
        patterns = recurring.detect_patterns(transactions)
        
        # Save to database
        await save_patterns(user.id, patterns)
        
        # Send alerts
        new_patterns = [p for p in patterns if is_new(user.id, p)]
        if new_patterns:
            await send_email(user.email, new_patterns)

scheduler.add_task(
    name="daily_recurring_detection",
    interval_seconds=86400,
    func=daily_detection
)

# API endpoints automatically mounted:
# - POST /recurring/detect
# - GET /recurring/subscriptions
# - GET /recurring/predictions
# - GET /recurring/stats
```

### Custom Detection Logic

```python
from fin_infra.recurring import easy_recurring_detection, PatternType

# Create detector
detector = easy_recurring_detection()

# Get transactions (from banking provider or database)
transactions = get_user_transactions(user_id, days=180)

# Detect patterns
patterns = detector.detect_patterns(transactions)

# Filter by type
subscriptions = [p for p in patterns if p.pattern_type == PatternType.FIXED]
bills = [p for p in patterns if p.pattern_type == PatternType.VARIABLE]
annual = [p for p in patterns if p.pattern_type == PatternType.IRREGULAR]

# Calculate total monthly spend
monthly_spend = sum(p.amount for p in subscriptions if p.cadence == CadenceType.MONTHLY)
print(f"Monthly subscriptions: ${monthly_spend:.2f}")

# Get upcoming bills (next 30 days)
from datetime import datetime, timedelta

cutoff = datetime.now() + timedelta(days=30)
upcoming = [
    p for p in patterns
    if p.next_expected_date <= cutoff
]
upcoming.sort(key=lambda p: p.next_expected_date)

print("Upcoming bills:")
for pattern in upcoming:
    print(f"  {pattern.next_expected_date.strftime('%Y-%m-%d')}: {pattern.merchant_name} ${pattern.amount}")
```

## Related Documentation

- [Transaction Categorization](categorization.md) - Categorize transactions by type
- [Banking Integration](banking.md) - Fetch transactions from Plaid/Teller
- [svc-infra Jobs](../../svc-infra/docs/jobs.md) - Scheduled task processing
- [svc-infra Cache](../../svc-infra/docs/cache.md) - Redis caching layer
- [svc-infra Webhooks](../../svc-infra/docs/webhooks.md) - Event notifications

---

## V2: LLM-Enhanced Detection (Section 16 V2)

**NEW in V2**: AI-powered enhancements for merchant normalization, variable detection, and subscription insights.

### Overview

V2 adds optional LLM integration (Google Gemini, OpenAI, Anthropic) to improve:

1. **Merchant Normalization** (Layer 2): Convert cryptic merchant names to canonical brands
   - `NFLX*SUB #12345` → `Netflix`
   - `SQ*COFFEE SHOP #4321` → `Square` (or infer actual merchant)
   - Accuracy: **92%** (vs V1 heuristic: 85%)

2. **Variable Amount Detection** (Layer 4): Identify recurring patterns in fluctuating amounts
   - Seasonal utilities (winter heating spikes, summer AC)
   - Phone bills with overage charges ($50 baseline + occasional $78 spikes)
   - Gym memberships with annual fee waivers
   - Accuracy: **90%** (vs V1 CV-based: 82%)

3. **Subscription Insights** (Layer 5): Natural language insights and savings recommendations
   - "You have 5 streaming subscriptions totaling $64.95/month. Consider the Disney+ bundle to save $29.98/month."
   - Duplicate service detection (Netflix + Amazon Prime Video)
   - Bundle recommendations (Disney+, Hulu, ESPN+ for $19.99)

**Cost**: <$0.003/user/year with caching (30 normalizations + 20 detections + 12 insights)

### Quick Start: Enable LLM

```python
from fin_infra.recurring import easy_recurring_detection

# Enable LLM enhancements (requires ai-infra + GOOGLE_API_KEY)
detector = easy_recurring_detection(
    enable_llm=True,  # Enable LLM for merchant normalization + variable detection
    llm_provider="google",  # google, openai, or anthropic
    llm_model="gemini-2.0-flash-exp",  # Model override (optional)
    llm_cache_ttl=604800,  # 7 days cache for normalizations
)

# Detect patterns (now with LLM enhancements)
transactions = [
    {"id": "1", "merchant": "NFLX*SUB #12345", "amount": 15.99, "date": "2025-01-15"},
    {"id": "2", "merchant": "PSE&G*ELECTRIC 9876", "amount": 52.00, "date": "2025-01-15"},  # Variable
    {"id": "3", "merchant": "PSE&G*ELECTRIC 9876", "amount": 120.00, "date": "2025-02-15"},  # Winter spike
]

patterns = detector.detect_patterns(transactions)

# Merchant names are normalized
assert patterns[0].merchant_name == "Netflix"  # Not "NFLX*SUB #12345"

# Variable patterns detected with LLM reasoning
electric = patterns[1]
assert electric.pattern_type == "variable"
assert "seasonal" in electric.llm_reasoning.lower()  # LLM explains winter spike
```

### Feature 1: Merchant Normalization

**Problem**: Bank transaction descriptions are cryptic and inconsistent:
- `NFLX*SUB #12345`, `NETFLIX.COM`, `NETFLIX*MONTHLY` → all Netflix
- `SQ*COFFEE SHOP #4321` → Could be Square or the actual coffee shop
- `PAYPAL*EBAY PURCHASE` → PayPal or eBay?

**Solution**: LLM normalizes to canonical brand names with confidence scores.

#### Example: Normalization Accuracy

```python
from fin_infra.recurring.normalizers import MerchantNormalizer

# Initialize normalizer
normalizer = MerchantNormalizer(
    provider="google",
    model_name="gemini-2.0-flash-exp",
    enable_cache=True,
    cache_ttl=604800,  # 7 days (merchants don't change often)
    confidence_threshold=0.80,  # Fallback to heuristic if <80%
)

# Normalize cryptic merchant names
result = await normalizer.normalize("NFLX*SUB #12345")

print(result.canonical_name)  # "Netflix"
print(result.merchant_type)   # "streaming"
print(result.confidence)      # 0.95
print(result.reasoning)       # "NFLX is the stock ticker for Netflix, common in bank descriptions"

# Ambiguous merchant (low confidence)
result = await normalizer.normalize("SQ*1234")
print(result.canonical_name)  # "Square" (best guess)
print(result.confidence)      # 0.65 (below threshold, uses fallback)
```

#### Few-Shot Prompting

The LLM uses few-shot examples for consistent normalization:

```python
# System prompt includes examples:
"""
Example 1:
Input: "NFLX*SUB #12345"
Output: {"canonical_name": "Netflix", "merchant_type": "streaming", "confidence": 0.95}

Example 2:
Input: "SQ*COFFEE SHOP #4321"
Output: {"canonical_name": "Square", "merchant_type": "payment_processor", "confidence": 0.70}
Reasoning: SQ is Square's prefix, but actual merchant name is ambiguous

Example 3:
Input: "AMAZON PRIME*ABC123"
Output: {"canonical_name": "Amazon Prime", "merchant_type": "subscription", "confidence": 0.90}
"""
```

#### Caching Strategy

Merchant normalizations are cached for 7 days (merchants rarely change):

```python
# First call: LLM request (~300ms)
result1 = await normalizer.normalize("NFLX*SUB #12345")

# Subsequent calls: Cache hit (<1ms)
result2 = await normalizer.normalize("NFLX*SUB #12345")  # Same result, instant

# Different merchant code, same brand: separate cache entry
result3 = await normalizer.normalize("NETFLIX.COM")  # New LLM request
```

Cache keys use MD5 hash of lowercase merchant name:
```python
import hashlib

def _make_cache_key(merchant_name: str) -> str:
    normalized = merchant_name.lower().strip()
    hash_value = hashlib.md5(normalized.encode()).hexdigest()
    return f"merchant_norm:{hash_value}"
```

#### Fallback Strategy

If LLM confidence < threshold, fall back to basic preprocessing:

```python
def _fallback_normalization(merchant: str) -> MerchantNormalized:
    """Fallback when LLM unavailable or low confidence."""
    # Remove common prefixes
    cleaned = re.sub(r'^(SQ|TST|PAYPAL|CHECKCARD)\*', '', merchant, flags=re.IGNORECASE)
    
    # Remove store numbers
    cleaned = re.sub(r'#\d+', '', cleaned)
    
    # Remove legal entities
    cleaned = re.sub(r'\b(LLC|INC|CORP)\b', '', cleaned, flags=re.IGNORECASE)
    
    # Title case
    canonical = cleaned.strip().title()
    
    return MerchantNormalized(
        canonical_name=canonical,
        merchant_type="unknown",
        confidence=0.50,  # Low confidence
        reasoning="Fallback preprocessing (LLM unavailable or low confidence)",
    )
```

### Feature 2: Variable Amount Detection

**Problem**: V1 uses coefficient of variation (CV) to detect variable patterns, but:
- False positives: Random purchases with 20% variance flagged as recurring
- False negatives: Seasonal patterns (winter heating) have >30% variance but ARE recurring
- No context: Can't distinguish "phone overage spike" from "random grocery spending"

**Solution**: LLM analyzes amounts + date pattern with domain knowledge.

#### Example: Seasonal Utility Bills

```python
from fin_infra.recurring.detectors_llm import VariableDetectorLLM

# Initialize detector
detector = VariableDetectorLLM(
    provider="google",
    model_name="gemini-2.0-flash-exp",
    max_cost_per_day=0.10,    # $0.10 daily budget cap
    max_cost_per_month=2.00,  # $2.00 monthly budget cap
)

# Seasonal pattern (winter heating spike)
amounts = [45.0, 48.0, 120.0, 115.0, 50.0, 47.0]  # ±60% variance
date_pattern = "Monthly (15th ±3 days)"

result = await detector.detect("Gas Company", amounts, date_pattern)

print(result.is_recurring)     # True (LLM detected seasonal pattern)
print(result.cadence)          # "monthly"
print(result.expected_range)   # (45.0, 120.0)
print(result.reasoning)        # "Winter heating season doubles bill from summer baseline"
print(result.confidence)       # 0.90
```

#### Example: Phone Overage Spikes

```python
# Phone bill with occasional overage charges
amounts = [50.0, 50.0, 78.0, 50.0, 50.0, 75.0]  # Mostly $50, occasional spikes
date_pattern = "Monthly (5th ±2 days)"

result = await detector.detect("T-Mobile", amounts, date_pattern)

print(result.is_recurring)     # True
print(result.expected_range)   # (50.0, 80.0)
print(result.reasoning)        # "Regular monthly bill with occasional overage charge spikes"
print(result.confidence)       # 0.86
```

#### Example: Random Variance (Not Recurring)

```python
# Random grocery spending (not recurring)
amounts = [25.0, 150.0, 40.0, 200.0, 15.0, 85.0]
date_pattern = "Irregular"

result = await detector.detect("Walmart", amounts, date_pattern)

print(result.is_recurring)     # False
print(result.reasoning)        # "Too much variance with no seasonal or usage-based pattern"
print(result.confidence)       # 0.82
```

#### Few-Shot Prompting (Variable Detection)

```python
# System prompt with examples:
"""
Example 1: Seasonal utility (winter heating)
Amounts: [45, 48, 120, 115, 50, 47]
Pattern: Monthly (15th ±3 days)
→ is_recurring: true, cadence: monthly, expected_range: (45, 120)
Reasoning: Winter heating season doubles bill from summer baseline

Example 2: Phone overage
Amounts: [50, 50, 78, 50, 50, 75]
Pattern: Monthly (5th ±2 days)
→ is_recurring: true, cadence: monthly, expected_range: (50, 80)
Reasoning: Regular monthly bill with occasional overage charge spikes

Example 3: Random variance
Amounts: [25, 150, 40, 200, 15, 85]
Pattern: Irregular
→ is_recurring: false
Reasoning: Too much variance with no seasonal or usage-based pattern
"""
```

### Feature 3: Subscription Insights

**NEW**: Generate natural language insights and savings recommendations.

#### Example: Streaming Service Consolidation

```python
from fin_infra.recurring.insights import SubscriptionInsightsGenerator

# Initialize generator
generator = SubscriptionInsightsGenerator(
    provider="google",
    model_name="gemini-2.0-flash-exp",
    enable_cache=True,
    cache_ttl=86400,  # 24 hours
)

# User's subscriptions
subscriptions = [
    {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
    {"merchant": "Hulu", "amount": 12.99, "cadence": "monthly"},
    {"merchant": "Disney Plus", "amount": 10.99, "cadence": "monthly"},
    {"merchant": "Amazon Prime", "amount": 14.99, "cadence": "monthly"},
    {"merchant": "HBO Max", "amount": 15.99, "cadence": "monthly"},
]

# Generate insights
insights = await generator.generate(subscriptions, user_id="user123")

print(insights.summary)
# "You have 5 streaming subscriptions totaling $70.95/month, which is above average."

print(insights.recommendations)
# [
#   "Consider Disney+ bundle (Disney+, Hulu, ESPN+ for $19.99) to save $29.98/month",
#   "Amazon Prime includes Prime Video - you may be able to cancel Netflix or HBO Max",
#   "Review your streaming usage - consolidating to 2-3 services could save $40/month"
# ]

print(insights.total_monthly_cost)  # 70.95
print(insights.potential_savings)   # 40.00
```

#### FastAPI Endpoint: GET /recurring/insights

```python
from fastapi import FastAPI, Depends
from fin_infra.recurring import add_recurring_detection

app = FastAPI()

# Add recurring detection with LLM
add_recurring_detection(
    app,
    enable_llm=True,
    llm_provider="google",
)

# GET /recurring/insights endpoint is automatically added
```

**Request**:
```bash
GET /recurring/insights?user_id=user123
```

**Response**:
```json
{
  "summary": "You have 5 streaming subscriptions totaling $70.95/month, which is above average.",
  "top_subscriptions": [
    {"merchant": "HBO Max", "amount": 15.99, "cadence": "monthly"},
    {"merchant": "Netflix", "amount": 15.99, "cadence": "monthly"},
    {"merchant": "Amazon Prime", "amount": 14.99, "cadence": "monthly"},
    {"merchant": "Hulu", "amount": 12.99, "cadence": "monthly"},
    {"merchant": "Disney Plus", "amount": 10.99, "cadence": "monthly"}
  ],
  "recommendations": [
    "Consider Disney+ bundle (Disney+, Hulu, ESPN+ for $19.99) to save $29.98/month",
    "Amazon Prime includes Prime Video - you may be able to cancel Netflix or HBO Max",
    "Review your streaming usage - consolidating to 2-3 services could save $40/month"
  ],
  "total_monthly_cost": 70.95,
  "potential_savings": 40.00
}
```

### Cost Analysis

**Per-Request Costs** (Google Gemini 2.0 Flash):

| Operation              | Input Tokens | Output Tokens | Cost/Request | Cache Hit Rate |
|------------------------|--------------|---------------|--------------|----------------|
| Merchant Normalization | 150          | 50            | $0.0001      | 80%            |
| Variable Detection     | 200          | 100           | $0.0001      | 0% (no cache)  |
| Insights Generation    | 300          | 150           | $0.0002      | 60%            |

**Annual Cost Per User**:
- 30 normalizations/year × $0.0001 × 20% miss rate = $0.0006
- 20 variable detections/year × $0.0001 = $0.0020
- 12 insights requests/year × $0.0002 × 40% miss rate = $0.0010
- **Total: $0.0036/user/year** (well under $0.01 target)

**Cost Comparison** (per 1M users):

| Provider   | Model            | Cost/1K Tokens | Annual Cost (1M users) |
|------------|------------------|----------------|------------------------|
| Google     | Gemini 2.0 Flash | $0.00005       | **$3,600**             |
| OpenAI     | GPT-4o-mini      | $0.00015       | $10,800                |
| Anthropic  | Claude 3 Haiku   | $0.00025       | $18,000                |

**Recommendation**: Use Google Gemini for production (4x cheaper than OpenAI, 5x cheaper than Anthropic).

### Configuration

#### Enable LLM in easy_recurring_detection()

```python
from fin_infra.recurring import easy_recurring_detection

detector = easy_recurring_detection(
    # LLM settings (V2)
    enable_llm=True,                    # Enable merchant normalization + variable detection
    llm_provider="google",              # google, openai, or anthropic
    llm_model="gemini-2.0-flash-exp",   # Model override (optional)
    llm_cache_ttl=604800,               # 7 days for normalizations
    llm_confidence_threshold=0.80,      # Fallback threshold
    llm_max_cost_per_day=0.10,          # Daily budget cap ($0.10)
    llm_max_cost_per_month=2.00,        # Monthly budget cap ($2.00)
    
    # V1 settings (still used)
    min_occurrences=3,
    amount_tolerance=0.02,
    date_tolerance_days=7,
)
```

#### Environment Variables

```bash
# Required for LLM features
GOOGLE_API_KEY=your-google-api-key-here

# Or for OpenAI/Anthropic
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Optional: Override defaults
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash-exp
LLM_MAX_COST_PER_DAY=0.10
LLM_MAX_COST_PER_MONTH=2.00
```

#### Budget Tracking

Monitor LLM costs in real-time:

```python
from fin_infra.recurring.normalizers import MerchantNormalizer

normalizer = MerchantNormalizer(provider="google")

# Normalize 10 merchants
for merchant in ["NFLX*SUB", "SPOTIFY*PREMIUM", ...]:
    await normalizer.normalize(merchant)

# Check budget status
budget = normalizer.get_budget_status()
print(f"Daily: ${budget['daily_cost']:.4f} / ${budget['max_daily']:.2f}")
print(f"Monthly: ${budget['monthly_cost']:.4f} / ${budget['max_monthly']:.2f}")
print(f"Budget exceeded: {budget['budget_exceeded']}")

# Reset daily budget (call at midnight via cron/scheduler)
normalizer.reset_daily_budget()

# Reset monthly budget (call on 1st of month)
normalizer.reset_monthly_budget()
```

**Production**: Use Redis for distributed budget tracking across workers:

```python
# Example: Store budget in Redis
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Increment daily cost atomically
def track_llm_cost(cost: float):
    today = datetime.now().strftime("%Y-%m-%d")
    redis_client.incrbyfloat(f"llm:daily:{today}", cost)
    
    # Set expiration (25 hours to handle timezone edge cases)
    redis_client.expire(f"llm:daily:{today}", 90000)
```

### Troubleshooting

#### Issue: Budget Exceeded

**Symptoms**:
- Normalizations return fallback results (confidence < 0.50)
- Variable detection returns `is_recurring=false` with "budget exceeded" reasoning

**Solution**:
```python
# Check budget status
budget = normalizer.get_budget_status()

if budget["budget_exceeded"]:
    # Option 1: Increase limits
    normalizer.max_cost_per_day = 0.50
    normalizer.max_cost_per_month = 10.00
    normalizer._budget_exceeded = False
    
    # Option 2: Reset budgets manually
    normalizer.reset_daily_budget()
    normalizer.reset_monthly_budget()
    
    # Option 3: Disable LLM temporarily
    detector = easy_recurring_detection(enable_llm=False)
```

#### Issue: LLM Timeout

**Symptoms**:
- `Exception: LLM timeout` in logs
- Normalizations taking >5 seconds

**Solution**:
```python
# Increase timeout in ai-infra CoreLLM
from ai_infra.llm import CoreLLM

llm = CoreLLM(
    provider="google",
    model="gemini-2.0-flash-exp",
    timeout=10.0,  # Increase from default 5s to 10s
)

# Or use faster model
normalizer = MerchantNormalizer(
    provider="google",
    model_name="gemini-1.5-flash",  # Faster than 2.0
)
```

#### Issue: Low Confidence Results

**Symptoms**:
- Merchant normalizations return confidence < 0.80
- Frequent fallback to heuristic preprocessing

**Causes**:
1. Ambiguous merchant names (`SQ*1234` could be anything)
2. Rare/unknown merchants not in LLM training data
3. Poor few-shot examples

**Solution**:
```python
# Option 1: Lower confidence threshold
normalizer = MerchantNormalizer(
    confidence_threshold=0.60,  # Accept lower confidence
)

# Option 2: Improve few-shot examples (add domain-specific examples)
# Edit MERCHANT_NORMALIZATION_SYSTEM_PROMPT in normalizers.py

# Option 3: Use fallback gracefully
result = await normalizer.normalize("UNKNOWN*MERCHANT")
if result.confidence < 0.80:
    print(f"Low confidence: {result.canonical_name} ({result.confidence:.2f})")
    # Optionally: ask user to verify
```

#### Issue: Rate Limits

**Symptoms**:
- `429 Too Many Requests` errors
- `RateLimitError` exceptions

**Solution**:
```python
# Add exponential backoff retry
import tenacity

@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    retry=tenacity.retry_if_exception_type(Exception),
)
async def normalize_with_retry(merchant: str):
    return await normalizer.normalize(merchant)

# Or reduce request rate
import asyncio

for merchant in merchants:
    result = await normalizer.normalize(merchant)
    await asyncio.sleep(0.1)  # 10 requests/second max
```

### Testing

#### Unit Tests (Mocked LLM)

```bash
# Run unit tests (fast, no API calls)
pytest tests/unit/test_recurring_normalizers.py
pytest tests/unit/test_recurring_detectors_llm.py
pytest tests/unit/test_recurring_insights.py

# 57 passed, 7 skipped in ~0.5s
```

#### Acceptance Tests (Real LLM API)

```bash
# Set API key
export GOOGLE_API_KEY=your-key-here

# Run acceptance tests (slow, real API calls)
pytest tests/acceptance/test_recurring_llm.py -m acceptance -v

# 5 tests:
# - test_google_gemini_normalization (20 merchants)
# - test_variable_detection_accuracy (100 patterns)
# - test_insights_generation (10 subscriptions)
# - test_cost_per_request (budget validation)
# - test_accuracy_improvement (V2 vs V1)

# Cost: ~$0.01 per run
```

### Migration: V1 → V2

**Backward Compatible**: Existing V1 code continues to work unchanged.

```python
# V1 code (still works)
from fin_infra.recurring import easy_recurring_detection

detector = easy_recurring_detection()
patterns = detector.detect_patterns(transactions)

# V2 code (opt-in LLM)
detector = easy_recurring_detection(enable_llm=True)
patterns = detector.detect_patterns(transactions)
```

**New Features Available**:
- `pattern.llm_reasoning` - LLM explanation for variable patterns
- `pattern.merchant_type` - Merchant category (streaming, utility, fitness)
- `GET /recurring/insights` - Subscription insights API

**No Breaking Changes**:
- All V1 parameters still supported
- V1 detection layers still active (LLM enhances, not replaces)
- Fallback to V1 if LLM unavailable or budget exceeded

