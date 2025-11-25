import React from 'react';
import { StatusBadge } from './StatusBadge';
import { ProgressBar } from './ProgressBar';

interface Job {
  id: string;
  original_filename: string;
  status: 'queued' | 'processing' | 'cancelling' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string | null;
  duration?: number;
  progress_percent?: number | null;
  progress_stage?: string | null;
  estimated_time_left?: number | null;
  estimated_total_seconds?: number | null;
  stalled_at?: string | null;
  speaker_count?: number | null;
  has_speaker_labels?: boolean;
  tags: Array<{ id: number; name: string; color: string }>;
}

interface JobCardProps {
  job: Job;
  onClick: (jobId: string) => void;
  onQuickAction?: (jobId: string, action: string) => void;
  onPlay?: (jobId: string) => void;
  onStop?: (jobId: string) => void;
  onSeek?: (jobId: string, percent: number) => void;
  onSpeed?: (jobId: string) => void;
  isActive?: boolean;
  isPlaying?: boolean;
  currentTime?: number;
  duration?: number;
  playbackRate?: number;
  onDownload?: (jobId: string) => void;
  onView?: (jobId: string) => void;
  selectionMode?: boolean;
  selected?: boolean;
  onSelectToggle?: (jobId: string, checked: boolean) => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onClick,
  onPlay,
  onStop,
  onSeek,
  onSpeed,
  isActive = false,
  isPlaying = false,
  currentTime = 0,
  duration = 0,
  playbackRate = 1,
  onDownload,
  onView,
  selectionMode = false,
  selected = false,
  onSelectToggle
}) => {
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  const speakerLabel = () => {
    if (job.speaker_count === null || job.speaker_count === undefined) return null;
    const mode = job.has_speaker_labels ? 'Detected' : 'Requested';
    return `${mode} ${job.speaker_count}`;
  };

  return (
    <div
      data-testid="job-card"
      className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onClick(job.id)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {selectionMode && (
            <input
              type="checkbox"
              className="h-4 w-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
              checked={selected}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => onSelectToggle?.(job.id, e.target.checked)}
              aria-label={`Select job ${job.original_filename}`}
            />
          )}
          <span className="text-lg">🎧</span>
          <h3 className="font-medium text-pine-deep truncate">{job.original_filename}</h3>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Metadata */}
      <div className="flex items-center gap-3 text-sm text-pine-mid mb-3">
        <span>{formatDate(job.created_at)}</span>
        {job.duration && job.status === 'completed' && (
          <>
            <span>•</span>
            <span>Duration: {formatDuration(job.duration)}</span>
          </>
        )}
        {speakerLabel() && (
          <>
            <span>•</span>
            <span>Speakers: {speakerLabel()}</span>
          </>
        )}
      </div>

      {/* Progress Bar for Processing */}
      {['processing', 'cancelling'].includes(job.status) && job.progress_percent != null && (
        <div className="mb-3">
          <ProgressBar
            percent={job.progress_percent}
            stage={job.progress_stage || undefined}
            estimatedTimeLeft={job.estimated_time_left || undefined}
            startedAt={job.started_at || undefined}
            createdAt={job.created_at || undefined}
            stalled={job.progress_stage === 'stalled' || Boolean(job.stalled_at)}
          />
        </div>
      )}

      {/* Tags */}
      {job.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {job.tags.map((tag) => (
            <span
              key={tag.id}
              className="text-xs px-2 py-1 rounded"
              style={{ backgroundColor: tag.color + '20', color: tag.color }}
            >
              #{tag.name}
            </span>
          ))}
        </div>
      )}

      {/* Quick Actions (for completed jobs) */}
      {job.status === 'completed' && (
        <div className="flex flex-col gap-2 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onPlay?.(job.id);
              }}
            >
              {isActive && isPlaying ? 'Pause' : 'Play'}
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onStop?.(job.id);
              }}
              disabled={!isActive}
            >
              Stop
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onSpeed?.(job.id);
              }}
              disabled={!isActive}
            >
              {playbackRate}x
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onDownload?.(job.id);
              }}
            >
              Download
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onView?.(job.id);
              }}
            >
              View
            </button>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0}
              max={100}
              value={duration ? Math.floor((currentTime / duration) * 100) : 0}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => onSeek?.(job.id, Number(e.target.value))}
              className="w-full accent-forest-green"
              disabled={!isActive || !duration}
              aria-label={`Seek ${job.original_filename}`}
            />
            <span className="text-xs text-pine-mid">
              {Math.floor(currentTime)}/{duration ? Math.floor(duration) : '0'}s
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
