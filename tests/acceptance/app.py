from __future__ import annotations


from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from fin_infra.documents import DocumentType, easy_documents
from svc_infra.storage.backends.memory import MemoryBackend


def make_app() -> FastAPI:
    app = FastAPI()

    # Storage and document manager (shared for all acceptance tests)
    storage = MemoryBackend()
    docs = easy_documents(storage=storage, default_ocr_provider="tesseract")

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"pong": "ok"}

    # Financial documents acceptance endpoints (no auth required for testing)
    @app.post("/documents/upload")
    async def upload_document(
        user_id: str = Form(...),
        document_type: str = Form(...),
        file: UploadFile = File(...),
        tax_year: str = Form(None),
        form_type: str = Form(None),
    ):
        """Upload financial document for acceptance testing."""
        content = await file.read()

        # Convert to DocumentType enum
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            doc_type = DocumentType.OTHER

        # Build metadata
        metadata = {}
        if tax_year:
            metadata["tax_year"] = int(tax_year) if tax_year.isdigit() else tax_year
        if form_type:
            metadata["form_type"] = form_type

        # Upload via manager
        doc = await docs.upload_financial(
            user_id=user_id,
            file=content,
            document_type=doc_type,
            filename=file.filename or "document.txt",
            metadata=metadata,
        )

        return doc.model_dump()

    @app.get("/documents/list")
    async def list_documents(
        user_id: str,
        type: str = None,
        year: int = None,
    ):
        """List documents for acceptance testing."""
        doc_type = DocumentType(type) if type else None
        documents = docs.list_financial(
            user_id=user_id,
            document_type=doc_type,
            tax_year=year,
        )
        return [doc.model_dump() for doc in documents]

    @app.get("/documents/{document_id}")
    async def get_document(document_id: str):
        """Get document metadata for acceptance testing."""
        try:
            doc = docs.get(document_id)
            return doc.model_dump()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.delete("/documents/{document_id}")
    async def delete_document(document_id: str):
        """Delete document for acceptance testing."""
        try:
            await docs.delete(document_id)
            return JSONResponse(content={"message": "Document deleted"}, status_code=200)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/documents/{document_id}/ocr")
    async def extract_text_ocr(
        document_id: str,
        provider: str = None,
        force_refresh: bool = False,
    ):
        """OCR text extraction for acceptance testing."""
        try:
            result = await docs.extract_text(
                document_id=document_id,
                provider=provider,
                force_refresh=force_refresh,
            )
            return result.model_dump()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/documents/{document_id}/analyze")
    async def analyze_document_ai(
        document_id: str,
        force_refresh: bool = False,
    ):
        """AI document analysis for acceptance testing."""
        try:
            analysis = await docs.analyze(
                document_id=document_id,
                force_refresh=force_refresh,
            )
            return analysis.model_dump()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    return app
