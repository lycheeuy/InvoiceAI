import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.log import ProcessingLog
from backend.app.services.document import DocumentStorageService


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
        invoice_uuid, storage_path, file_hash, file_size, mime_type = (
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

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Duplicate file detected. An invoice with this exact content has already been uploaded.",
                    "existing_invoice_id": str(existing.id),
                    "file_hash": file_hash,
                },
            )

        # 3. Create Invoice database record in PENDING state
        invoice = Invoice(
            id=invoice_uuid,
            file_name=file.filename or "unknown",
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while saving invoice record.",
            )
