import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import InvoicesPage from '@/app/invoices/page';
import { apiClient } from '@/lib/api';
import { mockInvoiceListItems } from '../fixtures/invoices';

vi.mock('@/lib/api', () => ({
  apiClient: {
    getInvoices: vi.fn(),
  }
}));

describe('Invoices List Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders loading state initially and then data', async () => {
    (apiClient.getInvoices as any).mockResolvedValue({
      items: mockInvoiceListItems,
      total: 2,
      page: 1,
      limit: 20
    });

    render(<InvoicesPage />);

    expect(screen.getByText('Loading invoices...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText('Loading invoices...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('invoice_1.pdf')).toBeInTheDocument();
    expect(screen.getByText('Vendor A')).toBeInTheDocument();
    expect(screen.getByText('100 USD')).toBeInTheDocument();
    
    // Check pagination text
    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(screen.getAllByText('1')[0]).toBeInTheDocument();
    expect(screen.getAllByText('2')[0]).toBeInTheDocument();
  });

  it('renders empty state when no invoices exist', async () => {
    (apiClient.getInvoices as any).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 20
    });

    render(<InvoicesPage />);

    await waitFor(() => {
      expect(screen.getByText('No invoices found')).toBeInTheDocument();
    });
  });

  it('renders error state on API failure', async () => {
    (apiClient.getInvoices as any).mockRejectedValue(new Error('Failed to fetch'));

    render(<InvoicesPage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
    });
  });

  it('handles pagination', async () => {
    (apiClient.getInvoices as any).mockResolvedValueOnce({
      items: Array(20).fill({ ...mockInvoiceListItems[0], id: 'inv_1' }),
      total: 25,
      page: 1,
      limit: 20
    });

    render(<InvoicesPage />);
    
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Next/i })[0]).not.toBeDisabled();
    });

    (apiClient.getInvoices as any).mockResolvedValueOnce({
      items: Array(5).fill({ ...mockInvoiceListItems[0], id: 'inv_2' }),
      total: 25,
      page: 2,
      limit: 20
    });

    // Need to find one of the next buttons (mobile or desktop)
    const nextButtons = screen.getAllByRole('button', { name: /Next/i });
    fireEvent.click(nextButtons[1] || nextButtons[0]);

    await waitFor(() => {
      expect(apiClient.getInvoices).toHaveBeenCalledWith(2, 20);
    });
  });
});
