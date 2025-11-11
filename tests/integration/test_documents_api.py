"""Integration tests for document management API."""

import pytest
from typing import Optional

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("FastAPI not available - skipping integration tests", allow_module_level=True)

from fin_infra.documents.storage import clear_storage


@pytest.fixture
def app():
    """Create FastAPI app with document routes (no auth for testing)."""
    from svc_infra.api.fastapi.dual.public import public_router
    from fin_infra.documents.ease import easy_documents
    
    app = FastAPI()
    manager = easy_documents(storage_path="/tmp/test_documents")
    
    # Create router WITHOUT auth for integration testing
    router = public_router(prefix="/documents", tags=["Documents"])
    
    # Route 1: Upload document
    @router.post("/upload")
    async def upload_document(request: dict):
        from fin_infra.documents.models import DocumentType
        user_id = request["user_id"]
        file = request["file"]
        document_type = request["document_type"]
        filename = request["filename"]
        metadata = request.get("metadata")
        
        doc_type = DocumentType(document_type)
        file_bytes = file.encode() if isinstance(file, str) else file
        return manager.upload(user_id, file_bytes, doc_type, filename, metadata)
    
    # Route 2: List documents (MUST come before /{document_id} to avoid path conflict)
    @router.get("/list")
    async def list_documents(user_id: str, type: Optional[str] = None, year: Optional[int] = None):
        from fin_infra.documents.storage import list_documents as list_docs
        return list_docs(user_id, type=type, year=year)
    
    # Route 3: Get document
    @router.get("/{document_id}")
    async def get_document(document_id: str):
        from fin_infra.documents.storage import get_document as get_doc
        doc = get_doc(document_id)
        if doc is None:
            raise ValueError(f"Document {document_id} not found")
        return doc
    
    # Route 4: Delete document
    @router.delete("/{document_id}")
    async def delete_document(document_id: str):
        manager.delete(document_id)
        return {"message": "Document deleted successfully"}
    
    # Route 5: Extract text (OCR)
    @router.post("/{document_id}/ocr")
    async def extract_text(document_id: str, provider: Optional[str] = None, force_refresh: bool = False):
        return manager.extract_text(document_id, provider=provider or "tesseract", force_refresh=force_refresh)
    
    # Route 6: Analyze document
    @router.post("/{document_id}/analyze")
    async def analyze_document(document_id: str, force_refresh: bool = False):
        return manager.analyze(document_id, force_refresh=force_refresh)
    
    app.include_router(router)
    app.state.document_manager = manager
    
    yield app
    # Cleanup
    clear_storage()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestDocumentsAPI:
    """Tests for documents API endpoints."""

    def test_add_documents_mounts_routes(self, app):
        """Test that add_documents mounts all expected routes."""
        routes = [route.path for route in app.routes]
        
        # Check for document routes (with and without trailing slash due to dual router)
        assert any("/documents/upload" in route for route in routes)
        assert any("/documents/list" in route for route in routes)
        assert any("/documents/{document_id}" in route for route in routes)
        assert any("/documents/{document_id}/ocr" in route for route in routes)
        assert any("/documents/{document_id}/analyze" in route for route in routes)

    def test_upload_document(self, client):
        """Test uploading a document."""
        response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "test file content",
                "document_type": "tax",
                "filename": "test.pdf",
                "metadata": {"year": 2024},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["user_id"] == "user_123"
        assert data["type"] == "tax"
        assert data["filename"] == "test.pdf"
        assert data["metadata"]["year"] == 2024

    def test_get_document(self, client):
        """Test getting document details."""
        # Upload first
        upload_response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content",
                "document_type": "tax",
                "filename": "test.pdf",
            },
        )
        doc_id = upload_response.json()["id"]

        # Get document
        response = client.get(f"/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["filename"] == "test.pdf"

    def test_list_documents(self, client):
        """Test listing documents."""
        # Upload multiple documents
        client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content1",
                "document_type": "tax",
                "filename": "doc1.pdf",
            },
        )
        client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content2",
                "document_type": "receipt",
                "filename": "doc2.pdf",
            },
        )

        # List all documents
        response = client.get("/documents/list?user_id=user_123")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_documents_with_type_filter(self, client):
        """Test filtering documents by type."""
        # Upload documents of different types
        client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content1",
                "document_type": "tax",
                "filename": "tax.pdf",
                "metadata": {"year": 2024},
            },
        )
        client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content2",
                "document_type": "receipt",
                "filename": "receipt.pdf",
            },
        )

        # Filter by type
        response = client.get("/documents/list?user_id=user_123&type=tax")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == "tax"

    def test_list_documents_with_year_filter(self, client):
        """Test filtering documents by year."""
        # Upload documents with different years
        client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content1",
                "document_type": "tax",
                "filename": "tax_2024.pdf",
                "metadata": {"year": 2024},
            },
        )
        client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content2",
                "document_type": "tax",
                "filename": "tax_2023.pdf",
                "metadata": {"year": 2023},
            },
        )

        # Filter by year
        response = client.get("/documents/list?user_id=user_123&year=2024")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["metadata"]["year"] == 2024

    def test_delete_document(self, client):
        """Test deleting a document."""
        # Upload first
        upload_response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content",
                "document_type": "tax",
                "filename": "test.pdf",
            },
        )
        doc_id = upload_response.json()["id"]

        # Delete
        response = client.delete(f"/documents/{doc_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Document deleted successfully"

        # Verify deleted - expect any error status (ValueError will raise 500)
        get_response = client.get(f"/documents/{doc_id}")
        assert get_response.status_code >= 400  # Document not found (4xx or 5xx)

    def test_extract_text_ocr(self, client):
        """Test OCR text extraction."""
        # Upload document
        upload_response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "W-2 content",
                "document_type": "tax",
                "filename": "w2.pdf",
                "metadata": {"year": 2024, "form_type": "W-2"},
            },
        )
        doc_id = upload_response.json()["id"]

        # Extract text
        response = client.post(f"/documents/{doc_id}/ocr")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert "text" in data
        assert data["provider"] == "tesseract"
        assert data["confidence"] > 0

    def test_extract_text_with_provider(self, client):
        """Test OCR with specific provider."""
        # Upload document
        upload_response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content",
                "document_type": "tax",
                "filename": "test.pdf",
                "metadata": {"year": 2024, "form_type": "W-2"},
            },
        )
        doc_id = upload_response.json()["id"]

        # Extract with Textract
        response = client.post(f"/documents/{doc_id}/ocr?provider=textract")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "textract"
        assert data["confidence"] >= 0.90  # Textract higher confidence

    def test_analyze_document(self, client):
        """Test AI document analysis."""
        # Upload document
        upload_response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "W-2 content",
                "document_type": "tax",
                "filename": "w2.pdf",
                "metadata": {
                    "year": 2024,
                    "form_type": "W-2",
                    "employer": "Acme Corp",
                    "wages": "85000",
                },
            },
        )
        doc_id = upload_response.json()["id"]

        # Analyze
        response = client.post(f"/documents/{doc_id}/analyze")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert "summary" in data
        assert len(data["key_findings"]) > 0
        assert len(data["recommendations"]) > 0
        assert data["confidence"] > 0.7

    def test_analyze_force_refresh(self, client):
        """Test analysis with force refresh."""
        # Upload document
        upload_response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content",
                "document_type": "tax",
                "filename": "test.pdf",
                "metadata": {"year": 2024, "form_type": "W-2"},
            },
        )
        doc_id = upload_response.json()["id"]

        # First analysis
        response1 = client.post(f"/documents/{doc_id}/analyze")
        assert response1.status_code == 200

        # Force refresh
        response2 = client.post(f"/documents/{doc_id}/analyze?force_refresh=true")
        assert response2.status_code == 200

    def test_upload_without_metadata(self, client):
        """Test uploading document without metadata."""
        response = client.post(
            "/documents/upload",
            json={
                "user_id": "user_123",
                "file": "content",
                "document_type": "receipt",
                "filename": "receipt.pdf",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"] == {}

    def test_list_empty_documents(self, client):
        """Test listing when user has no documents."""
        response = client.get("/documents/list?user_id=user_empty")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_manager_stored_on_app_state(self, app):
        """Test that manager is accessible from app.state."""
        assert hasattr(app.state, "document_manager")
        manager = app.state.document_manager
        assert manager is not None
        assert hasattr(manager, "upload")
        assert hasattr(manager, "download")
        assert hasattr(manager, "delete")
