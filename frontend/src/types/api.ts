export type InvoiceStatus = 'PENDING' | 'EXTRACTING' | 'PROCESSED' | 'NEEDS_REVIEW' | 'FAILED';

export interface ErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

export interface HealthResponse {
  status: string;
  database: string;
}

export interface InvoiceUploadResponse {
  id: string;
  file_name: string;
  file_hash: string;
  file_size_bytes: number;
  status: InvoiceStatus;
  message: string;
}

export interface InvoiceLineItemResponse {
  id: string;
  line_number: number;
  description: string;
  quantity: number | null;
  unit_price: number | null;
  amount: number | null;
  created_at: string;
}

export interface ProcessingLogResponse {
  id: string;
  stage: string;
  log_level: string;
  message: string;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface InvoiceStatusResponse {
  id: string;
  status: InvoiceStatus;
  review_reason: string | null;
  confidence_score: number | null;
  updated_at: string;
}

export interface InvoiceListItem {
  id: string;
  file_name: string;
  vendor_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  currency: string | null;
  total: number | null;
  status: InvoiceStatus;
  confidence_score: number | null;
  created_at: string;
}

export interface InvoiceListResponse {
  items: InvoiceListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface InvoiceDetailResponse {
  id: string;
  file_name: string;
  file_hash: string;
  file_type: string;
  file_size_bytes: number;
  status: InvoiceStatus;
  review_reason: string | null;
  vendor_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  currency: string | null;
  subtotal: number | null;
  tax: number | null;
  total: number | null;
  confidence_score: number | null;
  created_at: string;
  updated_at: string;
  line_items: InvoiceLineItemResponse[];
  logs: ProcessingLogResponse[];
}
