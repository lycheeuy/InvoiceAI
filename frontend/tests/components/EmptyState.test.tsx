import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EmptyState } from '@/components/ui/EmptyState';

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No Invoices" description="You have no invoices yet." />);
    expect(screen.getByText('No Invoices')).toBeInTheDocument();
    expect(screen.getByText('You have no invoices yet.')).toBeInTheDocument();
  });
});
