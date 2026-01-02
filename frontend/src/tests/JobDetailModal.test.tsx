import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import { JobDetailModal } from '../components/modals/JobDetailModal';
import type { Job } from '../services/jobs';
import * as transcriptService from '../services/transcripts';

vi.mock('../services/transcripts', () => ({
  fetchSpeakerLabels: vi.fn(),
  updateSpeakerLabels: vi.fn(),
}));

const mockJob: Job = {
  id: '123',
  original_filename: 'interview.mp3',
  file_size: 15728640, // 15 MB
  mime_type: 'audio/mpeg',
  duration: 1834, // 30:34
  status: 'completed',
  progress_percent: 100,
  progress_stage: 'completed',
  estimated_time_left: 0,
  estimated_total_seconds: 2000,
  model_used: 'medium',
  asr_provider_used: 'whisper',
  diarizer_used: 'diarization-3.1',
  diarizer_provider_used: 'pyannote',
  language_detected: 'English',
  speaker_count: null,
  has_timestamps: true,
  has_speaker_labels: false,
  tags: [
    { id: 1, name: 'interviews', color: '#2D6A4F' },
    { id: 2, name: 'important', color: '#C9A227' }
  ],
  created_at: '2025-11-15T10:30:00Z',
  updated_at: '2025-11-15T10:59:00Z',
  started_at: '2025-11-15T10:31:00Z',
  completed_at: '2025-11-15T11:00:00Z'
};

describe('JobDetailModal', () => {
  const mockOnClose = vi.fn();
  const mockOnPlay = vi.fn();
  const mockOnDownload = vi.fn();
  const mockOnRestart = vi.fn();
  const mockOnDelete = vi.fn();
  const mockOnStop = vi.fn();
  const mockOnPause = vi.fn();
  const mockOnResume = vi.fn();
  const mockOnRename = vi.fn();
  const mockOnViewTranscript = vi.fn();
  const mockOnUpdateTags = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnPlay.mockClear();
    mockOnDownload.mockClear();
    mockOnRestart.mockClear();
    mockOnDelete.mockClear();
    mockOnStop.mockClear();
    mockOnPause.mockClear();
    mockOnResume.mockClear();
    mockOnRename.mockClear();
    mockOnViewTranscript.mockClear();
    mockOnUpdateTags.mockClear();
    vi.mocked(transcriptService.fetchSpeakerLabels).mockReset();
    vi.mocked(transcriptService.updateSpeakerLabels).mockReset();
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText(/00:30:34/)).toBeInTheDocument(); // Duration
    expect(screen.getByText('Job ID')).toBeInTheDocument();
    expect(screen.getByText('123')).toBeInTheDocument();
    expect(screen.getByText('whisper / medium')).toBeInTheDocument(); // Model (provider / weight)
    expect(screen.getByText(/english/i)).toBeInTheDocument(); // Language
    expect(screen.getByText(/Requested:/i)).toBeInTheDocument(); // Speakers info
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText('interviews')).toBeInTheDocument();
    expect(screen.getByText('important')).toBeInTheDocument();
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText(/download transcript/i)).toBeInTheDocument();
  });

  it('calls onRename when rename is confirmed', async () => {
    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={mockJob}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
        onUpdateTags={mockOnUpdateTags}
      />
    );

    fireEvent.click(screen.getByText(/rename job/i));
    const dialog = screen.getByRole('dialog', { name: /rename job/i });
    fireEvent.change(screen.getByLabelText(/new name/i), { target: { value: 'Updated' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /^rename$/i }));
    await waitFor(() => {
      expect(mockOnRename).toHaveBeenCalledWith('123', 'Updated');
    });
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
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
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
        onUpdateTags={mockOnUpdateTags}
      />
    );
    
    expect(screen.getByText(/view transcript/i)).toBeInTheDocument();
  });

  it('renders speaker rename controls when speaker labels are available', async () => {
    vi.mocked(transcriptService.fetchSpeakerLabels).mockResolvedValue({
      speakers: ['SPEAKER_00', 'SPEAKER_01'],
    });
    vi.mocked(transcriptService.updateSpeakerLabels).mockResolvedValue({
      speakers: ['Lisa', 'Bob'],
    });

    render(
      <JobDetailModal
        isOpen={true}
        onClose={mockOnClose}
        job={{ ...mockJob, has_speaker_labels: true, speaker_count: 2 }}
        onPlay={mockOnPlay}
        onDownload={mockOnDownload}
        onRestart={mockOnRestart}
        onDelete={mockOnDelete}
        onStop={mockOnStop}
        onPause={mockOnPause}
        onResume={mockOnResume}
        onRename={mockOnRename}
        onViewTranscript={mockOnViewTranscript}
        onUpdateTags={mockOnUpdateTags}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/speaker names/i)).toBeInTheDocument();
    });

    const inputs = screen.getAllByPlaceholderText(/speaker name/i);
    expect(inputs).toHaveLength(2);
    fireEvent.change(inputs[0], { target: { value: 'Lisa' } });
    fireEvent.change(inputs[1], { target: { value: 'Bob' } });

    fireEvent.click(screen.getByText(/save speaker names/i));

    await waitFor(() => {
      expect(transcriptService.updateSpeakerLabels).toHaveBeenCalledWith('123', [
        { label: 'SPEAKER_00', name: 'Lisa' },
        { label: 'SPEAKER_01', name: 'Bob' },
      ]);
    });
  });
});

