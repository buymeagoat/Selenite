import React, { useEffect, useMemo, useState } from 'react';
import { Download, Eye, Gauge, Pause, Play, Square } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { getTagColor, getTagTextColor } from '../tags/tagColors';
import { formatDateTime, type DateTimePreferences } from '../../utils/dateTime';

interface Job {
  id: string;
  original_filename: string;
  status:
    | 'queued'
    | 'processing'
    | 'cancelling'
    | 'pausing'
    | 'paused'
    | 'completed'
    | 'failed'
    | 'cancelled';
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
  model_used?: string | null;
  asr_provider_used?: string | null;
  diarizer_used?: string | null;
  diarizer_provider_used?: string | null;
  completed_at?: string | null;
  owner_user_id?: number | null;
  owner_username?: string | null;
  owner_email?: string | null;
  tags: Array<{ id: number; name: string; color?: string | null }>;
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
  dateFormat?: DateTimePreferences['dateFormat'];
  timeFormat?: DateTimePreferences['timeFormat'];
  locale?: string | null;
  showOwnerLabel?: boolean;
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
  dateFormat = 'locale',
  timeFormat = 'locale',
  locale = null,
  showOwnerLabel = false,
}) => {
  const [now, setNow] = useState(() => Date.now());
  const durationSeconds = job.duration ?? 0;
  const isProcessing = ['processing', 'cancelling', 'pausing'].includes(job.status);

  const formatDuration = (seconds: number): string => {
    const totalSeconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`;
  };

  const parseTimestamp = (value?: string | null) => {
    if (!value) return null;
    let normalized = value.replace(' ', 'T');
    normalized = normalized.replace(/(\.\d{3})\d+/, '$1');
    if (!/Z$/i.test(normalized) && !/[+-]\d{2}:\d{2}$/.test(normalized)) {
      normalized = `${normalized}Z`;
    }
    const ts = Date.parse(normalized);
    return Number.isNaN(ts) ? null : ts;
  };

  const elapsedSeconds = useMemo(() => {
    const startedTs = parseTimestamp(job.started_at) ?? parseTimestamp(job.created_at);
    if (startedTs === null) return null;
    return Math.max(0, Math.floor((now - startedTs) / 1000));
  }, [job.created_at, job.started_at, now]);

  const formatStage = (stage?: string | null) => {
    if (stage) {
      const normalized = stage.replace(/_/g, ' ').trim();
      return normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : undefined;
    }
    if (job.status === 'cancelling') return 'Cancelling';
    if (job.status === 'pausing') return 'Pausing';
    return 'Processing';
  };

  useEffect(() => {
    if (!isProcessing) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isProcessing]);

  const speakerText = (() => {
    if (!job.has_speaker_labels) {
      return 'Disabled';
    }
    const detected = job.speaker_count ?? 1;
    return `Detected ${detected}`;
  })();

  const formatDate = (isoString: string): string =>
    formatDateTime(isoString, {
      timeZone,
      dateFormat,
      timeFormat,
      locale,
    });

  const showDuration = job.status === 'completed' && durationSeconds > 0;
  const showCompletedMetadata = job.status === 'completed';
  const progressPercent =
    typeof job.progress_percent === 'number' ? Math.max(0, Math.round(job.progress_percent)) : null;

  const asrDisplay = (() => {
    if (!job.model_used && !job.asr_provider_used) return null;
    const weight = job.model_used || 'Unknown';
    return job.asr_provider_used ? `${job.asr_provider_used} / ${weight}` : weight;
  })();

  const diarizerDisplay = (() => {
    if (!job.has_speaker_labels) return 'Disabled';
    if (!job.diarizer_used) return 'None';
    return job.diarizer_provider_used
      ? `${job.diarizer_provider_used} / ${job.diarizer_used}`
      : job.diarizer_used;
  })();
  const ownerLabel =
    job.owner_email ||
    job.owner_username ||
    (job.owner_user_id ? `User ${job.owner_user_id}` : 'Unassigned');

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
        {showOwnerLabel && (
          <>
            <span aria-hidden="true" className="text-gray-300">|</span>
            <span>Owner: {ownerLabel}</span>
          </>
        )}
        {showDuration && (
          <>
            <span aria-hidden="true" className="text-gray-300">|</span>
            <span>Duration: {formatDuration(durationSeconds)}</span>
          </>
        )}
        {job.status === 'completed' && (
          <>
            <span aria-hidden="true" className="text-gray-300">|</span>
            <span>Speakers: {speakerText}</span>
          </>
        )}
      </div>

      {showCompletedMetadata && (asrDisplay || diarizerDisplay) && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-pine-mid mb-3">
          {asrDisplay && <span>ASR: {asrDisplay}</span>}
          <span aria-hidden="true" className="text-gray-300">|</span>
          <span>Diarizer: {diarizerDisplay}</span>
        </div>
      )}

      {isProcessing && (
        <div className="flex items-center justify-between text-xs text-pine-mid mb-3">
          <span>
            {job.progress_stage === 'stalled' || Boolean(job.stalled_at)
              ? 'Stalled - no recent progress'
              : `${formatStage(job.progress_stage)}${progressPercent !== null ? ` (${progressPercent}%)` : ''}`}
          </span>
          {elapsedSeconds !== null && <span>Elapsed {formatDuration(elapsedSeconds)}</span>}
        </div>
      )}

      {/* Tags */}
      {job.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3" data-testid="job-tags">
          {job.tags.map((tag) => {
            const tagColor = getTagColor(tag);
            const tagTextColor = getTagTextColor(tagColor);
            return (
              <span
                key={tag.id}
                data-testid="job-tag-chip"
                className="text-xs px-2 py-1 rounded border"
                style={{
                  backgroundColor: tagColor,
                  color: tagTextColor,
                  borderColor: tagColor,
                }}
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
              aria-label={isActive && isPlaying ? 'Pause playback' : 'Play media'}
              title={isActive && isPlaying ? 'Pause' : 'Play'}
            >
              {isActive && isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onStop?.(job.id);
              }}
              disabled={!isActive}
              aria-label="Stop playback"
              title="Stop"
            >
              <Square className="w-4 h-4" />
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onSpeed?.(job.id);
              }}
              disabled={!isActive}
              aria-label="Change playback speed"
              title={`Speed ${playbackRate}x`}
            >
              <Gauge className="w-4 h-4" />
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onDownload?.(job.id);
              }}
              aria-label="Download transcript"
              title="Download"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep"
              onClick={(e) => {
                e.stopPropagation();
                onView?.(job.id);
              }}
              aria-label="View transcript"
              title="View"
            >
              <Eye className="w-4 h-4" />
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
              {formatDuration(currentTime)}/{formatDuration(durationSeconds)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
