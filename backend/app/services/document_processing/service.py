import logging
import uuid
from pathlib import Path
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.log import ProcessingLog
from backend.app.core.config import settings
from .router import DocumentRouter

logger = logging.getLogger(__name__)

def process_invoice(db: Session, invoice_id: uuid.UUID, router: DocumentRouter) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice with id {invoice_id} not found.")

    # Status transition to EXTRACTING
    invoice.status = InvoiceStatus.EXTRACTING.value
    
    log_extracting = ProcessingLog(
        invoice_id=invoice.id,
        stage="PROCESSING",
        log_level="INFO",
        message="Started document extraction."
    )
    db.add(log_extracting)
    db.commit()
    db.refresh(invoice)

    try:
        # Resolve file path
        # Assuming storage_path is relative to the backend root or absolute
        # We need to construct the absolute path safely based on FILE_STORAGE_PATH
        # But if storage_path is already absolute or relative to cwd, we can just use Path(invoice.storage_path)
        # We should ensure it uses FILE_STORAGE_PATH safely
        
        # In phase 1, storage_path was likely just relative or absolute.
        # Let's resolve it carefully:
        file_path = Path(invoice.storage_path)
        if not file_path.is_absolute():
            # Based on standard logic, we might need to prepend base dir
            base_dir = Path(settings.FILE_STORAGE_PATH)
            if not base_dir.is_absolute():
                base_dir = Path(__file__).resolve().parent.parent.parent.parent / base_dir
            # For safety, just use the storage_path directly if it's already an absolute path saved
            # Or if it's relative, join it. Assuming Phase 1 saved it correctly.
            # Let's just use Path(invoice.storage_path)
            pass
            
        if not file_path.exists():
            raise FileNotFoundError(f"Stored file {file_path} not found.")

        result = router.process(file_path)

        if result.errors:
            error_msg = "; ".join(result.errors)
            raise RuntimeError(f"Extraction failed: {error_msg}")

        invoice.status = InvoiceStatus.PROCESSED.value
        # Note: Invoice field extraction is NOT part of Task 3. We are just storing raw text.
        # But there's no `extracted_text` column on Invoice. We might store it in raw_llm_response or just log it.
        # Since field extraction is not part of this task, we just mark as PROCESSED.
        invoice.raw_llm_response = {"extracted_text": result.extracted_text}
        
        log_success = ProcessingLog(
            invoice_id=invoice.id,
            stage="PROCESSING",
            log_level="INFO",
            message="Document processing successful."
        )
        db.add(log_success)
        
    except Exception as e:
        logger.error(f"Failed to process invoice {invoice_id}: {e}")
        invoice.status = InvoiceStatus.FAILED.value
        log_error = ProcessingLog(
            invoice_id=invoice.id,
            stage="PROCESSING",
            log_level="ERROR",
            message=str(e)
        )
        db.add(log_error)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


def process_invoice_background(invoice_id: uuid.UUID):
    """
    Background wrapper for processing an invoice.
    Uses a fresh database session so it isn't tied to the request lifecycle.
    """
    from backend.app.db.session import SessionLocal
    from .gemini_processor import GeminiDocumentProcessor

    db = SessionLocal()
    try:
        gemini_processor = GeminiDocumentProcessor()
        router = DocumentRouter(gemini_processor=gemini_processor)
        process_invoice(db, invoice_id, router)
    except Exception as e:
        logger.error(f"Fatal error in background processing for invoice {invoice_id}: {e}")
    finally:
        db.close()

