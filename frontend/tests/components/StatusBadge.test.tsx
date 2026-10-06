import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from '@/components/ui/StatusBadge';

describe('StatusBadge', () => {
  it('renders PENDING status correctly', () => {
    render(<StatusBadge status="PENDING" />);
    expect(screen.getByText('Queued')).toBeInTheDocument();
  });

  it('renders EXTRACTING status correctly with loading state', () => {
    render(<StatusBadge status="EXTRACTING" />);
    expect(screen.getByText('Processing')).toBeInTheDocument();
  });

  it('renders PROCESSED status correctly', () => {
    render(<StatusBadge status="PROCESSED" />);
    expect(screen.getByText('Processed')).toBeInTheDocument();
  });

  it('renders NEEDS_REVIEW status correctly', () => {
    render(<StatusBadge status="NEEDS_REVIEW" />);
    expect(screen.getByText('Needs Review')).toBeInTheDocument();
  });

  it('renders FAILED status correctly', () => {
    render(<StatusBadge status="FAILED" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('handles unknown status gracefully', () => {
    render(<StatusBadge status={'UNKNOWN' as any} />);
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
  });
});
