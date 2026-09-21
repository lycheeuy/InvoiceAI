from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvoiceUploadResponse(BaseModel):
    id: UUID
    file_name: str
    file_hash: str
    file_size_bytes: int
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class DuplicateInvoiceResponse(BaseModel):
    detail: str = "Duplicate file detected. An invoice with this exact content has already been uploaded."
    existing_invoice_id: UUID
    file_hash: str


class InvoiceLineItemResponse(BaseModel):
    id: UUID
    line_number: int
    description: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessingLogResponse(BaseModel):
    id: UUID
    stage: str
    log_level: str
    message: str
    metadata_json: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceStatusResponse(BaseModel):
    id: UUID
    status: str
    review_reason: Optional[str] = None
    confidence_score: Optional[float] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceListItem(BaseModel):
    id: UUID
    file_name: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    currency: Optional[str] = None
    total: Optional[Decimal] = None
    status: str
    confidence_score: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceListResponse(BaseModel):
    items: List[InvoiceListItem]
    total: int
    page: int
    limit: int


class InvoiceDetailResponse(BaseModel):
    id: UUID
    file_name: str
    storage_path: str
    file_hash: str
    file_type: str
    file_size_bytes: int
    status: str
    review_reason: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    line_items: List[InvoiceLineItemResponse] = Field(default_factory=list)
    logs: List[ProcessingLogResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
