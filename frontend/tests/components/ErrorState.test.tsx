import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ErrorState } from '@/components/ui/ErrorState';

describe('ErrorState', () => {
  it('renders title and message', () => {
    render(<ErrorState message="Something went wrong." />);
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong.')).toBeInTheDocument();
  });
});
