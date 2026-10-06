import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import InvoiceDetailPage from '@/app/invoices/[id]/page';
import { apiClient } from '@/lib/api';
import { mockInvoiceProcessed, mockInvoiceNeedsReview, mockInvoiceFailed, mockInvoicePending, mockInvoiceProcessing } from '../fixtures/invoices';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'inv_1' })
}));

vi.mock('@/lib/api', () => ({
  apiClient: {
    getInvoiceDetail: vi.fn(),
    getInvoiceStatus: vi.fn(),
    updateInvoice: vi.fn(),
  },
  API_BASE_URL: 'http://test-api'
}));

describe('Invoice Detail Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders loading state initially', () => {
    (apiClient.getInvoiceDetail as any).mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<InvoiceDetailPage />);
    expect(screen.getByText('Loading invoice details...')).toBeInTheDocument();
  });

  it('renders PROCESSED invoice correctly', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceProcessed);
    
    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.queryByText('Loading invoice details...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('test_invoice.pdf')).toBeInTheDocument();
    expect(screen.getByText('Processed')).toBeInTheDocument(); // Badge
    expect(screen.getByDisplayValue('Acme Corp')).toBeInTheDocument();
    expect(screen.getByDisplayValue('INV-001')).toBeInTheDocument();
    expect(screen.getByDisplayValue('150')).toBeInTheDocument(); // Total
  });

  it('renders NEEDS_REVIEW invoice and handles update', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceNeedsReview);
    
    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Validation Issue')).toBeInTheDocument();
    });

    expect(screen.getByText('Total amount mismatch')).toBeInTheDocument();
    expect(screen.getByText('Needs Review')).toBeInTheDocument(); // Badge

    // Test form interaction
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...mockInvoiceNeedsReview,
      vendor_name: 'Acme Corp Updated'
    });

    const vendorInput = screen.getByDisplayValue('Acme Corp');
    fireEvent.change(vendorInput, { target: { value: 'Acme Corp Updated', name: 'vendor_name' } });

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    expect(screen.getByText('Syncing...')).toBeInTheDocument();

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith('inv_1', expect.objectContaining({
        vendor_name: 'Acme Corp Updated'
      }));
      expect(screen.getByText('Synced successfully')).toBeInTheDocument();
    });
  });

  it('renders FAILED invoice correctly', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceFailed);
    
    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Processing Error')).toBeInTheDocument();
    });

    expect(screen.getAllByText('Failed to extract text from PDF')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Failed')[0]).toBeInTheDocument();
  });

  it('polls when status is PENDING and stops when PROCESSED', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoicePending);
    
    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Queued')).toBeInTheDocument();
    });

    // Advance 3 seconds
    (apiClient.getInvoiceStatus as any).mockResolvedValue({ status: 'EXTRACTING' });
    
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    await waitFor(() => {
      expect(apiClient.getInvoiceStatus).toHaveBeenCalled();
    });
    expect(screen.getByText('Processing')).toBeInTheDocument();

    // Advance another 3 seconds to terminal state
    (apiClient.getInvoiceStatus as any).mockResolvedValue({ status: 'PROCESSED' });
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceProcessed);

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    await waitFor(() => {
      expect(apiClient.getInvoiceDetail).toHaveBeenCalledTimes(2); // Initial + after processed
    });
    expect(screen.getByText('Processed')).toBeInTheDocument();
    
    // Check if polling stopped (advance more time and ensure status not called again)
    (apiClient.getInvoiceStatus as any).mockClear();
    
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    expect(apiClient.getInvoiceStatus).not.toHaveBeenCalled();
  });
  
  it('polls when status is PENDING and handles NEEDS_REVIEW', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoicePending);
    
    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Queued')).toBeInTheDocument();
    });

    (apiClient.getInvoiceStatus as any).mockResolvedValue({ status: 'NEEDS_REVIEW' });
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceNeedsReview);
    
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Needs Review')).toBeInTheDocument();
    });
  });

  it('polls when status is PENDING and handles FAILED', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoicePending);
    
    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Queued')).toBeInTheDocument();
    });

    (apiClient.getInvoiceStatus as any).mockResolvedValue({ status: 'FAILED' });
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceFailed);
    
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    await waitFor(() => {
      expect(screen.getAllByText('Failed')[0]).toBeInTheDocument();
    });
  });
});
