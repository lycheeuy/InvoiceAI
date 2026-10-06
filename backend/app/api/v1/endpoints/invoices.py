from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status, BackgroundTasks
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.session import get_db
from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.schemas.invoice import (
    InvoiceDetailResponse,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceStatusResponse,
    InvoiceUploadResponse,
    InvoiceUpdateRequest,
)
from backend.app.schemas.error import ErrorResponse
from backend.app.services.invoice_service import InvoiceService
from backend.app.core.exceptions import ResourceNotFoundError

router = APIRouter()
invoice_service = InvoiceService()


from backend.app.services.document_processing.service import process_invoice_background

@router.post(
    "/invoices/upload",
    response_model=InvoiceUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload invoice file for ingestion and processing",
    tags=["Invoices"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid Request"},
        409: {"model": ErrorResponse, "description": "Duplicate Resource"},
        413: {"model": ErrorResponse, "description": "File Too Large"},
        415: {"model": ErrorResponse, "description": "Unsupported Media Type"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> InvoiceUploadResponse:
    """
    Accepts an invoice document (PDF, PNG, JPG, JPEG), validates magic bytes,
    enforces 10 MB limit, verifies SHA-256 deduplication, and persists metadata.
    Queues document processing via BackgroundTasks.
    """
    invoice = await invoice_service.ingest_invoice_file(file, db)
    
    # Enqueue the background task using a fresh DB session
    background_tasks.add_task(process_invoice_background, invoice.id)
    
    return InvoiceUploadResponse(
        id=invoice.id,
        file_name=invoice.file_name,
        file_hash=invoice.file_hash,
        file_size_bytes=invoice.file_size_bytes,
        status=invoice.status,
        message="Invoice uploaded successfully. Processing has been queued.",
    )


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    summary="List invoices with pagination and filters",
    tags=["Invoices"],
    responses={
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def list_invoices(
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status", description="Filter by status"),
    vendor: Optional[str] = Query(None, max_length=100, description="Search by vendor name"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> InvoiceListResponse:
    """Retrieves paginated list of invoices with optional status and vendor filters."""
    query = select(Invoice)

    if status_filter:
        query = query.where(Invoice.status == status_filter.value)
    if vendor:
        query = query.where(Invoice.vendor_name.ilike(f"%{vendor}%"))

    # Count total matching rows
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    # Apply pagination and sorting (newest first, fallback to id for determinism)
    offset = (page - 1) * limit
    paged_query = query.order_by(desc(Invoice.created_at), desc(Invoice.id)).offset(offset).limit(limit)
    invoices = db.execute(paged_query).scalars().all()

    items = [
        InvoiceListItem(
            id=inv.id,
            file_name=inv.file_name,
            vendor_name=inv.vendor_name,
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date,
            currency=inv.currency,
            total=inv.total,
            status=inv.status,
            confidence_score=inv.confidence_score,
            created_at=inv.created_at,
        )
        for inv in invoices
    ]

    return InvoiceListResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/invoices/{id}",
    response_model=InvoiceDetailResponse,
    summary="Get full invoice details, line items, and audit logs",
    tags=["Invoices"],
    responses={
        404: {"model": ErrorResponse, "description": "Invoice Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def get_invoice(
    id: UUID,
    db: Session = Depends(get_db),
) -> InvoiceDetailResponse:
    """Fetches complete invoice metadata, extracted line items, and processing audit logs."""
    stmt = (
        select(Invoice)
        .where(Invoice.id == id)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.logs))
    )
    invoice = db.execute(stmt).scalar_one_or_none()

    if not invoice:
        raise ResourceNotFoundError(
            message="Invoice not found.",
            code="INVOICE_NOT_FOUND"
        )

    return InvoiceDetailResponse.model_validate(invoice)


@router.get(
    "/invoices/{id}/status",
    response_model=InvoiceStatusResponse,
    summary="Get lightweight invoice status",
    tags=["Invoices"],
    responses={
        404: {"model": ErrorResponse, "description": "Invoice Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def get_invoice_status(
    id: UUID,
    db: Session = Depends(get_db),
) -> InvoiceStatusResponse:
    """Lightweight endpoint for polling document processing lifecycle state."""
    stmt = select(Invoice.id, Invoice.status, Invoice.review_reason, Invoice.confidence_score, Invoice.updated_at).where(
        Invoice.id == id
    )
    row = db.execute(stmt).first()

    if not row:
        raise ResourceNotFoundError(
            message="Invoice not found.",
            code="INVOICE_NOT_FOUND"
        )

    return InvoiceStatusResponse(
        id=row.id,
        status=row.status,
        review_reason=row.review_reason,
        confidence_score=row.confidence_score,
        updated_at=row.updated_at,
    )


@router.patch(
    "/invoices/{id}",
    response_model=InvoiceDetailResponse,
    summary="Update invoice details after manual review",
    tags=["Invoices"],
    responses={
        404: {"model": ErrorResponse, "description": "Invoice Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def update_invoice_endpoint(
    id: UUID,
    update_data: InvoiceUpdateRequest,
    db: Session = Depends(get_db),
) -> InvoiceDetailResponse:
    """Updates invoice details, re-runs financial validation, and updates status."""
    updated_invoice = invoice_service.update_invoice(id, update_data, db)
    
    # We need to reload relationships to return InvoiceDetailResponse correctly
    stmt = (
        select(Invoice)
        .where(Invoice.id == id)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.logs))
    )
    invoice = db.execute(stmt).scalar_one()
    return InvoiceDetailResponse.model_validate(invoice)
@router.get(
    "/invoices/{id}/file",
    summary="Get original uploaded file",
    tags=["Invoices"],
    responses={
        404: {"model": ErrorResponse, "description": "Invoice or File Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def get_invoice_file(
    id: UUID,
    db: Session = Depends(get_db),
):
    """Serves the original uploaded invoice file."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    from backend.app.core.config import settings
    
    stmt = select(Invoice.storage_path, Invoice.file_type, Invoice.file_name).where(Invoice.id == id)
    row = db.execute(stmt).first()
    
    if not row:
        raise ResourceNotFoundError(
            message="Invoice not found.",
            code="INVOICE_NOT_FOUND"
        )
        
    file_path = Path(settings.FILE_STORAGE_PATH).parent / row.storage_path
    if not file_path.exists():
        raise ResourceNotFoundError(
            message="Original file not found on disk.",
            code="FILE_NOT_FOUND"
        )
        
    return FileResponse(
        path=file_path, 
        media_type=row.file_type,
        filename=row.file_name,
        content_disposition_type="inline"
    )
