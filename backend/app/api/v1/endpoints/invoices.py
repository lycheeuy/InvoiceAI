from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status, BackgroundTasks
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.session import get_db
from backend.app.models.invoice import Invoice
from backend.app.schemas.invoice import (
    InvoiceDetailResponse,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceStatusResponse,
    InvoiceUploadResponse,
)
from backend.app.services.invoice_service import InvoiceService

router = APIRouter()
invoice_service = InvoiceService()


from backend.app.services.document_processing.service import process_invoice_background

@router.post(
    "/invoices/upload",
    response_model=InvoiceUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload invoice file for ingestion and processing",
    tags=["Invoices"],
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
)
def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    vendor: Optional[str] = Query(None, description="Search by vendor name"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> InvoiceListResponse:
    """Retrieves paginated list of invoices with optional status and vendor filters."""
    query = select(Invoice)

    if status_filter:
        query = query.where(Invoice.status == status_filter.upper())
    if vendor:
        query = query.where(Invoice.vendor_name.ilike(f"%{vendor}%"))

    # Count total matching rows
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    # Apply pagination and sorting (newest first)
    offset = (page - 1) * limit
    paged_query = query.order_by(desc(Invoice.created_at)).offset(offset).limit(limit)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID '{id}' was not found.",
        )

    return InvoiceDetailResponse.model_validate(invoice)


@router.get(
    "/invoices/{id}/status",
    response_model=InvoiceStatusResponse,
    summary="Get lightweight invoice status",
    tags=["Invoices"],
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID '{id}' was not found.",
        )

    return InvoiceStatusResponse(
        id=row.id,
        status=row.status,
        review_reason=row.review_reason,
        confidence_score=row.confidence_score,
        updated_at=row.updated_at,
    )
