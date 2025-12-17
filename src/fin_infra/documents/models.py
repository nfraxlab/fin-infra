"""
Pydantic models for financial document management.

This module defines financial-specific data models built on top of svc-infra base:
- FinancialDocument: Extends base Document with financial fields (type, tax_year, form_type)
- OCR extraction results for tax forms
- AI-powered document analysis

Architecture:
    Layer 1 (svc-infra): Generic Document with flexible metadata
    Layer 2 (fin-infra): FinancialDocument with financial-specific fields

Quick Start:
    >>> from fin_infra.documents.models import FinancialDocument, DocumentType
    >>>
    >>> # Create financial document (inherits from svc-infra Document)
    >>> doc = FinancialDocument(
    ...     id="doc_123",
    ...     user_id="user_123",
    ...     filename="w2.pdf",
    ...     file_size=524288,
    ...     storage_path="documents/user_123/doc_123.pdf",
    ...     content_type="application/pdf",
    ...     type=DocumentType.TAX,
    ...     tax_year=2024,
    ...     form_type="W-2"
    ... )
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from svc_infra.documents import Document as BaseDocument


class DocumentType(str, Enum):
    """Type of financial document (financial-specific extension)."""

    TAX = "tax"
    STATEMENT = "statement"
    RECEIPT = "receipt"
    CONFIRMATION = "confirmation"
    POLICY = "policy"
    CONTRACT = "contract"
    OTHER = "other"


class FinancialDocument(BaseDocument):
    """
    Financial document extending base Document with financial-specific fields.

    Inherits from svc-infra Document:
        - id, user_id, filename, file_size, upload_date
        - storage_path, content_type, checksum
        - metadata (Dict[str, Any])

    Adds financial-specific fields:
        - type: DocumentType enum
        - tax_year: Optional year for tax documents
        - form_type: Optional form identifier (W-2, 1099, etc.)

    Examples:
        >>> # Tax document with W-2 form
        >>> doc = FinancialDocument(
        ...     id="doc_123",
        ...     user_id="user_123",
        ...     filename="w2_2024.pdf",
        ...     file_size=524288,
        ...     storage_path="documents/user_123/doc_123.pdf",
        ...     content_type="application/pdf",
        ...     type=DocumentType.TAX,
        ...     tax_year=2024,
        ...     form_type="W-2"
        ... )
        >>>
        >>> # Bank statement
        >>> doc = FinancialDocument(
        ...     id="doc_456",
        ...     user_id="user_123",
        ...     filename="statement_jan.pdf",
        ...     file_size=102400,
        ...     storage_path="documents/user_123/doc_456.pdf",
        ...     content_type="application/pdf",
        ...     type=DocumentType.STATEMENT,
        ...     metadata={"month": "january", "account": "****1234"}
        ... )
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_abc123",
                "user_id": "user_123",
                "type": "tax",
                "filename": "w2_2024.pdf",
                "file_size": 524288,
                "upload_date": "2025-11-10T14:30:00Z",
                "metadata": {"employer": "ACME Corp", "employer_ein": "12-3456789"},
                "storage_path": "documents/user_123/2024/tax/doc_abc123.pdf",
                "content_type": "application/pdf",
                "checksum": "sha256:abc123...",
                "tax_year": 2024,
                "form_type": "W-2",
            }
        }
    )

    # Financial-specific fields
    type: DocumentType = Field(..., description="Document type category (financial-specific)")
    tax_year: Optional[int] = Field(None, description="Tax year for tax documents (e.g., 2024)")
    form_type: Optional[str] = Field(None, description="Tax form type (W-2, 1099-INT, 1040, etc.)")


# Backward compatibility: alias for existing code
Document = FinancialDocument


class OCRResult(BaseModel):
    """OCR text extraction result."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "doc_abc123",
                "text": "Employee Name: John Doe\\nEmployer: ACME Corp\\nWages: $75,000.00...",
                "confidence": 0.94,
                "fields_extracted": {
                    "employee_name": "John Doe",
                    "employer": "ACME Corp",
                    "wages": "75000.00",
                    "tax_year": "2024",
                },
                "extraction_date": "2025-11-10T14:35:00Z",
                "provider": "tesseract",
            }
        }
    )

    document_id: str = Field(..., description="Document that was analyzed")
    text: str = Field(..., description="Full extracted text")
    confidence: float = Field(
        ..., description="Overall OCR confidence score (0.0-1.0)", ge=0.0, le=1.0
    )
    fields_extracted: Dict[str, str] = Field(
        default_factory=dict,
        description="Structured fields extracted from document (names, amounts, dates)",
    )
    extraction_date: datetime = Field(
        default_factory=datetime.now, description="When OCR was performed"
    )
    provider: str = Field(..., description="OCR provider used (tesseract, textract, etc.)")


class DocumentAnalysis(BaseModel):
    """AI-powered document analysis result."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "doc_abc123",
                "summary": "W-2 form for tax year 2024 from ACME Corp showing wages of $75,000",
                "key_findings": [
                    "Total wages: $75,000.00",
                    "Federal tax withheld: $12,500.00",
                    "State tax withheld: $3,750.00",
                ],
                "recommendations": [
                    "Verify wages match your records",
                    "Keep for tax filing and 7 years after",
                    "File with your 2024 tax return",
                ],
                "analysis_date": "2025-11-10T14:40:00Z",
                "confidence": 0.92,
            }
        }
    )

    document_id: str = Field(..., description="Document that was analyzed")
    summary: str = Field(..., description="High-level document summary")
    key_findings: List[str] = Field(
        default_factory=list, description="Important facts extracted from document"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Action items or suggestions based on document content"
    )
    analysis_date: datetime = Field(
        default_factory=datetime.now, description="When analysis was performed"
    )
    confidence: float = Field(
        ..., description="Analysis confidence score (0.0-1.0)", ge=0.0, le=1.0
    )
