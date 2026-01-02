import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/jobs/StatusBadge';

describe('StatusBadge', () => {
  it('renders queued status with gray style', () => {
    render(<StatusBadge status="queued" />);
    const badge = screen.getByText('Queued');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-gray-200', 'text-gray-900');
  });

  it('renders processing status with high contrast', () => {
    render(<StatusBadge status="processing" />);
    const badge = screen.getByText('Processing');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-sky-600', 'text-white');
  });

  it('renders completed status with high contrast', () => {
    render(<StatusBadge status="completed" />);
    const badge = screen.getByText('Completed');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-emerald-600', 'text-white');
  });

  it('renders failed status with high contrast', () => {
    render(<StatusBadge status="failed" />);
    const badge = screen.getByText('Failed');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-red-600', 'text-white');
  });

  it('supports different sizes', () => {
    const { rerender } = render(<StatusBadge status="completed" size="sm" />);
    expect(screen.getByText('Completed')).toHaveClass('text-xs');
    
    rerender(<StatusBadge status="completed" size="lg" />);
    expect(screen.getByText('Completed')).toHaveClass('text-sm');
  });
});
