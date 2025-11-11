"""Unit tests for OCR extraction."""

import pytest

from fin_infra.documents.models import DocumentType
from fin_infra.documents.ocr import clear_cache, extract_text
from fin_infra.documents.storage import clear_storage, upload_document


@pytest.fixture(autouse=True)
def clean_caches():
    """Clear caches before and after each test."""
    clear_storage()
    clear_cache()
    yield
    clear_storage()
    clear_cache()


class TestExtractText:
    """Tests for extract_text function."""

    def test_extract_text_basic(self):
        """Test basic text extraction."""
        doc = upload_document(
            user_id="user_123",
            file=b"PDF content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2"},
        )

        result = extract_text(doc.id, provider="tesseract")

        assert result.document_id == doc.id
        assert result.text is not None
        assert len(result.text) > 0
        assert result.confidence > 0
        assert result.provider == "tesseract"
        assert result.extraction_date is not None

    def test_extract_text_w2_form(self):
        """Test extracting text from W-2 tax form."""
        doc = upload_document(
            user_id="user_123",
            file=b"W-2 content",
            document_type=DocumentType.TAX,
            filename="w2_2024.pdf",
            metadata={
                "year": 2024,
                "form_type": "W-2",
                "employer": "Acme Corp",
                "wages": "85000",
                "federal_tax": "18700",
                "state_tax": "4250",
                "document_id": "doc_w2",
            },
        )

        result = extract_text(doc.id, provider="tesseract")

        assert "W-2" in result.text
        assert "Acme Corp" in result.text
        assert result.fields_extracted is not None
        assert "employer" in result.fields_extracted
        assert "wages" in result.fields_extracted

    def test_extract_text_1099_form(self):
        """Test extracting text from 1099 tax form."""
        doc = upload_document(
            user_id="user_123",
            file=b"1099 content",
            document_type=DocumentType.TAX,
            filename="1099_2024.pdf",
            metadata={
                "year": 2024,
                "form_type": "1099",
                "payer": "Client LLC",
                "income": "45000",
                "document_id": "doc_1099",
            },
        )

        result = extract_text(doc.id, provider="tesseract")

        assert "1099" in result.text
        assert "Client LLC" in result.text
        assert result.fields_extracted is not None

    def test_extract_text_tesseract_provider(self):
        """Test Tesseract provider has lower confidence."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_tess"},
        )

        result = extract_text(doc.id, provider="tesseract")

        assert result.provider == "tesseract"
        # Tesseract should have lower confidence
        assert 0.80 <= result.confidence <= 0.90

    def test_extract_text_textract_provider(self):
        """Test AWS Textract provider has higher confidence."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_textract"},
        )

        result = extract_text(doc.id, provider="textract")

        assert result.provider == "textract"
        # Textract should have higher confidence
        assert result.confidence >= 0.90

    def test_extract_text_caching(self):
        """Test that OCR results are cached."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_cache"},
        )

        result1 = extract_text(doc.id, provider="tesseract")
        result2 = extract_text(doc.id, provider="tesseract")

        # Should be the same cached result
        assert result1.extraction_date == result2.extraction_date
        assert result1.text == result2.text

    def test_extract_text_force_refresh(self):
        """Test force refresh bypasses cache."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_refresh"},
        )

        result1 = extract_text(doc.id, provider="tesseract")
        result2 = extract_text(doc.id, provider="tesseract", force_refresh=True)

        # Should have different extraction dates
        assert result1.extraction_date != result2.extraction_date

    def test_extract_text_invalid_provider(self):
        """Test invalid provider raises error."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"document_id": "doc_invalid"},
        )

        with pytest.raises(ValueError, match="Unknown OCR provider"):
            extract_text(doc.id, provider="invalid")

    def test_extract_text_nonexistent_document(self):
        """Test extracting from non-existent document raises error."""
        with pytest.raises(ValueError, match="Document not found"):
            extract_text("doc_nonexistent")

    def test_extract_text_generic_document(self):
        """Test extracting text from generic document type."""
        doc = upload_document(
            user_id="user_123",
            file=b"Generic content",
            document_type=DocumentType.RECEIPT,
            filename="receipt.pdf",
        )

        result = extract_text(doc.id, provider="tesseract")

        assert result.document_id == doc.id
        assert result.text is not None
        assert result.confidence > 0

    def test_extract_text_fields_extracted(self):
        """Test that structured fields are extracted from W-2."""
        doc = upload_document(
            user_id="user_123",
            file=b"W-2 content",
            document_type=DocumentType.TAX,
            filename="w2.pdf",
            metadata={
                "year": 2024,
                "form_type": "W-2",
                "employer": "Test Company",
                "wages": "100000",
                "federal_tax": "22000",
                "state_tax": "5000",
                "document_id": "doc_fields",
            },
        )

        result = extract_text(doc.id, provider="textract")

        # Should have extracted fields
        assert len(result.fields_extracted) > 0
        assert "employer" in result.fields_extracted
        assert result.fields_extracted["employer"] == "Test Company"
        assert "wages" in result.fields_extracted
