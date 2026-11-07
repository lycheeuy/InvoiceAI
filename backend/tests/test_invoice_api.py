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


def test_patch_invoice_preserves_line_items_and_normalizes_idr(client: TestClient, db_session: Session):
    inv_id = uuid4()
    inv = Invoice(
        id=inv_id,
        file_name="idr.pdf",
        storage_path="idr.pdf",
        file_hash="idr_hash",
        file_type="application/pdf",
        file_size_bytes=500,
        status=InvoiceStatus.FAILED.value,
    )
    li = InvoiceLineItem(
        invoice_id=inv_id,
        line_number=1,
        description="Jasa Pengembangan",
        quantity=Decimal("1"),
        unit_price=Decimal("3725000.00"),
        amount=Decimal("3725000.00"),
    )
    db_session.add(inv)
    db_session.add(li)
    db_session.commit()

    # PATCH without line_items field and with Indonesian number strings + null dates
    res = client.patch(
        f"/api/v1/invoices/{inv_id}",
        json={
            "vendor_name": "PT Contoh Nusantara",
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "subtotal": "3.725.000",
            "tax": "372.500",
            "total": "4.097.500",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(data["subtotal"]) == Decimal("3725000.00")
    assert Decimal(data["tax"]) == Decimal("372500.00")
    assert Decimal(data["total"]) == Decimal("4097500.00")
    assert data["status"] == "PROCESSED"
    assert len(data["line_items"]) == 1
    assert data["line_items"][0]["id"] == str(li.id)
    assert data["line_items"][0]["description"] == "Jasa Pengembangan"


def test_patch_invoice_updates_and_clears_line_items_explicitly(client: TestClient, db_session: Session):
    inv_id = uuid4()
    inv = Invoice(
        id=inv_id,
        file_name="idr_items.pdf",
        storage_path="idr_items.pdf",
        file_hash="idr_items_hash",
        file_type="application/pdf",
        file_size_bytes=500,
        status=InvoiceStatus.NEEDS_REVIEW.value,
    )
    li = InvoiceLineItem(
        invoice_id=inv_id,
        line_number=1,
        description="Item Awal",
        quantity=Decimal("1"),
        unit_price=Decimal("100000.00"),
        amount=Decimal("100000.00"),
    )
    db_session.add(inv)
    db_session.add(li)
    db_session.commit()

    # 1. PATCH with explicit line_items normalizes unit_price and amount
    res_update = client.patch(
        f"/api/v1/invoices/{inv_id}",
        json={
            "subtotal": "3.725.000",
            "tax": "372.500",
            "total": "4.097.500",
            "line_items": [
                {
                    "description": "Jasa Implementasi",
                    "quantity": "1",
                    "unit_price": "3.725.000",
                    "amount": "Rp 3.725.000,-",
                }
            ],
        },
    )
    assert res_update.status_code == 200
    data_update = res_update.json()
    assert len(data_update["line_items"]) == 1
    assert data_update["line_items"][0]["description"] == "Jasa Implementasi"
    assert Decimal(data_update["line_items"][0]["unit_price"]) == Decimal("3725000.00")
    assert Decimal(data_update["line_items"][0]["amount"]) == Decimal("3725000.00")
    assert data_update["status"] == "PROCESSED"

    # 2. PATCH with explicit line_items=[] deletes existing line items
    res_clear = client.patch(
        f"/api/v1/invoices/{inv_id}",
        json={
            "line_items": [],
        },
    )
    assert res_clear.status_code == 200
    data_clear = res_clear.json()
    assert data_clear["line_items"] == []


def test_patch_invoice_multiple_line_items_lifecycle(client: TestClient, db_session: Session):
    inv_id = uuid4()
    inv = Invoice(
        id=inv_id,
        file_name="multi_items.pdf",
        storage_path="multi_items.pdf",
        file_hash="multi_items_hash",
        file_type="application/pdf",
        file_size_bytes=500,
        status=InvoiceStatus.FAILED.value,
    )
    db_session.add(inv)
    db_session.commit()

    # 1. Add multiple line items to an invoice with initially empty line_items
    res_add = client.patch(
        f"/api/v1/invoices/{inv_id}",
        json={
            "vendor_name": "PT Multi Item",
            "invoice_number": "INV-MULTI-01",
            "subtotal": "3.500.000",
            "tax": "350.000",
            "total": "3.850.000",
            "line_items": [
                {
                    "description": "Lisensi Cloud",
                    "quantity": "2",
                    "unit_price": "1.000.000",
                    "amount": "2.000.000",
                },
                {
                    "description": "Jasa Integrasi",
                    "quantity": "1,5",
                    "unit_price": "1.000.000",
                    "amount": "1.500.000",
                },
            ],
        },
    )
    assert res_add.status_code == 200
    data_add = res_add.json()
    assert data_add["status"] == "PROCESSED"
    assert len(data_add["line_items"]) == 2
    assert data_add["line_items"][0]["description"] == "Lisensi Cloud"
    assert Decimal(data_add["line_items"][0]["amount"]) == Decimal("2000000.00")
    assert data_add["line_items"][1]["description"] == "Jasa Integrasi"
    assert Decimal(data_add["line_items"][1]["quantity"]) == Decimal("1.5")
    assert Decimal(data_add["line_items"][1]["amount"]) == Decimal("1500000.00")

    # 2. Remove one item and edit the remaining item
    existing_id = data_add["line_items"][0]["id"]
    res_edit_remove = client.patch(
        f"/api/v1/invoices/{inv_id}",
        json={
            "subtotal": "3.000.000",
            "tax": "300.000",
            "total": "3.300.000",
            "line_items": [
                {
                    "id": existing_id,
                    "description": "Lisensi Cloud Enterprise",
                    "quantity": "3",
                    "unit_price": "1.000.000",
                    "amount": "3.000.000",
                }
            ],
        },
    )
    assert res_edit_remove.status_code == 200
    data_edit = res_edit_remove.json()
    assert data_edit["status"] == "PROCESSED"
    assert len(data_edit["line_items"]) == 1
    assert data_edit["line_items"][0]["description"] == "Lisensi Cloud Enterprise"
    assert Decimal(data_edit["line_items"][0]["quantity"]) == Decimal("3")
    assert Decimal(data_edit["line_items"][0]["amount"]) == Decimal("3000000.00")
