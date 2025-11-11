"""
Easy builder for document management.

Provides a simple interface for document upload, OCR, and analysis.
Returns a manager instance with all document operations.

Quick Start:
    >>> from fin_infra.documents import easy_documents
    >>>
    >>> # Create manager
    >>> manager = easy_documents(storage_path="/data/documents")
    >>>
    >>> # Upload document
    >>> doc = manager.upload(
    ...     user_id="user_123",
    ...     file=uploaded_file,
    ...     document_type="tax",
    ...     metadata={"year": 2024}
    ... )
    >>>
    >>> # Extract text
    >>> ocr_result = manager.extract_text(doc.id)
    >>>
    >>> # Analyze document
    >>> analysis = manager.analyze(doc.id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import Document, DocumentAnalysis, DocumentType, OCRResult


class DocumentManager:
    """
    Document manager for upload, OCR, and analysis operations.

    Attributes:
        storage_path: Base path for document storage
        default_ocr_provider: Default OCR provider (tesseract/textract)

    Examples:
        >>> manager = DocumentManager(storage_path="/data/documents")
        >>> doc = manager.upload(user_id="user_123", file=file_bytes, document_type="tax")
    """

    def __init__(
        self,
        storage_path: str = "/tmp/documents",
        default_ocr_provider: str = "tesseract",
    ):
        """
        Initialize document manager.

        Args:
            storage_path: Base path for document storage
            default_ocr_provider: Default OCR provider (tesseract/textract)
        """
        self.storage_path = storage_path
        self.default_ocr_provider = default_ocr_provider

    def upload(
        self,
        user_id: str,
        file: bytes,
        document_type: "DocumentType",
        filename: str,
        metadata: Optional[dict] = None,
    ) -> "Document":
        """
        Upload a financial document.

        Args:
            user_id: User uploading the document
            file: File content as bytes
            document_type: Type of document
            filename: Original filename
            metadata: Optional custom metadata

        Returns:
            Uploaded document

        Examples:
            >>> doc = manager.upload(
            ...     user_id="user_123",
            ...     file=file_bytes,
            ...     document_type="tax",
            ...     filename="w2_2024.pdf",
            ...     metadata={"year": 2024}
            ... )
        """
        from .storage import upload_document

        return upload_document(user_id, file, document_type, filename, metadata)

    def download(self, document_id: str) -> bytes:
        """
        Download a document by ID.

        Args:
            document_id: Document identifier

        Returns:
            Document file content

        Examples:
            >>> file_data = manager.download("doc_abc123")
        """
        from .storage import download_document

        return download_document(document_id)

    def delete(self, document_id: str) -> None:
        """
        Delete a document.

        Args:
            document_id: Document identifier

        Examples:
            >>> manager.delete("doc_abc123")
        """
        from .storage import delete_document

        delete_document(document_id)

    def list(
        self,
        user_id: str,
        type: Optional["DocumentType"] = None,
        year: Optional[int] = None,
    ) -> list["Document"]:
        """
        List user's documents.

        Args:
            user_id: User identifier
            type: Optional document type filter
            year: Optional year filter

        Returns:
            List of documents

        Examples:
            >>> docs = manager.list(user_id="user_123", type="tax", year=2024)
        """
        from .storage import list_documents

        return list_documents(user_id, type, year)

    def extract_text(
        self,
        document_id: str,
        provider: Optional[str] = None,
        force_refresh: bool = False,
    ) -> "OCRResult":
        """
        Extract text from document using OCR.

        Args:
            document_id: Document identifier
            provider: OCR provider (defaults to instance default)
            force_refresh: Force re-extraction

        Returns:
            OCR result with extracted text

        Examples:
            >>> result = manager.extract_text("doc_abc123")
            >>> print(result.text)
        """
        from .ocr import extract_text

        return extract_text(document_id, provider or self.default_ocr_provider, force_refresh)

    def analyze(
        self,
        document_id: str,
        force_refresh: bool = False,
    ) -> "DocumentAnalysis":
        """
        Analyze document using AI.

        Args:
            document_id: Document identifier
            force_refresh: Force re-analysis

        Returns:
            Document analysis with insights

        Examples:
            >>> analysis = manager.analyze("doc_abc123")
            >>> print(analysis.summary)
        """
        from .analysis import analyze_document

        return analyze_document(document_id, force_refresh)


def easy_documents(
    storage_path: str = "/tmp/documents",
    default_ocr_provider: str = "tesseract",
) -> DocumentManager:
    """
    Create a document manager with sensible defaults.

    Args:
        storage_path: Base path for document storage
        default_ocr_provider: Default OCR provider (tesseract/textract)

    Returns:
        Configured document manager

    Examples:
        >>> # Development (local storage, free OCR)
        >>> manager = easy_documents()
        >>>
        >>> # Production (S3 storage, AWS Textract)
        >>> manager = easy_documents(
        ...     storage_path="s3://my-bucket/documents",
        ...     default_ocr_provider="textract"
        ... )
    """
    return DocumentManager(storage_path=storage_path, default_ocr_provider=default_ocr_provider)
