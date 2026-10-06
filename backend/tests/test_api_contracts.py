import io
import uuid
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient
from backend.app.main import app

def test_health_contract(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data

def test_api_v1_health_contract(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data

def test_upload_contract(client: TestClient, valid_pdf_bytes: bytes):
    files = {"file": ("contract_test.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert "file_name" in data
    assert "status" in data
    assert data["status"] == "PENDING"
    assert "message" in data

def test_list_invoices_contract(client: TestClient, valid_pdf_bytes: bytes):
    # Upload first
    files = {"file": ("list_test.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    client.post("/api/v1/invoices/upload", files=files)

    response = client.get("/api/v1/invoices")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        assert "id" in item
        assert "status" in item

def test_detail_and_status_contract(client: TestClient, valid_pdf_bytes: bytes):
    files = {"file": ("detail_test.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    res = client.post("/api/v1/invoices/upload", files=files)
    inv_id = res.json()["id"]

    # detail
    detail_res = client.get(f"/api/v1/invoices/{inv_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "id" in detail
    assert "status" in detail
    assert "file_name" in detail
    assert "storage_path" not in detail
    assert "logs" in detail
    assert "line_items" in detail

    # status
    status_res = client.get(f"/api/v1/invoices/{inv_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "id" in status_data
    assert "status" in status_data
    assert "updated_at" in status_data


def test_decimal_and_null_serialization(client: TestClient, db_session):
    from backend.app.models.invoice import Invoice
    import uuid
    # create a mock invoice directly in DB to avoid processing delay
    inv_id = uuid.uuid4()
    inv = Invoice(
        id=inv_id,
        file_name="financial.pdf",
        storage_path="some_path",
        file_hash="hash_financial",
        file_type="application/pdf",
        file_size_bytes=100,
        status="PROCESSED",
        subtotal=Decimal("100.50"),
        tax=Decimal("10.05"),
        total=Decimal("110.55"),
        vendor_name=None,
        due_date=None
    )
    db_session.add(inv)
    db_session.commit()

    res = client.get(f"/api/v1/invoices/{inv_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["subtotal"] == "100.50"
    assert data["tax"] == "10.05"
    assert data["total"] == "110.55"
    assert data["vendor_name"] is None
    assert data["due_date"] is None
