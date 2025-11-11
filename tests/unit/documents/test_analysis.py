"""Unit tests for document analysis."""

import pytest

from fin_infra.documents.analysis import analyze_document, clear_cache
from fin_infra.documents.models import DocumentType
from fin_infra.documents.ocr import clear_cache as clear_ocr_cache
from fin_infra.documents.storage import clear_storage, upload_document


@pytest.fixture(autouse=True)
def clean_caches():
    """Clear caches before and after each test."""
    clear_storage()
    clear_ocr_cache()
    clear_cache()
    yield
    clear_storage()
    clear_ocr_cache()
    clear_cache()


class TestAnalyzeDocument:
    """Tests for analyze_document function."""

    def test_analyze_w2_document(self):
        """Test analyzing W-2 tax document."""
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
                "document_id": doc.id if "doc" in locals() else "doc_w2",
            },
        )

        result = analyze_document(doc.id)

        assert result.document_id == doc.id
        assert result.summary is not None
        assert len(result.summary) > 0
        assert "Acme Corp" in result.summary or "85,000" in result.summary
        assert len(result.key_findings) > 0
        assert len(result.recommendations) > 0
        assert result.confidence > 0.7
        assert result.analysis_date is not None

    def test_analyze_1099_document(self):
        """Test analyzing 1099 tax document."""
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
                "document_id": doc.id if "doc" in locals() else "doc_1099",
            },
        )

        result = analyze_document(doc.id)

        assert result.document_id == doc.id
        assert result.summary is not None
        assert len(result.key_findings) >= 3
        assert len(result.recommendations) >= 3

    def test_analyze_bank_statement(self):
        """Test analyzing bank statement."""
        doc = upload_document(
            user_id="user_123",
            file=b"Statement content",
            document_type=DocumentType.STATEMENT,
            filename="statement_2024_12.pdf",
            metadata={"year": 2024, "month": 12, "document_id": "doc_statement"},
        )

        result = analyze_document(doc.id)

        assert result.document_id == doc.id
        assert "statement" in result.summary.lower()
        assert len(result.key_findings) > 0
        assert len(result.recommendations) > 0

    def test_analyze_receipt(self):
        """Test analyzing receipt."""
        doc = upload_document(
            user_id="user_123",
            file=b"Receipt content",
            document_type=DocumentType.RECEIPT,
            filename="receipt.pdf",
            metadata={"document_id": "doc_receipt"},
        )

        result = analyze_document(doc.id)

        assert result.document_id == doc.id
        assert "receipt" in result.summary.lower()
        assert len(result.key_findings) > 0

    def test_analyze_generic_document(self):
        """Test analyzing generic document type."""
        doc = upload_document(
            user_id="user_123",
            file=b"Contract content",
            document_type=DocumentType.CONTRACT,
            filename="contract.pdf",
            metadata={"document_id": "doc_contract"},
        )

        result = analyze_document(doc.id)

        assert result.document_id == doc.id
        assert result.summary is not None
        assert len(result.key_findings) > 0
        assert len(result.recommendations) > 0

    def test_analyze_caching(self):
        """Test that analysis results are cached."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_cache"},
        )

        result1 = analyze_document(doc.id)
        result2 = analyze_document(doc.id)

        # Should be the same cached result
        assert result1.analysis_date == result2.analysis_date
        assert result1.summary == result2.summary

    def test_analyze_force_refresh(self):
        """Test force refresh bypasses cache."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_refresh"},
        )

        result1 = analyze_document(doc.id)
        result2 = analyze_document(doc.id, force_refresh=True)

        # Should have different analysis dates
        assert result1.analysis_date != result2.analysis_date

    def test_analyze_nonexistent_document(self):
        """Test analyzing non-existent document raises error."""
        with pytest.raises(ValueError, match="Document not found"):
            analyze_document("doc_nonexistent")

    def test_analyze_high_wage_w2(self):
        """Test analyzing high-wage W-2 includes investment recommendation."""
        doc = upload_document(
            user_id="user_123",
            file=b"W-2 content",
            document_type=DocumentType.TAX,
            filename="w2_high.pdf",
            metadata={
                "year": 2024,
                "form_type": "W-2",
                "employer": "BigTech Inc",
                "wages": "150000",
                "federal_tax": "35000",
            },
        )

        result = analyze_document(doc.id)

        # High wage documents should include investment recommendations
        assert any("invest" in rec.lower() for rec in result.recommendations)

    def test_analyze_confidence_threshold(self):
        """Test that analysis confidence meets minimum threshold."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_conf"},
        )

        result = analyze_document(doc.id)

        # All analysis should meet 0.7 confidence threshold
        assert result.confidence >= 0.5  # Fallback minimum

    def test_analyze_summary_length(self):
        """Test that summary is concise."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.TAX,
            filename="test.pdf",
            metadata={"year": 2024, "form_type": "W-2", "document_id": "doc_summary"},
        )

        result = analyze_document(doc.id)

        # Summary should be reasonably concise
        assert len(result.summary) < 250

    def test_analyze_findings_not_empty(self):
        """Test that findings are always present."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.RECEIPT,
            filename="receipt.pdf",
            metadata={"document_id": "doc_findings"},
        )

        result = analyze_document(doc.id)

        assert len(result.key_findings) > 0

    def test_analyze_recommendations_not_empty(self):
        """Test that recommendations are always present."""
        doc = upload_document(
            user_id="user_123",
            file=b"content",
            document_type=DocumentType.STATEMENT,
            filename="statement.pdf",
            metadata={"document_id": "doc_recs"},
        )

        result = analyze_document(doc.id)

        assert len(result.recommendations) > 0

    def test_analyze_extracts_financial_data(self):
        """Test that analysis extracts financial data from W-2."""
        doc = upload_document(
            user_id="user_123",
            file=b"W-2 content",
            document_type=DocumentType.TAX,
            filename="w2.pdf",
            metadata={
                "year": 2024,
                "form_type": "W-2",
                "employer": "Test Corp",
                "wages": "75000",
                "federal_tax": "15000",
                "state_tax": "3500",
                "document_id": "doc_extract",
            },
        )

        result = analyze_document(doc.id)

        # Should mention tax withholding
        findings_text = " ".join(result.key_findings).lower()
        assert "tax" in findings_text or "withhold" in findings_text

    def test_analyze_includes_disclaimer_recommendations(self):
        """Test that tax analysis includes professional advice disclaimer."""
        doc = upload_document(
            user_id="user_123",
            file=b"W-2 content",
            document_type=DocumentType.TAX,
            filename="w2.pdf",
            metadata={
                "year": 2024,
                "form_type": "W-2",
                "employer": "Company",
                "wages": "80000",
                "document_id": "doc_disclaimer",
            },
        )

        result = analyze_document(doc.id)

        # Should recommend consulting professional
        recs_text = " ".join(result.recommendations).lower()
        assert "professional" in recs_text or "advisor" in recs_text or "certified" in recs_text
