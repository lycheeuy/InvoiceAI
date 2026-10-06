import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Card } from '@/components/ui/Card';

describe('Card Component', () => {
  it('renders card with children', () => {
    render(
      <Card>
        <p>Test Content</p>
      </Card>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });
});
