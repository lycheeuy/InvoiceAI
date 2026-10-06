import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.log import ProcessingLog
from backend.app.services.document import DocumentStorageService
from backend.app.core.exceptions import DuplicateResourceError, DatabaseError


class InvoiceService:
    """Orchestrates invoice upload, validation, duplicate prevention, and database persistence."""

    def __init__(self, storage_service: Optional[DocumentStorageService] = None):
        self.storage_service = storage_service or DocumentStorageService(
            storage_dir=settings.FILE_STORAGE_PATH,
            max_file_size=settings.MAX_UPLOAD_SIZE,
            allowed_extensions=settings.allowed_extensions_set,
        )

    async def ingest_invoice_file(self, file: UploadFile, db: Session) -> Invoice:
        """
        Validates, hashes, stores on disk, and persists the invoice record.
        Detects duplicate documents by SHA-256 and rejects them with HTTP 409.
        """
        # 1. Validate and write file to disk
        invoice_uuid, storage_path, file_hash, file_size, mime_type, safe_filename = (
            await self.storage_service.validate_and_store(file)
        )

        # 2. Check for duplicate SHA-256 hash in database
        stmt = select(Invoice).where(Invoice.file_hash == file_hash)
        existing = db.execute(stmt).scalar_one_or_none()

        if existing:
            logger.warning(
                f"Duplicate upload detected: File hash {file_hash} matches existing invoice {existing.id}"
            )
            # Clean up the newly written duplicate file from storage
            full_path = Path(settings.FILE_STORAGE_PATH).parent / storage_path
            if full_path.exists():
                full_path.unlink()

            raise DuplicateResourceError(
                message="Duplicate file detected. An invoice with this exact content has already been uploaded.",
                details={
                    "existing_invoice_id": str(existing.id),
                    "file_hash": file_hash,
                }
            )

        # 3. Create Invoice database record in PENDING state
        invoice = Invoice(
            id=invoice_uuid,
            file_name=safe_filename,
            storage_path=storage_path,
            file_hash=file_hash,
            file_type=mime_type,
            file_size_bytes=file_size,
            status=InvoiceStatus.PENDING.value,
        )
        db.add(invoice)

        # 4. Create initial audit log entry
        log_entry = ProcessingLog(
            invoice_id=invoice_uuid,
            stage="UPLOAD",
            log_level="INFO",
            message=f"Document '{file.filename}' uploaded and verified successfully.",
            metadata_json={
                "file_hash": file_hash,
                "file_type": mime_type,
                "file_size_bytes": file_size,
            },
        )
        db.add(log_entry)

        try:
            db.commit()
            db.refresh(invoice)
            logger.info(f"Persisted new invoice {invoice.id} with status PENDING.")
            return invoice
        except Exception as exc:
            db.rollback()
            # Clean up file on DB failure
            full_path = Path(settings.FILE_STORAGE_PATH).parent / storage_path
            if full_path.exists():
                full_path.unlink()
            logger.error(f"Database error while saving invoice {invoice_uuid}: {exc}")
            raise DatabaseError(message="Database error while saving invoice record.")

    def update_invoice(self, invoice_id: UUID, update_data: "InvoiceUpdateRequest", db: Session) -> Invoice:
        from backend.app.schemas.invoice import InvoiceSchema, Vendor, LineItem, InvoiceUpdateRequest
        from backend.app.services.invoice_validation_service import InvoiceValidationService
        from backend.app.core.exceptions import ResourceNotFoundError
        from backend.app.models.invoice import InvoiceLineItem

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ResourceNotFoundError(message="Invoice not found.", code="INVOICE_NOT_FOUND")

        # Update basic fields
        if update_data.vendor_name is not None:
            invoice.vendor_name = update_data.vendor_name
        if update_data.invoice_number is not None:
            invoice.invoice_number = update_data.invoice_number
        if update_data.invoice_date is not None:
            invoice.invoice_date = update_data.invoice_date
        if update_data.due_date is not None:
            invoice.due_date = update_data.due_date
        if update_data.currency is not None:
            invoice.currency = update_data.currency
        if update_data.subtotal is not None:
            invoice.subtotal = update_data.subtotal
        if update_data.tax is not None:
            invoice.tax = update_data.tax
        if update_data.total is not None:
            invoice.total = update_data.total

        # Recreate line items
        db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice_id).delete()
        
        new_line_items = []
        for i, li in enumerate(update_data.line_items, start=1):
            db_li = InvoiceLineItem(
                invoice_id=invoice_id,
                line_number=i,
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                amount=li.amount
            )
            new_line_items.append(db_li)
            db.add(db_li)

        schema_vendor = Vendor(name=invoice.vendor_name) if invoice.vendor_name else None
        schema_line_items = [
            LineItem(
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                amount=li.amount
            ) for li in new_line_items
        ]
        
        validation_schema = InvoiceSchema(
            invoice_number=invoice.invoice_number,
            vendor=schema_vendor,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            currency=invoice.currency,
            subtotal=invoice.subtotal,
            tax=invoice.tax,
            total=invoice.total,
            line_items=schema_line_items
        )

        validation_result = InvoiceValidationService.validate_invoice(validation_schema)

        if validation_result.is_valid:
            invoice.status = InvoiceStatus.PROCESSED.value
            invoice.review_reason = None
            log_level = "INFO"
            log_message = "Invoice manually reviewed and successfully validated."
        else:
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.review_reason = "\n".join(validation_result.errors)
            log_level = "WARNING"
            log_message = "Invoice manually reviewed but still failed financial validation."
            
        log_entry = ProcessingLog(
            invoice_id=invoice_id,
            stage="MANUAL_REVIEW",
            log_level=log_level,
            message=log_message,
            metadata_json={"validation_errors": validation_result.errors, "validation_warnings": validation_result.warnings}
        )
        db.add(log_entry)

        try:
            db.commit()
            db.refresh(invoice)
            return invoice
        except Exception as exc:
            db.rollback()
            logger.error(f"Database error while updating invoice {invoice_id}: {exc}")
            raise DatabaseError(message="Database error while updating invoice record.")
