import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi } from 'vitest';
import { TranscriptView } from '../pages/TranscriptView';
import { ApiError } from '../lib/api';

const fetchTranscriptMock = vi.fn();

vi.mock('../services/transcripts', () => ({
  fetchTranscript: (...args: any[]) => fetchTranscriptMock(...args),
}));

const toastMock = {
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showToast: vi.fn(),
  showInfo: vi.fn(),
};

vi.mock('../context/ToastContext', () => ({
  useToast: () => toastMock,
}));

const renderWithRouter = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/transcripts/:jobId" element={<TranscriptView />} />
      </Routes>
    </MemoryRouter>
  );

describe('TranscriptView', () => {
  beforeEach(() => {
    localStorage.clear();
    fetchTranscriptMock.mockReset();
    toastMock.showError.mockReset();
    toastMock.showSuccess.mockReset();
  });

  it('loads and displays transcript content', async () => {
    fetchTranscriptMock.mockResolvedValue({
      job_id: 'job-1',
      text: 'Full transcript text',
      segments: [
        { id: 1, start: 0, end: 5, text: 'Hello world' },
      ],
      language: 'en',
      duration: 5,
    });

    window.history.pushState({}, 'Transcript', '/transcripts/job-1?token=abc123');
    renderWithRouter('/transcripts/job-1?token=abc123');

    await waitFor(() => expect(fetchTranscriptMock).toHaveBeenCalledWith('job-1'));
    expect(localStorage.getItem('auth_token')).toBe('abc123');
    expect(screen.getByText(/job id: job-1/i)).toBeInTheDocument();
    expect(screen.getByText(/full transcript text/i)).toBeInTheDocument();
    expect(screen.getByText(/hello world/i)).toBeInTheDocument();
  });

  it('surfaces errors and shows fallback when transcript cannot be loaded', async () => {
    fetchTranscriptMock.mockRejectedValue(new ApiError('Not found', 404));

    window.history.pushState({}, 'Transcript missing', '/transcripts/missing');
    renderWithRouter('/transcripts/missing');

    await waitFor(() => expect(toastMock.showError).toHaveBeenCalled());
    expect(screen.getByText(/transcript not available/i)).toBeInTheDocument();
  });
});
