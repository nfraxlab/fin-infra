# ADR 0027: Document Management Design

**Status**: ✅ Accepted  
**Date**: 2024-01-15  
**Authors**: fin-infra team

---

## Context

Fintech applications need robust document management for handling tax forms, bank statements, receipts, invoices, and other financial documents. Users must be able to upload, organize, search, and extract insights from these documents. The system must support:

1. **Multiple document types**: Tax forms (W-2, 1099), bank statements, receipts, invoices, contracts, insurance documents
2. **OCR extraction**: Extract text from images and PDFs for analysis
3. **AI analysis**: Generate insights, recommendations, and summaries
4. **Secure storage**: Protect sensitive financial information
5. **Fast retrieval**: Filter by type, year, and other metadata
6. **Production scalability**: Handle thousands of documents per user

### Problem Statement

Building a document management system from scratch is complex and time-consuming. Existing solutions either:
- Lack financial-specific features (generic file storage)
- Are tightly coupled to specific providers (S3-only, Textract-only)
- Have no AI analysis capabilities
- Are difficult to test without external dependencies

We need a solution that:
- Works immediately for testing (no external services required)
- Has a clear migration path to production infrastructure
- Supports multiple OCR providers
- Integrates AI analysis for financial insights
- Follows fin-infra conventions (svc-infra for backend, ai-infra for LLM)

---

## Decision

We will implement a **modular document management system** with three layers:

### 1. Storage Layer (`storage.py`)

**Decision**: Use **in-memory dictionaries** for testing, with clear migration path to **S3 + SQL** for production.

**Rationale**:
- In-memory storage is simple, fast, and requires no setup for testing
- No external dependencies (no Redis, no S3, no SQL during development)
- Easy to clear between tests (`clear_storage()` function)
- Production migration is straightforward: swap dicts for svc-infra S3/SQL
- Separation of concerns: storage logic isolated from business logic

**Implementation**:
```python
# Testing (current)
_documents: Dict[str, Document] = {}
_file_storage: Dict[str, bytes] = {}

# Production (future)
from svc_infra.storage import S3Storage
from svc_infra.db import get_session

s3 = S3Storage(bucket="user-documents")
# SQL table for metadata with indexes
```

**Trade-offs**:
- ✅ Fast development and testing
- ✅ No external dependencies
- ✅ Clear migration path
- ❌ Data lost on restart (acceptable for testing)
- ❌ Not scalable (migration required for production)

---

### 2. OCR Layer (`ocr.py`)

**Decision**: **Simulated OCR** with mock text generation for testing, supporting multiple providers (Tesseract, AWS Textract) with different confidence levels.

**Rationale**:
- Real OCR requires pytesseract or AWS credentials (barriers to testing)
- Mock generation allows testing all code paths without external services
- Provider-specific confidence levels (Tesseract 85%, Textract 96%) simulate real-world behavior
- Tax form parsing logic can be tested independently
- Production migration is a configuration change, not a code rewrite

**Implementation**:
```python
# Testing: Generate mock text from metadata
def _generate_mock_w2_text(year, metadata):
    return f"W-2 Wage and Tax Statement\n{year}\nWages: ${metadata.get('wages', '75000')}\n..."

# Production: Call real OCR
import pytesseract  # or boto3 for Textract
text = pytesseract.image_to_string(image)
```

**Trade-offs**:
- ✅ Testable without external services
- ✅ Fast test execution
- ✅ Multiple provider support
- ✅ Realistic confidence levels
- ❌ Doesn't test actual OCR accuracy (acceptable for unit tests)

---

### 3. Analysis Layer (`analysis.py`)

**Decision**: **Rule-based analysis** for testing, with clear migration to **ai-infra CoreLLM** for production.

**Rationale**:
- Real LLM calls cost money and add latency (not suitable for unit tests)
- Rule-based logic provides deterministic, testable results
- Financial domain rules (wage extraction, tax rate calculation) can be implemented locally
- Production migration to ai-infra CoreLLM is seamless (replace analyzer function)
- Cost management (budget caps, caching) can be added at production migration time

**Implementation**:
```python
# Testing: Rule-based analysis
def _analyze_tax_document(ocr_text, metadata, document_id):
    wages = extract_wages_from_text(ocr_text)
    tax_rate = calculate_tax_rate(wages, federal_tax)
    return DocumentAnalysis(
        summary=f"W-2 for {year} showing ${wages} in wages",
        key_findings=[...],
        recommendations=[...]
    )

# Production: AI-powered analysis
from ai_infra.llm import CoreLLM

llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")
result = await llm.achat(messages=[{"role": "user", "content": prompt}], ...)
```

**Trade-offs**:
- ✅ No LLM API costs during testing
- ✅ Deterministic, predictable results
- ✅ Fast test execution
- ✅ Financial domain logic reusable in production
- ❌ Not as intelligent as real LLM (acceptable for testing)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│          (add_documents with svc-infra user_router)          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   DocumentManager          │
        │   (easy_documents builder) │
        └───────┬───────────────────┘
                │
    ┌───────────┼───────────┬───────────────┐
    │           │           │               │
    ▼           ▼           ▼               ▼
┌────────┐  ┌──────┐  ┌─────────┐  ┌──────────────┐
│Storage │  │ OCR  │  │Analysis │  │Models        │
│        │  │      │  │         │  │(Pydantic v2) │
├────────┤  ├──────┤  ├─────────┤  ├──────────────┤
│In-Mem  │  │Mock  │  │Rule-    │  │DocumentType  │
│Dicts   │  │Text  │  │Based    │  │Document      │
│        │  │Gen   │  │Logic    │  │OCRResult     │
│        │  │      │  │         │  │DocAnalysis   │
└────────┘  └──────┘  └─────────┘  └──────────────┘
    │           │           │
    ▼           ▼           ▼
Production Migration Targets:
┌────────┐  ┌──────┐  ┌─────────┐
│S3/SQL  │  │Redis │  │ai-infra │
│Storage │  │Cache │  │CoreLLM  │
└────────┘  └──────┘  └─────────┘
```

---

## Component Boundaries

### Storage Module
**Responsibility**: Document persistence (upload, download, delete, list)  
**Dependencies**: None (in-memory) → svc-infra (production)  
**Interface**: `upload(), download(), delete(), list()`

### OCR Module
**Responsibility**: Text extraction from documents  
**Dependencies**: None (mock generation) → pytesseract or boto3 (production)  
**Interface**: `extract_text(document_id, provider, force_refresh)`

### Analysis Module
**Responsibility**: Generate insights and recommendations  
**Dependencies**: None (rule-based) → ai-infra CoreLLM (production)  
**Interface**: `analyze_document(document_id, force_refresh)`

### Models Module
**Responsibility**: Data validation and serialization  
**Dependencies**: Pydantic v2  
**Interface**: `Document, DocumentType, OCRResult, DocumentAnalysis`

---

## API Design

### Endpoint Structure

```
POST   /documents/upload              # Upload new document
GET    /documents/list                # List with filters
GET    /documents/{id}                # Get metadata
DELETE /documents/{id}                # Delete document
POST   /documents/{id}/ocr            # Extract text
POST   /documents/{id}/analyze        # AI analysis
```

### Route Ordering (CRITICAL)

FastAPI matches routes in definition order. Specific routes MUST come before parameterized routes:

```python
# ✅ CORRECT: List before {document_id}
@router.get("/list")
async def list_documents(...): ...

@router.get("/{document_id}")
async def get_document(...): ...

# ❌ WRONG: {document_id} catches "list"
@router.get("/{document_id}")
async def get_document(...): ...

@router.get("/list")
async def list_documents(...): ...  # Never reached!
```

### Authentication

**Decision**: Use svc-infra `user_router` for authentication in production.

**Rationale**:
- Consistent with fin-infra conventions
- Documents contain sensitive financial data (require auth)
- user_router provides RequireUser dependency
- Integration tests can use public_router to bypass auth

```python
# Production (add.py)
from svc_infra.api.fastapi.dual.protected import user_router

router = user_router(prefix="/documents", tags=["Documents"])

# Integration tests (test_documents_api.py)
from svc_infra.api.fastapi.dual.public import public_router

router = public_router(prefix="/documents", tags=["Documents"])
```

---

## Data Flow

### Upload Flow
```
1. User uploads file via POST /documents/upload
2. Generate unique ID: doc_{uuid}
3. Calculate SHA-256 checksum
4. Detect MIME type
5. Store file bytes in _file_storage
6. Store metadata in _documents
7. Return Document model
```

### OCR Flow
```
1. User requests OCR via POST /documents/{id}/ocr
2. Check cache for existing result (key: {id}:{provider})
3. If cached and not force_refresh, return cached result
4. Retrieve document from storage
5. Call OCR provider (mock text generation or real OCR)
6. Parse structured fields (W-2, 1099)
7. Cache result
8. Return OCRResult model
```

### Analysis Flow
```
1. User requests analysis via POST /documents/{id}/analyze
2. Check cache for existing result (key: {id})
3. If cached and not force_refresh, return cached result
4. Retrieve document metadata
5. Retrieve OCR text (call extract_text if needed)
6. Route to specialized analyzer by document type
7. Generate summary, findings, recommendations
8. Validate analysis quality (confidence >= 0.7, non-empty fields)
9. Cache result
10. Return DocumentAnalysis model
```

---

## Testing Strategy

### Unit Tests (42 tests)

**Storage**: Test upload, get, download, delete, list with filters  
**OCR**: Test extraction, caching, provider selection, field parsing  
**Analysis**: Test type-specific analyzers, validation, caching

**No external dependencies**: All tests use in-memory storage and mock generation.

### Integration Tests (14 tests)

**API**: Test FastAPI endpoints with TestClient  
**Fixture**: Create app with test routes (public_router, no auth)  
**Coverage**: Upload, list, get, delete, OCR, analysis endpoints

**Key Insight**: Use `TestClient(app, raise_server_exceptions=False)` to test error responses properly.

---

## Production Migration Path

### Phase 1: Storage Migration
1. Replace `_documents` dict with SQL table (svc-infra)
2. Replace `_file_storage` dict with S3 (svc-infra)
3. Add indexes: user_id, type, upload_date
4. Implement soft-delete (deleted_at column)

### Phase 2: OCR Migration
1. Install pytesseract for Tesseract provider
2. Configure AWS credentials for Textract
3. Replace cache dict with Redis (svc-infra)
4. Set TTL to 7 days

### Phase 3: Analysis Migration
1. Replace rule-based logic with ai-infra CoreLLM
2. Implement cost tracking per user
3. Enforce budget caps ($0.10/day, $2/month)
4. Use svc-infra cache with 24h TTL
5. Add graceful degradation to rule-based fallback

### Phase 4: Security Hardening
1. Enable authentication (user_router)
2. Add rate limiting (svc-infra middleware)
3. Implement file size limits (10MB)
4. Validate MIME types on upload
5. Encrypt sensitive documents (S3 KMS)

---

## Alternatives Considered

### Alternative 1: Use S3 from Day 1

**Rejected**: Requires AWS credentials for testing, slows down development, adds complexity.

**Trade-off**: In-memory is simpler for testing, migration is straightforward.

---

### Alternative 2: Use Real LLM for Analysis

**Rejected**: Costs money per test run, adds latency, requires API keys.

**Trade-off**: Rule-based is deterministic and fast, production migration is seamless.

---

### Alternative 3: Single Unified Endpoint for All Operations

**Rejected**: RESTful separation of concerns is clearer, easier to test and secure.

**Trade-off**: Multiple endpoints follow REST conventions, better OpenAPI docs.

---

### Alternative 4: Store Files in Database BLOBs

**Rejected**: S3 is industry standard for file storage, better performance, cheaper.

**Trade-off**: SQL for metadata + S3 for files is standard practice.

---

## Consequences

### Positive

✅ **Fast development**: No external dependencies for testing  
✅ **Easy testing**: Clear storage, deterministic results  
✅ **Production-ready**: Clear migration path to svc-infra infrastructure  
✅ **Modular**: Each layer can be upgraded independently  
✅ **Cost-effective**: No LLM API costs during development  
✅ **Flexible**: Multiple OCR providers supported  

### Negative

❌ **Data loss on restart**: In-memory storage not persistent (acceptable for testing)  
❌ **Limited intelligence**: Rule-based analysis not as smart as LLM (production migration required)  
❌ **Migration required**: Production deployment needs infrastructure setup  

### Mitigations

- Document migration path clearly (Production Migration section)
- Provide production code examples (S3/SQL/LLM integration)
- Mark production TODOs in code comments
- Test suite ensures migration doesn't break functionality

---

## Compliance and Security

### Data Privacy

- **PII Handling**: Documents may contain SSN, account numbers, salaries
- **Encryption**: Production must encrypt at rest (S3 KMS)
- **Access Control**: user_router ensures users only access their own documents
- **Audit Logs**: Track all document access (svc-infra logging)

### Financial Regulations

- **Disclaimer**: All analysis includes "not a substitute for certified advisor" message
- **Accuracy**: Confidence scores help users assess reliability
- **Retention**: Compliance with tax document retention requirements (7 years IRS)

---

## Related Decisions

- [ADR 0001: fin-infra vs svc-infra Boundaries](0001-fin-infra-vs-svc-infra-boundaries.md)
- [ADR 0011: Admin Scope and Impersonation](0011-admin-scope-and-impersonation.md)
- svc-infra: Storage abstraction (S3, SQL)
- ai-infra: LLM integration (CoreLLM)

---

## Implementation Timeline

**Phase 1** (Complete): Core implementation
- ✅ Storage layer (in-memory)
- ✅ OCR layer (mock generation)
- ✅ Analysis layer (rule-based)
- ✅ Models and validation
- ✅ Unit tests (42 tests)
- ✅ Integration tests (14 tests)
- ✅ FastAPI helper (add_documents)
- ✅ Documentation (docs/documents.md, this ADR)

**Phase 2** (Future): Production migration
- [ ] S3/SQL storage
- [ ] Real OCR (pytesseract/Textract)
- [ ] ai-infra CoreLLM analysis
- [ ] Redis caching
- [ ] Security hardening
- [ ] Monitoring and alerts

---

**Decision Status**: ✅ Accepted  
**Implementation Status**: ✅ Complete (testing infrastructure) / 🔄 Pending (production migration)  
**Review Date**: 2024-06-15 (6 months after initial implementation)
