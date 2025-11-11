"""
Pydantic models for document management.

This module defines data models for:
- Document metadata and storage
- OCR extraction results
- AI-powered document analysis
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    """Type of financial document."""

    TAX = "tax"
    STATEMENT = "statement"
    RECEIPT = "receipt"
    CONFIRMATION = "confirmation"
    POLICY = "policy"
    CONTRACT = "contract"
    OTHER = "other"


class Document(BaseModel):
    """Financial document metadata and storage information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_abc123",
                "user_id": "user_123",
                "type": "tax",
                "filename": "w2_2024.pdf",
                "file_size": 524288,
                "upload_date": "2025-11-10T14:30:00Z",
                "metadata": {"year": 2024, "form_type": "W-2", "employer": "ACME Corp"},
                "storage_path": "documents/user_123/2024/tax/doc_abc123.pdf",
                "content_type": "application/pdf",
                "checksum": "sha256:abc123...",
            }
        }
    )

    id: str = Field(..., description="Unique document identifier")
    user_id: str = Field(..., description="User who uploaded the document")
    type: DocumentType = Field(..., description="Document type category")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(..., description="Upload timestamp")
    metadata: Dict[str, str | int | float] = Field(
        default_factory=dict, description="Custom document metadata (year, form type, etc.)"
    )
    storage_path: str = Field(..., description="Storage location path")
    content_type: str = Field(..., description="MIME type (application/pdf, image/jpeg, etc.)")
    checksum: Optional[str] = Field(None, description="File checksum for integrity validation")


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
