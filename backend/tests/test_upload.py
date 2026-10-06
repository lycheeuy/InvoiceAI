import io
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.log import ProcessingLog


def test_successful_pdf_upload(client: TestClient, db_session: Session, valid_pdf_bytes: bytes):
    """Tests successful upload of a valid PDF invoice."""
    files = {"file": ("invoice_sample.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["file_name"] == "invoice_sample.pdf"
    assert data["status"] == "PENDING"
    assert len(data["file_hash"]) == 64  # SHA-256 length

    # Verify database persistence
    invoice_id = uuid.UUID(data["id"])
    db_invoice = db_session.get(Invoice, invoice_id)
    assert db_invoice is not None
    assert db_invoice.file_name == "invoice_sample.pdf"
    assert db_invoice.file_type == "application/pdf"
    assert db_invoice.status == InvoiceStatus.PENDING.value
    assert db_invoice.file_size_bytes == len(valid_pdf_bytes)

    # Verify audit log entry
    logs = db_session.execute(
        select(ProcessingLog).where(ProcessingLog.invoice_id == invoice_id)
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].stage == "UPLOAD"
    assert logs[0].log_level == "INFO"


def test_successful_png_upload(client: TestClient, db_session: Session, valid_png_bytes: bytes):
    """Tests successful upload of a valid PNG image invoice."""
    files = {"file": ("receipt.png", io.BytesIO(valid_png_bytes), "image/png")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "PENDING"

    invoice_id = uuid.UUID(data["id"])
    db_invoice = db_session.get(Invoice, invoice_id)
    assert db_invoice is not None
    assert db_invoice.file_type == "image/png"


def test_successful_jpeg_upload(client: TestClient, db_session: Session, valid_jpeg_bytes: bytes):
    """Tests successful upload of a valid JPEG image invoice."""
    files = {"file": ("bill.jpg", io.BytesIO(valid_jpeg_bytes), "image/jpeg")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "PENDING"

    invoice_id = uuid.UUID(data["id"])
    db_invoice = db_session.get(Invoice, invoice_id)
    assert db_invoice is not None
    assert db_invoice.file_type == "image/jpeg"


def test_unsupported_file_extension(client: TestClient):
    """Tests rejection of unsupported file extensions (e.g. .txt, .docx)."""
    files = {"file": ("notes.txt", io.BytesIO(b"invoice details in text"), "text/plain")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 415
    assert "unsupported" in response.json()["error"]["message"].lower()


def test_invalid_magic_bytes(client: TestClient):
    """Tests rejection of files whose magic bytes do not match expected format."""
    fake_pdf = b"NOT_A_PDF_CONTENT_JUST_TEXT"
    files = {"file": ("fake_invoice.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 415
    assert "signature" in response.json()["error"]["message"].lower()


def test_signature_and_extension_mismatch(client: TestClient, valid_png_bytes: bytes):
    """Tests rejection when content is PNG but filename declared as .pdf."""
    files = {"file": ("sneaky_disguise.pdf", io.BytesIO(valid_png_bytes), "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 415
    assert "mismatch" in response.json()["error"]["message"].lower()


def test_file_larger_than_10mb(client: TestClient):
    """Tests rejection of files exceeding the 10 MB limit."""
    # Create 10.5 MB payload starting with valid PDF magic bytes
    large_content = b"%PDF-1.4\n" + b"A" * (10 * 1024 * 1024 + 500 * 1024)
    files = {"file": ("huge_invoice.pdf", io.BytesIO(large_content), "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 413
    assert "exceeds" in response.json()["error"]["message"].lower()


def test_empty_file_upload(client: TestClient):
    """Tests rejection of empty (0-byte) files."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 400
    assert "empty" in response.json()["error"]["message"].lower()


def test_duplicate_sha256_upload(client: TestClient, valid_pdf_bytes: bytes):
    """Tests that uploading the identical file twice is detected and rejected with HTTP 409."""
    # First upload - should succeed
    files_1 = {"file": ("invoice_original.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    res_1 = client.post("/api/v1/invoices/upload", files=files_1)
    assert res_1.status_code == 202
    first_id = res_1.json()["id"]

    # Second upload with identical bytes (even with a different filename)
    files_2 = {"file": ("renamed_copy.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    res_2 = client.post("/api/v1/invoices/upload", files=files_2)

    assert res_2.status_code == 409
    error_data = res_2.json()["error"]
    assert "duplicate" in error_data["message"].lower()
    assert error_data["details"]["existing_invoice_id"] == first_id


def test_get_invoice_detail_and_status(client: TestClient, valid_pdf_bytes: bytes):
    """Tests retrieval of invoice detail and status endpoints."""
    # Upload an invoice
    files = {"file": ("test_flow.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/invoices/upload", files=files)
    invoice_id = upload_res.json()["id"]

    # Test GET /invoices/{id}
    detail_res = client.get(f"/api/v1/invoices/{invoice_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == invoice_id
    assert detail_data["status"] == "PENDING"
    assert detail_data["file_name"] == "test_flow.pdf"
    assert len(detail_data["logs"]) >= 1

    # Test GET /invoices/{id}/status
    status_res = client.get(f"/api/v1/invoices/{invoice_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "PENDING"

    # Test GET /invoices (list)
    list_res = client.get("/api/v1/invoices")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == invoice_id for item in list_data["items"])


from unittest.mock import patch

def test_upload_queues_background_task(client: TestClient, db_session: Session, valid_pdf_bytes: bytes):
    """Tests that the upload endpoint enqueues process_invoice_background."""
    with patch("backend.app.api.v1.endpoints.invoices.BackgroundTasks.add_task") as mock_add_task:
        files = {"file": ("test_bg.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/invoices/upload", files=files)
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "PENDING"
        assert "Processing has been queued" in data["message"]
        
        invoice_id = uuid.UUID(data["id"])
        
        # Verify add_task was called with process_invoice_background and invoice_id
        from backend.app.services.document_processing.service import process_invoice_background
        mock_add_task.assert_called_once_with(process_invoice_background, invoice_id)
