import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { JobDetailModal } from '../components/modals/JobDetailModal';

const mockJob = {
  id: '123',
  original_filename: 'interview.mp3',
  file_size: 15728640, // 15 MB
  duration: 1834, // 30:34
  status: 'completed',
  model_used: 'medium',
  language_detected: 'English',
  speaker_count: 2,
  tags: [
    { id: 1, name: 'interviews', color: '#2D6A4F' },
    { id: 2, name: 'important', color: '#C9A227' }
  ],
  created_at: '2025-11-15T10:30:00Z',
  completed_at: '2025-11-15T11:00:00Z'
};

describe('JobDetailModal', () => {
  const mockOnClose = vi.fn();
  const mockOnPlay = vi.fn();
  const mockOnDownload = vi.fn();
  const mockOnRestart = vi.fn();
  const mockOnDelete = vi.fn();
  const mockOnUpdateTags = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnPlay.mockClear();
    mockOnDownload.mockClear();
    mockOnRestart.mockClear();
    mockOnDelete.mockClear();
    mockOnUpdateTags.mockClear();
  });

  it('does not render when isOpen is false', () => {
    render(
      <JobDetailModal
        isOpen={false}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.queryByText('interview.mp3')).not.toBeInTheDocument();
  });

  it('renders modal when isOpen is true', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText('interview.mp3')).toBeInTheDocument();
  });

  it('displays status badge', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('displays all metadata fields', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText(/30:34/)).toBeInTheDocument(); // Duration
    expect(screen.getByText('medium')).toBeInTheDocument(); // Model
    expect(screen.getByText('English')).toBeInTheDocument(); // Language
    expect(screen.getByText(/2 detected/)).toBeInTheDocument(); // Speakers
    expect(screen.getByText(/15 MB/)).toBeInTheDocument(); // File size
  });

  it('displays tags', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText('#interviews')).toBeInTheDocument();
    expect(screen.getByText('#important')).toBeInTheDocument();
  });

  it('closes modal when X button is clicked', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    const closeButton = screen.getByLabelText(/close/i);
    fireEvent.click(closeButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onPlay when play button is clicked', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    const playButton = screen.getByText(/play media/i);
    fireEvent.click(playButton);
    expect(mockOnPlay).toHaveBeenCalledWith('123');
  });

  it('has download button with dropdown', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText(/download transcript/i)).toBeInTheDocument();
  });

  it('calls onRestart when restart button is clicked', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    const restartButton = screen.getByText(/restart transcription/i);
    fireEvent.click(restartButton);
    expect(mockOnRestart).toHaveBeenCalledWith('123');
  });

  it('shows delete confirmation when delete button is clicked', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    const deleteButton = screen.getByText(/delete job/i);
    fireEvent.click(deleteButton);
    
    // Confirmation dialog should appear
    expect(screen.getByText(/this will permanently delete/i)).toBeInTheDocument();
  });

  it('has view transcript button', () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText(/view transcript/i)).toBeInTheDocument();
  });
});
