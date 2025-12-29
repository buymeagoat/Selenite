import React, { useState, useEffect, useMemo } from 'react';
import { X, Play, FileText, Download, RotateCw, Trash2, ChevronDown, StopCircle, Pencil } from 'lucide-react';
import { StatusBadge } from '../jobs/StatusBadge';
import { ConfirmDialog } from './ConfirmDialog';
import type { Job } from '../../services/jobs';
import { createTag, type Tag } from '../../services/tags';
import { TagInput } from '../tags/TagInput';
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
  onRename: (jobId: string, name: string) => Promise<void> | void;
  onViewTranscript: (jobId: string) => void;
  onUpdateTags: (jobId: string, tagIds: number[]) => void;
  availableTags?: Tag[];
  timeZone?: string | null;
  asrProviderHint?: string | null;
  defaultDiarizerHint?: string | null;
}

type TagOption = {
  id: number;
  name: string;
  color: string | null;
};

const mergeTags = (...groups: TagOption[][]) => {
  const map = new Map<number, TagOption>();
  groups.flat().forEach((tag) => map.set(tag.id, tag));
  return Array.from(map.values());
};

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  isOpen,
  onClose,
  job,
  onPlay,
  onDownload,
  onRestart,
  onDelete,
  onStop,
  onRename,
  onViewTranscript,
  onUpdateTags,
  availableTags,
  timeZone = null,
  asrProviderHint = null,
  defaultDiarizerHint = null,
}) => {
  const resolvedAvailableTags = useMemo(() => availableTags ?? [], [availableTags]);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [renameError, setRenameError] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  const [editableTags, setEditableTags] = useState<TagOption[]>(job.tags);
  const [tagCatalog, setTagCatalog] = useState<TagOption[]>(() => mergeTags(job.tags, resolvedAvailableTags));

  const stripExtension = (name: string) => name.replace(/\.[^/.]+$/, '');

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    // keep local tags in sync when a different job is opened
    setEditableTags(job.tags);
    setTagCatalog((prev) => mergeTags(prev, job.tags, resolvedAvailableTags));
    setRenameValue(stripExtension(job.original_filename));
    setRenameError('');
    setShowRenameModal(false);
    setIsRenaming(false);
  }, [isOpen, job, resolvedAvailableTags]);

  if (!isOpen) return null;

  // UI Logic: Determine what actions are available based on job status
  const hasTranscript = job.status === 'completed';
const canRestart = ['completed', 'failed', 'cancelled'].includes(job.status);
const canDelete = !['processing', 'cancelling'].includes(job.status);
const canRename = !['processing', 'cancelling'].includes(job.status);
const canStop = job.status === 'processing' || job.status === 'queued';
  const hasMedia = true; // Media always exists if job was created
  const canPlayMedia = hasMedia && job.status !== 'processing';
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
    if (!job.diarizer_used) {
      if (defaultDiarizerHint) return `${defaultDiarizerHint} (failed)`;
      return 'None';
    }
    const weight = job.diarizer_used;
    return job.diarizer_provider_used ? `${job.diarizer_provider_used} / ${weight}` : weight;
  })();

  const speakerDetected =
    job.speaker_count ?? (job.status === 'completed' ? 1 : 'Pending');
  const speakerSummary = `Requested: ${job.has_speaker_labels ? 'Yes' : 'No'} | Detected: ${speakerDetected}`;
  const jobExtension = job.original_filename.includes('.')
    ? job.original_filename.slice(job.original_filename.lastIndexOf('.'))
    : '';

  const handleDelete = () => {
    onDelete(job.id);
    setShowDeleteConfirm(false);
    onClose();
  };

  const handleDownloadFormat = (format: string) => {
    onDownload(job.id, format);
    setShowDownloadMenu(false);
  };

  const handleRenameSubmit = async () => {
    const trimmed = renameValue.trim();
    if (!trimmed) {
      setRenameError('Enter a job name.');
      return;
    }
    if (!canRename) {
      setRenameError('Active jobs cannot be renamed.');
      return;
    }
    setIsRenaming(true);
    setRenameError('');
    try {
      await onRename(job.id, trimmed);
      setShowRenameModal(false);
    } catch (error) {
      devError('Rename failed', error);
      setRenameError('Failed to rename job. Please try again.');
    } finally {
      setIsRenaming(false);
    }
  };

  const handleCreateTag = async (name: string, color: string) => {
    const trimmed = name.trim();
    if (!trimmed) {
      throw new Error('Tag name required');
    }
    const existing = tagCatalog.find((tag) => tag.name.toLowerCase() === trimmed.toLowerCase());
    if (existing) {
      return existing;
    }
    try {
      const created = await createTag({ name: trimmed, color });
      setTagCatalog((prev) => mergeTags(prev, [created]));
      return created;
    } catch (err) {
      devError('Failed to create tag', err);
      throw err;
    }
  };

  const handleTagIdsChange = (tagIds: number[]) => {
    const tagMap = new Map<number, TagOption>();
    [...tagCatalog, ...editableTags].forEach((tag) => tagMap.set(tag.id, tag));
    const nextTags = tagIds.map((id) => tagMap.get(id)).filter(Boolean) as TagOption[];
    setEditableTags(nextTags);
    onUpdateTags(job.id, tagIds);
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
                <div className="text-sm text-pine-mid">Job ID</div>
                <div className="text-base font-medium text-pine-deep">
                  {job.id}
                </div>
              </div>
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
                <div className="text-sm text-pine-mid">ASR model / weight</div>
                <div className="text-base font-medium text-pine-deep">
                  {(job.asr_provider_used || asrProviderHint || 'Unknown') + ' / ' + (job.model_used || 'Unknown')}
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
              {editableTags.length === 0 && (
                <div className="text-xs text-pine-mid mb-2">No tags</div>
              )}
              <div className="max-w-md" data-testid="job-tags">
                <TagInput
                  availableTags={tagCatalog}
                  selectedTags={editableTags.map((tag) => tag.id)}
                  selectedTagOptions={editableTags}
                  selectedTagsPosition="above"
                  onChange={handleTagIdsChange}
                  onCreate={handleCreateTag}
                  placeholder="Add tag"
                />
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
                onClick={() => canPlayMedia && onPlay(job.id)}
                disabled={!canPlayMedia}
                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                  canPlayMedia
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

              <button
                onClick={() => canRename && setShowRenameModal(true)}
                disabled={!canRename}
                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                  canRename
                    ? 'bg-sage-light text-pine-deep hover:bg-sage-mid'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                <Pencil className="w-5 h-5" />
                <span>Rename Job</span>
              </button>

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

      {showRenameModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="bg-white rounded-lg shadow-lg w-full max-w-md p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="rename-job-title"
          >
            <h2 id="rename-job-title" className="text-lg font-semibold text-pine-deep mb-4">
              Rename job
            </h2>
            <label className="text-sm text-pine-deep mb-2 block" htmlFor="rename-job-input">
              New name
            </label>
            <input
              id="rename-job-input"
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
              value={renameValue}
              onChange={(event) => {
                setRenameValue(event.target.value);
                if (renameError) {
                  setRenameError('');
                }
              }}
              placeholder="Enter a name"
            />
            <p className="text-xs text-pine-mid mt-2">
              File extension {jobExtension || '(.ext)'} stays the same.
            </p>
            {!canRename && (
              <p className="text-xs text-amber-700 mt-2">
                Active jobs cannot be renamed while processing.
              </p>
            )}
            {renameError && <p className="text-sm text-red-600 mt-2">{renameError}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
                onClick={() => setShowRenameModal(false)}
                disabled={isRenaming}
              >
                Cancel
              </button>
              <button
                className="px-3 py-2 text-sm bg-forest-green text-white rounded hover:bg-pine-deep disabled:opacity-50"
                onClick={handleRenameSubmit}
                disabled={!canRename || isRenaming}
              >
                {isRenaming ? 'Renaming...' : 'Rename'}
              </button>
            </div>
          </div>
        </div>
      )}

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

