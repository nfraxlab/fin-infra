"""
Financial document manager (extends svc-infra DocumentManager with OCR/AI).

Provides financial-specific document operations built on svc-infra base:
- Upload, download, delete, list (inherited from svc-infra)
- OCR text extraction for tax forms (financial extension)
- AI-powered analysis (financial extension)

Architecture:
    Layer 1 (svc-infra): Generic document CRUD
    Layer 2 (fin-infra): + OCR + AI analysis

Quick Start:
    >>> from fin_infra.documents import easy_documents
    >>> from svc_infra.storage import easy_storage
    >>>
    >>> storage = easy_storage()  # Auto-detects backend
    >>> manager = easy_documents(storage)
    >>>
    >>> # Upload financial document (with financial fields)
    >>> doc = await manager.upload_financial(
    ...     user_id="user_123",
    ...     file=uploaded_file,
    ...     document_type=DocumentType.TAX,
    ...     filename="w2.pdf",
    ...     tax_year=2024,
    ...     form_type="W-2"
    ... )
    >>>
    >>> # Extract text with OCR
    >>> ocr_result = await manager.extract_text(doc.id)
    >>>
    >>> # Analyze with AI
    >>> analysis = await manager.analyze(doc.id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

try:
    from svc_infra.documents import DocumentManager as BaseDocumentManager
except ImportError:
    # Fallback for older svc-infra versions without documents module
    # This provides backward compatibility until svc-infra 0.1.668+ is published
    import warnings
    warnings.warn(
        "svc_infra.documents not found. Using legacy implementation. "
        "Please upgrade svc-infra to >=0.1.668 for layered architecture support.",
        DeprecationWarning,
        stacklevel=2
    )
    BaseDocumentManager = object  # type: ignore

if TYPE_CHECKING:
    from svc_infra.storage.base import StorageBackend

    from .models import DocumentAnalysis, DocumentType, FinancialDocument, OCRResult


class FinancialDocumentManager(BaseDocumentManager):
    """
    Financial document manager extending svc-infra with OCR and AI analysis.

    Inherits from svc-infra DocumentManager:
        - upload(), download(), delete(), get(), list() for base document CRUD
        - storage backend integration
    
    Adds financial-specific methods:
        - upload_financial(): Upload with DocumentType, tax_year, form_type
        - extract_text(): OCR for tax forms  
        - analyze(): AI-powered financial insights

    Attributes:
        storage: Storage backend (inherited from BaseDocumentManager)
        default_ocr_provider: OCR provider (tesseract/textract)

    Examples:
        >>> from svc_infra.storage import easy_storage
        >>> storage = easy_storage()
        >>> manager = FinancialDocumentManager(storage)
        >>>
        >>> # Upload W-2 tax form
        >>> doc = await manager.upload_financial(
        ...     user_id="user_123",
        ...     file=file_bytes,
        ...     document_type=DocumentType.TAX,
        ...     filename="w2.pdf",
        ...     tax_year=2024,
        ...     form_type="W-2"
        ... )
    """

    def __init__(
        self,
        storage: "StorageBackend",
        default_ocr_provider: str = "tesseract",
    ):
        """
        Initialize financial document manager.

        Args:
            storage: Storage backend instance (S3/local/memory)
            default_ocr_provider: Default OCR provider (tesseract/textract)
        """
        super().__init__(storage)
        self.default_ocr_provider = default_ocr_provider

    async def upload_financial(
        self,
        user_id: str,
        file: bytes,
        document_type: "DocumentType",
        filename: str,
        metadata: Optional[dict] = None,
        tax_year: Optional[int] = None,
        form_type: Optional[str] = None,
    ) -> "FinancialDocument":
        """
        Upload a financial document with financial-specific fields.

        Args:
            user_id: User uploading the document
            file: File content as bytes
            document_type: Type of financial document
            filename: Original filename
            metadata: Optional custom metadata (employer, account, etc.)
            tax_year: Optional tax year (2024, 2023, etc.)
            form_type: Optional form type (W-2, 1099-INT, etc.)

        Returns:
            FinancialDocument with storage info and financial fields

        Examples:
            >>> doc = await manager.upload_financial(
            ...     user_id="user_123",
            ...     file=file_bytes,
            ...     document_type=DocumentType.TAX,
            ...     filename="w2_2024.pdf",
            ...     metadata={"employer": "ACME Corp"},
            ...     tax_year=2024,
            ...     form_type="W-2"
            ... )
        """
        from .storage import upload_document

        return await upload_document(
            storage=self.storage,
            user_id=user_id,
            file=file,
            document_type=document_type,
            filename=filename,
            metadata=metadata,
            tax_year=tax_year,
            form_type=form_type,
        )

    def list_financial(
        self,
        user_id: str,
        document_type: Optional["DocumentType"] = None,
        tax_year: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list["FinancialDocument"]:
        """
        List user's financial documents with filters.

        Args:
            user_id: User identifier
            document_type: Optional document type filter
            tax_year: Optional tax year filter
            limit: Maximum number of documents (default: 100)
            offset: Number of documents to skip (default: 0)

        Returns:
            List of financial documents

        Examples:
            >>> # All documents
            >>> docs = manager.list_financial(user_id="user_123")
            >>>
            >>> # Tax documents only
            >>> tax_docs = manager.list_financial(
            ...     user_id="user_123",
            ...     document_type=DocumentType.TAX
            ... )
            >>>
            >>> # 2024 tax documents
            >>> tax_2024 = manager.list_financial(
            ...     user_id="user_123",
            ...     document_type=DocumentType.TAX,
            ...     tax_year=2024
            ... )
        """
        from .storage import list_documents

        return list_documents(
            user_id=user_id,
            document_type=document_type,
            tax_year=tax_year,
            limit=limit,
            offset=offset,
        )

    async def extract_text(
        self,
        document_id: str,
        provider: Optional[str] = None,
        force_refresh: bool = False,
    ) -> "OCRResult":
        """
        Extract text from document using OCR (financial extension).

        Args:
            document_id: Document identifier
            provider: OCR provider (defaults to instance default)
            force_refresh: Force re-extraction

        Returns:
            OCR result with extracted text

        Examples:
            >>> result = await manager.extract_text("doc_abc123")
            >>> print(result.text)
            >>> print(result.fields_extracted)  # Structured tax form fields
        """
        from .ocr import extract_text

        return await extract_text(
            storage=self.storage,
            document_id=document_id,
            provider=provider or self.default_ocr_provider,
            force_refresh=force_refresh,
        )

    async def analyze(
        self,
        document_id: str,
        force_refresh: bool = False,
    ) -> "DocumentAnalysis":
        """
        Analyze document using AI (financial extension).

        Args:
            document_id: Document identifier
            force_refresh: Force re-analysis

        Returns:
            Document analysis with financial insights

        Examples:
            >>> analysis = await manager.analyze("doc_abc123")
            >>> print(analysis.summary)
            >>> print(analysis.key_findings)
            >>> print(analysis.recommendations)
        """
        from .analysis import analyze_document

        return await analyze_document(
            storage=self.storage, document_id=document_id, force_refresh=force_refresh
        )


# Backward compatibility alias
DocumentManager = FinancialDocumentManager


def easy_documents(
    storage: Optional["StorageBackend"] = None,
    default_ocr_provider: str = "tesseract",
) -> FinancialDocumentManager:
    """
    Create a financial document manager with sensible defaults.

    Args:
        storage: Storage backend (auto-detects if None)
        default_ocr_provider: Default OCR provider (tesseract/textract)

    Returns:
        Configured financial document manager

    Examples:
        >>> from svc_infra.storage import easy_storage
        >>>
        >>> # Auto-detect storage backend
        >>> manager = easy_documents()
        >>>
        >>> # Explicit S3 storage
        >>> storage = easy_storage()  # Uses env vars for S3 config
        >>> manager = easy_documents(storage, default_ocr_provider="textract")
        >>>
        >>> # Memory backend for testing
        >>> from svc_infra.storage import MemoryBackend
        >>> storage = MemoryBackend()
        >>> manager = easy_documents(storage)
    """
    if storage is None:
        from svc_infra.storage import easy_storage

        storage = easy_storage()

    return FinancialDocumentManager(storage=storage, default_ocr_provider=default_ocr_provider)
