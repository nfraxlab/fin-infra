"""
Financial document management demonstrations.

This module shows how to use fin-infra's layered documents architecture:
- Layer 1 (svc-infra): Base CRUD operations (upload, list, get, delete)
- Layer 2 (fin-infra): Financial extensions (OCR extraction, AI analysis)

Examples:
- demo.py: Complete document lifecycle with OCR and AI analysis
"""

from .demo import demo_financial_documents, demo_tax_document_workflow

__all__ = ["demo_financial_documents", "demo_tax_document_workflow"]
