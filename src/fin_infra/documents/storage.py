"""
Financial document storage operations (Layer 2 - delegates to svc-infra Layer 1).

This module provides financial-specific wrappers around svc-infra's generic document storage.
All storage operations delegate to svc-infra/documents for consistency.

Architecture:
    Layer 1 (svc-infra): Generic document CRUD using storage backend
    Layer 2 (fin-infra): Financial wrappers with DocumentType, tax_year, form_type

Quick Start:
    >>> from fin_infra.documents.storage import upload_document, list_documents
    >>> from svc_infra.storage import easy_storage
    >>>
    >>> storage = easy_storage()  # Auto-detects S3/local/memory
    >>>
    >>> # Upload financial document
    >>> doc = await upload_document(
    ...     storage=storage,
    ...     user_id="user_123",
    ...     file=uploaded_file,
    ...     document_type=DocumentType.TAX,
    ...     filename="w2_2024.pdf",
    ...     metadata={"tax_year": 2024, "form_type": "W-2"}
    ... )
    >>>
    >>> # List user's documents
    >>> docs = list_documents(user_id="user_123", document_type=DocumentType.TAX)
    >>>
    >>> # Download document
    >>> file_data = await download_document(storage, doc.id)
    >>>
    >>> # Delete document
    >>> await delete_document(storage, doc.id)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

try:
    from svc_infra.documents import (
        delete_document as base_delete_document,
        download_document as base_download_document,
        get_document as base_get_document,
        list_documents as base_list_documents,
        upload_document as base_upload_document,
    )
    HAS_SVC_INFRA_DOCUMENTS = True
except ImportError:
    # Fallback for older svc-infra versions - use legacy implementation
    HAS_SVC_INFRA_DOCUMENTS = False
    base_delete_document = None  # type: ignore
    base_download_document = None  # type: ignore
    base_get_document = None  # type: ignore
    base_list_documents = None  # type: ignore
    base_upload_document = None  # type: ignore

if TYPE_CHECKING:
    from svc_infra.storage.base import StorageBackend

    from .models import DocumentType, FinancialDocument


async def upload_document(
    storage: "StorageBackend",
    user_id: str,
    file: bytes,
    document_type: "DocumentType",
    filename: str,
    metadata: Optional[dict] = None,
    tax_year: Optional[int] = None,
    form_type: Optional[str] = None,
) -> "FinancialDocument":
    """
    Upload a financial document (delegates to svc-infra, adds financial fields).

    Args:
        storage: Storage backend instance
        user_id: User uploading the document
        file: File content as bytes
        document_type: Type of financial document
        filename: Original filename
        metadata: Optional custom metadata (employer, account, etc.)
        tax_year: Optional tax year (2024, 2023, etc.)
        form_type: Optional form type (W-2, 1099-INT, etc.)

    Returns:
        FinancialDocument with storage information and financial fields

    Examples:
        >>> from svc_infra.storage import easy_storage
        >>> storage = easy_storage()
        >>>
        >>> # Upload W-2 tax document
        >>> doc = await upload_document(
        ...     storage=storage,
        ...     user_id="user_123",
        ...     file=file_bytes,
        ...     document_type=DocumentType.TAX,
        ...     filename="w2_2024.pdf",
        ...     metadata={"employer": "ACME Corp"},
        ...     tax_year=2024,
        ...     form_type="W-2"
        ... )

    Notes:
        - Delegates to svc-infra.documents.upload_document for base storage
        - Adds financial-specific fields (type, tax_year, form_type)
        - Uses svc-infra storage backend (S3/local/memory)
    """
    from .models import FinancialDocument

    # Merge financial metadata into base metadata
    merged_metadata = metadata or {}
    merged_metadata["document_type"] = document_type.value
    if tax_year:
        merged_metadata["tax_year"] = tax_year
    if form_type:
        merged_metadata["form_type"] = form_type

    # Upload via svc-infra base layer
    base_doc = await base_upload_document(
        storage=storage,
        user_id=user_id,
        file=file,
        filename=filename,
        metadata=merged_metadata,
    )

    # Convert to FinancialDocument with financial-specific fields
    financial_doc = FinancialDocument(
        **base_doc.model_dump(),
        type=document_type,
        tax_year=tax_year,
        form_type=form_type,
    )

    return financial_doc


def get_document(document_id: str) -> Optional["FinancialDocument"]:
    """
    Get financial document metadata by ID (delegates to svc-infra).

    Args:
        document_id: Document identifier

    Returns:
        FinancialDocument metadata or None if not found

    Examples:
        >>> doc = get_document("doc_abc123")
        >>> if doc:
        ...     print(doc.filename, doc.type, doc.tax_year)
    
    Notes:
        - Delegates to svc-infra.documents.get_document
        - Converts base Document to FinancialDocument
        - Extracts financial fields from metadata if present
    """
    from .models import DocumentType, FinancialDocument

    base_doc = base_get_document(document_id)
    if not base_doc:
        return None

    # Extract financial fields from metadata
    doc_type_str = base_doc.metadata.get("document_type", "other")
    tax_year = base_doc.metadata.get("tax_year")
    form_type = base_doc.metadata.get("form_type")

    # Convert to FinancialDocument
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.OTHER

    financial_doc = FinancialDocument(
        **base_doc.model_dump(),
        type=doc_type,
        tax_year=tax_year,
        form_type=form_type,
    )

    return financial_doc


async def download_document(storage: "StorageBackend", document_id: str) -> bytes:
    """
    Download a financial document by ID (delegates to svc-infra).

    Args:
        storage: Storage backend instance
        document_id: Document identifier

    Returns:
        Document file content as bytes

    Raises:
        ValueError: If document not found

    Examples:
        >>> from svc_infra.storage import easy_storage
        >>> storage = easy_storage()
        >>> file_data = await download_document(storage, "doc_abc123")

    Notes:
        - Delegates to svc-infra.documents.download_document
        - Uses svc-infra storage backend for retrieval
    """
    return await base_download_document(storage=storage, document_id=document_id)


async def delete_document(storage: "StorageBackend", document_id: str) -> bool:
    """
    Delete a financial document and its metadata (delegates to svc-infra).

    Args:
        storage: Storage backend instance
        document_id: Document identifier

    Returns:
        True if deleted successfully, False if not found

    Examples:
        >>> from svc_infra.storage import easy_storage
        >>> storage = easy_storage()
        >>> success = await delete_document(storage, "doc_abc123")

    Notes:
        - Delegates to svc-infra.documents.delete_document
        - Removes from storage backend and metadata
    """
    return await base_delete_document(storage=storage, document_id=document_id)


def list_documents(
    user_id: str,
    document_type: Optional["DocumentType"] = None,
    tax_year: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> List["FinancialDocument"]:
    """
    List user's financial documents with optional filters (delegates to svc-infra).

    Args:
        user_id: User identifier
        document_type: Optional document type filter (TAX, STATEMENT, etc.)
        tax_year: Optional tax year filter
        limit: Maximum number of documents to return (default: 100)
        offset: Number of documents to skip (default: 0)

    Returns:
        List of user's financial documents

    Examples:
        >>> # All documents
        >>> docs = list_documents(user_id="user_123")
        >>>
        >>> # Tax documents only
        >>> tax_docs = list_documents(user_id="user_123", type=DocumentType.TAX)
        >>>
        >>> # 2024 tax documents
        >>> tax_2024 = list_documents(
        ...     user_id="user_123",
        ...     document_type=DocumentType.TAX,
        ...     tax_year=2024
        ... )

    Notes:
        - Delegates to svc-infra.documents.list_documents
        - Applies financial-specific filters on top of base results
        - Converts base Documents to FinancialDocuments
    """
    from .models import DocumentType, FinancialDocument

    # Get all user documents from svc-infra
    base_docs = base_list_documents(user_id=user_id, limit=limit, offset=offset)

    # Convert to FinancialDocuments and apply filters
    financial_docs = []
    for base_doc in base_docs:
        # Extract financial fields from metadata
        doc_type_str = base_doc.metadata.get("document_type", "other")
        year = base_doc.metadata.get("tax_year")
        form = base_doc.metadata.get("form_type")

        try:
            doc_type = DocumentType(doc_type_str)
        except ValueError:
            doc_type = DocumentType.OTHER

        # Apply filters
        if document_type is not None and doc_type != document_type:
            continue
        if tax_year is not None and year != tax_year:
            continue

        # Convert to FinancialDocument
        financial_doc = FinancialDocument(
            **base_doc.model_dump(),
            type=doc_type,
            tax_year=year,
            form_type=form,
        )
        financial_docs.append(financial_doc)

    return financial_docs


def clear_storage() -> None:
    """
    Clear all document metadata (for testing only).

    Delegates to svc-infra clear_storage.

    Examples:
        >>> clear_storage()  # Clears all documents for testing

    Notes:
        - Only for testing - DO NOT use in production
        - Delegates to svc-infra.documents.clear_storage
    """
    from svc_infra.documents import clear_storage as base_clear_storage

    base_clear_storage()
