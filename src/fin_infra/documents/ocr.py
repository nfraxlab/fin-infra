"""
OCR (Optical Character Recognition) for document text extraction.

Supports multiple OCR providers:
- Tesseract: Free, open-source, runs locally (simulated)
- AWS Textract: Paid, cloud-based, high accuracy for forms/tables (simulated)

Quick Start:
    >>> from fin_infra.documents.ocr import extract_text
    >>>
    >>> # Extract text from document
    >>> result = extract_text(document_id="doc_abc123", provider="tesseract")
    >>> print(result.text)
    >>> print(result.confidence)
    >>> print(result.fields_extracted)  # Structured data

Production Integration:
    - Default to Tesseract (free) for basic documents
    - Use AWS Textract for tax forms and complex tables
    - Cache OCR results to avoid repeated processing
    - Store OCR results in svc-infra SQL database
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from .models import OCRResult

# In-memory OCR cache (production: use svc-infra cache)
_ocr_cache: Dict[str, "OCRResult"] = {}


def extract_text(
    document_id: str,
    provider: str = "tesseract",
    force_refresh: bool = False,
) -> "OCRResult":
    """
    Extract text from a document using OCR.

    Args:
        document_id: Document identifier
        provider: OCR provider ("tesseract" or "textract")
        force_refresh: Force re-extraction even if cached result exists

    Returns:
        OCR result with extracted text and structured fields

    Examples:
        >>> # Basic OCR (Tesseract)
        >>> result = extract_text("doc_abc123")
        >>>
        >>> # High-accuracy OCR (AWS Textract)
        >>> result = extract_text("doc_abc123", provider="textract")
        >>>
        >>> # Force re-extraction
        >>> result = extract_text("doc_abc123", force_refresh=True)

    Notes:
        - Current: Simulated OCR (mock text extraction)
        - Production: Check cache before extraction (use svc-infra cache)
        - Production: Queue long-running OCR jobs (use svc-infra jobs)
        - Production: Store results in svc-infra SQL database
        - Production: Add retry logic for cloud providers
    """
    from .storage import download_document, get_document

    # Check cache first
    cache_key = f"{document_id}:{provider}"
    if not force_refresh and cache_key in _ocr_cache:
        return _ocr_cache[cache_key]

    # Get document metadata
    doc = get_document(document_id)
    if not doc:
        raise ValueError(f"Document not found: {document_id}")

    # Download file content
    file_content = download_document(document_id)

    # Extract text based on provider
    if provider == "tesseract":
        result = _extract_with_tesseract(file_content, doc.filename, doc.metadata, document_id)
    elif provider == "textract":
        result = _extract_with_textract(file_content, doc.filename, doc.metadata, document_id)
    else:
        raise ValueError(f"Unknown OCR provider: {provider}")

    # Cache result
    _ocr_cache[cache_key] = result

    return result


def _extract_with_tesseract(
    file_content: bytes, filename: str, metadata: dict, document_id: str
) -> "OCRResult":
    """
    Extract text using Tesseract OCR (simulated).

    Args:
        file_content: Document file content
        filename: Original filename
        metadata: Document metadata
        document_id: Document identifier

    Returns:
        OCR result with confidence and fields

    Notes:
        - Current: Simulated extraction (mock data)
        - Free, open-source OCR
        - Good for basic documents (receipts, statements)
        - Lower accuracy for complex forms/tables
        - Production: Requires pytesseract package
    """
    from .models import OCRResult

    # Simulate OCR extraction (production: use pytesseract)
    # Generate mock text based on document type in metadata
    form_type = metadata.get("form_type", "")
    year = metadata.get("year", 2024)

    if form_type == "W-2":
        text = _generate_mock_w2_text(year, metadata)
        fields = _parse_tax_form(text, form_type)
        confidence = 0.85  # Lower confidence for Tesseract
    elif form_type == "1099":
        text = _generate_mock_1099_text(year, metadata)
        fields = _parse_tax_form(text, form_type)
        confidence = 0.82
    else:
        text = f"Document content: {filename}\nSize: {len(file_content)} bytes"
        fields = {}
        confidence = 0.75

    return OCRResult(
        document_id=document_id,
        text=text,
        confidence=confidence,
        fields_extracted=fields,
        extraction_date=datetime.utcnow(),
        provider="tesseract",
    )


def _extract_with_textract(
    file_content: bytes, filename: str, metadata: dict, document_id: str
) -> "OCRResult":
    """
    Extract text using AWS Textract (simulated).

    Args:
        file_content: Document file content
        filename: Original filename
        metadata: Document metadata
        document_id: Document identifier

    Returns:
        OCR result with high-confidence structured data

    Notes:
        - Current: Simulated extraction (mock data)
        - Paid cloud service (per page pricing)
        - High accuracy for tax forms and tables
        - Extracts key-value pairs automatically
        - Production: Requires AWS credentials (use svc-infra settings)
    """
    from .models import OCRResult

    # Simulate AWS Textract (production: use boto3 textract)
    form_type = metadata.get("form_type", "")
    year = metadata.get("year", 2024)

    if form_type == "W-2":
        text = _generate_mock_w2_text(year, metadata)
        fields = _parse_tax_form(text, form_type)
        confidence = 0.96  # Higher confidence for Textract
    elif form_type == "1099":
        text = _generate_mock_1099_text(year, metadata)
        fields = _parse_tax_form(text, form_type)
        confidence = 0.94
    else:
        text = f"Document content: {filename}\nSize: {len(file_content)} bytes"
        fields = {}
        confidence = 0.90

    return OCRResult(
        document_id=document_id,
        text=text,
        confidence=confidence,
        fields_extracted=fields,
        extraction_date=datetime.utcnow(),
        provider="textract",
    )


def _parse_tax_form(text: str, form_type: Optional[str] = None) -> dict[str, str]:
    """
    Parse tax form text into structured fields.

    Args:
        text: Raw OCR text
        form_type: Type of tax form (W-2, 1099, etc.)

    Returns:
        Dictionary of extracted fields (employer, wages, etc.)

    Examples:
        >>> fields = _parse_tax_form(ocr_text, form_type="W-2")
        >>> print(fields["employer"])
        >>> print(fields["wages"])

    Notes:
        - Use regex patterns for common tax forms
        - Validate extracted values (SSN format, dollar amounts)
        - Return empty dict if parsing fails
    """
    fields = {}

    if form_type == "W-2":
        # Extract employer
        employer_match = re.search(r"Employer:\s*(.+)", text)
        if employer_match:
            fields["employer"] = employer_match.group(1).strip()

        # Extract wages
        wages_match = re.search(r"Wages:\s*\$?([\d,]+\.?\d*)", text)
        if wages_match:
            fields["wages"] = wages_match.group(1).strip()

        # Extract federal tax withheld
        federal_match = re.search(r"Federal Tax Withheld:\s*\$?([\d,]+\.?\d*)", text)
        if federal_match:
            fields["federal_tax"] = federal_match.group(1).strip()

        # Extract state tax withheld
        state_match = re.search(r"State Tax Withheld:\s*\$?([\d,]+\.?\d*)", text)
        if state_match:
            fields["state_tax"] = state_match.group(1).strip()

    elif form_type == "1099":
        # Extract payer
        payer_match = re.search(r"Payer:\s*(.+)", text)
        if payer_match:
            fields["payer"] = payer_match.group(1).strip()

        # Extract income
        income_match = re.search(r"Income:\s*\$?([\d,]+\.?\d*)", text)
        if income_match:
            fields["income"] = income_match.group(1).strip()

    return fields


def _generate_mock_w2_text(year: int, metadata: dict) -> str:
    """Generate mock W-2 text for testing."""
    employer = metadata.get("employer", "Acme Corporation")
    wages = metadata.get("wages", "85,000.00")
    federal_tax = metadata.get("federal_tax", "18,700.00")
    state_tax = metadata.get("state_tax", "4,250.00")

    return f"""Form W-2 Wage and Tax Statement
Tax Year: {year}

Employer: {employer}
Wages: ${wages}
Federal Tax Withheld: ${federal_tax}
State Tax Withheld: ${state_tax}

Employee: John Doe
SSN: XXX-XX-1234
"""


def _generate_mock_1099_text(year: int, metadata: dict) -> str:
    """Generate mock 1099 text for testing."""
    payer = metadata.get("payer", "Freelance Client LLC")
    income = metadata.get("income", "45,000.00")

    return f"""Form 1099-NEC Nonemployee Compensation
Tax Year: {year}

Payer: {payer}
Income: ${income}

Recipient: Jane Smith
SSN: XXX-XX-5678
"""


def clear_cache() -> None:
    """Clear OCR cache (for testing only)."""
    _ocr_cache.clear()
