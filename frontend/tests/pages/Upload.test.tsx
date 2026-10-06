import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import UploadPage from '@/app/upload/page';
import { apiClient } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  apiClient: {
    uploadInvoice: vi.fn(),
  }
}));

describe('Upload Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders upload form', () => {
    render(<UploadPage />);
    expect(screen.getByRole('heading', { name: 'Upload Invoice' })).toBeInTheDocument();
    expect(screen.getByText('Select a PDF, PNG, or JPEG file to begin extraction.')).toBeInTheDocument();
  });

  it('shows error if file is larger than 10MB', async () => {
    render(<UploadPage />);
    
    const file = new File(['a'.repeat(10 * 1024 * 1024 + 1)], 'large.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/Upload a file/i);
    
    fireEvent.change(input, { target: { files: [file] } });
    
    const submitButton = screen.getByRole('button', { name: /Upload Invoice/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('File exceeds the 10MB maximum size limit.')).toBeInTheDocument();
    });
    expect(apiClient.uploadInvoice).not.toHaveBeenCalled();
  });

  it('handles successful upload', async () => {
    (apiClient.uploadInvoice as any).mockResolvedValue({
      id: 'inv_123',
      file_name: 'test.pdf',
      status: 'PENDING',
    });

    render(<UploadPage />);
    
    const file = new File(['dummy content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/Upload a file/i);
    
    fireEvent.change(input, { target: { files: [file] } });
    
    const submitButton = screen.getByRole('button', { name: /Upload Invoice/i });
    fireEvent.click(submitButton);

    expect(screen.getByText('Uploading & Queuing...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Upload Successful')).toBeInTheDocument();
    });

    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('Queued')).toBeInTheDocument(); // StatusBadge renders this
    expect(apiClient.uploadInvoice).toHaveBeenCalledTimes(1);
  });

  it('handles API errors safely', async () => {
    (apiClient.uploadInvoice as any).mockRejectedValue(new Error('Unsupported file type'));

    render(<UploadPage />);
    
    const file = new File(['dummy content'], 'test.txt', { type: 'text/plain' });
    const input = screen.getByLabelText(/Upload a file/i);
    
    fireEvent.change(input, { target: { files: [file] } });
    
    const submitButton = screen.getByRole('button', { name: /Upload Invoice/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Unsupported file type')).toBeInTheDocument();
    });
  });
});
