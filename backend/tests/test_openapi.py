import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def test_openapi_schema_contains_required_models(client: TestClient):
    """Verify OpenAPI schema includes required response models and constraints."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    
    schemas = openapi.get("components", {}).get("schemas", {})
    
    # Models
    assert "HealthResponse" in schemas
    assert "InvoiceUploadResponse" in schemas
    assert "InvoiceListResponse" in schemas
    assert "InvoiceDetailResponse" in schemas
    assert "InvoiceStatusResponse" in schemas
    assert "ErrorResponse" in schemas
    
    # Enum
    assert "InvoiceStatus" in schemas
    
    # Check pagination constraints in the list endpoint
    paths = openapi.get("paths", {})
    list_path = paths.get("/api/v1/invoices", {}).get("get", {})
    parameters = list_path.get("parameters", [])
    
    page_param = next((p for p in parameters if p["name"] == "page"), None)
    assert page_param is not None
    assert page_param["schema"].get("minimum", 1) >= 1
    
    limit_param = next((p for p in parameters if p["name"] == "limit"), None)
    assert limit_param is not None
    assert limit_param["schema"].get("maximum", 100) <= 100

def test_openapi_path_parameters_uuid(client: TestClient):
    """Verify OpenAPI schema specifies UUID format for ID parameters."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    
    paths = openapi.get("paths", {})
    detail_path = paths.get("/api/v1/invoices/{id}", {}).get("get", {})
    parameters = detail_path.get("parameters", [])
    
    id_param = next((p for p in parameters if p["name"] == "invoice_id"), None)
    if not id_param:
        id_param = next((p for p in parameters if p["name"] == "id"), None)
        
    assert id_param is not None
    assert id_param["schema"].get("format") == "uuid"
