# Document Management

> **Status**: ✅ Complete  
> **Version**: 1.0.0  
> **Last Updated**: 2024-01-15

Financial document management system with OCR extraction and AI-powered analysis for tax forms, bank statements, receipts, and other financial documents.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Use Cases](#use-cases)
4. [Architecture](#architecture)
5. [API Reference](#api-reference)
6. [Models](#models)
7. [Storage](#storage)
8. [OCR Extraction](#ocr-extraction)
9. [AI Analysis](#ai-analysis)
10. [FastAPI Integration](#fastapi-integration)
11. [Production Migration](#production-migration)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The documents module provides a complete solution for managing financial documents in fintech applications. It handles:

- **Document Upload**: Store tax forms, bank statements, receipts, invoices, contracts, insurance docs
- **OCR Extraction**: Extract text from images/PDFs with Tesseract or AWS Textract
- **AI Analysis**: Generate insights, recommendations, and summaries
- **Secure Storage**: In-memory for testing, S3 + SQL for production
- **FastAPI Integration**: One-liner to mount full REST API

### Key Features

✅ Multiple document types (7 supported: tax, bank_statement, receipt, invoice, contract, insurance, other)  
✅ OCR text extraction with provider selection (Tesseract 85% confidence, Textract 96%)  
✅ AI-powered document analysis with insights and recommendations  
✅ Document filtering by type and year  
✅ SHA-256 checksums for integrity verification  
✅ MIME type detection  
✅ Caching for OCR and analysis results  
✅ Production-ready architecture with clear migration path

---

## Quick Start

### Installation

```bash
# fin-infra includes documents module
poetry add fin-infra

# Or from local source
cd fin-infra
poetry install
```

### Basic Usage (Programmatic)

```python
from fin_infra.documents import easy_documents, DocumentType

# Create manager
docs = easy_documents(
    storage_path="/data/documents",
    default_ocr_provider="tesseract"
)

# Upload document
with open("w2_2024.pdf", "rb") as f:
    doc = docs.upload(
        user_id="user_123",
        file=f.read(),
        document_type=DocumentType.TAX,
        filename="w2_2024.pdf",
        metadata={"year": 2024, "form_type": "W-2"}
    )

print(f"Uploaded: {doc.id}")

# Extract text via OCR
ocr_result = docs.extract_text(doc.id, provider="tesseract")
print(f"OCR confidence: {ocr_result.confidence}")

# Analyze document with AI
analysis = docs.analyze(doc.id)
print(f"Summary: {analysis.summary}")
for finding in analysis.key_findings:
    print(f"  - {finding}")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fin_infra.documents import add_documents

app = FastAPI()

# One-liner: mount all document endpoints
manager = add_documents(
    app,
    storage_path="/data/documents",
    default_ocr_provider="tesseract",
    prefix="/documents"
)

# Endpoints now available:
# POST /documents/upload
# GET /documents/list?user_id=...&type=...&year=...
# GET /documents/{document_id}
# DELETE /documents/{document_id}
# POST /documents/{document_id}/ocr
# POST /documents/{document_id}/analyze
```

---

## Use Cases

### 1. Tax Document Management

**Scenario**: Personal finance app users upload tax forms for automated analysis.

```python
# User uploads W-2
doc = docs.upload(
    user_id="user_123",
    file=w2_file_bytes,
    document_type=DocumentType.TAX,
    filename="w2_acme_corp_2024.pdf",
    metadata={"year": 2024, "form_type": "W-2", "employer": "Acme Corp"}
)

# Extract text via OCR
ocr = docs.extract_text(doc.id, provider="textract")  # Higher accuracy for tax forms

# Analyze for insights
analysis = docs.analyze(doc.id)
# Returns:
# - Summary: "W-2 for 2024 tax year showing $85,000 in wages"
# - Key findings: ["Total wages: $85,000", "Federal tax withheld: $12,750"]
# - Recommendations: ["Consider increasing 401(k) contributions", "Review W-4 withholding"]
```

### 2. Bank Statement Processing

**Scenario**: Fintech app aggregates bank statements for spending analysis.

```python
# Upload statement
doc = docs.upload(
    user_id="user_456",
    file=statement_bytes,
    document_type=DocumentType.BANK_STATEMENT,
    filename="chase_jan_2024.pdf",
    metadata={"year": 2024, "month": 1, "bank": "Chase"}
)

# Analyze spending patterns
analysis = docs.analyze(doc.id)
# Returns spending insights, recurring patterns, unusual transactions
```

### 3. Receipt Management

**Scenario**: Expense tracking app allows users to photograph receipts.

```python
# User uploads receipt photo
doc = docs.upload(
    user_id="user_789",
    file=receipt_image_bytes,
    document_type=DocumentType.RECEIPT,
    filename="starbucks_receipt.jpg",
    metadata={"merchant": "Starbucks", "date": "2024-01-15"}
)

# OCR extracts amount and items
ocr = docs.extract_text(doc.id)

# Analysis categorizes expense
analysis = docs.analyze(doc.id)
# Returns: Category suggestion, deductibility status
```

### 4. Document Organization

**Scenario**: User wants to view all tax documents from a specific year.

```python
# List all tax documents from 2024
tax_docs_2024 = docs.list(
    user_id="user_123",
    type=DocumentType.TAX,
    year=2024
)

for doc in tax_docs_2024:
    print(f"{doc.filename} - uploaded {doc.upload_date}")
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                     (add_documents)                          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   DocumentManager          │
        │   (easy_documents)         │
        └───────┬───────────────────┘
                │
    ┌───────────┼───────────┬───────────────┐
    │           │           │               │
    ▼           ▼           ▼               ▼
┌────────┐  ┌──────┐  ┌─────────┐  ┌──────────────┐
│Storage │  │ OCR  │  │Analysis │  │   Models     │
│  .py   │  │ .py  │  │  .py    │  │(Pydantic v2) │
└────────┘  └──────┘  └─────────┘  └──────────────┘
    │           │           │
    ▼           ▼           ▼
┌────────┐  ┌──────┐  ┌─────────┐
│In-Mem  │  │Cache │  │  Cache  │
│Dict    │  │Dict  │  │  Dict   │
└────────┘  └──────┘  └─────────┘

Production Migration:
┌────────┐      ┌──────┐      ┌─────────┐
│S3/SQL  │      │Redis │      │ai-infra │
│Storage │      │Cache │      │CoreLLM  │
└────────┘      └──────┘      └─────────┘
```

### Component Responsibilities

**Storage** (`storage.py`):
- Document upload with unique ID generation (`doc_{uuid}`)
- SHA-256 checksum calculation
- MIME type detection
- Retrieval, deletion, listing with filters
- In-memory storage (production: S3 for files, SQL for metadata)

**OCR** (`ocr.py`):
- Text extraction from images/PDFs
- Provider selection (Tesseract, AWS Textract)
- Tax form field parsing (W-2, 1099)
- Result caching (production: Redis with 7d TTL)

**Analysis** (`analysis.py`):
- Document analysis with insights and recommendations
- Type-specific analyzers (tax, bank statement, receipt, generic)
- Quality validation (confidence >= 0.7, non-empty fields)
- Result caching (production: Redis with 24h TTL)
- Production: Use ai-infra CoreLLM for AI-powered analysis

**Models** (`models.py`):
- Pydantic v2 models for data validation
- DocumentType enum (7 types)
- Document model (metadata)
- OCRResult model (text, confidence, fields)
- DocumentAnalysis model (summary, findings, recommendations)

---

## API Reference

### DocumentManager Class

#### `easy_documents(storage_path, default_ocr_provider) -> DocumentManager`

Factory function to create configured DocumentManager.

**Parameters:**
- `storage_path` (str): Base path for document storage (default: "/tmp/documents")
- `default_ocr_provider` (str): Default OCR provider - "tesseract" or "textract" (default: "tesseract")

**Returns:** DocumentManager instance

**Example:**
```python
from fin_infra.documents import easy_documents

docs = easy_documents(
    storage_path="/data/documents",
    default_ocr_provider="textract"
)
```

---

#### `upload(user_id, file, document_type, filename, metadata=None) -> Document`

Upload a financial document.

**Parameters:**
- `user_id` (str): User identifier
- `file` (bytes): File content
- `document_type` (DocumentType): Document type enum
- `filename` (str): Original filename
- `metadata` (Optional[dict]): Additional metadata (year, form_type, etc.)

**Returns:** Document model with generated ID, checksum, MIME type

**Raises:**
- `ValueError`: If file is empty or filename invalid

**Example:**
```python
with open("w2.pdf", "rb") as f:
    doc = docs.upload(
        user_id="user_123",
        file=f.read(),
        document_type=DocumentType.TAX,
        filename="w2.pdf",
        metadata={"year": 2024, "form_type": "W-2"}
    )
print(f"Document ID: {doc.id}")
print(f"Checksum: {doc.checksum}")
```

---

#### `download(document_id) -> bytes`

Download document file content.

**Parameters:**
- `document_id` (str): Document identifier

**Returns:** File bytes

**Raises:**
- `ValueError`: If document not found

**Example:**
```python
file_bytes = docs.download("doc_abc123")
with open("downloaded.pdf", "wb") as f:
    f.write(file_bytes)
```

---

#### `delete(document_id) -> None`

Delete document (hard delete in current implementation).

**Parameters:**
- `document_id` (str): Document identifier

**Raises:**
- `ValueError`: If document not found

**Example:**
```python
docs.delete("doc_abc123")
```

---

#### `list(user_id, type=None, year=None) -> List[Document]`

List user's documents with optional filters.

**Parameters:**
- `user_id` (str): User identifier
- `type` (Optional[DocumentType]): Filter by document type
- `year` (Optional[int]): Filter by year (extracted from metadata)

**Returns:** List of Document models, sorted by upload_date descending

**Example:**
```python
# All documents for user
all_docs = docs.list(user_id="user_123")

# Only tax documents
tax_docs = docs.list(user_id="user_123", type=DocumentType.TAX)

# Tax documents from 2024
tax_2024 = docs.list(user_id="user_123", type=DocumentType.TAX, year=2024)
```

---

#### `extract_text(document_id, provider=None, force_refresh=False) -> OCRResult`

Extract text from document using OCR.

**Parameters:**
- `document_id` (str): Document identifier
- `provider` (Optional[str]): OCR provider - "tesseract" or "textract" (default: manager's default_ocr_provider)
- `force_refresh` (bool): Bypass cache and re-extract (default: False)

**Returns:** OCRResult with text, confidence, and extracted fields

**Caching:** Results cached in-memory (production: Redis 7d TTL)

**Example:**
```python
# Use default provider
ocr = docs.extract_text("doc_abc123")

# Use specific provider
ocr = docs.extract_text("doc_abc123", provider="textract")

# Force re-extraction
ocr = docs.extract_text("doc_abc123", force_refresh=True)

print(f"Confidence: {ocr.confidence}")
print(f"Text: {ocr.text[:100]}...")
if ocr.fields:
    print(f"Extracted fields: {ocr.fields}")
```

---

#### `analyze(document_id, force_refresh=False) -> DocumentAnalysis`

Analyze document with AI for insights and recommendations.

**Parameters:**
- `document_id` (str): Document identifier
- `force_refresh` (bool): Bypass cache and re-analyze (default: False)

**Returns:** DocumentAnalysis with summary, key_findings, recommendations

**Caching:** Results cached in-memory (production: Redis 24h TTL)

**Example:**
```python
analysis = docs.analyze("doc_abc123")

print(f"Summary: {analysis.summary}")
print("Key Findings:")
for finding in analysis.key_findings:
    print(f"  - {finding}")
print("Recommendations:")
for rec in analysis.recommendations:
    print(f"  - {rec}")
```

---

## Models

### DocumentType (Enum)

```python
class DocumentType(str, Enum):
    TAX = "tax"                      # W-2, 1099, tax returns
    BANK_STATEMENT = "bank_statement"  # Monthly statements
    RECEIPT = "receipt"              # Purchase receipts
    INVOICE = "invoice"              # Bills, invoices
    CONTRACT = "contract"            # Agreements, contracts
    INSURANCE = "insurance"          # Insurance documents
    OTHER = "other"                  # Misc documents
```

---

### Document

```python
class Document(BaseModel):
    id: str                        # Format: doc_{uuid}
    user_id: str                   # User identifier
    type: DocumentType             # Document type
    filename: str                  # Original filename
    upload_date: datetime          # Upload timestamp
    size_bytes: int                # File size
    checksum: str                  # SHA-256 checksum
    mime_type: str                 # Detected MIME type
    metadata: dict                 # Additional metadata

    model_config = ConfigDict(use_enum_values=True)
```

**Example:**
```python
{
    "id": "doc_abc123",
    "user_id": "user_123",
    "type": "tax",
    "filename": "w2_2024.pdf",
    "upload_date": "2024-01-15T10:30:00",
    "size_bytes": 45678,
    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "mime_type": "application/pdf",
    "metadata": {"year": 2024, "form_type": "W-2", "employer": "Acme Corp"}
}
```

---

### OCRResult

```python
class OCRResult(BaseModel):
    document_id: str               # Associated document
    text: str                      # Extracted text
    confidence: float              # OCR confidence (0.0-1.0)
    provider: str                  # OCR provider used
    extracted_at: datetime         # Extraction timestamp
    fields: Optional[dict]         # Parsed fields (tax forms)
```

**Example:**
```python
{
    "document_id": "doc_abc123",
    "text": "W-2 Wage and Tax Statement\\n2024\\nEmployer: Acme Corp\\nWages: $85,000\\n...",
    "confidence": 0.96,
    "provider": "textract",
    "extracted_at": "2024-01-15T10:31:00",
    "fields": {
        "employer": "Acme Corp",
        "wages": "85000",
        "federal_tax": "12750",
        "state_tax": "4250"
    }
}
```

---

### DocumentAnalysis

```python
class DocumentAnalysis(BaseModel):
    document_id: str               # Associated document
    summary: str                   # Brief summary (max 250 chars)
    key_findings: List[str]        # Important findings (3-5 items)
    recommendations: List[str]     # Actionable recommendations (3-5)
    confidence: float              # Analysis confidence (0.0-1.0)
    analyzed_at: datetime          # Analysis timestamp
```

**Example:**
```python
{
    "document_id": "doc_abc123",
    "summary": "W-2 for 2024 tax year showing $85,000 in wages with effective tax rate of 20%",
    "key_findings": [
        "Total wages: $85,000",
        "Federal tax withheld: $12,750 (15% of wages)",
        "Effective tax rate: 20%",
        "No state disability insurance reported"
    ],
    "recommendations": [
        "Consider increasing 401(k) contributions to lower taxable income",
        "Review W-4 withholding - may be over-withholding",
        "Consult with tax professional about HSA eligibility",
        "Note: This is not a substitute for advice from a certified financial advisor or tax professional"
    ],
    "confidence": 0.92,
    "analyzed_at": "2024-01-15T10:32:00"
}
```

---

## Storage

### In-Memory Implementation (Current)

**Purpose**: Testing and development

**Structure:**
- `_documents`: Dict[str, Document] - Document metadata by ID
- `_file_storage`: Dict[str, bytes] - File content by ID

**Benefits:**
- Fast and simple
- No external dependencies
- Easy to clear between tests

**Limitations:**
- Data lost on restart
- Not scalable for production
- No persistence

### Production Migration

**Recommended Architecture:**

```python
# Use svc-infra for production storage
from svc_infra.storage import S3Storage
from svc_infra.db import get_session

# Store files in S3
s3 = S3Storage(bucket="user-documents")
file_url = s3.upload(key=f"documents/{doc.id}", content=file_bytes)

# Store metadata in SQL
async with get_session() as session:
    db_doc = DocumentModel(
        id=doc.id,
        user_id=doc.user_id,
        type=doc.type,
        filename=doc.filename,
        s3_url=file_url,
        checksum=doc.checksum,
        size_bytes=doc.size_bytes,
        metadata=doc.metadata
    )
    session.add(db_doc)
    await session.commit()
```

**Benefits:**
- S3: Scalable, durable file storage
- SQL: Queryable metadata with indexes
- svc-infra: Battle-tested infrastructure

---

## OCR Extraction

### Providers

**Tesseract** (default):
- Open-source OCR engine
- 85% typical confidence
- Free, runs locally
- Good for clear scans

**AWS Textract**:
- Cloud-based OCR service
- 96% typical confidence
- Paid service (AWS pricing)
- Superior for complex layouts, handwriting

### Usage

```python
# Use Tesseract (default)
ocr = docs.extract_text("doc_abc123")

# Use Textract for higher accuracy
ocr = docs.extract_text("doc_abc123", provider="textract")

# Check confidence
if ocr.confidence < 0.9:
    print("Warning: Low OCR confidence")
```

### Tax Form Field Extraction

The OCR module automatically extracts structured fields from W-2 and 1099 forms:

**W-2 Fields:**
- employer
- wages
- federal_tax
- state_tax

**1099 Fields:**
- payer
- income

**Example:**
```python
ocr = docs.extract_text("doc_w2", provider="textract")
fields = ocr.fields

print(f"Employer: {fields['employer']}")
print(f"Wages: ${fields['wages']}")
print(f"Federal Tax: ${fields['federal_tax']}")
```

### Caching

OCR results are cached to avoid redundant processing:

- **Storage**: In-memory dict (production: Redis)
- **TTL**: 7 days (production)
- **Cache Key**: `{document_id}:{provider}`
- **Bypass**: Use `force_refresh=True`

---

## AI Analysis

### Rule-Based Analysis (Current)

**Purpose**: Simulated AI for testing without external LLM dependencies

**Tax Documents:**
- Extracts wages from OCR text using regex: `Wages:\s*\$?([\d,]+\.?\d*)`
- Calculates effective tax rate from federal_tax
- Generates 3-5 recommendations
- Adds investment advice for wages > $100k
- Includes professional advisor disclaimer

**Bank Statements:**
- Generic spending insights

**Receipts:**
- Amount extraction
- Categorization advice

**Generic:**
- Basic "extracted successfully" message

### Production Migration (ai-infra CoreLLM)

```python
from ai_infra.llm import CoreLLM

llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")

# Build financial context
prompt = f"""
Analyze this {document_type} document:

OCR Text:
{ocr_text}

Metadata:
{metadata}

Provide:
1. Brief summary (max 100 words)
2. 3-5 key findings
3. 3-5 actionable recommendations

Note: Always end with "This is not a substitute for advice from a certified financial advisor or tax professional."
"""

# Get analysis with structured output
analysis_schema = {
    "summary": str,
    "key_findings": List[str],
    "recommendations": List[str]
}

result = await llm.achat(
    messages=[{"role": "user", "content": prompt}],
    output_schema=analysis_schema,
    output_method="prompt"
)
```

**Cost Management** (MANDATORY):
- Track daily/monthly spend per user
- Enforce budget caps ($0.10/day, $2/month default)
- Use svc-infra cache for expensive operations (24h TTL)
- Target: <$0.10/user/month with caching
- Graceful degradation when budget exceeded (fall back to rule-based)

### Quality Validation

All analyses must pass validation:

```python
def _validate_analysis(analysis: DocumentAnalysis) -> bool:
    # Confidence threshold
    if analysis.confidence < 0.7:
        return False
    
    # Non-empty fields
    if not analysis.key_findings or not analysis.recommendations:
        return False
    
    # Summary length limit
    if len(analysis.summary) > 250:
        return False
    
    return True
```

---

## FastAPI Integration

### Basic Setup

```python
from fastapi import FastAPI
from fin_infra.documents import add_documents

app = FastAPI()

# Mount document endpoints
manager = add_documents(
    app,
    storage_path="/data/documents",
    default_ocr_provider="tesseract",
    prefix="/documents"
)

# Manager available for programmatic access
doc = manager.upload(...)
```

### Endpoints

**POST /documents/upload**

Upload a new document.

**Request Body:**
```json
{
    "user_id": "user_123",
    "file": "base64_encoded_file_or_string",
    "document_type": "tax",
    "filename": "w2_2024.pdf",
    "metadata": {"year": 2024, "form_type": "W-2"}
}
```

**Response:** Document model

---

**GET /documents/list?user_id=...&type=...&year=...**

List user's documents with optional filters.

**Query Parameters:**
- `user_id` (required): User identifier
- `type` (optional): Document type filter
- `year` (optional): Year filter

**Response:** List[Document]

---

**GET /documents/{document_id}**

Get document metadata.

**Response:** Document model

---

**DELETE /documents/{document_id}**

Delete a document.

**Response:**
```json
{"message": "Document deleted successfully"}
```

---

**POST /documents/{document_id}/ocr?provider=...&force_refresh=...**

Extract text from document.

**Query Parameters:**
- `provider` (optional): OCR provider ("tesseract" or "textract")
- `force_refresh` (optional): Bypass cache (default: false)

**Response:** OCRResult model

---

**POST /documents/{document_id}/analyze?force_refresh=...**

Analyze document with AI.

**Query Parameters:**
- `force_refresh` (optional): Bypass cache (default: false)

**Response:** DocumentAnalysis model

---

### Authentication

Production `add.py` uses svc-infra `user_router` for authentication:

```python
from svc_infra.api.fastapi.dual.protected import user_router

router = user_router(prefix="/documents", tags=["Documents"])

@router.post("/upload")
async def upload_document(user: RequireUser, ...):
    # User authenticated via user_router
    ...
```

### Documentation

The module automatically registers with svc-infra scoped docs:

```python
from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs

add_prefixed_docs(
    app,
    prefix="/documents",
    title="Documents",
    auto_exclude_from_root=True,
    visible_envs=None  # Show in all environments
)
```

**Access:**
- Landing page card: `/` → "Documents" card
- Scoped OpenAPI: `/documents/openapi.json`
- Scoped Swagger UI: `/documents/docs`
- Scoped ReDoc: `/documents/redoc`

---

## Production Migration

### Checklist

**Storage Migration:**
- [ ] Replace in-memory dicts with S3 for files
- [ ] Use svc-infra SQL for document metadata
- [ ] Add indexes on user_id, type, upload_date
- [ ] Implement soft-delete (add deleted_at column)
- [ ] Configure S3 lifecycle policies (archive old docs)

**OCR Migration:**
- [ ] Install pytesseract for Tesseract provider
- [ ] Configure AWS credentials for Textract
- [ ] Replace in-memory cache with Redis via svc-infra
- [ ] Set TTL to 7 days for OCR results
- [ ] Add error handling for provider failures

**Analysis Migration:**
- [ ] Replace rule-based logic with ai-infra CoreLLM
- [ ] Implement cost tracking per user
- [ ] Enforce budget caps ($0.10/day, $2/month)
- [ ] Add graceful degradation to rule-based fallback
- [ ] Use svc-infra cache with 24h TTL
- [ ] Filter sensitive data before sending to LLM

**Security:**
- [ ] Enable authentication via user_router
- [ ] Add rate limiting (svc-infra middleware)
- [ ] Implement file size limits (10MB default)
- [ ] Validate MIME types on upload
- [ ] Scan uploads for malware (ClamAV)
- [ ] Encrypt sensitive documents at rest (S3 KMS)

**Monitoring:**
- [ ] Add svc-infra observability (metrics, traces, logs)
- [ ] Track upload success/failure rates
- [ ] Monitor OCR confidence distributions
- [ ] Alert on low analysis confidence
- [ ] Track LLM costs per user

---

## Testing

### Unit Tests (42 tests, all passing)

**Storage Tests** (`tests/unit/documents/test_storage.py` - 16 tests):
- Upload with/without metadata
- Unique ID generation
- Checksum calculation
- Get/download/delete operations
- List filtering by type and year
- Date sorting

**OCR Tests** (`tests/unit/documents/test_ocr.py` - 11 tests):
- Basic text extraction
- W-2 and 1099 form parsing
- Provider confidence differences
- Caching and force_refresh
- Invalid provider errors
- Field extraction validation

**Analysis Tests** (`tests/unit/documents/test_analysis.py` - 15 tests):
- W-2, 1099, bank statement, receipt, generic analysis
- Caching and force_refresh
- High-wage W-2 investment recommendations
- Confidence validation
- Summary length limits
- Non-empty findings/recommendations
- Professional advisor disclaimer

### Integration Tests (14 tests, all passing)

**API Tests** (`tests/integration/test_documents_api.py`):
- add_documents helper mounts all routes
- Upload with/without metadata
- Get document details
- List documents (all, by type, by year)
- Delete document with verification
- OCR extraction (default provider, specific provider)
- Analysis (basic, force refresh)
- Empty list for new user
- Manager stored on app.state

### Running Tests

```bash
# Unit tests
poetry run pytest tests/unit/documents/ -v

# Integration tests
poetry run pytest tests/integration/test_documents_api.py -v

# All documents tests
poetry run pytest tests/unit/documents/ tests/integration/test_documents_api.py -v

# With coverage
poetry run pytest tests/unit/documents/ --cov=src/fin_infra/documents --cov-report=term-missing
```

---

## Troubleshooting

### Issue: Upload fails with "File is empty"

**Cause:** File bytes are empty

**Solution:**
```python
# Ensure file is not empty
if not file_bytes:
    raise ValueError("File cannot be empty")

# Check file size
print(f"File size: {len(file_bytes)} bytes")
```

---

### Issue: OCR confidence is low (<0.7)

**Cause:** Poor image quality, complex layout, or handwriting

**Solutions:**
1. Try Textract provider: `docs.extract_text(doc_id, provider="textract")`
2. Improve image quality (higher DPI, better lighting)
3. Manually review extracted text
4. Implement human-in-the-loop review for low confidence

---

### Issue: Analysis returns generic insights

**Cause:** Rule-based analysis has limited intelligence

**Solution:** Migrate to ai-infra CoreLLM for production:
```python
from ai_infra.llm import CoreLLM

llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")
# See "Production Migration" section for full implementation
```

---

### Issue: Document not found after upload

**Cause:** Storage cleared (in-memory) or wrong document_id

**Solutions:**
1. Check document ID: `print(doc.id)`
2. Verify storage not cleared: `clear_storage()` in tests
3. Check user_id matches: `docs.list(user_id="...")`

---

### Issue: Routes conflict (/documents/list matches /{document_id})

**Cause:** FastAPI route ordering - more specific routes must come first

**Solution:**
```python
# List route MUST come before /{document_id}
@router.get("/list")
async def list_documents(...): ...

@router.get("/{document_id}")
async def get_document(...): ...
```

---

### Issue: TestClient raises exceptions instead of returning error responses

**Cause:** Default TestClient raises server exceptions

**Solution:**
```python
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)
```

---

## Future Enhancements

**Short Term:**
- [ ] Multipart/form-data upload support for file uploads
- [ ] Download endpoint (`GET /documents/{id}/download`)
- [ ] Async processing with svc-infra webhooks
- [ ] Soft-delete with deleted_at column
- [ ] File size limits and validation

**Medium Term:**
- [ ] Batch OCR processing for multiple documents
- [ ] Document versioning (track updates)
- [ ] Sharing/permissions (public links, team access)
- [ ] Search across OCR text (Elasticsearch integration)
- [ ] Document tagging system

**Long Term:**
- [ ] AI-powered document classification (auto-detect type)
- [ ] Multi-language OCR support
- [ ] Handwriting recognition
- [ ] Form pre-filling (extract data to tax software)
- [ ] Compliance checks (GDPR, SOC 2)

---

## Related Documentation

- [ADR 0027: Document Management Design](adr/0027-document-management-design.md)
- [svc-infra Storage Guide](../../svc-infra/docs/storage.md)
- [svc-infra Caching Guide](../../svc-infra/docs/cache.md)
- [ai-infra LLM Guide](../../ai-infra/docs/llm.md)
- [fin-infra README](../README.md)

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-15  
**Authors**: fin-infra team  
**License**: MIT
