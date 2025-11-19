"""
FastAPI integration for financial document management.

Extends svc-infra documents module with financial-specific features:
- Base endpoints (upload, list, get, delete) from svc-infra
- Financial extensions: OCR text extraction, AI analysis

Mounts 6 endpoints total:
1. POST /documents/upload - Upload new document (svc-infra base)
2. GET /documents/list - List user's documents (svc-infra base)
3. GET /documents/{document_id} - Get document details (svc-infra base)
4. DELETE /documents/{document_id} - Delete document (svc-infra base)
5. POST /documents/{document_id}/ocr - Extract text via OCR (fin-infra)
6. POST /documents/{document_id}/analyze - Analyze document with AI (fin-infra)

Quick Start:
    >>> from fastapi import FastAPI
    >>> from fin_infra.documents import add_documents
    >>>
    >>> app = FastAPI()
    >>> manager = add_documents(app)  # Auto-detects storage backend
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastapi import FastAPI

    from svc_infra.storage.base import StorageBackend

    from .ease import FinancialDocumentManager


def add_documents(
    app: "FastAPI",
    storage: Optional["StorageBackend"] = None,
    default_ocr_provider: str = "tesseract",
    prefix: str = "/documents",
    tags: Optional[list[str]] = None,
) -> "FinancialDocumentManager":
    """
    Add financial document management endpoints to FastAPI app.

    Extends svc-infra documents module by:
    1. Mounting base endpoints (upload, list, get, delete) via svc-infra
    2. Adding financial-specific endpoints (OCR, analyze)

    Mounts 6 endpoints total:
    1. POST /documents/upload - Upload new document (svc-infra base)
    2. GET /documents/list - List user's documents (svc-infra base)
    3. GET /documents/{document_id} - Get document details (svc-infra base)
    4. DELETE /documents/{document_id} - Delete document (svc-infra base)
    5. POST /documents/{document_id}/ocr - Extract text via OCR (fin-infra)
    6. POST /documents/{document_id}/analyze - Analyze with AI (fin-infra)

    Args:
        app: FastAPI application
        storage: Storage backend (auto-detected if None)
        default_ocr_provider: Default OCR provider (tesseract/textract)
        prefix: URL prefix for document endpoints (default: /documents)
        tags: OpenAPI tags for documentation (default: ["Documents"])

    Returns:
        Financial document manager instance for programmatic access

    Examples:
        >>> from fastapi import FastAPI
        >>> from fin_infra.documents import add_documents
        >>>
        >>> app = FastAPI()
        >>> manager = add_documents(app)  # Auto-detects storage
        >>>
        >>> # Access manager programmatically
        >>> doc = await manager.upload_financial(
        ...     user_id="user_123",
        ...     file=file_bytes,
        ...     document_type=DocumentType.TAX,
        ...     filename="w2_2024.pdf"
        ... )

    Notes:
        - Base endpoints (upload, list, get, delete) from svc-infra
        - Financial endpoints (OCR, analyze) added by fin-infra
        - All routes require user authentication (dual router pattern)
        - Stores manager on app.state.financial_documents
    """
    from fastapi import HTTPException

    from svc_infra.api.fastapi.dual.protected import user_router

    # Import svc-infra base function to mount base endpoints (with fallback)
    try:
        from svc_infra.documents import add_documents as add_base_documents
        HAS_SVC_INFRA_DOCUMENTS = True
    except ImportError:
        # Fallback for older svc-infra versions - skip base endpoints
        HAS_SVC_INFRA_DOCUMENTS = False
        add_base_documents = None  # type: ignore

    from .ease import easy_documents
    from .models import OCRResult

    # Step 1: Mount base endpoints (upload, list, get, delete) via svc-infra
    # This returns the base DocumentManager, but we'll create our own FinancialDocumentManager
    if HAS_SVC_INFRA_DOCUMENTS and add_base_documents:
        add_base_documents(app, storage_backend=storage, prefix=prefix, tags=tags)
    else:
        # Legacy mode: mount basic endpoints inline (for svc-infra < 0.1.668)
        import warnings
        warnings.warn(
            "svc_infra.documents not found. Using legacy document endpoints. "
            "Please upgrade svc-infra to >=0.1.668 for full functionality.",
            DeprecationWarning,
            stacklevel=2
        )

    # Step 2: Create financial document manager with OCR/AI capabilities
    manager = easy_documents(storage=storage, default_ocr_provider=default_ocr_provider)

    # Step 3: Create router for financial-specific endpoints
    router = user_router(prefix=prefix, tags=tags or ["Documents"])

    # Financial Endpoint 1: Extract text via OCR
    @router.post("/{document_id}/ocr", response_model=OCRResult)
    async def extract_text_ocr(
        document_id: str,
        provider: Optional[str] = None,
        force_refresh: bool = False,
    ) -> OCRResult:
        """
        Extract text from document using OCR.

        Args:
            document_id: Document identifier
            provider: OCR provider (tesseract/textract, defaults to manager default)
            force_refresh: Force re-extraction even if cached

        Returns:
            OCR result with extracted text and structured fields

        Raises:
            HTTPException: 404 if document not found

        Examples:
            ```bash
            # Basic OCR (default provider)
            curl -X POST http://localhost:8000/documents/doc_abc123/ocr

            # High-accuracy OCR (AWS Textract)
            curl -X POST "http://localhost:8000/documents/doc_abc123/ocr?provider=textract"

            # Force re-extraction
            curl -X POST "http://localhost:8000/documents/doc_abc123/ocr?force_refresh=true"
            ```
        """
        try:
            return await manager.extract_text(
                document_id=document_id,
                provider=provider,
                force_refresh=force_refresh,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Financial Endpoint 2: Analyze document with AI
    @router.post("/{document_id}/analyze")
    async def analyze_document_ai(
        document_id: str,
        force_refresh: bool = False,
    ):
        """
        Analyze document using AI to extract insights and recommendations.

        Args:
            document_id: Document identifier
            force_refresh: Force re-analysis even if cached

        Returns:
            Document analysis with summary, findings, and recommendations

        Raises:
            HTTPException: 404 if document not found

        Examples:
            ```bash
            # Analyze document
            curl -X POST http://localhost:8000/documents/doc_abc123/analyze

            # Force re-analysis
            curl -X POST "http://localhost:8000/documents/doc_abc123/analyze?force_refresh=true"
            ```

            Response:
            ```json
            {
                "document_id": "doc_abc123",
                "summary": "W-2 showing $85,000 annual wages from Acme Corp",
                "key_findings": [
                    "High federal tax withholding (22% effective rate)",
                    "State tax withholding matches California brackets"
                ],
                "recommendations": [
                    "Consider adjusting W-4 allowances",
                    "Review retirement contribution limits"
                ],
                "confidence": 0.92
            }
            ```
        """
        try:
            return await manager.analyze(
                document_id=document_id, force_refresh=force_refresh
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Mount financial endpoints
    app.include_router(router)

    # Store financial manager on app.state for route access
    app.state.financial_documents = manager

    return manager
