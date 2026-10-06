import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_upload_wrong_content_type(client: TestClient, valid_pdf_bytes: bytes):
    """Test that a file with correct extension and content but wrong Content-Type is rejected."""
    files = {"file": ("invoice.pdf", io.BytesIO(valid_pdf_bytes), "image/jpeg")}
    response = client.post("/api/v1/invoices/upload", files=files)
    assert response.status_code == 415
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE_TYPE"
    assert "Content-Type mismatch" in data["error"]["message"]

def test_upload_path_traversal_filename(client: TestClient, db_session: Session, valid_pdf_bytes: bytes):
    """Test that path traversal characters in filename are neutralized."""
    malicious_names = [
        "../../etc/passwd.pdf",
        "..\\..\\Windows\\System32\\config\\SAM.pdf",
        "/absolute/path/invoice.pdf",
    ]
    for name in malicious_names:
        files = {"file": (name, io.BytesIO(valid_pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/invoices/upload", files=files)
        # Should either succeed with safe name or fail if it extracts weird extension
        if response.status_code == 202:
            data = response.json()
            assert "/" not in data["file_name"]
            assert "\\" not in data["file_name"]
            assert data["file_name"] in ["passwd.pdf", "SAM.pdf", "invoice.pdf"]
            
            # Clean up for next iteration to prevent duplicate error
            db_session.execute(
                __import__("sqlalchemy").text(f"DELETE FROM invoices WHERE id = '{data['id']}'")
            )
            db_session.commit()

def test_malformed_uuid_rejected(client: TestClient):
    """Test that malformed UUID path parameters return 422 Validation Error."""
    response = client.get("/api/v1/invoices/not-a-uuid")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    
def test_pagination_validation(client: TestClient):
    """Test that pagination parameters are strictly validated."""
    # Negative page
    response = client.get("/api/v1/invoices?page=-1")
    assert response.status_code == 422
    
    # Page zero
    response = client.get("/api/v1/invoices?page=0")
    assert response.status_code == 422
    
    # Limit too high
    response = client.get("/api/v1/invoices?limit=101")
    assert response.status_code == 422
    
    # Valid pagination
    response = client.get("/api/v1/invoices?page=1&limit=50")
    assert response.status_code == 200

def test_query_params_max_length(client: TestClient):
    """Test that vendor and status queries have max lengths."""
    long_status = "A" * 51
    response = client.get(f"/api/v1/invoices?status={long_status}")
    assert response.status_code == 422
    
    long_vendor = "A" * 101
    response = client.get(f"/api/v1/invoices?vendor={long_vendor}")
    assert response.status_code == 422
