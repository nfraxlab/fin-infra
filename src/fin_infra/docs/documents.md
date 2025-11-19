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

> **Architecture**: fin-infra documents is built as **Layer 2** on top of svc-infra's generic document storage (**Layer 1**). This provides a clean separation: svc-infra handles base CRUD operations, while fin-infra adds financial-specific features like OCR for tax forms and AI-powered analysis. See [Architecture](#architecture) section for details.

The documents module provides a complete solution for managing financial documents in fintech applications. It handles:

- **Document Upload**: Store tax forms, bank statements, receipts, invoices, contracts, insurance docs (Layer 1: svc-infra)
- **OCR Extraction**: Extract text from images/PDFs with Tesseract or AWS Textract (Layer 2: fin-infra)
- **AI Analysis**: Generate insights, recommendations, and summaries (Layer 2: fin-infra)
- **Secure Storage**: In-memory for testing, S3 + SQL for production (Layer 1: svc-infra)
- **FastAPI Integration**: One-liner to mount full REST API (6 endpoints total)

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

# One-liner: mount all document endpoints (Layer 1 + Layer 2)
manager = add_documents(
    app,
    storage_path="/data/documents",
    default_ocr_provider="tesseract",
    prefix="/documents"
)

# Endpoints now available:
# Layer 1 (svc-infra base - generic CRUD):
#   POST /documents/upload           - Upload document
#   GET /documents/list              - List documents with filters
#   GET /documents/{document_id}     - Get document details
#   DELETE /documents/{document_id}  - Delete document
#
# Layer 2 (fin-infra extensions - financial features):
#   POST /documents/{document_id}/ocr     - Extract text via OCR
#   POST /documents/{document_id}/analyze - AI-powered analysis
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

### Layered Design (svc-infra Base + fin-infra Extensions)

fin-infra documents module is built as **Layer 2** on top of svc-infra's generic document system (**Layer 1**):

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
│                     (add_documents)                             │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
        ┌────────────────────────────────┐
        │ FinancialDocumentManager        │  ← Layer 2 (fin-infra)
        │   extends BaseDocumentManager   │     Financial features
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   BaseDocumentManager           │  ← Layer 1 (svc-infra)
        │   (generic CRUD)                │     Generic storage
        └────────────┬───────────────────┘
                     │
    ┌────────────────┼────────────────┬────────────────┐
    │                │                │                │
    ▼                ▼                ▼                ▼
┌─────────┐   ┌─────────┐   ┌──────────┐   ┌──────────────┐
│ Storage │   │   OCR   │   │ Analysis │   │    Models    │
│  (Base) │   │(Fin Ext)│   │(Fin Ext) │   │ (Financial)  │
└─────────┘   └─────────┘   └──────────┘   └──────────────┘
     │             │              │
     ▼             ▼              ▼
┌─────────┐   ┌─────────┐   ┌──────────┐
│svc-infra│   │  Cache  │   │ai-infra  │
│ Storage │   │  Dict   │   │ CoreLLM  │
│ Backend │   │(→Redis) │   │(→GenAI)  │
└─────────┘   └─────────┘   └──────────┘
```

**Layer 1 (svc-infra)**: Generic document infrastructure
- `svc_infra.documents.Document` - Base document model
- `svc_infra.documents.upload_document()` - Storage integration
- `svc_infra.documents.add_documents()` - 4 base endpoints (upload, list, get, delete)
- Works with ANY storage backend (S3, local, memory)
- Domain-agnostic - usable by ANY application

**Layer 2 (fin-infra)**: Financial-specific extensions
- `FinancialDocument` extends `Document` with tax_year, form_type, DocumentType
- `extract_text()` - OCR for tax forms (W-2, 1099) with field parsing
- `analyze()` - AI-powered financial insights and recommendations
- 2 additional endpoints: POST /documents/{id}/ocr, POST /documents/{id}/analyze
- Backward compatible - same API surface as before

**Why This Architecture?**
✅ **Separation of concerns**: Generic file storage vs financial domain logic  
✅ **Reusability**: Other domains (medical, legal) can use svc-infra base  
✅ **No duplication**: fin-infra imports from svc-infra (not copy-paste)  
✅ **Clear extension pattern**: Shows how to build domain features on generic base  
✅ **Backward compatible**: fin-infra API unchanged, just refactored internally

### Component Responsibilities

**Storage** (`storage.py`) - **Layer 2 Wrapper**:
- Delegates to `svc_infra.documents` for all CRUD operations
- Converts between `Document` (base) and `FinancialDocument` (extended)
- Injects/extracts financial metadata (document_type, tax_year, form_type)
- Maintains backward compatibility via function aliases
- Uses svc-infra storage backend (S3, local, memory)

**OCR** (`ocr.py`) - **Financial Extension**:
- Text extraction from images/PDFs
- Provider selection (Tesseract, AWS Textract)
- Tax form field parsing (W-2, 1099)
- Result caching (production: Redis with 7d TTL)

**Analysis** (`analysis.py`) - **Financial Extension**:
- Document analysis with financial insights and recommendations
- Type-specific analyzers (tax, bank statement, receipt, generic)
- Quality validation (confidence >= 0.7, non-empty fields)
- Result caching (production: Redis with 24h TTL)
- Production: Use ai-infra CoreLLM for AI-powered analysis
- Extracts financial metrics (wages, taxes, spending patterns)

**Models** (`models.py`) - **Layer 2 Extensions**:
- `FinancialDocument` extends `svc_infra.documents.Document` with financial fields
- `Document` = alias for backward compatibility
- `DocumentType` enum (7 types: TAX, BANK_STATEMENT, RECEIPT, etc.)
- `OCRResult` model (text, confidence, fields for W-2/1099 forms)
- `DocumentAnalysis` model (summary, findings, recommendations)
- Pydantic v2 models for data validation

### How fin-infra Extends svc-infra

**Import Pattern**:
```python
# fin-infra imports base functionality from svc-infra
from svc_infra.documents import (
    Document as BaseDocument,
    upload_document as base_upload_document,
    add_documents as add_base_documents
)

# Then extends with financial features
class FinancialDocument(BaseDocument):
    type: DocumentType  # Financial-specific enum
    tax_year: Optional[int] = None
    form_type: Optional[str] = None
```

**add_documents() Pattern** (Layer 2 calls Layer 1):
```python
def add_documents(app, storage, prefix="/documents"):
    # Step 1: Mount base CRUD endpoints from svc-infra
    add_base_documents(app, storage_backend=storage, prefix=prefix)
    # This gives you: POST /upload, GET /list, GET /{id}, DELETE /{id}
    
    # Step 2: Add financial-specific endpoints
    @router.post("/{document_id}/ocr")
    async def extract_text_ocr(...):
        return await manager.extract_text(...)
    
    @router.post("/{document_id}/analyze")
    async def analyze_document_ai(...):
        return await manager.analyze(...)
```

**For Other Domains**: Follow the same pattern:
- Medical app: `MedicalDocument` extends `BaseDocument` with diagnosis_codes, treatment_dates
- Legal app: `LegalDocument` extends `BaseDocument` with case_number, court_jurisdiction
- E-commerce: `ProductDocument` extends `BaseDocument` with sku, category

**Reference Implementation**: See svc-infra's generic documents at `src/svc_infra/docs/documents.md`

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

### Layered Storage Architecture

fin-infra delegates all storage operations to **svc-infra's generic storage system** (Layer 1).

**How It Works:**
```python
# fin-infra storage.py delegates to svc-infra
from svc_infra.documents import (
    upload_document as base_upload,
    download_document as base_download
)

# Financial wrapper adds DocumentType, tax_year, form_type
async def upload_document(storage, user_id, file, document_type, ...):
    # Convert financial fields to metadata
    metadata = {"document_type": document_type.value, ...}
    
    # Call base layer
    base_doc = await base_upload(storage, user_id, file, metadata=metadata)
    
    # Convert to FinancialDocument
    return FinancialDocument(**base_doc.model_dump(), type=document_type)
```

**Storage Backends** (via svc-infra):
- **MemoryBackend**: Testing (fast, no persistence)
- **LocalBackend**: Railway volumes, filesystem storage
- **S3Backend**: AWS S3, DigitalOcean Spaces, Wasabi, Backblaze B2

**See**: [svc-infra Storage Guide](../../../svc-infra/src/svc_infra/docs/storage.md) for backend documentation

### Production Setup

**Configuration** (via environment variables):
```bash
# For S3 backend
export STORAGE_S3_BUCKET=user-documents
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# For Railway volumes
export RAILWAY_VOLUME_MOUNT_PATH=/data
```

**Usage**:
```python
from fin_infra.documents import add_documents, easy_documents
from svc_infra.storage import easy_storage

# Create storage backend (auto-detects from environment)
storage = easy_storage()  # → S3Backend or LocalBackend

# Option 1: FastAPI integration
add_documents(app, storage=storage)

# Option 2: Programmatic
docs = easy_documents(storage=storage)
doc = await docs.upload(user_id, file, DocumentType.TAX, ...)
```

**Benefits:**
- **Layered design**: Generic base + financial extensions
- **Backend flexibility**: S3, Railway, local, memory
- **Battle-tested**: Uses svc-infra infrastructure
- **No vendor lock-in**: Switch backends via environment variables

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

**Layered Architecture**:
- [svc-infra Documents Guide](../../../svc-infra/src/svc_infra/docs/documents.md) - Generic Layer 1 base
- [svc-infra Storage Guide](../../../svc-infra/src/svc_infra/docs/storage.md) - Backend abstraction (S3, local, memory)

**Financial Features**:
- [ADR 0027: Document Management Design](adr/0027-document-management-design.md) - Design decisions
- [ai-infra LLM Guide](../../../ai-infra/docs/llm.md) - AI-powered analysis

**Infrastructure**:
- [svc-infra Caching Guide](../../../svc-infra/src/svc_infra/docs/cache.md) - OCR/analysis result caching
- [fin-infra README](../README.md) - Package overview

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-15  
**Authors**: fin-infra team  
**License**: MIT
