"""
Demonstrations of financial document management with OCR and AI analysis.

Shows how to use the layered documents architecture:
- Layer 1 (svc-infra): Base CRUD (upload, list, get, delete)
- Layer 2 (fin-infra): OCR extraction + AI analysis

Run these demos to see the full document lifecycle in action.
"""

from typing import Optional

from fin_infra.documents import DocumentType, easy_documents


async def demo_financial_documents(user_id: str = "demo_user") -> None:
    """
    Demonstrate complete financial document management workflow.

    Shows:
    1. Uploading documents (Layer 1: svc-infra base)
    2. Listing documents by type and year (Layer 1: svc-infra base)
    3. OCR text extraction (Layer 2: fin-infra extension)
    4. AI-powered document analysis (Layer 2: fin-infra extension)
    5. Retrieving document content (Layer 1: svc-infra base)
    6. Deleting documents (Layer 1: svc-infra base)

    Args:
        user_id: User identifier for demo

    Example:
        >>> import asyncio
        >>> asyncio.run(demo_financial_documents("user_123"))
    """
    print("\n" + "=" * 70)
    print("DEMO: Financial Document Management (Layered Architecture)")
    print("=" * 70)

    # Initialize document manager
    docs = easy_documents(
        storage_path="/tmp/demo_documents",
        default_ocr_provider="tesseract",
    )

    # ========================================================================
    # Layer 1 (svc-infra): Base Document Upload
    # ========================================================================
    print("\n📤 Step 1: Upload tax document (Layer 1: svc-infra base)")
    print("-" * 70)

    # Sample W-2 content (simplified for demo)
    sample_w2_content = b"""
    Form W-2 Wage and Tax Statement
    Tax Year: 2024
    
    Employee: John Doe
    SSN: XXX-XX-1234
    
    Employer: Acme Corporation
    EIN: 12-3456789
    
    Box 1: Wages, tips, other compensation     $85,000.00
    Box 2: Federal income tax withheld         $18,700.00
    Box 3: Social security wages               $85,000.00
    Box 4: Social security tax withheld         $5,270.00
    Box 5: Medicare wages and tips             $85,000.00
    Box 6: Medicare tax withheld                $1,232.50
    Box 17: State income tax withheld           $6,375.00
    """

    doc = await docs.upload(
        user_id=user_id,
        file=sample_w2_content,
        document_type=DocumentType.TAX,
        filename="w2_2024.pdf",
        metadata={"year": 2024, "form_type": "W-2", "employer": "Acme Corporation"},
    )

    print(f"✅ Uploaded: {doc.id}")
    print(f"   Type: {doc.document_type.value}")
    print(f"   Size: {len(sample_w2_content)} bytes")
    print(f"   Metadata: {doc.metadata}")

    # ========================================================================
    # Layer 1 (svc-infra): List Documents by Type
    # ========================================================================
    print("\n📋 Step 2: List tax documents (Layer 1: svc-infra base)")
    print("-" * 70)

    tax_docs = await docs.list_documents(user_id=user_id, document_type=DocumentType.TAX)

    print(f"✅ Found {len(tax_docs)} tax documents:")
    for td in tax_docs:
        print(f"   - {td.filename} ({td.document_type.value}, year: {td.metadata.get('year')})")

    # ========================================================================
    # Layer 2 (fin-infra): OCR Text Extraction
    # ========================================================================
    print("\n🔍 Step 3: Extract text via OCR (Layer 2: fin-infra extension)")
    print("-" * 70)

    ocr_result = await docs.extract_text(document_id=doc.id, provider="tesseract")

    print(f"✅ OCR completed:")
    print(f"   Provider: {ocr_result.provider}")
    print(f"   Confidence: {ocr_result.confidence:.1%}")
    print(f"   Text length: {len(ocr_result.text)} characters")
    print(f"\n   First 200 chars of extracted text:")
    print(f"   {ocr_result.text[:200]}...")

    if ocr_result.structured_fields:
        print(f"\n   📊 Structured Fields Detected:")
        for key, value in list(ocr_result.structured_fields.items())[:5]:
            print(f"      {key}: {value}")

    # ========================================================================
    # Layer 2 (fin-infra): AI-Powered Document Analysis
    # ========================================================================
    print("\n🤖 Step 4: Analyze document with AI (Layer 2: fin-infra extension)")
    print("-" * 70)

    analysis = await docs.analyze(document_id=doc.id)

    print(f"✅ AI Analysis completed:")
    print(f"\n   📝 Summary:")
    print(f"   {analysis.summary}")

    if analysis.key_findings:
        print(f"\n   🔑 Key Findings:")
        for finding in analysis.key_findings[:3]:
            print(f"      • {finding}")

    if analysis.recommendations:
        print(f"\n   💡 Recommendations:")
        for rec in analysis.recommendations[:3]:
            print(f"      • {rec}")

    print(f"\n   📊 Confidence: {analysis.confidence:.1%}")

    # ========================================================================
    # Layer 1 (svc-infra): Retrieve Document Content
    # ========================================================================
    print("\n📥 Step 5: Retrieve document content (Layer 1: svc-infra base)")
    print("-" * 70)

    content = await docs.get_document_content(document_id=doc.id)

    print(f"✅ Retrieved content:")
    print(f"   Size: {len(content)} bytes")
    print(f"   SHA-256: {doc.checksum[:16]}...")

    # ========================================================================
    # Layer 1 (svc-infra): Delete Document
    # ========================================================================
    print("\n🗑️  Step 6: Delete document (Layer 1: svc-infra base)")
    print("-" * 70)

    await docs.delete_document(document_id=doc.id)

    print(f"✅ Deleted: {doc.id}")

    # Verify deletion
    remaining = await docs.list_documents(user_id=user_id, document_type=DocumentType.TAX)
    print(f"   Remaining tax documents: {len(remaining)}")

    print("\n" + "=" * 70)
    print("✅ Demo completed successfully!")
    print("=" * 70)


async def demo_tax_document_workflow(
    user_id: str = "demo_user",
    ocr_provider: Optional[str] = None,
) -> None:
    """
    Demonstrate end-to-end tax document processing workflow.

    This shows a realistic scenario where a user:
    1. Uploads multiple tax documents (W-2, 1099, receipts)
    2. Extracts text from each using OCR
    3. Gets AI-powered tax insights across all documents
    4. Receives actionable recommendations

    Args:
        user_id: User identifier
        ocr_provider: OCR provider (tesseract/textract, None=default)

    Example:
        >>> import asyncio
        >>> # High accuracy with AWS Textract
        >>> asyncio.run(demo_tax_document_workflow("user_123", ocr_provider="textract"))
    """
    print("\n" + "=" * 70)
    print("DEMO: Tax Document Workflow (Multi-Document Processing)")
    print("=" * 70)

    docs = easy_documents(default_ocr_provider=ocr_provider or "tesseract")

    # Sample documents
    documents = [
        {
            "content": b"W-2 2024: $85,000 wages, $18,700 federal tax withheld",
            "filename": "w2_2024.pdf",
            "type": DocumentType.TAX,
            "metadata": {"year": 2024, "form_type": "W-2"},
        },
        {
            "content": b"1099-INT 2024: $1,250 interest income from savings",
            "filename": "1099_int_2024.pdf",
            "type": DocumentType.TAX,
            "metadata": {"year": 2024, "form_type": "1099-INT"},
        },
        {
            "content": b"Medical expense receipt: $3,500 dental work",
            "filename": "medical_receipt_2024.pdf",
            "type": DocumentType.RECEIPT,
            "metadata": {"year": 2024, "category": "medical", "deductible": True},
        },
    ]

    print("\n📤 Step 1: Upload tax documents")
    print("-" * 70)

    uploaded_docs = []
    for doc_data in documents:
        doc = await docs.upload(
            user_id=user_id,
            file=doc_data["content"],
            document_type=doc_data["type"],
            filename=doc_data["filename"],
            metadata=doc_data["metadata"],
        )
        uploaded_docs.append(doc)
        print(f"✅ Uploaded: {doc.filename} ({doc.document_type.value})")

    print(f"\n   Total: {len(uploaded_docs)} documents uploaded")

    # ========================================================================
    # Batch OCR Processing
    # ========================================================================
    print("\n🔍 Step 2: Batch OCR extraction")
    print("-" * 70)

    ocr_results = []
    for doc in uploaded_docs:
        ocr = await docs.extract_text(document_id=doc.id)
        ocr_results.append(ocr)
        print(f"✅ OCR: {doc.filename} - {ocr.confidence:.1%} confidence")

    print(f"\n   Average confidence: {sum(r.confidence for r in ocr_results) / len(ocr_results):.1%}")

    # ========================================================================
    # Multi-Document Analysis
    # ========================================================================
    print("\n🤖 Step 3: AI-powered tax insights")
    print("-" * 70)

    # Analyze each document
    analyses = []
    for doc in uploaded_docs:
        analysis = await docs.analyze(document_id=doc.id)
        analyses.append(analysis)

    # Aggregate insights
    print(f"✅ Analyzed {len(analyses)} documents\n")

    print("   📊 Combined Tax Summary:")
    print(f"      • W-2 Income: $85,000")
    print(f"      • Interest Income: $1,250")
    print(f"      • Medical Deductions: $3,500")

    print("\n   💡 Key Recommendations:")
    print("      • Consider itemizing deductions (medical > standard)")
    print("      • Review retirement contribution limits")
    print("      • File by April 15 to avoid penalties")

    print("\n   🎯 Next Actions:")
    print("      • Schedule CPA consultation")
    print("      • Gather remaining 1099 forms")
    print("      • Review estimated tax payments")

    print("\n" + "=" * 70)
    print("✅ Tax workflow demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    """Run demos from command line."""
    import asyncio
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "tax":
        asyncio.run(demo_tax_document_workflow())
    else:
        asyncio.run(demo_financial_documents())
