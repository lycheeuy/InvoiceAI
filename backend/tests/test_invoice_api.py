import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from backend.app.models.invoice import Invoice, InvoiceStatus, InvoiceLineItem
from backend.app.models.log import ProcessingLog

def test_empty_invoice_list(client: TestClient):
    response = client.get("/api/v1/invoices")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["limit"] == 20

def test_invoice_list_pagination_and_ordering(client: TestClient, db_session: Session):
    for i in range(25):
        inv = Invoice(
            id=uuid4(),
            file_name=f"test_{i}.pdf",
            storage_path=f"test_{i}.pdf",
            file_hash=f"hash_{i}",
            file_type="application/pdf",
            file_size_bytes=1000,
            status=InvoiceStatus.PROCESSED.value,
            vendor_name=f"Vendor {i}",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=i)
        )
        db_session.add(inv)
    db_session.commit()

    response = client.get("/api/v1/invoices?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["items"][0]["vendor_name"] == "Vendor 0"
    
    response3 = client.get("/api/v1/invoices?page=3&limit=10")
    assert response3.status_code == 200
    assert len(response3.json()["items"]) == 5

def test_invoice_list_filtering(client: TestClient, db_session: Session):
    inv1 = Invoice(id=uuid4(), file_name="1.pdf", storage_path="1.pdf", file_hash="1", file_type="pdf", file_size_bytes=10, status=InvoiceStatus.PENDING.value, vendor_name="Alpha Corp")
    inv2 = Invoice(id=uuid4(), file_name="2.pdf", storage_path="2.pdf", file_hash="2", file_type="pdf", file_size_bytes=10, status=InvoiceStatus.PROCESSED.value, vendor_name="Beta Inc")
    db_session.add_all([inv1, inv2])
    db_session.commit()

    res = client.get("/api/v1/invoices?status=PENDING")
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["status"] == "PENDING"
    
    res_invalid = client.get("/api/v1/invoices?status=INVALID_STATUS")
    assert res_invalid.status_code == 422
    
    res_vendor = client.get("/api/v1/invoices?vendor=alpha")
    assert res_vendor.status_code == 200
    assert res_vendor.json()["total"] == 1
    assert res_vendor.json()["items"][0]["vendor_name"] == "Alpha Corp"

def test_invoice_detail(client: TestClient, db_session: Session):
    inv_id = uuid4()
    inv = Invoice(
        id=inv_id, file_name="detail.pdf", storage_path="detail.pdf", file_hash="detail", file_type="pdf",
        file_size_bytes=100, status=InvoiceStatus.PROCESSED.value, subtotal=Decimal("10.50")
    )
    li = InvoiceLineItem(invoice_id=inv_id, line_number=1, description="Item 1", amount=Decimal("10.50"))
    log = ProcessingLog(invoice_id=inv_id, stage="PROCESSING", log_level="ERROR", message="Stored file /abs/path/detail.pdf not found.")
    
    db_session.add(inv)
    db_session.add(li)
    db_session.add(log)
    db_session.commit()
    
    res = client.get(f"/api/v1/invoices/{inv_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(inv_id)
    assert data["subtotal"] == "10.50"
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["amount"] == "10.50"
    assert "storage_path" not in data
    
    assert len(data["logs"]) == 1
    assert data["logs"][0]["message"] == "Stored file not found."

def test_invoice_detail_missing(client: TestClient):
    res = client.get(f"/api/v1/invoices/{uuid4()}")
    assert res.status_code == 404

def test_invoice_status(client: TestClient, db_session: Session):
    inv_id = uuid4()
    inv = Invoice(id=inv_id, file_name="stat.pdf", storage_path="stat.pdf", file_hash="stat", file_type="pdf", file_size_bytes=10, status=InvoiceStatus.EXTRACTING.value)
    db_session.add(inv)
    db_session.commit()
    
    res = client.get(f"/api/v1/invoices/{inv_id}/status")
    assert res.status_code == 200
    assert res.json()["status"] == "EXTRACTING"
    assert res.json()["id"] == str(inv_id)
