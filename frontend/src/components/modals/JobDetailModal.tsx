import React, { useState, useEffect } from 'react';
import { X, Play, FileText, Download, RotateCw, Trash2, ChevronDown, StopCircle } from 'lucide-react';
import { StatusBadge } from '../jobs/StatusBadge';
import { ConfirmDialog } from './ConfirmDialog';
import type { Job } from '../../services/jobs';
import { createTag, type Tag } from '../../services/tags';
import { devError } from '../../lib/debug';

interface JobDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: Job;
  onPlay: (jobId: string) => void;
  onDownload: (jobId: string, format: string) => void;
  onRestart: (jobId: string) => void;
  onDelete: (jobId: string) => void;
  onStop: (jobId: string) => void;
  onViewTranscript: (jobId: string) => void;
  onUpdateTags: (jobId: string, tagIds: number[]) => void;
  availableTags?: Tag[];
  timeZone?: string | null;
  asrProviderHint?: string | null;
  defaultDiarizerHint?: string | null;
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  isOpen,
  onClose,
  job,
  onPlay,
  onDownload,
  onRestart,
  onDelete,
  onStop,
  onViewTranscript,
  onUpdateTags,
  availableTags = [],
  timeZone = null,
  asrProviderHint = null,
  defaultDiarizerHint = null,
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [tagInputValue, setTagInputValue] = useState('');
  const [editableTags, setEditableTags] = useState(job.tags);

  useEffect(() => {
    // keep local tags in sync when a different job is opened
    setEditableTags(job.tags);
  }, [job]);

  if (!isOpen) return null;

  // UI Logic: Determine what actions are available based on job status
  const hasTranscript = job.status === 'completed';
const canRestart = ['completed', 'failed', 'cancelled'].includes(job.status);
const canDelete = !['processing', 'cancelling'].includes(job.status);
const canStop = job.status === 'processing' || job.status === 'queued';
  const hasMedia = true; // Media always exists if job was created
  const mediaDuration = job.duration ?? 0;
  const processingDuration =
    job.started_at && job.completed_at
      ? Math.max(
          0,
          Math.round(
            (parseAsUTC(job.completed_at).getTime() - parseAsUTC(job.started_at).getTime()) / 1000
          )
        )
      : null;

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`;
  }

function parseAsUTC(value: string): Date {
  if (!value) return new Date();
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

  function formatDate(isoString: string): string {
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
  }

  function languageName(code: string | null | undefined): string {
    if (!code) return 'Unknown';
    try {
    const dn = new Intl.DisplayNames([navigator.language || 'en'], { type: 'language' });
    return dn.of(code) || code;
  } catch {
    const map: Record<string, string> = {
      en: 'English',
      es: 'Spanish',
      fr: 'French',
      de: 'German',
      it: 'Italian',
      pt: 'Portuguese',
      nl: 'Dutch',
      ru: 'Russian',
      zh: 'Chinese',
      ja: 'Japanese',
      ko: 'Korean',
    };
    return map[code.toLowerCase()] || code;
    }
  }

  const diarizerDisplay = (() => {
    if (job.diarizer_used) return job.diarizer_used;
    if (defaultDiarizerHint) return `${defaultDiarizerHint} (failed)`;
    return 'None';
  })();

  const speakerDetected = job.speaker_count ?? (job.has_speaker_labels ? 1 : 1);
  const speakerSummary = `Requested: ${job.has_speaker_labels ? 'Yes' : 'No'} · Detected: ${speakerDetected}`;

  const handleDelete = () => {
    onDelete(job.id);
    setShowDeleteConfirm(false);
    onClose();
  };

  const handleDownloadFormat = (format: string) => {
    onDownload(job.id, format);
    setShowDownloadMenu(false);
  };

  const handleAddTag = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    // Already on job
    if (editableTags.some(t => t.name.toLowerCase() === trimmed.toLowerCase())) {
      setTagInputValue('');
      return;
    }
    // Reuse existing tag if available globally
    let tagToUse = availableTags.find(t => t.name.toLowerCase() === trimmed.toLowerCase());
    if (!tagToUse) {
      try {
        tagToUse = await createTag({ name: trimmed, color: '#0F3D2E' });
      } catch (err) {
        devError('Failed to create tag', err);
        setTagInputValue('');
        return;
      }
    }
    const next = [...editableTags, tagToUse];
    setEditableTags(next);
    setTagInputValue('');
    onUpdateTags(job.id, next.map(t => t.id));
  };

  const handleRemoveTag = async (id: number) => {
    const next = editableTags.filter(t => t.id !== id);
    setEditableTags(next);
    onUpdateTags(job.id, next.map(t => t.id));
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" data-testid="job-detail-modal">
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black bg-opacity-50"
          onClick={onClose}
        />
        
        {/* Modal */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
            <div className="flex-1 min-w-0">
              <h2 className="text-2xl font-semibold text-pine-deep mb-2 truncate">
                {job.original_filename}
              </h2>
              <StatusBadge status={job.status} />
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close modal"
              className="ml-4 text-pine-mid hover:text-pine-deep transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6" data-testid="job-metadata">
              <div>
                <div className="text-sm text-pine-mid">Duration</div>
                <div className="text-base font-medium text-pine-deep">
                  {mediaDuration > 0 ? formatDuration(mediaDuration) : 'Unknown'}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Created</div>
                <div className="text-base font-medium text-pine-deep">
                  {formatDate(job.created_at)}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">ASR provider / entry</div>
                <div className="text-base font-medium text-pine-deep">
                  {(asrProviderHint || 'Unknown') + ' / ' + (job.model_used || 'Unknown')}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Diarizer</div>
                <div className="text-base font-medium text-pine-deep">
                  {diarizerDisplay}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Languages</div>
                <div className="text-base font-medium text-pine-deep">
                  {languageName(job.language_detected)}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Speakers</div>
                <div className="text-base font-medium text-pine-deep">
                  {speakerSummary}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Source file size</div>
                <div className="text-base font-medium text-pine-deep">
                  {formatFileSize(job.file_size)}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Job processing duration</div>
                <div className="text-base font-medium text-pine-deep">
                  {processingDuration !== null ? formatDuration(processingDuration) : 'Unknown'}
                </div>
              </div>
            </div>

            {/* Tags Section (view & edit) */}
            <div className="mb-6" data-testid="job-tags-section">
              <div className="text-sm text-pine-mid mb-2" data-testid="tags-section-title">Tags</div>
              <div className="flex flex-wrap gap-2 mb-3" data-testid="job-tags">
                {editableTags.map((tag) => (
                  <span
                    key={tag.id}
                    data-testid="tag-chip"
                    className="flex items-center gap-2 text-sm px-3 py-1 rounded-full bg-sage-light text-pine-deep"
                    style={{ backgroundColor: tag.color + '20', color: tag.color }}
                  >
                    <span>#{tag.name}</span>
                    <button
                      type="button"
                      data-testid="remove-tag"
                      aria-label={`Remove tag ${tag.name}`}
                      onClick={() => handleRemoveTag(tag.id)}
                      className="text-xs px-1 rounded hover:bg-red-100 hover:text-red-600 transition"
                    >
                      ×
                    </button>
                  </span>
                ))}
                {editableTags.length === 0 && (
                  <span className="text-xs text-pine-mid">No tags</span>
                )}
              </div>
              <div className="relative max-w-xs">
                <input
                  data-testid="tag-input"
                  type="text"
                  value={tagInputValue}
                  onChange={(e) => setTagInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag(tagInputValue);
                    }
                  }}
                  placeholder="Add tag"
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none text-sm"
                />
                <button
                  type="button"
                  onClick={() => handleAddTag(tagInputValue.trim())}
                  disabled={!tagInputValue.trim()}
                  className="mt-2 px-3 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50 text-sm"
                >
                  Add tag
                </button>
              </div>
            </div>

            {job.status === 'cancelling' && (
              <p className="text-xs text-amber-700 mb-4">
                Cancellation requested. This job will stop once the current step finishes.
              </p>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3" data-testid="job-actions">
              {/* Play Media - Always available if media exists */}
              <button
                onClick={() => onPlay(job.id)}
                disabled={!hasMedia}
                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                  hasMedia
                    ? 'bg-forest-green text-white hover:bg-pine-deep'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                <Play className="w-5 h-5" />
                <span>Play Media</span>
              </button>

              {/* View Transcript - Only available if transcript exists */}
              <button
                onClick={() => hasTranscript && onViewTranscript(job.id)}
                disabled={!hasTranscript}
                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                  hasTranscript
                    ? 'bg-sage-light text-pine-deep hover:bg-sage-mid'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                <FileText className="w-5 h-5" />
                <span>View Transcript</span>
              </button>

              {/* Download Transcript - Only available if transcript exists */}
              <div className="relative" data-testid="download-menu">
                <button
                  onClick={() => hasTranscript && setShowDownloadMenu(!showDownloadMenu)}
                  disabled={!hasTranscript}
                  className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                    hasTranscript
                      ? 'bg-sage-light text-pine-deep hover:bg-sage-mid'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  <Download className="w-5 h-5" />
                  <span>Download Transcript</span>
                  <ChevronDown className="w-4 h-4" />
                </button>
                
                {showDownloadMenu && hasTranscript && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20" data-testid="download-options">
                    {['txt', 'md', 'srt', 'vtt', 'json', 'docx'].map((format) => (
                      <button
                        key={format}
                        onClick={() => handleDownloadFormat(format)}
                        className="w-full px-4 py-2 text-left text-pine-deep hover:bg-sage-light transition-colors first:rounded-t-lg last:rounded-b-lg"
                      >
                        .{format}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Restart Transcription - Only for completed/failed/cancelled jobs */}
              {canRestart && (
                <button
                  onClick={() => onRestart(job.id)}
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-sage-light text-pine-deep rounded-lg hover:bg-sage-mid transition-colors"
                >
                  <RotateCw className="w-5 h-5" />
                  <span>Restart Transcription</span>
                </button>
              )}

              {/* Stop Transcription - Only for processing jobs */}
              {canStop && (
                <button
                  onClick={() => onStop(job.id)}
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-orange-50 text-orange-600 rounded-lg hover:bg-orange-100 transition-colors"
                >
                  <StopCircle className="w-5 h-5" />
                  <span>Stop Transcription</span>
                </button>
              )}

              {/* Delete Job - Disabled for processing jobs */}
              <button
                onClick={() => canDelete && setShowDeleteConfirm(true)}
                disabled={!canDelete}
                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors col-span-2 md:col-span-1 ${
                  canDelete
                    ? 'bg-red-50 text-red-600 hover:bg-red-100'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                <Trash2 className="w-5 h-5" />
                <span>Delete Job</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Job?"
        message="This will permanently delete the job and all associated files. This action cannot be undone."
        confirmText="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </>
  );
};

