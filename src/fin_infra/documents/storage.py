"""
Document storage operations.

Handles upload, download, deletion, and listing of financial documents.
Uses in-memory storage for simplicity (production: use svc-infra S3/SQL).

Quick Start:
    >>> from fin_infra.documents.storage import upload_document, list_documents
    >>>
    >>> # Upload document
    >>> doc = upload_document(
    ...     user_id="user_123",
    ...     file=uploaded_file,
    ...     document_type=DocumentType.TAX,
    ...     metadata={"year": 2024, "form_type": "W-2"}
    ... )
    >>>
    >>> # List user's documents
    >>> docs = list_documents(user_id="user_123", type=DocumentType.TAX, year=2024)
    >>>
    >>> # Download document
    >>> file_data = download_document(doc.id)
    >>>
    >>> # Delete document
    >>> delete_document(doc.id)

Production Integration:
    - Use svc-infra file storage for S3/local filesystem
    - Store metadata in svc-infra SQL database
    - Enable virus scanning (ClamAV integration)
    - Implement retention policies (auto-delete after N years)
    - Add document versioning support
"""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .models import Document, DocumentType

# In-memory storage (production: use svc-infra SQL + S3)
_documents: Dict[str, "Document"] = {}
_file_storage: Dict[str, bytes] = {}


def upload_document(
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
        metadata: Optional custom metadata (year, form type, etc.)

    Returns:
        Document with storage information

    Examples:
        >>> doc = upload_document(
        ...     user_id="user_123",
        ...     file=file_bytes,
        ...     document_type=DocumentType.TAX,
        ...     filename="w2_2024.pdf",
        ...     metadata={"year": 2024, "form_type": "W-2"}
        ... )

    Notes:
        - Current: In-memory storage (for development/testing)
        - Production: Use svc-infra file storage (S3/local)
        - Production: Enable virus scanning before storage
        - Production: Store metadata in svc-infra SQL database
    """
    from .models import Document

    # Generate unique document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"

    # Generate unique storage path
    storage_path = f"/documents/{user_id}/{doc_id}/{filename}"

    # Calculate checksum for integrity
    checksum = hashlib.sha256(file).hexdigest()

    # Detect content type
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    # Create document metadata
    doc = Document(
        id=doc_id,
        user_id=user_id,
        type=document_type,
        filename=filename,
        file_size=len(file),
        upload_date=datetime.utcnow(),
        metadata=metadata or {},
        storage_path=storage_path,
        content_type=content_type,
        checksum=checksum,
    )

    # Store document metadata and file
    _documents[doc_id] = doc
    _file_storage[doc_id] = file

    return doc


def get_document(document_id: str) -> Optional["Document"]:
    """
    Get document metadata by ID.

    Args:
        document_id: Document identifier

    Returns:
        Document metadata or None if not found

    Examples:
        >>> doc = get_document("doc_abc123")
        >>> if doc:
        ...     print(doc.filename)
    """
    return _documents.get(document_id)


def download_document(document_id: str) -> bytes:
    """
    Download a document by ID.

    Args:
        document_id: Document identifier

    Returns:
        Document file content as bytes

    Raises:
        ValueError: If document not found

    Examples:
        >>> file_data = download_document("doc_abc123")

    Notes:
        - Current: In-memory storage
        - Production: Use svc-infra file storage retrieval
        - Production: Check user permissions before download
        - Production: Log download for audit trail
    """
    if document_id not in _file_storage:
        raise ValueError(f"Document not found: {document_id}")

    return _file_storage[document_id]


def delete_document(document_id: str) -> None:
    """
    Delete a document and its metadata.

    Args:
        document_id: Document identifier

    Raises:
        ValueError: If document not found

    Examples:
        >>> delete_document("doc_abc123")

    Notes:
        - Current: Hard delete from memory
        - Production: Check user permissions before deletion
        - Production: Soft-delete (mark as deleted, don't remove immediately)
        - Production: Implement retention policy (auto-delete after N days)
        - Production: Remove from file storage and database
    """
    if document_id not in _documents:
        raise ValueError(f"Document not found: {document_id}")

    # Remove from both storages
    del _documents[document_id]
    del _file_storage[document_id]


def list_documents(
    user_id: str,
    type: Optional["DocumentType"] = None,
    year: Optional[int] = None,
) -> List["Document"]:
    """
    List user's documents with optional filters.

    Args:
        user_id: User identifier
        type: Optional document type filter
        year: Optional year filter (from metadata)

    Returns:
        List of user's documents

    Examples:
        >>> # All documents
        >>> docs = list_documents(user_id="user_123")
        >>>
        >>> # Tax documents only
        >>> tax_docs = list_documents(user_id="user_123", type=DocumentType.TAX)
        >>>
        >>> # 2024 tax documents
        >>> tax_2024 = list_documents(user_id="user_123", type=DocumentType.TAX, year=2024)

    Notes:
        - Current: In-memory filtering
        - Production: Query svc-infra SQL database
        - Production: Add pagination for large result sets
        - Production: Sort by upload_date descending
        - Production: Include soft-deleted flag in filters
    """
    # Filter by user_id
    docs = [doc for doc in _documents.values() if doc.user_id == user_id]

    # Filter by type
    if type is not None:
        docs = [doc for doc in docs if doc.type == type]

    # Filter by year (from metadata)
    if year is not None:
        docs = [doc for doc in docs if doc.metadata.get("year") == year]

    # Sort by upload_date descending
    docs.sort(key=lambda d: d.upload_date, reverse=True)

    return docs


def clear_storage() -> None:
    """
    Clear all documents from storage (for testing only).

    Examples:
        >>> clear_storage()
    """
    _documents.clear()
    _file_storage.clear()
