import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import InvoiceDetailPage from '@/app/invoices/[id]/page';
import { apiClient } from '@/lib/api';
import { mockInvoiceProcessed, mockInvoiceNeedsReview, mockInvoiceFailed, mockInvoicePending } from '../fixtures/invoices';

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

  it('normalizes Indonesian Rupiah thousand separators (e.g. 3.725.000) before PATCH', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceFailed);
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...mockInvoiceFailed,
      status: 'PROCESSED',
      subtotal: 3725000,
      tax: 372500,
      total: 4097500,
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Processing Error')).toBeInTheDocument();
    });

    const subtotalInput = document.querySelector('input[name="subtotal"]') as HTMLInputElement;
    const taxInput = document.querySelector('input[name="tax"]') as HTMLInputElement;
    const totalInput = document.querySelector('input[name="total"]') as HTMLInputElement;

    fireEvent.change(subtotalInput, { target: { name: 'subtotal', value: '3.725.000' } });
    fireEvent.change(taxInput, { target: { name: 'tax', value: '372.500' } });
    fireEvent.change(totalInput, { target: { name: 'total', value: '4.097.500' } });

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith('inv_1', {
        vendor_name: null,
        invoice_number: null,
        invoice_date: null,
        due_date: null,
        subtotal: '3725000',
        tax: '372500',
        total: '4097500',
      });
    });
  });

  it('preserves standard decimal and international formats (372.50, 3,725.00, 3,725, 10,000) before PATCH', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceFailed);
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...mockInvoiceFailed,
      status: 'PROCESSED',
      subtotal: 3725,
      tax: 372.5,
      total: 10000,
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Processing Error')).toBeInTheDocument();
    });

    const subtotalInput = document.querySelector('input[name="subtotal"]') as HTMLInputElement;
    const taxInput = document.querySelector('input[name="tax"]') as HTMLInputElement;
    const totalInput = document.querySelector('input[name="total"]') as HTMLInputElement;

    fireEvent.change(subtotalInput, { target: { name: 'subtotal', value: '3,725.00' } });
    fireEvent.change(taxInput, { target: { name: 'tax', value: '372.50' } });
    fireEvent.change(totalInput, { target: { name: 'total', value: '10,000' } });

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith('inv_1', expect.objectContaining({
        subtotal: '3725.00',
        tax: '372.50',
        total: '10000',
        invoice_date: null,
        due_date: null,
      }));
    });
  });

  it('adds multiple line items, auto-calculates amount, allows manual amount override, and saves normalized IDR values', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceFailed);
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...mockInvoiceFailed,
      status: 'PROCESSED',
      subtotal: 3725000,
      tax: 372500,
      total: 4097500,
      line_items: [
        {
          id: 'li_1',
          line_number: 1,
          description: 'Lisensi Server',
          quantity: 2,
          unit_price: 1500000,
          amount: 3000000,
          created_at: new Date().toISOString(),
        },
        {
          id: 'li_2',
          line_number: 2,
          description: 'Jasa Setup (Diskon)',
          quantity: 1,
          unit_price: 800000,
          amount: 725000,
          created_at: new Date().toISOString(),
        },
      ],
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('No line items found.')).toBeInTheDocument();
    });

    const addBtn = screen.getByRole('button', { name: '+ Add Item' });
    fireEvent.click(addBtn);
    fireEvent.click(addBtn);

    // Item 1: Auto-calculate amount from Quantity (2) * Unit Price (1.500.000) -> 3000000
    const desc1 = screen.getByLabelText('Line item 1 description') as HTMLInputElement;
    const qty1 = screen.getByLabelText('Line item 1 quantity') as HTMLInputElement;
    const price1 = screen.getByLabelText('Line item 1 unit price') as HTMLInputElement;
    const amount1 = screen.getByLabelText('Line item 1 amount') as HTMLInputElement;

    fireEvent.change(desc1, { target: { value: 'Lisensi Server' } });
    fireEvent.change(qty1, { target: { value: '2' } });
    fireEvent.change(price1, { target: { value: '1.500.000' } });
    expect(amount1.value).toBe('3000000');

    // Item 2: Auto-calculate first, then manually override Amount
    const desc2 = screen.getByLabelText('Line item 2 description') as HTMLInputElement;
    const qty2 = screen.getByLabelText('Line item 2 quantity') as HTMLInputElement;
    const price2 = screen.getByLabelText('Line item 2 unit price') as HTMLInputElement;
    const amount2 = screen.getByLabelText('Line item 2 amount') as HTMLInputElement;

    fireEvent.change(desc2, { target: { value: 'Jasa Setup (Diskon)' } });
    fireEvent.change(qty2, { target: { value: '1' } });
    fireEvent.change(price2, { target: { value: '800.000' } });
    expect(amount2.value).toBe('800000');

    // Manual override on amount2 using Indonesian Rupiah format
    fireEvent.change(amount2, { target: { value: 'Rp 725.000,-' } });
    expect(amount2.value).toBe('Rp 725.000,-');

    // Also set subtotal, tax, total
    const subtotalInput = document.querySelector('input[name="subtotal"]') as HTMLInputElement;
    const taxInput = document.querySelector('input[name="tax"]') as HTMLInputElement;
    const totalInput = document.querySelector('input[name="total"]') as HTMLInputElement;
    fireEvent.change(subtotalInput, { target: { name: 'subtotal', value: '3.725.000' } });
    fireEvent.change(taxInput, { target: { name: 'tax', value: '372.500' } });
    fireEvent.change(totalInput, { target: { name: 'total', value: '4.097.500' } });

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith('inv_1', {
        vendor_name: null,
        invoice_number: null,
        invoice_date: null,
        due_date: null,
        subtotal: '3725000',
        tax: '372500',
        total: '4097500',
        line_items: [
          {
            description: 'Lisensi Server',
            quantity: '2',
            unit_price: '1500000',
            amount: '3000000',
          },
          {
            description: 'Jasa Setup (Diskon)',
            quantity: '1',
            unit_price: '800000',
            amount: '725000',
          },
        ],
      });
    });
  });

  it('edits existing line items and removes a single line item', async () => {
    const invoiceWithTwoItems = {
      ...mockInvoiceNeedsReview,
      subtotal: 300000,
      tax: 30000,
      total: 330000,
      line_items: [
        {
          id: 'li_existing_1',
          line_number: 1,
          description: 'Item Satu',
          quantity: 1,
          unit_price: 100000,
          amount: 100000,
          created_at: new Date().toISOString(),
        },
        {
          id: 'li_existing_2',
          line_number: 2,
          description: 'Item Dua',
          quantity: 2,
          unit_price: 100000,
          amount: 200000,
          created_at: new Date().toISOString(),
        },
      ],
    };

    (apiClient.getInvoiceDetail as any).mockResolvedValue(invoiceWithTwoItems);
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...invoiceWithTwoItems,
      status: 'PROCESSED',
      line_items: [
        {
          id: 'li_existing_1',
          line_number: 1,
          description: 'Item Satu Diperbarui',
          quantity: 3,
          unit_price: 100000,
          amount: 300000,
          created_at: new Date().toISOString(),
        },
      ],
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Item Satu')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Item Dua')).toBeInTheDocument();
    });

    // Remove second item
    const removeItem2Btn = screen.getByRole('button', { name: 'Remove line item 2' });
    fireEvent.click(removeItem2Btn);

    expect(screen.queryByDisplayValue('Item Dua')).not.toBeInTheDocument();

    // Edit first item description and quantity
    const desc1 = screen.getByLabelText('Line item 1 description') as HTMLInputElement;
    const qty1 = screen.getByLabelText('Line item 1 quantity') as HTMLInputElement;
    fireEvent.change(desc1, { target: { value: 'Item Satu Diperbarui' } });
    fireEvent.change(qty1, { target: { value: '3' } });

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith(
        'inv_1',
        expect.objectContaining({
          line_items: [
            {
              id: 'li_existing_1',
              description: 'Item Satu Diperbarui',
              quantity: '3',
              unit_price: 100000,
              amount: '300000',
            },
          ],
        })
      );
    });
  });

  it('sends line_items: [] when user removes all existing line items', async () => {
    const invoiceWithItem = {
      ...mockInvoiceNeedsReview,
      line_items: [
        {
          id: 'li_existing_1',
          line_number: 1,
          description: 'Item Hapus Semua',
          quantity: 1,
          unit_price: 150000,
          amount: 150000,
          created_at: new Date().toISOString(),
        },
      ],
    };

    (apiClient.getInvoiceDetail as any).mockResolvedValue(invoiceWithItem);
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...invoiceWithItem,
      line_items: [],
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Item Hapus Semua')).toBeInTheDocument();
    });

    const removeBtn = screen.getByRole('button', { name: 'Remove line item 1' });
    fireEvent.click(removeBtn);

    expect(screen.getByText('No line items found.')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith(
        'inv_1',
        expect.objectContaining({
          line_items: [],
        })
      );
    });
  });

  it('omits line_items from payload and preserves existing line item IDs and records when saving header-only changes', async () => {
    const invoiceWithItem = {
      ...mockInvoiceProcessed,
      subtotal: 150,
      tax: 0,
      total: 150,
      line_items: [
        {
          id: 'li_keep_1',
          line_number: 1,
          description: 'Existing Service',
          quantity: 1,
          unit_price: 150,
          amount: 150,
          created_at: new Date().toISOString(),
        },
      ],
    };

    (apiClient.getInvoiceDetail as any).mockResolvedValue(invoiceWithItem);
    (apiClient.updateInvoice as any).mockResolvedValueOnce({
      ...invoiceWithItem,
      vendor_name: 'Acme Corp Renamed',
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Existing Service')).toBeInTheDocument();
    });

    // 1. Header-only change (isLineItemsDirty === false)
    const vendorInput = screen.getByDisplayValue('Acme Corp');
    fireEvent.change(vendorInput, { target: { name: 'vendor_name', value: 'Acme Corp Renamed' } });

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledTimes(1);
      const [calledId, sentPayload] = (apiClient.updateInvoice as any).mock.calls[0];
      expect(calledId).toBe('inv_1');
      expect(sentPayload).toEqual({
        vendor_name: 'Acme Corp Renamed',
        invoice_number: 'INV-001',
        invoice_date: '2023-10-01',
        due_date: null,
        subtotal: 150,
        tax: 0,
        total: 150,
      });
      expect(sentPayload).not.toHaveProperty('line_items');
      expect(screen.getByDisplayValue('Existing Service')).toBeInTheDocument();
    });

    // 2. Verify existing line item record and its ID ('li_keep_1') were preserved after header-only save
    (apiClient.updateInvoice as any).mockResolvedValueOnce({
      ...invoiceWithItem,
      vendor_name: 'Acme Corp Renamed',
      line_items: [
        {
          ...invoiceWithItem.line_items[0],
          description: 'Existing Service Updated',
        },
      ],
    });

    const desc1 = screen.getByLabelText('Line item 1 description') as HTMLInputElement;
    fireEvent.change(desc1, { target: { value: 'Existing Service Updated' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledTimes(2);
      const [, secondPayload] = (apiClient.updateInvoice as any).mock.calls[1];
      expect(secondPayload.line_items).toEqual([
        {
          id: 'li_keep_1',
          description: 'Existing Service Updated',
          quantity: 1,
          unit_price: 150,
          amount: 150,
        },
      ]);
    });
  });

  it('clears amount when quantity or unit_price is emptied or invalid, while still allowing manual amount entry', async () => {
    (apiClient.getInvoiceDetail as any).mockResolvedValue(mockInvoiceFailed);
    (apiClient.updateInvoice as any).mockResolvedValue({
      ...mockInvoiceFailed,
      status: 'PROCESSED',
    });

    render(<InvoiceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('No line items found.')).toBeInTheDocument();
    });

    const addBtn = screen.getByRole('button', { name: '+ Add Item' });
    fireEvent.click(addBtn);

    const desc = screen.getByLabelText('Line item 1 description') as HTMLInputElement;
    const qty = screen.getByLabelText('Line item 1 quantity') as HTMLInputElement;
    const price = screen.getByLabelText('Line item 1 unit price') as HTMLInputElement;
    const amount = screen.getByLabelText('Line item 1 amount') as HTMLInputElement;

    fireEvent.change(desc, { target: { value: 'Layanan Konsultasi' } });
    fireEvent.change(qty, { target: { value: '2' } });
    fireEvent.change(price, { target: { value: '500.000' } });
    expect(amount.value).toBe('1000000');

    // Empty quantity -> amount should automatically clear
    fireEvent.change(qty, { target: { value: '' } });
    expect(amount.value).toBe('');

    // Re-enter valid quantity -> amount recalculated
    fireEvent.change(qty, { target: { value: '3' } });
    expect(amount.value).toBe('1500000');

    // Enter invalid unit_price -> amount should automatically clear
    fireEvent.change(price, { target: { value: 'abc' } });
    expect(amount.value).toBe('');

    // Re-enter valid unit_price -> amount recalculated
    fireEvent.change(price, { target: { value: '250.000' } });
    expect(amount.value).toBe('750000');

    // Empty unit_price -> amount should automatically clear
    fireEvent.change(price, { target: { value: '' } });
    expect(amount.value).toBe('');

    // User can still manually fill amount when unit_price is empty
    fireEvent.change(amount, { target: { value: '900.000' } });
    expect(amount.value).toBe('900.000');

    const submitBtn = screen.getByRole('button', { name: 'Approve & Sync' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.updateInvoice).toHaveBeenCalledWith(
        'inv_1',
        expect.objectContaining({
          line_items: [
            {
              description: 'Layanan Konsultasi',
              quantity: '3',
              unit_price: null,
              amount: '900000',
            },
          ],
        })
      );
    });
  });
});
