import logging
import uuid
from pathlib import Path
from sqlalchemy.orm import Session

from backend.app.models.invoice import Invoice, InvoiceStatus, InvoiceLineItem
from backend.app.models.log import ProcessingLog
from backend.app.core.config import settings
from .router import DocumentRouter
from backend.app.services.invoice_extraction_service import InvoiceExtractionService
from backend.app.services.invoice_validation_service import InvoiceValidationService

logger = logging.getLogger(__name__)

def process_invoice(db: Session, invoice_id: uuid.UUID, router: DocumentRouter, extraction_service: InvoiceExtractionService = None) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice with id {invoice_id} not found.")

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
        storage_root = Path(settings.FILE_STORAGE_PATH).resolve()
        stored_path = Path(invoice.storage_path)

        if stored_path.is_absolute():
            # Preserve trusted internal and legacy absolute paths.
            file_path = stored_path.resolve()
        else:
            file_path = (storage_root.parent / stored_path).resolve()
            if not file_path.is_relative_to(storage_root):
                raise ValueError(
                    "Stored invoice path is outside the configured storage directory."
                )

        if not file_path.exists():
            raise FileNotFoundError(f"Stored file {file_path} not found.")

        # 1. Document Routing (Layer 1)
        result = router.process(file_path)

        if result.errors:
            error_msg = "; ".join(result.errors)
            raise RuntimeError(f"Extraction failed: {error_msg}")

        extracted_text = result.extracted_text or ""
        invoice.raw_llm_response = {"extracted_text": extracted_text}
        
        db.add(ProcessingLog(
            invoice_id=invoice.id,
            stage="PROCESSING",
            log_level="INFO",
            message="Document routing and text processing successful."
        ))

        # 2. Structured Extraction (Layer 2)
        ext_service = extraction_service or InvoiceExtractionService()
        invoice_schema = ext_service.extract_invoice(extracted_text)
        
        db.add(ProcessingLog(
            invoice_id=invoice.id,
            stage="PROCESSING",
            log_level="INFO",
            message="Structured extraction successful."
        ))

        # 3. Deterministic Financial Validation (Layer 3)
        val_result = InvoiceValidationService.validate_invoice(invoice_schema)

        # Persist structured data
        if invoice_schema.vendor:
            invoice.vendor_name = invoice_schema.vendor.name
        invoice.invoice_number = invoice_schema.invoice_number
        invoice.invoice_date = invoice_schema.invoice_date
        invoice.due_date = invoice_schema.due_date
        invoice.currency = invoice_schema.currency
        invoice.subtotal = invoice_schema.subtotal
        invoice.tax = invoice_schema.tax
        invoice.total = invoice_schema.total

        # Persist line items
        if invoice_schema.line_items:
            for i, li in enumerate(invoice_schema.line_items):
                db_li = InvoiceLineItem(
                    invoice_id=invoice.id,
                    line_number=i + 1,
                    description=li.description or "",
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    amount=li.amount
                )
                db.add(db_li)

        db.add(ProcessingLog(
            invoice_id=invoice.id,
            stage="PROCESSING",
            log_level="INFO",
            message="Financial validation completed."
        ))


        if val_result.is_valid:
            invoice.status = InvoiceStatus.PROCESSED.value
            invoice.review_reason = None
            db.add(ProcessingLog(
                invoice_id=invoice.id,
                stage="PROCESSING",
                log_level="INFO",
                message="Processing completed successfully."
            ))
        else:
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.review_reason = "; ".join(val_result.errors)
            db.add(ProcessingLog(
                invoice_id=invoice.id,
                stage="PROCESSING",
                log_level="WARNING",
                message="Processing needs review due to financial inconsistencies."
            ))
            
        db.commit()
        db.refresh(invoice)

    except Exception as e:

        logger.error(f"Failed to process invoice {invoice_id}: {e}")
        db.rollback()
        try:
            invoice = db.get(Invoice, invoice_id)
            if invoice:
                invoice.status = InvoiceStatus.FAILED.value
                db.add(ProcessingLog(
                    invoice_id=invoice.id,
                    stage="PROCESSING",
                    log_level="ERROR",
                    message=str(e)
                ))
                db.commit()
        except Exception as commit_err:
            db.rollback()
            logger.error(f"Failed to persist FAILED status for invoice {invoice_id}: {commit_err}")

    
    return invoice

def process_invoice_background(invoice_id: uuid.UUID):
    from backend.app.db.session import SessionLocal
    from .gemini_processor import GeminiDocumentProcessor
    from backend.app.services.invoice_extraction_service import InvoiceExtractionService

    db = SessionLocal()
    try:
        gemini_processor = GeminiDocumentProcessor()
        router = DocumentRouter(gemini_processor=gemini_processor)
        extraction_service = InvoiceExtractionService()
        process_invoice(db, invoice_id, router, extraction_service)
    except Exception as e:
        logger.error(f"Fatal error in background processing for invoice {invoice_id}: {e}")
    finally:
        db.close()
