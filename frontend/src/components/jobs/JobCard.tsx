import React from 'react';
import { StatusBadge } from './StatusBadge';
import { ProgressBar } from './ProgressBar';

interface Job {
  id: string;
  original_filename: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  created_at: string;
  duration?: number;
  progress_percent?: number;
  progress_stage?: string;
  estimated_time_left?: number;
  tags: Array<{ id: number; name: string; color: string }>;
}

interface JobCardProps {
  job: Job;
  onClick: (jobId: string) => void;
  onQuickAction?: (jobId: string, action: string) => void;
}

export const JobCard: React.FC<JobCardProps> = ({ job, onClick }) => {
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

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onClick(job.id)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-lg">🎵</span>
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
      </div>

      {/* Progress Bar for Processing */}
      {job.status === 'processing' && job.progress_percent !== undefined && (
        <div className="mb-3">
          <ProgressBar
            percent={job.progress_percent}
            stage={job.progress_stage}
            estimatedTimeLeft={job.estimated_time_left}
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
        <div className="flex gap-2 pt-3 border-t border-gray-100">
          <button className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep">
            Play
          </button>
          <button className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep">
            Download
          </button>
          <button className="text-sm px-3 py-1 rounded bg-sage-light hover:bg-sage-mid text-pine-deep">
            View
          </button>
        </div>
      )}
    </div>
  );
};
