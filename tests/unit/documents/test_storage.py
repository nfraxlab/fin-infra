"""Unit tests for document storage operations."""

import pytest

from fin_infra.documents.models import DocumentType
from fin_infra.documents.storage import (
    clear_storage,
    delete_document,
    download_document,
    get_document,
    list_documents,
    upload_document,
)


@pytest.fixture(autouse=True)
def clean_storage():
    """Clear storage before and after each test."""
    clear_storage()
    yield
    clear_storage()


class TestUploadDocument:
    """Tests for upload_document function."""

    def test_upload_basic_document(self):
        """Test uploading a basic document."""
        file_content = b"Test document content"
        doc = upload_document(
            user_id="user_123",
            file=file_content,
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024},
        )

        assert doc.id.startswith("doc_")
        assert doc.user_id == "user_123"
        assert doc.type == DocumentType.TAX
        assert doc.filename == "test.pdf"
        assert doc.file_size == len(file_content)
        assert doc.metadata["year"] == 2024
        assert doc.content_type == "application/pdf"
        assert doc.checksum is not None

    def test_upload_without_metadata(self):
        """Test uploading document without metadata."""
        doc = upload_document(
            user_id="user_456",
            file=b"content",
            document_type=DocumentType.RECEIPT,
            filename="receipt.jpg",
        )

        assert doc.metadata == {}
        assert doc.content_type == "image/jpeg"

    def test_upload_generates_unique_ids(self):
        """Test that each upload generates a unique ID."""
        doc1 = upload_document(
            user_id="user_123",
            file=b"content1",
            document_type=DocumentType.TAX,
            filename="doc1.pdf",
        )
        doc2 = upload_document(
            user_id="user_123",
            file=b"content2",
            document_type=DocumentType.TAX,
            filename="doc2.pdf",
        )

        assert doc1.id != doc2.id

    def test_upload_calculates_checksum(self):
        """Test that checksum is calculated for uploaded files."""
        file_content = b"Test content for checksum"
        doc = upload_document(
            user_id="user_123",
            file=file_content,
            document_type=DocumentType.STATEMENT,
            filename="statement.pdf",
        )

        assert doc.checksum is not None
        assert len(doc.checksum) == 64  # SHA-256 hex digest


class TestGetDocument:
    """Tests for get_document function."""

    def test_get_existing_document(self):
        """Test getting an existing document."""
        uploaded = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
        )

        retrieved = get_document(uploaded.id)
        assert retrieved is not None
        assert retrieved.id == uploaded.id
        assert retrieved.filename == uploaded.filename

    def test_get_nonexistent_document(self):
        """Test getting a non-existent document returns None."""
        result = get_document("doc_nonexistent")
        assert result is None


class TestDownloadDocument:
    """Tests for download_document function."""

    def test_download_existing_document(self):
        """Test downloading an existing document."""
        file_content = b"Test file content"
        doc = upload_document(
            user_id="user_123",
            file=file_content,
            document_type=DocumentType.TAX,
            filename="test.pdf",
        )

        downloaded = download_document(doc.id)
        assert downloaded == file_content

    def test_download_nonexistent_document(self):
        """Test downloading non-existent document raises error."""
        with pytest.raises(ValueError, match="Document not found"):
            download_document("doc_nonexistent")


class TestDeleteDocument:
    """Tests for delete_document function."""

    def test_delete_existing_document(self):
        """Test deleting an existing document."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
        )

        delete_document(doc.id)

        # Verify document is deleted
        assert get_document(doc.id) is None

        # Verify file is deleted
        with pytest.raises(ValueError, match="Document not found"):
            download_document(doc.id)

    def test_delete_nonexistent_document(self):
        """Test deleting non-existent document raises error."""
        with pytest.raises(ValueError, match="Document not found"):
            delete_document("doc_nonexistent")


class TestListDocuments:
    """Tests for list_documents function."""

    def test_list_all_user_documents(self):
        """Test listing all documents for a user."""
        doc1 = upload_document(
            user_id="user_123",
            file=b"content1",
            document_type=DocumentType.TAX,
            filename="tax.pdf",
        )
        doc2 = upload_document(
            user_id="user_123",
            file=b"content2",
            document_type=DocumentType.RECEIPT,
            filename="receipt.pdf",
        )
        # Different user
        upload_document(
            user_id="user_456",
            file=b"content3",
            document_type=DocumentType.TAX,
            filename="other.pdf",
        )

        docs = list_documents(user_id="user_123")
        assert len(docs) == 2
        assert doc1.id in [d.id for d in docs]
        assert doc2.id in [d.id for d in docs]

    def test_list_documents_by_type(self):
        """Test filtering documents by type."""
        doc1 = upload_document(
            user_id="user_123",
            file=b"content1",
            document_type=DocumentType.TAX,
            filename="tax.pdf",
        )
        upload_document(
            user_id="user_123",
            file=b"content2",
            document_type=DocumentType.RECEIPT,
            filename="receipt.pdf",
        )

        docs = list_documents(user_id="user_123", type=DocumentType.TAX)
        assert len(docs) == 1
        assert docs[0].id == doc1.id

    def test_list_documents_by_year(self):
        """Test filtering documents by year."""
        doc1 = upload_document(
            user_id="user_123",
            file=b"content1",
            document_type=DocumentType.TAX,
            filename="tax_2024.pdf",
            metadata={"year": 2024},
        )
        upload_document(
            user_id="user_123",
            file=b"content2",
            document_type=DocumentType.TAX,
            filename="tax_2023.pdf",
            metadata={"year": 2023},
        )

        docs = list_documents(user_id="user_123", year=2024)
        assert len(docs) == 1
        assert docs[0].id == doc1.id

    def test_list_documents_by_type_and_year(self):
        """Test filtering by both type and year."""
        doc1 = upload_document(
            user_id="user_123",
            file=b"content1",
            document_type=DocumentType.TAX,
            filename="tax_2024.pdf",
            metadata={"year": 2024},
        )
        upload_document(
            user_id="user_123",
            file=b"content2",
            document_type=DocumentType.TAX,
            filename="tax_2023.pdf",
            metadata={"year": 2023},
        )
        upload_document(
            user_id="user_123",
            file=b"content3",
            document_type=DocumentType.RECEIPT,
            filename="receipt_2024.pdf",
            metadata={"year": 2024},
        )

        docs = list_documents(user_id="user_123", type=DocumentType.TAX, year=2024)
        assert len(docs) == 1
        assert docs[0].id == doc1.id

    def test_list_documents_sorted_by_date(self):
        """Test that documents are sorted by upload date descending."""
        doc1 = upload_document(
            user_id="user_123",
            file=b"content1",
            document_type=DocumentType.TAX,
            filename="first.pdf",
        )
        doc2 = upload_document(
            user_id="user_123",
            file=b"content2",
            document_type=DocumentType.TAX,
            filename="second.pdf",
        )

        docs = list_documents(user_id="user_123")
        # Most recent first
        assert docs[0].id == doc2.id
        assert docs[1].id == doc1.id

    def test_list_documents_empty(self):
        """Test listing documents for user with no documents."""
        docs = list_documents(user_id="user_empty")
        assert docs == []
