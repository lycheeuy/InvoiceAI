import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Spinner } from '@/components/ui/Spinner';

describe('Spinner', () => {
  it('renders loading spinner', () => {
    render(<Spinner />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('animate-spin');
  });
});
