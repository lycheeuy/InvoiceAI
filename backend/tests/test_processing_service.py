import pytest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from decimal import Decimal

from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.log import ProcessingLog
from backend.app.schemas.invoice import InvoiceSchema
from backend.app.services.document_processing.schemas import DocumentProcessingResult, ProcessingMethod, DocumentType
from backend.app.services.document_processing.service import process_invoice
from backend.app.services.document_processing.router import DocumentRouter
from backend.app.services.invoice_extraction_service import InvoiceExtractionService

def test_invoice_not_found(db_session: Session):
    router = MagicMock(spec=DocumentRouter)
    with pytest.raises(ValueError, match="not found"):
        process_invoice(db_session, uuid.uuid4(), router)

def test_successful_processing(db_session: Session, tmp_path):
    dummy_file = tmp_path / "test.pdf"
    dummy_file.write_bytes(b"dummy")
    
    invoice = Invoice(
        file_name="test.pdf",
        storage_path=str(dummy_file),
        file_hash="fakehash",
        file_type="application/pdf",
        file_size_bytes=5
    )
    db_session.add(invoice)
    db_session.commit()
    
    router = MagicMock(spec=DocumentRouter)
    router.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        extracted_text="Hello World"
    )
    
    extraction_service = MagicMock(spec=InvoiceExtractionService)
    extraction_service.extract_invoice.return_value = InvoiceSchema(
        invoice_number="INV-001",
        subtotal=Decimal("100"),
        tax=Decimal("10"),
        total=Decimal("110")
    )
    
    process_invoice(db_session, invoice.id, router, extraction_service=extraction_service)
    
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.PROCESSED.value
    assert invoice.raw_llm_response == {"extracted_text": "Hello World"}
    
    logs = db_session.query(ProcessingLog).filter_by(invoice_id=invoice.id).all()
    assert any(log.message == "Started document extraction." for log in logs)

def test_processing_failure(db_session: Session, tmp_path):
    dummy_file = tmp_path / "test2.pdf"
    dummy_file.write_bytes(b"dummy")
    
    invoice = Invoice(
        file_name="test2.pdf",
        storage_path=str(dummy_file),
        file_hash="fakehash2",
        file_type="application/pdf",
        file_size_bytes=5
    )
    db_session.add(invoice)
    db_session.commit()
    
    router = MagicMock(spec=DocumentRouter)
    router.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        errors=["Fake error"]
    )
    
    with patch.object(db_session, "rollback"):
        process_invoice(db_session, invoice.id, router)
    
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.FAILED.value

def test_invalid_stored_file(db_session: Session):
    invoice = Invoice(
        file_name="missing.pdf",
        storage_path="/invalid/path/missing.pdf",
        file_hash="fakehash3",
        file_type="application/pdf",
        file_size_bytes=5
    )
    db_session.add(invoice)
    db_session.commit()
    
    router = MagicMock(spec=DocumentRouter)
    
    with patch.object(db_session, "rollback"):
        process_invoice(db_session, invoice.id, router)
    
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.FAILED.value


def test_process_invoice_background(db_session: Session, tmp_path):
    from unittest.mock import patch
    from backend.app.services.document_processing.service import process_invoice_background
    
    dummy_file = tmp_path / "bg_test.pdf"
    dummy_file.write_bytes(b"dummy")
    
    invoice = Invoice(
        file_name="bg_test.pdf",
        storage_path=str(dummy_file),
        file_hash="fakehash_bg",
        file_type="application/pdf",
        file_size_bytes=5
    )
    db_session.add(invoice)
    db_session.commit()
    
    with patch("backend.app.db.session.SessionLocal") as mock_session_local,          patch("backend.app.services.document_processing.service.process_invoice") as mock_process:
        
        mock_session_local.return_value = db_session
        process_invoice_background(invoice.id)
        mock_process.assert_called_once()
