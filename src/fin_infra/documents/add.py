"""
FastAPI integration for document management.

Mounts document endpoints:
- POST /documents/upload - Upload new document
- GET /documents/{document_id} - Get document details
- GET /documents/list - List user's documents
- DELETE /documents/{document_id} - Delete document
- POST /documents/{document_id}/ocr - Extract text via OCR
- POST /documents/{document_id}/analyze - Analyze document with AI

Quick Start:
    >>> from fastapi import FastAPI
    >>> from fin_infra.documents import add_documents
    >>>
    >>> app = FastAPI()
    >>> manager = add_documents(app, storage_path="/data/documents")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .ease import DocumentManager


def add_documents(
    app: "FastAPI",
    storage_path: str = "/tmp/documents",
    default_ocr_provider: str = "tesseract",
    prefix: str = "/documents",
) -> "DocumentManager":
    """
    Add document management endpoints to FastAPI app.

    Mounts 6 endpoints:
    1. POST /documents/upload - Upload new document
    2. GET /documents/{document_id} - Get document details
    3. GET /documents/list - List user's documents
    4. DELETE /documents/{document_id} - Delete document
    5. POST /documents/{document_id}/ocr - Extract text via OCR
    6. POST /documents/{document_id}/analyze - Analyze document with AI

    Args:
        app: FastAPI application
        storage_path: Base path for document storage
        default_ocr_provider: Default OCR provider (tesseract/textract)
        prefix: URL prefix for document endpoints

    Returns:
        Document manager instance for programmatic access

    Examples:
        >>> from fastapi import FastAPI
        >>> from fin_infra.documents import add_documents
        >>>
        >>> app = FastAPI()
        >>> manager = add_documents(
        ...     app,
        ...     storage_path="/data/documents",
        ...     default_ocr_provider="tesseract"
        ... )
        >>>
        >>> # Access manager programmatically
        >>> doc = manager.upload(user_id="user_123", file=file_bytes, document_type="tax")

    Notes:
        - Uses svc-infra dual routers (user_router for auth)
        - Registers scoped docs with add_prefixed_docs
        - Stores manager on app.state for route access
        - All routes require user authentication
    """
    from .ease import easy_documents

    # Create manager
    manager = easy_documents(
        storage_path=storage_path,
        default_ocr_provider=default_ocr_provider,
    )

    # Create router with svc-infra dual router (user_router for auth)
    from svc_infra.api.fastapi.dual.protected import user_router

    router = user_router(prefix=prefix, tags=["Documents"])

    # Route 1: Upload document
    @router.post("/upload")
    async def upload_document(
        user_id: str,
        file: bytes,
        document_type: str,
        filename: str,
        metadata: Optional[dict] = None,
    ):
        """
        Upload a financial document.

        Args:
            user_id: User uploading the document
            file: File content as bytes
            document_type: Type of document (tax, statement, receipt, etc.)
            filename: Original filename
            metadata: Optional custom metadata (year, form_type, etc.)

        Returns:
            Uploaded document with ID and storage information

        Examples:
            >>> # Upload W-2 tax document
            >>> POST /documents/upload
            >>> {
            ...     "user_id": "user_123",
            ...     "file": <binary data>,
            ...     "document_type": "tax",
            ...     "filename": "w2_2024.pdf",
            ...     "metadata": {"year": 2024, "form_type": "W-2"}
            ... }
        """
        from .models import DocumentType

        return manager.upload(
            user_id=user_id,
            file=file,
            document_type=DocumentType(document_type),
            filename=filename,
            metadata=metadata,
        )

    # Route 2: Get document details
    @router.get("/{document_id}")
    async def get_document(document_id: str):
        """
        Get document details (not file content).

        Args:
            document_id: Document identifier

        Returns:
            Document metadata

        Examples:
            >>> GET /documents/doc_abc123
        """
        from .storage import get_document as get_doc_metadata

        doc = get_doc_metadata(document_id)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        return doc

    # Route 3: List user's documents
    @router.get("/list")
    async def list_documents(
        user_id: str,
        type: Optional[str] = None,
        year: Optional[int] = None,
    ):
        """
        List user's documents with optional filters.

        Args:
            user_id: User identifier
            type: Optional document type filter
            year: Optional year filter

        Returns:
            List of user's documents

        Examples:
            >>> # All documents
            >>> GET /documents/list?user_id=user_123
            >>>
            >>> # Tax documents only
            >>> GET /documents/list?user_id=user_123&type=tax
            >>>
            >>> # 2024 tax documents
            >>> GET /documents/list?user_id=user_123&type=tax&year=2024
        """
        from .models import DocumentType

        type_enum = DocumentType(type) if type else None
        return manager.list(user_id=user_id, type=type_enum, year=year)

    # Route 4: Delete document
    @router.delete("/{document_id}")
    async def delete_document(document_id: str):
        """
        Delete a document and its metadata.

        Args:
            document_id: Document identifier

        Returns:
            Success message

        Examples:
            >>> DELETE /documents/doc_abc123
        """
        manager.delete(document_id)
        return {"message": "Document deleted successfully"}

    # Route 5: Extract text via OCR
    @router.post("/{document_id}/ocr")
    async def extract_text(
        document_id: str,
        provider: Optional[str] = None,
        force_refresh: bool = False,
    ):
        """
        Extract text from document using OCR.

        Args:
            document_id: Document identifier
            provider: OCR provider (tesseract/textract, defaults to manager default)
            force_refresh: Force re-extraction even if cached

        Returns:
            OCR result with extracted text and structured fields

        Examples:
            >>> # Basic OCR (default provider)
            >>> POST /documents/doc_abc123/ocr
            >>>
            >>> # High-accuracy OCR (AWS Textract)
            >>> POST /documents/doc_abc123/ocr?provider=textract
            >>>
            >>> # Force re-extraction
            >>> POST /documents/doc_abc123/ocr?force_refresh=true
        """
        return manager.extract_text(
            document_id=document_id,
            provider=provider,
            force_refresh=force_refresh,
        )

    # Route 6: Analyze document with AI
    @router.post("/{document_id}/analyze")
    async def analyze_document(
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

        Examples:
            >>> POST /documents/doc_abc123/analyze
            >>> {
            ...     "document_id": "doc_abc123",
            ...     "summary": "W-2 showing $85,000 annual wages from Acme Corp",
            ...     "key_findings": [
            ...         "High federal tax withholding (22% effective rate)",
            ...         "State tax withholding matches California brackets"
            ...     ],
            ...     "recommendations": [
            ...         "Consider adjusting W-4 allowances",
            ...         "Review retirement contribution limits"
            ...     ],
            ...     "confidence": 0.92
            ... }
        """
        return manager.analyze(document_id=document_id, force_refresh=force_refresh)

    # Mount router
    app.include_router(router, include_in_schema=True)

    # Register scoped docs for landing page card
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs

    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Document Management",
        auto_exclude_from_root=True,
        visible_envs=None,  # Show in all environments
    )

    # Store manager on app.state for route access
    app.state.document_manager = manager

    return manager
