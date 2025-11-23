import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBar } from '../components/jobs/ProgressBar';

describe('ProgressBar', () => {
  it('renders progress bar with correct percentage', () => {
    render(<ProgressBar percent={45} />);
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '45');
  });

  it('displays stage and time estimate when provided', () => {
    render(<ProgressBar percent={30} stage="Transcribing..." estimatedTimeLeft={420} />);
    expect(screen.getByText(/Transcribing/i)).toBeInTheDocument();
    expect(screen.getByText(/7m 00s/i)).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('handles edge cases for percentage', () => {
    const { rerender } = render(<ProgressBar percent={0} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    
    rerender(<ProgressBar percent={100} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });

  it('applies success variant styling', () => {
    render(<ProgressBar percent={100} variant="success" />);
    const fill = screen.getByRole('progressbar').querySelector('[data-fill]');
    expect(fill).toHaveClass('bg-green-500');
  });

  it('applies error variant styling', () => {
    render(<ProgressBar percent={50} variant="error" />);
    const fill = screen.getByRole('progressbar').querySelector('[data-fill]');
    expect(fill).toHaveClass('bg-terracotta');
  });
});
