import pytest
import io
import uuid
from unittest.mock import patch, MagicMock
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.log import ProcessingLog
from backend.app.services.document_processing.schemas import DocumentProcessingResult, ProcessingMethod, DocumentType

def test_e2e_upload_to_processed(client: TestClient, db_session: Session, temp_storage: Path):
    """
    End-to-End Style Test:
    Upload -> Invoice created -> PENDING
    Background processing -> DocumentRouter -> Digital PDF processor -> PROCESSED
    
    Using a mocked PDF processor to simulate the extraction without real file parsing,
    and avoiding real Gemini calls.
    """
    # 1. Simulate Upload
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    
    with patch("backend.app.api.v1.endpoints.invoices.BackgroundTasks.add_task") as mock_add_task:
        files = {"file": ("e2e_test.pdf", io.BytesIO(fake_pdf), "application/pdf")}
        response = client.post("/api/v1/invoices/upload", files=files)
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "PENDING"
        
        invoice_id = uuid.UUID(data["id"])
        
        # Verify it queued the task
        mock_add_task.assert_called_once()
    
    db_invoice = db_session.get(Invoice, invoice_id)
    assert db_invoice.status == InvoiceStatus.PENDING.value
    
    # Fix the storage path to be absolute so process_invoice can find it
    # because DocumentStorageService saves a relative path and the tests don't have FILE_STORAGE_PATH setup exactly like prod
    filename = Path(db_invoice.storage_path).name
    absolute_path = temp_storage / filename
    db_invoice.storage_path = str(absolute_path)
    db_session.commit()
    
    # 2. Simulate Background Processing execution
    from backend.app.services.document_processing.service import process_invoice_background
    
    with patch.object(db_session, "close"), \
         patch("backend.app.db.session.SessionLocal", return_value=db_session), \
         patch("backend.app.services.document_processing.gemini_processor.GeminiDocumentProcessor") as mock_gemini_class, \
         patch("backend.app.services.document_processing.router.PdfTextProcessor") as mock_pdf_processor_class, \
         patch("backend.app.services.invoice_extraction_service.InvoiceExtractionService") as mock_ext_service_class:
    
        mock_pdf_instance = MagicMock()
        # Simulate >= 100 meaningful chars so it routes to Digital PDF processor
        mock_pdf_instance.process.return_value = DocumentProcessingResult(
            processing_method=ProcessingMethod.PDFPLUMBER,
            document_type=DocumentType.DIGITAL_PDF,
            extracted_text="A" * 100
        )
        mock_pdf_processor_class.return_value = mock_pdf_instance
        
        mock_gemini_instance = MagicMock()
        mock_gemini_class.return_value = mock_gemini_instance
            
        mock_ext_instance = MagicMock()
        from backend.app.schemas.invoice import InvoiceSchema
        mock_ext_instance.extract_invoice.return_value = InvoiceSchema(invoice_number="E2E-123")
        mock_ext_service_class.return_value = mock_ext_instance
        
        # Execute background task
        process_invoice_background(invoice_id)
        
        # 3. Verify DocumentRouter used PdfTextProcessor
        # The file path in process() call should be the storage path
        mock_pdf_instance.process.assert_called_once_with(Path(db_invoice.storage_path))
        # Gemini should not be called because text length >= 100
        mock_gemini_instance.process.assert_not_called()
    
    # 4. Verify Final State
    db_session.refresh(db_invoice)
    assert db_invoice.status == InvoiceStatus.PROCESSED.value
    assert db_invoice.raw_llm_response == {"extracted_text": "A" * 100}
    
    logs = db_session.query(ProcessingLog).filter_by(invoice_id=invoice_id).order_by(ProcessingLog.created_at).all()
    # logs: UPLOAD -> Started extraction -> Document processing successful
    assert any(log.stage == "UPLOAD" for log in logs)
    assert any("Started document extraction" in log.message for log in logs)
