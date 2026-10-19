import {
  ErrorResponse,
  HealthResponse,
  InvoiceUploadResponse,
  InvoiceListResponse,
  InvoiceDetailResponse,
  InvoiceStatusResponse,
  InvoiceStatus,
} from '../types/api';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  public code: string;
  public status: number;
  public details?: unknown;

  constructor(status: number, message: string, code: string = 'UNKNOWN_ERROR', details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function fetchWithHandleError<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);

  if (!response.ok) {
    let errorData: ErrorResponse | undefined;
    try {
      errorData = await response.json();
    } catch {
      // Ignored
    }

    if (errorData?.error) {
      throw new ApiError(
        response.status,
        errorData.error.message,
        errorData.error.code,
        errorData.error.details
      );
    }

    throw new ApiError(
      response.status,
      `Request failed with status ${response.status}`,
      'INTERNAL_SERVER_ERROR'
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const apiClient = {
  getHealth: (): Promise<HealthResponse> => {
    return fetchWithHandleError(`${API_BASE_URL}/health`);
  },

  uploadInvoice: (file: File): Promise<InvoiceUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchWithHandleError(`${API_BASE_URL}/invoices/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  getInvoices: (
    page: number = 1,
    limit: number = 20,
    status?: InvoiceStatus,
    vendor?: string
  ): Promise<InvoiceListResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    if (status) params.append('status', status);
    if (vendor) params.append('vendor', vendor);

    return fetchWithHandleError(`${API_BASE_URL}/invoices?${params.toString()}`);
  },

  getInvoiceDetail: (id: string): Promise<InvoiceDetailResponse> => {
    return fetchWithHandleError(`${API_BASE_URL}/invoices/${id}`);
  },

  getInvoiceStatus: (id: string): Promise<InvoiceStatusResponse> => {
    return fetchWithHandleError(`${API_BASE_URL}/invoices/${id}/status`);
  },

  updateInvoice: (id: string, data: Partial<InvoiceDetailResponse>): Promise<InvoiceDetailResponse> => {
    return fetchWithHandleError(`${API_BASE_URL}/invoices/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  }
};
