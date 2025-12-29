import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { JobCard } from '../components/jobs/JobCard';

const mockJob = {
  id: '123',
  original_filename: 'interview.mp3',
  status: 'completed' as const,
  created_at: '2025-11-15T10:30:00Z',
  duration: 1834, // 30:34 in seconds
  tags: [
    { id: 1, name: 'interviews', color: '#2D6A4F' },
    { id: 2, name: 'important', color: '#C9A227' }
  ]
};

describe('JobCard', () => {
  it('renders job card with filename and status', () => {
    const onClick = vi.fn();
    render(<JobCard job={mockJob} onClick={onClick} />);
    
    expect(screen.getByText('interview.mp3')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('displays tags', () => {
    const onClick = vi.fn();
    render(<JobCard job={mockJob} onClick={onClick} />);
    
    expect(screen.getByText('#interviews')).toBeInTheDocument();
    expect(screen.getByText('#important')).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn();
    render(<JobCard job={mockJob} onClick={onClick} />);
    
    fireEvent.click(screen.getByText('interview.mp3'));
    expect(onClick).toHaveBeenCalledWith('123');
  });

  it('shows processing status with elapsed time instead of a progress bar', () => {
    const processingJob = {
      ...mockJob,
      status: 'processing' as const,
      progress_percent: 45,
      progress_stage: 'Transcribing...',
      estimated_time_left: 420,
      estimated_total_seconds: 900,
      started_at: '2025-11-15T10:31:00Z'
    };
    
    render(<JobCard job={processingJob} onClick={vi.fn()} />);
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(screen.getByText(/Transcribing/i)).toBeInTheDocument();
    expect(screen.getByText(/Elapsed/i)).toBeInTheDocument();
  });

  it('shows queued state without progress', () => {
    const queuedJob = {
      ...mockJob,
      status: 'queued' as const,
      duration: undefined
    };
    
    render(<JobCard job={queuedJob} onClick={vi.fn()} />);
    expect(screen.getByText('Queued')).toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('shows failed state with error styling', () => {
    const failedJob = {
      ...mockJob,
      status: 'failed' as const
    };
    
    render(<JobCard job={failedJob} onClick={vi.fn()} />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('formats duration correctly for completed jobs', () => {
    const onClick = vi.fn();
    render(<JobCard job={mockJob} onClick={onClick} />);
    
    expect(screen.getByText(/Duration:\s*00:30:34/)).toBeInTheDocument();
  });
});
