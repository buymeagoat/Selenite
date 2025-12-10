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
  playbackRate?: number;
  onDownload?: (jobId: string) => void;
  onView?: (jobId: string) => void;
  selectionMode?: boolean;
  selected?: boolean;
  onSelectToggle?: (jobId: string, checked: boolean) => void;
  timeZone?: string | null;
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
  playbackRate = 1,
  onDownload,
  onView,
  selectionMode = false,
  selected = false,
  onSelectToggle,
  timeZone = null,
}) => {
  const durationSeconds = job.duration ?? 0;

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const speakerText = (() => {
    const detected = job.speaker_count ?? (job.has_speaker_labels ? 1 : null);
    if (detected === null) return null;
    const mode = job.has_speaker_labels ? 'Detected' : 'Requested';
    return `${mode} ${detected}`;
  })();

  const parseAsUTC = (isoString: string): Date => {
    if (!isoString) return new Date();
    // If the string lacks a timezone, treat it as UTC to avoid double-shifting local times.
    const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(isoString);
    return new Date(hasZone ? isoString : `${isoString}Z`);
  };

  const formatDate = (isoString: string): string => {
    const date = parseAsUTC(isoString);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZone: timeZone || undefined,
      timeZoneName: 'short',
    });
  };

  const showDuration = job.status === 'completed' && durationSeconds > 0;

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
          <h2 className="font-medium text-pine-deep truncate text-sm md:text-base">
            {job.original_filename}
          </h2>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Metadata */}
      <div className="flex items-center gap-3 text-sm text-pine-mid mb-3">
        <span>{formatDate(job.created_at)}</span>
        {showDuration && (
          <>
            <span aria-hidden="true" className="text-gray-300">|</span>
            <span>Duration: {formatDuration(durationSeconds)}</span>
          </>
        )}
        {speakerText && (
          <>
            <span aria-hidden="true" className="text-gray-300">|</span>
            <span>Speakers: {speakerText}</span>
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
        <div className="flex flex-wrap gap-2 mb-3" data-testid="job-tags">
          {job.tags.map((tag) => {
            return (
              <span
                key={tag.id}
                data-testid="job-tag-chip"
                className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-900 border border-gray-300"
              >
                #{tag.name}
              </span>
            );
          })}
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
              value={durationSeconds ? Math.floor((currentTime / durationSeconds) * 100) : 0}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => onSeek?.(job.id, Number(e.target.value))}
              className="w-full accent-forest-green"
              disabled={!isActive || !durationSeconds}
              aria-label={`Seek ${job.original_filename}`}
            />
            <span className="text-xs text-pine-mid">
              {Math.floor(currentTime)}/{durationSeconds ? Math.floor(durationSeconds) : '0'}s
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
