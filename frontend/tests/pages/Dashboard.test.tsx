import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from '@/app/page';
import { apiClient } from '@/lib/api';
import { mockInvoiceListItems } from '../fixtures/invoices';

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    getHealth: vi.fn(),
    getInvoices: vi.fn(),
  }
}));

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders loading state initially and then data', async () => {
    (apiClient.getHealth as any).mockResolvedValue({ status: 'healthy', database: 'connected' });
    (apiClient.getInvoices as any).mockImplementation((page: number, limit: number, status?: string) => {
      if (!status) {
        return Promise.resolve({ items: mockInvoiceListItems, total: 2, page: 1, limit: 5 });
      }
      if (status === 'PROCESSED') {
        return Promise.resolve({ items: [], total: 1, page: 1, limit: 1 });
      }
      if (status === 'NEEDS_REVIEW') {
        return Promise.resolve({ items: [], total: 1, page: 1, limit: 1 });
      }
      if (status === 'FAILED') {
        return Promise.resolve({ items: [], total: 0, page: 1, limit: 1 });
      }
      return Promise.resolve({ items: [], total: 0, page: 1, limit: 1 });
    });

    render(<Dashboard />);
    
    // Initially shows loading
    expect(screen.getByText(/Loading dashboard insights/i)).toBeInTheDocument();

    // Wait for the data to load
    await waitFor(() => {
      expect(screen.queryByText(/Loading dashboard insights/i)).not.toBeInTheDocument();
    });

    // Check KPI cards
    expect(screen.getByText('Total Invoices')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Total Processed')).toBeInTheDocument();
    // 1 processed, 1 needs review, 0 failed, but the total on the first mock is 1
    // The query finds '1' for processed and '1' for needs review, '0' for failures.
    
    // Check recent invoices table
    expect(screen.getByText('invoice_1.pdf')).toBeInTheDocument();
    expect(screen.getByText('invoice_2.pdf')).toBeInTheDocument();
    
    // Check system health
    expect(screen.getByText('API Connection')).toBeInTheDocument();
  });

  it('renders error state on API failure', async () => {
    (apiClient.getHealth as any).mockRejectedValue(new Error('API Down'));
    (apiClient.getInvoices as any).mockRejectedValue(new Error('API Down'));

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('API Down')).toBeInTheDocument();
    });
  });

  it('renders empty state when no recent invoices exist', async () => {
    (apiClient.getHealth as any).mockResolvedValue({ status: 'healthy', database: 'connected' });
    (apiClient.getInvoices as any).mockResolvedValue({ items: [], total: 0, page: 1, limit: 5 });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/No recent invoices/i)).toBeInTheDocument();
      expect(screen.getByText(/You haven't uploaded any invoices yet/i)).toBeInTheDocument();
    });
  });
});
