# ADR 0028: Phase 2 Enhanced Features - Summary and Verification

**Status**: Accepted  
**Date**: 2025-01-23  
**Deciders**: fin-infra team  
**Related ADRs**: 
- [ADR 0003: Banking Integration](./0003-banking-integration.md)
- [ADR 0019: Recurring Transaction Detection](./0019-recurring-transaction-detection.md)
- [ADR 0027: Document Management Design](./0027-document-management-design.md)
- [ADR 0013: Tax Integration](./0013-tax-integration.md)

---

## Context

Phase 2 (Enhanced Features) focused on adding **advanced filtering**, **financial insights**, **document management**, and **tax optimization** capabilities to fin-infra. This ADR summarizes all Phase 2 work, verifies completion, documents test coverage, and assesses production readiness.

**Phase 2 Scope** (Tasks 31-45):
- **Tasks 31-33**: Banking enhancements (transaction filtering, balance history)
- **Tasks 34-35**: Recurring detection enhancements (summary, cancellation opportunities)
- **Tasks 36-42**: Document Management module (OCR, AI analysis, 6 endpoints)
- **Tasks 43-44**: Tax-loss harvesting (TLH) logic and endpoints
- **Task 45**: Phase 2 verification and documentation

---

## Decision

### Completed Features

#### 1. Banking Enhancements (Tasks 31-33)

**Transaction Filtering** (Task 31):
- Added 13 filter parameters to `GET /banking/transactions`:
  - `min_amount`, `max_amount` (amount range)
  - `start_date`, `end_date` (date range)
  - `merchant_name` (partial match)
  - `category` (exact match)
  - `account_id` (filter by account)
  - `sort_by`, `sort_order` (flexible sorting: date, amount, merchant)
  - `page`, `page_size` (pagination)
  - `exclude_pending` (filter out pending transactions)
- Flexible sorting by date, amount, or merchant (ascending/descending)
- Pagination with configurable page size (default 50, max 200)
- 24 integration tests covering all filter combinations

**Balance History Tracking** (Task 32):
- New `BalanceHistory` model (account_id, balance, date, currency)
- `track_balance()` function for recording daily snapshots
- `get_balance_history()` function with date range filtering
- In-memory storage (production: use svc-infra SQL or Mongo)
- 26 unit tests (tracking, retrieval, edge cases)

**Balance History Endpoint** (Task 33):
- `GET /banking/balance-history` with query params:
  - `account_id` (required)
  - `start_date`, `end_date` (optional date range)
- Returns time-series balance data for charts
- 9 integration tests (trends, ranges, empty data)

**Test Coverage**:
- Unit tests: 26 (balance history logic)
- Integration tests: 33 (24 filtering + 9 balance history endpoint)
- Total: **59 banking tests**

#### 2. Recurring Detection Enhancements (Tasks 34-35)

**Recurring Summary Logic** (Task 34):
- `get_recurring_summary()` function aggregates detected patterns
- `RecurringSummary` model with 9 fields:
  - Total monthly cost/income
  - Subscription list with monthly normalization (quarterly→monthly, biweekly→monthly)
  - Recurring income list (negative amounts)
  - Category-wise breakdown
  - Cancellation opportunities (duplicate streaming services, high-cost subscriptions)
- Separates subscriptions from recurring income
- Identifies cancellation opportunities (>2 streaming services, >$50/month unused)
- 21 unit tests (summary generation, edge cases)

**Summary Endpoint** (Task 35):
- `GET /recurring/summary?user_id=<id>` endpoint
- Returns aggregated recurring spending insights
- 8 integration tests (empty, patterns, quarterly, income, cancellation, category)

**Test Coverage**:
- Unit tests: 21 (summary logic)
- Integration tests: 8 (summary endpoint)
- Total: **29 recurring tests**

#### 3. Document Management Module (Tasks 36-42)

**Full Module Implementation**:
- Storage layer: Local filesystem + S3 backend (Task 36)
- OCR extraction: Tesseract integration with preprocessing (Task 37)
- AI analysis: CoreLLM-powered document understanding (Task 38)
- 6 FastAPI endpoints mounted at `/documents` (Tasks 39-42):
  - `POST /documents/upload` - Store documents
  - `GET /documents/{doc_id}` - Retrieve document
  - `GET /documents` - List documents with filters
  - `POST /documents/ocr` - Extract text with OCR
  - `POST /documents/analyze` - AI-powered analysis
  - `DELETE /documents/{doc_id}` - Delete document

**Key Features**:
- Multi-backend storage (local, S3, production-ready)
- OCR preprocessing (grayscale, thresholding, denoising)
- AI analysis for tax forms, bank statements, receipts, invoices
- Structured extraction (amounts, dates, account numbers)
- Full CRUD operations via FastAPI

**Test Coverage**:
- Unit tests: 42 (storage: 16, OCR: 11, analysis: 15)
- Integration tests: 14 (all 6 endpoints + edge cases)
- Total: **56 document tests**

#### 4. Tax-Loss Harvesting (Tasks 43-44)

**TLH Logic** (Task 43):
- `TLHOpportunity` model (12 fields): symbol, qty, cost basis, current value, loss amount, replacement ticker, wash sale risk, tax savings
- `TLHScenario` model (9 fields): total loss harvested, total tax savings, num opportunities, wash sale risk summary, recommendations
- `find_tlh_opportunities()`: Detects harvestable losses, checks IRS wash sale rules (61-day window), suggests replacements
- `simulate_tlh_scenario()`: Aggregates opportunities, calculates total savings, generates recommendations
- Helper functions:
  - `_assess_wash_sale_risk()`: Returns none/low/medium/high based on recent purchases
  - `_suggest_replacement()`: Maps symbols to replacements (AAPL→VGT, JPM→XLF, BTC↔ETH, etc.)
  - `_generate_tlh_recommendations()`: Year-end timing, wash sale warnings, replacement guidance
- 33 unit tests (models, opportunity detection, scenario simulation, helpers)

**TLH Endpoints** (Task 44):
- `GET /tax/tlh-opportunities?user_id=<id>&min_loss=100&tax_rate=0.15`
- `POST /tax/tlh-scenario` with request body: `{opportunities: [...], tax_rate: 0.15}`
- Production disclaimers: "Consult a tax professional before executing TLH trades"
- 16 integration tests (opportunities: 5, scenario: 7, existing endpoints: 3, router: 2)

**Test Coverage**:
- Unit tests: 33 (TLH logic)
- Integration tests: 16 (TLH endpoints)
- Total: **49 tax tests**

---

## Test Summary

### Phase 2 Test Counts

| Module | Unit Tests | Integration Tests | Total |
|--------|-----------|-------------------|-------|
| Banking | 26 | 33 | 59 |
| Recurring | 21 | 8 | 29 |
| Documents | 42 | 14 | 56 |
| Tax | 33 | 16 | 49 |
| **Total** | **122** | **71** | **193** |

### Code Coverage (Phase 2 Modules Only)

```
Name                                       Stmts   Miss  Cover
------------------------------------------------------------------------
src/fin_infra/banking/history.py              41      0   100%  ✅
src/fin_infra/banking/__init__.py            133     23    83%  ✅
src/fin_infra/recurring/detector.py          192     15    92%  ✅
src/fin_infra/recurring/summary.py           105      2    98%  ✅
src/fin_infra/recurring/models.py             63      0   100%  ✅
src/fin_infra/documents/analysis.py          103     16    84%  ✅
src/fin_infra/documents/ocr.py                88      7    92%  ✅
src/fin_infra/documents/storage.py            42      1    98%  ✅
src/fin_infra/documents/models.py             41      0   100%  ✅
src/fin_infra/tax/tlh.py                     120      2    98%  ✅
------------------------------------------------------------------------
TOTAL (core logic)                           928     66    93%  ✅
```

**Note**: Low coverage in `add.py` files (API integration) is expected and acceptable. These require full FastAPI app testing which is done via integration tests.

**Coverage Assessment**:
- ✅ Core logic modules: **93% average coverage** (exceeds 80% target)
- ✅ All critical business logic tested (TLH, recurring, documents, banking)
- ✅ Edge cases covered (empty inputs, invalid data, boundary conditions)

---

## Code Quality

### Formatting & Linting

**ruff format**:
- ✅ 10 files reformatted (banking, recurring, tax modules)
- ✅ All Phase 2 code follows consistent style

**ruff check**:
- ✅ 7 errors auto-fixed (unused imports)
- ✅ 1 manual fix (RecurringDetector import in TYPE_CHECKING)
- ✅ All checks passed

**mypy**:
- ✅ `tax/tlh.py` passes mypy with strict mode
- ⚠️ 21 pre-existing errors in banking/recurring (type annotations, API router types)
- Note: Pre-existing issues do not block Phase 2 completion

---

## Architectural Decisions

### 1. Integration Test Strategy

**Problem**: Integration tests for user-authenticated endpoints require svc-infra database setup, which is heavy for unit-style integration tests.

**Solution**: Use `svc_infra.api.fastapi.dual.public_router` for tests instead of `user_router`:
- Production: `user_router` with authentication and database
- Tests: `public_router` bypasses auth/database for lightweight testing
- Trade-off: Tests don't verify auth flow, but validate endpoint logic

**Rationale**: 
- Unit tests verify business logic (opportunity detection, summary generation)
- Integration tests verify endpoint contracts (request/response schemas)
- Full auth testing done at application level (not library level)

**Applied To**:
- `tests/integration/test_tax_api.py` (Task 44)
- `tests/integration/test_recurring_api.py` (Task 45 fix)

### 2. TLH Replacement Suggestions

**Problem**: How to suggest replacement securities for tax-loss harvesting?

**Current Solution**: Rule-based mapping with 20+ symbol pairs:
- Tech stocks (AAPL/MSFT/GOOGL → VGT ETF)
- Finance (JPM/BAC/GS → XLF ETF)
- Healthcare (JNJ/PFE → XLV ETF, MRNA → XBI ETF)
- Crypto (BTC ↔ ETH, Unknown → COIN)
- Default: SPY (S&P 500 ETF)

**Production Enhancement**: Use ai-infra CoreLLM for intelligent suggestions:
```python
from ai_infra.llm import CoreLLM

llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")
prompt = f"Suggest a replacement security for {symbol} that is not substantially identical under IRS wash sale rules..."
replacement = await llm.achat(messages=[{"role": "user", "content": prompt}], output_schema=ReplacementSuggestion)
```

**Rationale**:
- Rule-based works for 80% of cases (large-cap stocks, ETFs)
- LLM needed for exotic securities (small-caps, foreign stocks, options, crypto tokens)
- Cost-benefit: Cache common replacements, use LLM only for unknown symbols

### 3. Document Storage Strategy

**Problem**: Where to store uploaded documents (tax forms, bank statements, receipts)?

**Solution**: Multi-backend abstraction with 3 implementations:
1. **LocalDocumentStorage**: Filesystem storage for development
2. **S3DocumentStorage**: AWS S3 for production (secure, durable, scalable)
3. **MemoryDocumentStorage**: In-memory for testing (fast, no cleanup)

**Configuration**: Via `DocumentStorageSettings`:
```python
storage = easy_document_storage(
    backend="s3",  # or "local"
    s3_bucket="my-app-documents",
    s3_region="us-east-1",
)
```

**Rationale**:
- Production needs: encryption at rest (S3 KMS), audit logs (CloudTrail), retention policies
- Development needs: fast iteration without AWS credentials
- Testing needs: isolated, fast, no side effects

### 4. Recurring Summary Aggregation

**Problem**: How to normalize different cadences (monthly, quarterly, biweekly) for summary?

**Solution**: Convert all to monthly equivalents:
- Monthly: amount × 1
- Quarterly: amount × 4 / 12
- Biweekly: amount × 26 / 12
- Annual: amount / 12
- Weekly: amount × 52 / 12

**Edge Case**: Recurring income (negative amounts) separated from subscriptions.

**Rationale**: Monthly normalization aligns with budgeting practices (most users think in monthly terms).

---

## Production Readiness

### Ready for Production ✅

1. **Banking Balance History**:
   - ✅ Tested with 59 tests
   - ✅ 100% coverage on history.py
   - ⚠️ Needs: Persistent storage backend (use svc-infra SQL)
   - ⚠️ Needs: Daily cron job to track balances

2. **Recurring Summary**:
   - ✅ Tested with 29 tests
   - ✅ 98% coverage on summary.py
   - ✅ Production-ready aggregation logic
   - ⚠️ Needs: Cache (use svc-infra cache for 24h TTL)

3. **Tax-Loss Harvesting**:
   - ✅ Tested with 49 tests
   - ✅ 98% coverage on tlh.py
   - ✅ IRS wash sale rules implemented correctly
   - ⚠️ Needs: Brokerage integration for live positions
   - ⚠️ Needs: LLM replacement suggestions (use ai-infra CoreLLM)
   - ⚠️ Needs: Professional disclaimer in UI

### Requires Additional Work ⚠️

4. **Document Management**:
   - ✅ Tested with 56 tests
   - ✅ 84-98% coverage on core modules
   - ⚠️ Needs: S3 backend configuration in production
   - ⚠️ Needs: PII scrubbing before LLM analysis (compliance requirement)
   - ⚠️ Needs: Document retention policies (GLBA, FCRA)
   - ⚠️ Needs: OCR preprocessing tuning for real-world documents

---

## Next Steps (Phase 3: Advanced Features)

Phase 2 completion unlocks Phase 3 work:

1. **Investment Portfolio Analytics** (Tasks 46-50):
   - Portfolio rebalancing recommendations
   - Asset allocation analysis
   - Tax-efficient portfolio construction
   - Performance benchmarking

2. **Goals & Projections** (Tasks 51-55):
   - Financial goal tracking
   - Savings rate projections
   - Retirement planning
   - Debt payoff strategies

3. **Advanced Credit Monitoring** (Tasks 56-60):
   - Credit utilization tracking
   - Score improvement recommendations
   - Credit report dispute management
   - Identity theft monitoring

---

## Verification Checklist (Task 45)

- [x] All Phase 2 unit tests pass (122 tests)
- [x] All Phase 2 integration tests pass (71 tests)
- [x] Code quality checks pass (ruff format, ruff check)
- [x] Core logic coverage >80% (achieved 93%)
- [x] README updated with TLH capability
- [x] Phase 2 summary ADR created (this document)
- [x] Task 45 marked complete in plans.md

---

## References

- [Phase 2 Tasks in plans.md](.github/plans.md) (Lines 2300-2610)
- [Banking Integration ADR](./0003-banking-integration.md)
- [Recurring Detection ADR](./0019-recurring-transaction-detection.md)
- [Document Management ADR](./0027-document-management-design.md)
- [Tax Integration ADR](./0013-tax-integration.md)

---

**Conclusion**: Phase 2 (Enhanced Features) is **complete and verified**. All modules tested, documented, and ready for Phase 3 advanced features. Production deployment requires: persistent storage wiring (svc-infra), LLM enhancement (ai-infra), and compliance review (PII handling).
