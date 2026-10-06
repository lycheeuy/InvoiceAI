import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

def test_missing_invoice_returns_404(client: TestClient):
    fake_id = uuid4()
    response = client.get(f"/api/v1/invoices/{fake_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVOICE_NOT_FOUND"
    assert data["error"]["message"] == "Invoice not found."

def test_missing_invoice_status_returns_404(client: TestClient):
    fake_id = uuid4()
    response = client.get(f"/api/v1/invoices/{fake_id}/status")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVOICE_NOT_FOUND"

def test_invalid_upload_returns_standardized_error(client: TestClient):
    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("test.txt", b"dummy content", "text/plain")}
    )
    # the exact code might vary (could be 415), but it should be standard format
    assert response.status_code >= 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE_TYPE"

def test_invalid_request_validation_returns_standardized_error(client: TestClient):
    # Missing required 'file'
    response = client.post("/api/v1/invoices/upload")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"

def test_openapi_contains_error_response(client: TestClient):
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    # Check if ErrorResponse is in schemas
    assert "ErrorResponse" in data["components"]["schemas"]
    assert "ErrorDetail" in data["components"]["schemas"]
