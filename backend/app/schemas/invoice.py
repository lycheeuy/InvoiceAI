from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    amount: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessingLogResponse(BaseModel):
    id: UUID
    stage: str
    log_level: str
    message: str
    metadata_json: Optional[dict] = None
    created_at: datetime

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        import re
        if "Stored file" in v and "not found" in v:
            return "Stored file not found."
        v = re.sub(r'(?:[A-Za-z]:\\[^\s]+|/[^\s]+)', '<redacted_path>', v)
        return v

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

# --- Phase 3: AI Extraction Structured Schemas ---

def normalize_monetary_value(v: object) -> object:
    """
    Normalizes Indonesian (Rp/IDR) and standard monetary string representations
    into a clean numeric string before Pydantic Decimal parsing.
    Examples:
      - "Rp 3.725.000" -> "3725000"
      - "372.500" -> "372500"
      - "4.097.500" -> "4097500"
      - "3.725.000,50" -> "3725000.50"
      - "1,250.50" -> "1250.50"
      - "100.50" -> "100.50"
    """
    if v is None or isinstance(v, (Decimal, int, float)):
        return v
    if not isinstance(v, str):
        return v

    import re
    s = v.strip()
    if not s:
        return None

    # Strip currency symbols/prefixes (Rp, IDR, $) while preserving sign
    s = re.sub(r"^(?:Rp\.?|IDR|\$)\s*", "", s, flags=re.IGNORECASE).strip()
    if s.startswith("-") or s.startswith("+"):
        sign = s[0]
        rest = re.sub(r"^(?:Rp\.?|IDR|\$)\s*", "", s[1:].strip(), flags=re.IGNORECASE).strip()
        s = sign + rest

    # Strip Indonesian trailing ",-" (e.g., "Rp 3.725.000,-")
    if s.endswith(",-"):
        s = s[:-2].strip()

    # Remove spaces inside numbers
    s = s.replace(" ", "")

    # 1. Indonesian format with thousand dots and decimal comma: e.g. "3.725.000,50" or "372.500,00"
    if re.match(r"^-?\d{1,3}(?:\.\d{3})+,\d+$", s):
        s = s.replace(".", "").replace(",", ".")
    # 2. US/International format with thousand commas and decimal dot: e.g. "3,725,000.50"
    elif re.match(r"^-?\d{1,3}(?:,\d{3})+\.\d+$", s):
        s = s.replace(",", "")
    # 3. Multiple thousand dots without decimals: e.g. "3.725.000" or "4.097.500"
    elif re.match(r"^-?\d{1,3}(?:\.\d{3}){2,}$", s):
        s = s.replace(".", "")
    # 4. Single thousand dot with 3 trailing digits (non-zero leading): e.g. "372.500", "10.000"
    elif re.match(r"^-?[1-9]\d{0,2}\.\d{3}$", s):
        s = s.replace(".", "")
    # 5. Multiple thousand commas without decimals: e.g. "3,725,000"
    elif re.match(r"^-?\d{1,3}(?:,\d{3}){2,}$", s):
        s = s.replace(",", "")
    # 6. Single thousand comma with 3 trailing digits (non-zero leading): e.g. "3,725", "10,000"
    elif re.match(r"^-?[1-9]\d{0,2},\d{3}$", s):
        s = s.replace(",", "")
    # 7. Plain number with decimal comma (1-2 decimal digits): e.g. "100,50"
    elif re.match(r"^-?\d+,\d{1,2}$", s):
        s = s.replace(",", ".")

    return s


class Vendor(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None

class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    unit_price: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    amount: Optional[Decimal] = Field(default=None, ge=Decimal('0'))

    @field_validator("quantity", "unit_price", "amount", mode="before")
    @classmethod
    def _normalize_monetary(cls, v: object) -> object:
        return normalize_monetary_value(v)

class InvoiceSchema(BaseModel):
    invoice_number: Optional[str] = None
    vendor: Optional[Vendor] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    subtotal: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    tax: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    total: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    line_items: Optional[List[LineItem]] = Field(default_factory=list)

    @field_validator("subtotal", "tax", "total", mode="before")
    @classmethod
    def _normalize_monetary(cls, v: object) -> object:
        return normalize_monetary_value(v)

class InvoiceLineItemUpdateRequest(BaseModel):
    id: Optional[UUID] = None
    description: str
    quantity: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    unit_price: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    amount: Optional[Decimal] = Field(default=None, ge=Decimal('0'))

    @field_validator("quantity", "unit_price", "amount", mode="before")
    @classmethod
    def _normalize_monetary(cls, v: object) -> object:
        return normalize_monetary_value(v)

class InvoiceUpdateRequest(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    subtotal: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    tax: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    total: Optional[Decimal] = Field(default=None, ge=Decimal('0'))
    line_items: Optional[List[InvoiceLineItemUpdateRequest]] = None

    @field_validator("subtotal", "tax", "total", mode="before")
    @classmethod
    def _normalize_monetary(cls, v: object) -> object:
        return normalize_monetary_value(v)
