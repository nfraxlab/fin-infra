"""
Document management module for financial documents.

Provides upload, storage, OCR extraction, and AI-powered analysis for:
- Tax documents (W-2, 1099, tax returns)
- Bank statements
- Investment confirmations
- Receipts
- Insurance policies
- Contracts

Quick Start:
    >>> from fin_infra.documents import easy_documents
    >>>
    >>> # Create document manager
    >>> manager = easy_documents(storage_path="/data/documents")
    >>>
    >>> # Upload document
    >>> doc = manager.upload_document(
    ...     user_id="user_123",
    ...     file=uploaded_file,
    ...     document_type="tax",
    ...     metadata={"year": 2024, "form_type": "W-2"}
    ... )
    >>>
    >>> # Extract text with OCR
    >>> ocr_result = manager.extract_text(doc.id)
    >>>
    >>> # Analyze with AI
    >>> analysis = manager.analyze_document(doc.id)

FastAPI Integration:
    >>> from fastapi import FastAPI
    >>> from fin_infra.documents import add_documents
    >>>
    >>> app = FastAPI()
    >>> manager = add_documents(app, storage_path="/data/documents")
    >>>
    >>> # Available endpoints:
    >>> # POST /documents/upload
    >>> # GET /documents/{document_id}
    >>> # GET /documents/list
    >>> # DELETE /documents/{document_id}
    >>> # POST /documents/{document_id}/ocr
    >>> # POST /documents/{document_id}/analyze
"""

from .add import add_documents
from .ease import easy_documents
from .models import (
    Document,
    DocumentAnalysis,
    DocumentType,
    OCRResult,
)

__all__ = [
    # Easy builders
    "easy_documents",
    "add_documents",
    # Models
    "Document",
    "DocumentType",
    "OCRResult",
    "DocumentAnalysis",
]
