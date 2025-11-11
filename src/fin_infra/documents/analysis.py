"""
AI-powered document analysis and insights.

Uses rule-based analysis (simulated AI) for financial documents.
Production: Use ai-infra CoreLLM for real AI-powered insights.

Quick Start:
    >>> from fin_infra.documents.analysis import analyze_document
    >>>
    >>> # Analyze document
    >>> result = analyze_document(document_id="doc_abc123")
    >>> print(result.summary)
    >>> print(result.key_findings)
    >>> print(result.recommendations)

Production Integration:
    - Use ai-infra CoreLLM for all LLM calls (never custom clients)
    - Cache analysis results (24h TTL via svc-infra cache)
    - Track LLM costs per user (ai-infra cost tracking)
    - Add disclaimers for financial advice
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .models import DocumentAnalysis

# In-memory analysis cache (production: use svc-infra cache)
_analysis_cache: Dict[str, "DocumentAnalysis"] = {}


def analyze_document(
    document_id: str,
    force_refresh: bool = False,
) -> "DocumentAnalysis":
    """
    Analyze a document using AI to extract insights and recommendations.

    Args:
        document_id: Document identifier
        force_refresh: Force re-analysis even if cached result exists

    Returns:
        Document analysis with summary, findings, and recommendations

    Examples:
        >>> # Analyze W-2 tax document
        >>> analysis = analyze_document("doc_abc123")
        >>> print(analysis.summary)
        >>> # "W-2 showing $85,000 annual wages from Acme Corp"
        >>>
        >>> print(analysis.key_findings)
        >>> # ["High federal tax withholding (22% effective rate)", ...]
        >>>
        >>> print(analysis.recommendations)
        >>> # ["Consider adjusting W-4 allowances", ...]

    Notes:
        - Current: Rule-based analysis (simulated AI)
        - Production: Use ai-infra CoreLLM (never custom LLM clients)
        - Production: Check cache before analysis (svc-infra cache, 24h TTL)
        - Production: Track LLM costs (ai-infra cost tracking)
        - Production: Add disclaimer: "Not a substitute for certified financial advisor"
        - Production: Filter sensitive data (SSN, passwords) before LLM
    """
    from .models import DocumentAnalysis
    from .ocr import extract_text
    from .storage import get_document

    # Check cache first
    if not force_refresh and document_id in _analysis_cache:
        return _analysis_cache[document_id]

    # Get document metadata
    doc = get_document(document_id)
    if not doc:
        raise ValueError(f"Document not found: {document_id}")

    # Extract text via OCR (uses OCR cache if available)
    ocr_result = extract_text(document_id, provider="tesseract", force_refresh=False)

    # Analyze based on document type
    if doc.type.value == "tax":
        analysis = _analyze_tax_document(ocr_result.text, doc.metadata, document_id)
    elif doc.type.value == "statement":
        analysis = _analyze_bank_statement(ocr_result.text, doc.metadata, document_id)
    elif doc.type.value == "receipt":
        analysis = _analyze_receipt(ocr_result.text, doc.metadata, document_id)
    else:
        # Generic analysis for other document types
        analysis = _analyze_generic_document(
            ocr_result.text, doc.type.value, doc.metadata, document_id
        )

    # Validate analysis
    if not _validate_analysis(analysis):
        # Fall back to minimal analysis
        analysis = DocumentAnalysis(
            document_id=document_id,
            summary=f"{doc.type.value.title()} document: {doc.filename}",
            key_findings=["Document extracted successfully"],
            recommendations=["Review document for accuracy"],
            analysis_date=datetime.utcnow(),
            confidence=0.5,
        )

    # Cache result
    _analysis_cache[document_id] = analysis

    return analysis


def _build_analysis_prompt(ocr_text: str, document_type: str, metadata: dict) -> str:
    """
    Build LLM prompt for document analysis.

    Args:
        ocr_text: Extracted text from OCR
        document_type: Type of document
        metadata: Document metadata (year, form_type, etc.)

    Returns:
        Structured prompt for LLM analysis

    Examples:
        >>> prompt = _build_analysis_prompt(
        ...     ocr_text="W-2 Wage and Tax Statement...",
        ...     document_type="tax",
        ...     metadata={"year": 2024, "form_type": "W-2"}
        ... )

    Notes:
        - Include document type and year in prompt
        - Request structured output (summary, findings, recommendations)
        - Add financial context (tax brackets, deduction limits, etc.)
        - Add disclaimer requirement
    """
    year = metadata.get("year", "unknown")
    form_type = metadata.get("form_type", document_type)

    prompt = f"""Analyze this {document_type} document from {year}.

Document Type: {form_type}
Document Text:
{ocr_text}

Provide:
1. A concise summary (one sentence)
2. 3-5 key findings about the document
3. 3-5 actionable recommendations

Important: This analysis is not a substitute for professional financial advice.
"""
    return prompt


def _validate_analysis(analysis: "DocumentAnalysis") -> bool:
    """
    Validate LLM analysis output.

    Args:
        analysis: Document analysis from LLM

    Returns:
        True if analysis meets quality standards, False otherwise

    Examples:
        >>> valid = _validate_analysis(analysis)
        >>> if not valid:
        ...     # Retry with different prompt or fall back to rule-based

    Notes:
        - Check confidence threshold (>0.7)
        - Ensure findings list is not empty
        - Ensure recommendations are actionable
        - Verify summary is concise (<200 chars)
    """
    if analysis.confidence < 0.7:
        return False

    if not analysis.key_findings or len(analysis.key_findings) == 0:
        return False

    if not analysis.recommendations or len(analysis.recommendations) == 0:
        return False

    if len(analysis.summary) > 250:
        return False

    return True


def _analyze_tax_document(ocr_text: str, metadata: dict, document_id: str) -> "DocumentAnalysis":
    """
    Specialized analysis for tax documents.

    Args:
        ocr_text: Extracted text from tax form
        metadata: Document metadata (year, form_type, employer)
        document_id: Document identifier

    Returns:
        Tax-specific analysis with withholding insights and recommendations

    Examples:
        >>> analysis = _analyze_tax_document(w2_text, {"year": 2024, "form_type": "W-2"}, "doc_123")

    Notes:
        - Current: Rule-based analysis (simulated AI)
        - Production: Use ai-infra CoreLLM with financial tax prompt
        - Production: Include tax bracket information
        - Production: Suggest W-4 adjustments if applicable
        - Production: Identify potential deductions or credits
        - Production: Add disclaimer about professional tax advice
    """
    from .models import DocumentAnalysis

    form_type = metadata.get("form_type", "tax form")
    year = metadata.get("year", "unknown")

    # Extract financial data from OCR text or metadata
    wages_match = re.search(r"Wages:\s*\$?([\d,]+\.?\d*)", ocr_text)
    if wages_match:
        wages = float(wages_match.group(1).replace(",", ""))
    else:
        # Fallback to metadata if OCR didn't extract wages
        wages_str = metadata.get("wages", "0")
        wages = float(str(wages_str).replace(",", ""))

    # Extract employer
    employer_match = re.search(r"Employer:\s*(.+)", ocr_text)
    if employer_match:
        employer = employer_match.group(1).strip()
    else:
        employer = metadata.get("employer", "Unknown Employer")

    # Generate summary
    summary = f"{form_type} showing ${wages:,.2f} annual wages from {employer} ({year})"

    # Generate key findings
    key_findings = []
    if wages > 0:
        # Calculate effective tax rate (simplified)
        federal_match = re.search(r"Federal Tax Withheld:\s*\$?([\d,]+\.?\d*)", ocr_text)
        if federal_match:
            federal_tax = float(federal_match.group(1).replace(",", ""))
            effective_rate = (federal_tax / wages) * 100
            key_findings.append(
                f"Federal tax withholding: ${federal_tax:,.2f} ({effective_rate:.1f}% effective rate)"
            )
        elif "federal_tax" in metadata:
            federal_tax = float(str(metadata["federal_tax"]).replace(",", ""))
            effective_rate = (federal_tax / wages) * 100
            key_findings.append(
                f"Federal tax withholding: ${federal_tax:,.2f} ({effective_rate:.1f}% effective rate)"
            )

        state_match = re.search(r"State Tax Withheld:\s*\$?([\d,]+\.?\d*)", ocr_text)
        if state_match:
            state_tax = float(state_match.group(1).replace(",", ""))
            key_findings.append(f"State tax withholding: ${state_tax:,.2f}")
        elif "state_tax" in metadata:
            state_tax = float(str(metadata["state_tax"]).replace(",", ""))
            key_findings.append(f"State tax withholding: ${state_tax:,.2f}")

    if not key_findings:
        key_findings = [
            "Tax document extracted successfully",
            f"Year: {year}",
            f"Form type: {form_type}",
        ]

    # Generate recommendations
    recommendations = [
        "Review W-4 withholding allowances for accuracy",
        "Consider maximizing retirement contributions (401k, IRA)",
        "Consult a certified tax professional for personalized advice",
    ]

    if wages > 100000:
        recommendations.insert(1, "Explore tax-advantaged investment strategies")

    return DocumentAnalysis(
        document_id=document_id,
        summary=summary,
        key_findings=key_findings,
        recommendations=recommendations,
        analysis_date=datetime.utcnow(),
        confidence=0.85,
    )


def _analyze_bank_statement(ocr_text: str, metadata: dict, document_id: str) -> "DocumentAnalysis":
    """
    Specialized analysis for bank statements.

    Args:
        ocr_text: Extracted text from bank statement
        metadata: Document metadata (year, month, account_type)
        document_id: Document identifier

    Returns:
        Statement-specific analysis with spending insights

    Examples:
        >>> analysis = _analyze_bank_statement(stmt_text, {"year": 2024, "month": 12}, "doc_123")

    Notes:
        - Current: Rule-based analysis (simulated AI)
        - Production: Use ai-infra CoreLLM with spending analysis prompt
        - Production: Identify unusual transactions or patterns
        - Production: Compare to typical spending (if available)
        - Production: Suggest budget optimizations
    """
    from .models import DocumentAnalysis

    year = metadata.get("year", "unknown")
    month = metadata.get("month", "unknown")

    summary = f"Bank statement for {month}/{year}"

    key_findings = [
        "Statement extracted successfully",
        "Review transactions for accuracy",
        "Check for unauthorized charges",
    ]

    recommendations = [
        "Set up automatic savings transfers",
        "Review recurring subscriptions",
        "Monitor account for fraud protection",
    ]

    return DocumentAnalysis(
        document_id=document_id,
        summary=summary,
        key_findings=key_findings,
        recommendations=recommendations,
        analysis_date=datetime.utcnow(),
        confidence=0.80,
    )


def _analyze_receipt(ocr_text: str, metadata: dict, document_id: str) -> "DocumentAnalysis":
    """
    Specialized analysis for receipts.

    Args:
        ocr_text: Extracted text from receipt
        metadata: Document metadata
        document_id: Document identifier

    Returns:
        Receipt-specific analysis
    """
    from .models import DocumentAnalysis

    # Extract amount from receipt
    amount_match = re.search(r"Total:?\s*\$?([\d,]+\.?\d*)", ocr_text)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0

    summary = f"Receipt for ${amount:.2f}"

    key_findings = [
        "Receipt extracted successfully",
        f"Total amount: ${amount:.2f}",
    ]

    recommendations = [
        "Categorize expense for tax purposes",
        "Keep receipt for warranty/returns",
    ]

    return DocumentAnalysis(
        document_id=document_id,
        summary=summary,
        key_findings=key_findings,
        recommendations=recommendations,
        analysis_date=datetime.utcnow(),
        confidence=0.75,
    )


def _analyze_generic_document(
    ocr_text: str, document_type: str, metadata: dict, document_id: str
) -> "DocumentAnalysis":
    """
    Generic analysis for other document types.

    Args:
        ocr_text: Extracted text
        document_type: Type of document
        metadata: Document metadata
        document_id: Document identifier

    Returns:
        Generic document analysis
    """
    from .models import DocumentAnalysis

    summary = f"{document_type.title()} document extracted"

    key_findings = [
        "Document extracted successfully",
        f"Document type: {document_type}",
    ]

    recommendations = [
        "Review document for accuracy",
        "Store securely for future reference",
    ]

    return DocumentAnalysis(
        document_id=document_id,
        summary=summary,
        key_findings=key_findings,
        recommendations=recommendations,
        analysis_date=datetime.utcnow(),
        confidence=0.70,
    )


def clear_cache() -> None:
    """Clear analysis cache (for testing only)."""
    _analysis_cache.clear()
