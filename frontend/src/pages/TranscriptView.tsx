import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchTranscript, TranscriptResponse } from '../services/transcripts';
import { ApiError, API_BASE_URL } from '../lib/api';
import { useToast } from '../context/ToastContext';

const DOWNLOAD_FORMATS = ['txt', 'md', 'srt', 'vtt', 'json', 'docx'] as const;

export const TranscriptView: React.FC = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      if (!jobId) {
        setIsLoading(false);
        return;
      }
      try {
        // Handle token passed via query param for cross-tab opening
        const urlToken = new URLSearchParams(window.location.search).get('token');
        if (urlToken) {
          localStorage.setItem('auth_token', urlToken);
        }
        const data = await fetchTranscript(jobId);
        setTranscript(data);
      } catch (error) {
        console.error('Failed to load transcript:', error);
        if (error instanceof ApiError) {
          showError(error.message);
        } else {
          showError('Failed to load transcript.');
        }
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [jobId, showError]);

  const handleDownload = async (format: typeof DOWNLOAD_FORMATS[number]) => {
    if (!jobId) return;
    try {
      const token = localStorage.getItem('auth_token');
      const url = `${API_BASE_URL}/transcripts/${jobId}/export?format=${format}`;
      const response = await fetch(url, {
        headers: token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : undefined,
      });
      if (!response.ok) {
        throw new Error(`Download failed (${response.status})`);
      }
      const blob = await response.blob();
      const link = document.createElement('a');
      const downloadUrl = window.URL.createObjectURL(blob);
      link.href = downloadUrl;
      const disposition = response.headers.get('Content-Disposition');
      const match = disposition?.match(/filename=\"?(.+?)\"?$/);
      link.download = match?.[1] ?? `transcript.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      showSuccess(`Transcript downloaded (${format.toUpperCase()})`);
    } catch (error) {
      console.error('Download error:', error);
      showError(error instanceof Error ? error.message : 'Download failed.');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-sage-light">
        <p className="text-pine-mid">Loading transcript…</p>
      </div>
    );
  }

  if (!transcript) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-sage-light px-6">
        <p className="text-pine-deep text-lg">Transcript not available.</p>
        <button
          className="px-4 py-2 bg-forest-green text-white rounded-lg"
          onClick={() => navigate('/', { replace: true })}
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-sage-light px-6 py-8">
      <div className="max-w-3xl mx-auto bg-white border border-sage-mid rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h1 className="text-2xl font-semibold text-pine-deep">Transcript</h1>
            <p className="text-sm text-pine-mid mt-1">Job ID: {transcript.job_id}</p>
          </div>
          <button
            className="px-3 py-2 text-sm bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
            onClick={() => navigate('/', { replace: true })}
          >
            Back to Dashboard
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mb-6">
          {DOWNLOAD_FORMATS.map((fmt) => (
            <button
              key={fmt}
              className="px-3 py-1 text-sm bg-sage-light text-pine-deep rounded hover:bg-sage-mid transition"
              onClick={() => handleDownload(fmt)}
            >
              Download {fmt.toUpperCase()}
            </button>
          ))}
        </div>

        <section className="mb-6">
          <h2 className="text-lg font-medium text-pine-deep mb-2">Full Text</h2>
          <div className="bg-sage-50 border border-sage-mid rounded-lg p-4 text-sm text-pine-deep whitespace-pre-wrap">
            {transcript.text}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-medium text-pine-deep mb-2">Segments</h2>
          <div className="space-y-3">
            {transcript.segments.map((segment) => (
              <div key={segment.id} className="border border-gray-200 rounded-lg p-3 text-sm">
                <div className="text-xs text-pine-mid mb-1">
                  {segment.start.toFixed(1)}s – {segment.end.toFixed(1)}s
                </div>
                <div>{segment.text}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
