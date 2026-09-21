import pytest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice, InvoiceStatus, InvoiceLineItem
from backend.app.models.log import ProcessingLog
from backend.app.schemas.invoice import InvoiceSchema, LineItem, Vendor
from backend.app.services.document_processing.schemas import DocumentProcessingResult, ProcessingMethod, DocumentType
from backend.app.services.document_processing.service import process_invoice
from backend.app.services.document_processing.router import DocumentRouter
from backend.app.services.invoice_extraction_service import InvoiceExtractionService, InvoiceExtractionError

@pytest.fixture
def dummy_invoice(db_session: Session, tmp_path):
    dummy_file = tmp_path / "integration.pdf"
    dummy_file.write_bytes(b"dummy")
    
    invoice = Invoice(
        file_name="integration.pdf",
        storage_path=str(dummy_file),
        file_hash=str(uuid.uuid4()),
        file_type="application/pdf",
        file_size_bytes=5
    )
    db_session.add(invoice)
    db_session.commit()
    return invoice

@pytest.fixture
def mock_router():
    router = MagicMock(spec=DocumentRouter)
    router.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        extracted_text="Raw extracted text"
    )
    return router

def test_pipeline_valid_structured_invoice_to_processed(db_session: Session, dummy_invoice, mock_router):
    extraction_service = MagicMock(spec=InvoiceExtractionService)
    extraction_service.extract_invoice.return_value = InvoiceSchema(
        invoice_number="INV-001",
        vendor=Vendor(name="Vendor A"),
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.00"),
        line_items=[
            LineItem(description="Item 1", quantity=Decimal("1"), unit_price=Decimal("100.00"), amount=Decimal("100.00"))
        ]
    )
    
    with patch.object(db_session, "rollback"):
            process_invoice(db_session, dummy_invoice.id, mock_router, extraction_service)
    
    db_session.refresh(dummy_invoice)
    assert dummy_invoice.status == InvoiceStatus.PROCESSED.value
    assert dummy_invoice.invoice_number == "INV-001"
    assert dummy_invoice.vendor_name == "Vendor A"
    assert dummy_invoice.subtotal == Decimal("100.00")
    
    db_line_items = db_session.query(InvoiceLineItem).filter_by(invoice_id=dummy_invoice.id).all()
    assert len(db_line_items) == 1
    assert db_line_items[0].description == "Item 1"
    assert db_line_items[0].amount == Decimal("100.00")

def test_pipeline_financial_inconsistency_to_needs_review(db_session: Session, dummy_invoice, mock_router):
    extraction_service = MagicMock(spec=InvoiceExtractionService)
    extraction_service.extract_invoice.return_value = InvoiceSchema(
        invoice_number="INV-002",
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("150.00"), # Error!
        line_items=[]
    )
    
    with patch.object(db_session, "rollback"):
            process_invoice(db_session, dummy_invoice.id, mock_router, extraction_service)
    
    db_session.refresh(dummy_invoice)
    assert dummy_invoice.status == InvoiceStatus.NEEDS_REVIEW.value
    assert "Total (150.00) does not match subtotal (100.00) + tax (10.00)" in dummy_invoice.review_reason
    assert dummy_invoice.total == Decimal("150.00") # No auto correction

def test_pipeline_extraction_failure_to_failed(db_session: Session, dummy_invoice, mock_router):
    extraction_service = MagicMock(spec=InvoiceExtractionService)
    extraction_service.extract_invoice.side_effect = InvoiceExtractionError("Malformed JSON")
    
    with patch.object(db_session, "rollback"):
            process_invoice(db_session, dummy_invoice.id, mock_router, extraction_service)
    
    db_session.refresh(dummy_invoice)
    assert dummy_invoice.status == InvoiceStatus.FAILED.value
    
    logs = db_session.query(ProcessingLog).filter_by(invoice_id=dummy_invoice.id).all()
    assert any("Malformed JSON" in log.message for log in logs)

def test_pipeline_missing_optional_data_not_false_failure(db_session: Session, dummy_invoice, mock_router):
    extraction_service = MagicMock(spec=InvoiceExtractionService)
    extraction_service.extract_invoice.return_value = InvoiceSchema(
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        tax=None,
        line_items=[]
    )
    
    with patch.object(db_session, "rollback"):
            process_invoice(db_session, dummy_invoice.id, mock_router, extraction_service)
    
    db_session.refresh(dummy_invoice)
    assert dummy_invoice.status == InvoiceStatus.PROCESSED.value # Missing tax skips verification, doesn't fail
    assert dummy_invoice.total == Decimal("100.00")

def test_pipeline_unexpected_exception_safely_failed(db_session: Session, dummy_invoice, mock_router):
    mock_router.process.side_effect = Exception("Database crash simulated")
    
    with patch.object(db_session, "rollback"):
            process_invoice(db_session, dummy_invoice.id, mock_router)
    
    db_session.refresh(dummy_invoice)
    assert dummy_invoice.status == InvoiceStatus.FAILED.value
    
    logs = db_session.query(ProcessingLog).filter_by(invoice_id=dummy_invoice.id).all()
    assert any("Database crash simulated" in log.message for log in logs)


def test_pipeline_transaction_rollback_on_persistence_error(db_session: Session, dummy_invoice, mock_router):
    extraction_service = MagicMock(spec=InvoiceExtractionService)
    extraction_service.extract_invoice.return_value = InvoiceSchema(
        invoice_number="INV-001",
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.00"),
        line_items=[
            LineItem(description="Item 1", quantity=Decimal("1"), unit_price=Decimal("100.00"), amount=Decimal("100.00"))
        ]
    )
    
    # We will simulate a database error
    original_add = db_session.add
    
    def side_effect(instance):
        if isinstance(instance, InvoiceLineItem):
            from sqlalchemy.exc import IntegrityError
            raise IntegrityError("Simulated DB Insert Error", params={}, orig=Exception())
        original_add(instance)
        
    with patch.object(db_session, "add", side_effect=side_effect):
        with patch.object(db_session, "rollback"):
            process_invoice(db_session, dummy_invoice.id, mock_router, extraction_service)
        
    db_session.refresh(dummy_invoice)
    assert dummy_invoice.status == InvoiceStatus.FAILED.value
