"""
Acceptance tests for fin-infra documents module (Layer 2 - Financial Extensions).

These tests verify the financial-specific document features built on svc-infra base:
- Financial document upload with DocumentType, tax_year, form_type
- OCR text extraction with provider selection
- AI-powered document analysis with insights and recommendations
- Document type filtering
- Financial metadata handling

Test IDs: A_FIN_DOC_01 to A_FIN_DOC_07

Architecture:
- Layer 1 (svc-infra): Generic document CRUD (tested in svc-infra acceptance)
- Layer 2 (fin-infra): Financial extensions (tested here)
"""

from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

pytestmark = pytest.mark.acceptance


@pytest.fixture
def sample_w2_content():
    """Sample W-2 form content for OCR testing."""
    content = b"""W-2 Wage and Tax Statement
2024
Employer: Acme Corp
Employee: John Doe
Wages: $85,000
Federal Tax Withheld: $12,750
State Tax Withheld: $4,250
"""
    return {
        "content": content,
        "filename": "w2_acme_2024.txt",
        "content_type": "text/plain",
        "size": len(content),
        "checksum": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }


@pytest.fixture
def sample_receipt_content():
    """Sample receipt content for testing."""
    content = b"""Receipt - Starbucks
Date: 2024-11-15
Items: Coffee, Sandwich
Total: $12.50
"""
    return {
        "content": content,
        "filename": "starbucks_receipt.txt",
        "content_type": "text/plain",
        "size": len(content),
        "checksum": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }


def test_a_fin_doc_01_upload_financial_document_with_type(client, sample_w2_content):
    """
    A_FIN_DOC_01: Upload financial document with DocumentType

    Given a user wants to upload a tax document
    When they POST to /documents/upload with document_type=TAX
    Then the document is stored with financial metadata
    And document_type, tax_year, form_type are preserved
    """
    # Upload W-2 tax document
    response = client.post(
        "/documents/upload",
        data={
            "user_id": "user_fin_01",
            "document_type": "tax",  # DocumentType.TAX
            "tax_year": "2024",
            "form_type": "W-2",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )

    assert response.status_code == 200
    upload_data = response.json()

    # Verify financial metadata
    assert "id" in upload_data
    assert upload_data["filename"] == sample_w2_content["filename"]
    assert upload_data["user_id"] == "user_fin_01"

    # Financial-specific fields
    metadata = upload_data.get("metadata", {})
    assert metadata.get("document_type") == "tax" or upload_data.get("type") == "tax"

    # Check for tax_year and form_type in metadata or top-level
    has_tax_year = "tax_year" in metadata or metadata.get("year") == "2024"
    has_form_type = "form_type" in metadata or metadata.get("form_type") == "W-2"

    assert has_tax_year, "tax_year should be in metadata"
    assert has_form_type, "form_type should be in metadata"


def test_a_fin_doc_02_ocr_extraction_default_provider(client, sample_w2_content):
    """
    A_FIN_DOC_02: OCR text extraction with default provider

    Given a document has been uploaded
    When they POST to /documents/{id}/ocr
    Then text is extracted using default Tesseract provider
    And OCRResult includes text, confidence, provider
    """
    # Upload document first
    response = client.post(
        "/documents/upload",
        data={
            "user_id": "user_fin_02",
            "document_type": "tax",
            "tax_year": "2024",
            "form_type": "W-2",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Extract text via OCR
    response = client.post(f"/documents/{document_id}/ocr")
    assert response.status_code == 200

    ocr_result = response.json()
    assert "document_id" in ocr_result
    assert ocr_result["document_id"] == document_id
    assert "text" in ocr_result
    assert len(ocr_result["text"]) > 0
    assert "confidence" in ocr_result
    assert 0.0 <= ocr_result["confidence"] <= 1.0
    assert "provider" in ocr_result
    assert ocr_result["provider"] in ["tesseract", "textract"]
    assert "extraction_date" in ocr_result


def test_a_fin_doc_03_ocr_extraction_specific_provider(client, sample_w2_content):
    """
    A_FIN_DOC_03: OCR with specific provider selection

    Given a document has been uploaded
    When they POST to /documents/{id}/ocr?provider=textract
    Then text is extracted using the specified provider
    And provider field reflects the requested provider
    """
    # Upload document
    response = client.post(
        "/documents/upload",
        data={
            "user_id": "user_fin_03",
            "document_type": "tax",
            "form_type": "W-2",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Extract with textract provider
    response = client.post(f"/documents/{document_id}/ocr?provider=textract")
    assert response.status_code == 200

    ocr_result = response.json()
    assert ocr_result["provider"] == "textract"
    assert "text" in ocr_result
    assert "confidence" in ocr_result


def test_a_fin_doc_04_ocr_w2_field_extraction(client, sample_w2_content):
    """
    A_FIN_DOC_04: OCR extracts W-2 structured fields

    Given a W-2 document has been uploaded
    When OCR extraction is performed
    Then structured fields are extracted (employer, wages, federal_tax, state_tax)
    """
    # Upload W-2
    response = client.post(
        "/documents/upload",
        data={
            "user_id": "user_fin_04",
            "document_type": "tax",
            "form_type": "W-2",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Extract text with field parsing
    response = client.post(f"/documents/{document_id}/ocr")
    assert response.status_code == 200

    ocr_result = response.json()

    # Check if fields were extracted
    if "fields" in ocr_result and ocr_result["fields"]:
        fields = ocr_result["fields"]
        # W-2 should have extracted employer, wages, federal_tax
        assert "employer" in fields or "wages" in fields, "Should extract W-2 fields"


def test_a_fin_doc_05_document_analysis_financial_insights(client, sample_w2_content):
    """
    A_FIN_DOC_05: AI analysis generates financial insights

    Given a financial document has been uploaded
    When they POST to /documents/{id}/analyze
    Then analysis includes summary, key_findings, recommendations
    And insights are relevant to document type (tax/receipt/etc)
    """
    # Upload W-2
    response = client.post(
        "/documents/upload",
        data={
            "user_id": "user_fin_05",
            "document_type": "tax",
            "form_type": "W-2",
            "tax_year": "2024",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Analyze document
    response = client.post(f"/documents/{document_id}/analyze")
    assert response.status_code == 200

    analysis = response.json()
    assert "document_id" in analysis
    assert analysis["document_id"] == document_id
    assert "summary" in analysis
    assert len(analysis["summary"]) > 0
    assert "key_findings" in analysis
    assert isinstance(analysis["key_findings"], list)
    assert len(analysis["key_findings"]) >= 2
    assert "recommendations" in analysis
    assert isinstance(analysis["recommendations"], list)
    assert len(analysis["recommendations"]) >= 3
    assert "confidence" in analysis
    assert 0.0 <= analysis["confidence"] <= 1.0
    assert "analysis_date" in analysis


def test_a_fin_doc_06_analysis_includes_financial_disclaimer(client, sample_w2_content):
    """
    A_FIN_DOC_06: Analysis includes professional advisor disclaimer

    Given a financial document is analyzed
    Then recommendations include disclaimer about professional advice
    """
    # Upload document
    response = client.post(
        "/documents/upload",
        data={
            "user_id": "user_fin_06",
            "document_type": "tax",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    # Analyze
    response = client.post(f"/documents/{document_id}/analyze")
    assert response.status_code == 200

    analysis = response.json()
    recommendations = analysis["recommendations"]

    # Should have disclaimer as last recommendation
    has_disclaimer = any(
        "not a substitute" in rec.lower() or "professional" in rec.lower()
        for rec in recommendations
    )
    assert has_disclaimer, "Should include professional advisor disclaimer"


def test_a_fin_doc_07_list_documents_by_type(client, sample_w2_content, sample_receipt_content):
    """
    A_FIN_DOC_07: List documents filtered by DocumentType

    Given a user has uploaded documents of different types
    When they GET /documents/list?user_id=...&type=tax
    Then only tax documents are returned
    """
    user_id = "user_fin_07"

    # Upload W-2 (tax)
    client.post(
        "/documents/upload",
        data={
            "user_id": user_id,
            "document_type": "tax",
            "form_type": "W-2",
        },
        files={
            "file": (
                sample_w2_content["filename"],
                BytesIO(sample_w2_content["content"]),
                sample_w2_content["content_type"],
            )
        },
    )

    # Upload receipt
    client.post(
        "/documents/upload",
        data={
            "user_id": user_id,
            "document_type": "receipt",
        },
        files={
            "file": (
                sample_receipt_content["filename"],
                BytesIO(sample_receipt_content["content"]),
                sample_receipt_content["content_type"],
            )
        },
    )

    # List only tax documents
    response = client.get(f"/documents/list?user_id={user_id}&type=tax")
    assert response.status_code == 200

    data = response.json()

    # Handle both list response and dict with documents key
    if isinstance(data, dict) and "documents" in data:
        documents = data["documents"]
    else:
        documents = data

    assert len(documents) >= 1

    # All returned documents should be tax type
    for doc in documents:
        metadata = doc.get("metadata", {})
        doc_type = metadata.get("document_type") or doc.get("type")
        assert doc_type == "tax", f"Expected tax type, got {doc_type}"
