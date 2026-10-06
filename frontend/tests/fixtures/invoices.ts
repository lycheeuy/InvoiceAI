import { InvoiceDetailResponse, InvoiceListItem, InvoiceStatusResponse } from '@/types/api';

export const mockInvoicePending: InvoiceDetailResponse = {
  id: 'inv_1',
  file_name: 'test_invoice.pdf',
  file_hash: 'hash1',
  file_type: 'application/pdf',
  file_size_bytes: 1024,
  status: 'PENDING',
  review_reason: null,
  vendor_name: null,
  invoice_number: null,
  invoice_date: null,
  due_date: null,
  currency: null,
  subtotal: null,
  tax: null,
  total: null,
  confidence_score: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  line_items: [],
  logs: []
};

export const mockInvoiceExtracting: InvoiceDetailResponse = {
  ...mockInvoicePending,
  status: 'EXTRACTING'
};

export const mockInvoiceProcessed: InvoiceDetailResponse = {
  ...mockInvoicePending,
  status: 'PROCESSED',
  vendor_name: 'Acme Corp',
  invoice_number: 'INV-001',
  invoice_date: '2023-10-01',
  total: 150.00,
  confidence_score: 0.95
};

export const mockInvoiceNeedsReview: InvoiceDetailResponse = {
  ...mockInvoicePending,
  status: 'NEEDS_REVIEW',
  review_reason: 'Total amount mismatch',
  vendor_name: 'Acme Corp',
  total: 150.00
};

export const mockInvoiceFailed: InvoiceDetailResponse = {
  ...mockInvoicePending,
  status: 'FAILED',
  logs: [
    {
      id: 'log_1',
      stage: 'EXTRACTION',
      log_level: 'ERROR',
      message: 'Failed to extract text from PDF',
      metadata_json: null,
      created_at: new Date().toISOString()
    }
  ]
};

export const mockInvoiceListItems: InvoiceListItem[] = [
  {
    id: 'inv_1',
    file_name: 'invoice_1.pdf',
    vendor_name: 'Vendor A',
    invoice_number: 'INV-A',
    invoice_date: '2023-01-01',
    currency: 'USD',
    total: 100,
    status: 'PROCESSED',
    confidence_score: 0.9,
    created_at: new Date().toISOString()
  },
  {
    id: 'inv_2',
    file_name: 'invoice_2.pdf',
    vendor_name: null,
    invoice_number: null,
    invoice_date: null,
    currency: null,
    total: null,
    status: 'NEEDS_REVIEW',
    confidence_score: 0.5,
    created_at: new Date().toISOString()
  }
];

export const mockStatusPending: InvoiceStatusResponse = {
  id: 'inv_1',
  status: 'PENDING',
  review_reason: null,
  confidence_score: null,
  updated_at: new Date().toISOString()
};

export const mockStatusExtracting: InvoiceStatusResponse = {
  ...mockStatusPending,
  status: 'EXTRACTING'
};

export const mockStatusProcessed: InvoiceStatusResponse = {
  ...mockStatusPending,
  status: 'PROCESSED',
  confidence_score: 0.95
};
