import React, { useState, useEffect } from 'react';
import { X, Play, FileText, Download, RotateCw, Trash2, ChevronDown, StopCircle } from 'lucide-react';
import { StatusBadge } from '../jobs/StatusBadge';
import { ConfirmDialog } from './ConfirmDialog';
import type { Job } from '../../services/jobs';

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
  onUpdateTags: _onUpdateTags
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
  const canDelete = !['processing'].includes(job.status);
  const canStop = job.status === 'processing';
  const hasMedia = true; // Media always exists if job was created

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

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

  const handleDelete = () => {
    onDelete(job.id);
    setShowDeleteConfirm(false);
    onClose();
  };

  const handleDownloadFormat = (format: string) => {
    onDownload(job.id, format);
    setShowDownloadMenu(false);
  };

  const handleAddTag = (name: string) => {
    if (!name.trim()) return;
    // Avoid duplicates by name
    if (editableTags.some(t => t.name.toLowerCase() === name.toLowerCase())) {
      setTagInputValue('');
      return;
    }
    const newTag = {
      id: Date.now(),
      name,
      color: '#0F3D2E'
    };
    setEditableTags([...editableTags, newTag]);
    setTagInputValue('');
  };

  const handleRemoveTag = (id: number) => {
    setEditableTags(editableTags.filter(t => t.id !== id));
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
                  {formatDuration(job.duration)}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Created</div>
                <div className="text-base font-medium text-pine-deep">
                  {formatDate(job.created_at)}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Model</div>
                <div className="text-base font-medium text-pine-deep">
                  {job.model_used}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Language</div>
                <div className="text-base font-medium text-pine-deep">
                  {job.language_detected}
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">Speakers</div>
                <div className="text-base font-medium text-pine-deep">
                  {job.speaker_count} detected
                </div>
              </div>
              <div>
                <div className="text-sm text-pine-mid">File Size</div>
                <div className="text-base font-medium text-pine-deep">
                  {formatFileSize(job.file_size)}
                </div>
              </div>
            </div>

            {/* Tags Section (view & edit) */}
            <div className="mb-6" data-testid="job-tags">
              <div className="text-sm text-pine-mid mb-2">Tags</div>
              <div className="flex flex-wrap gap-2 mb-3">
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
                  type="text"
                  value={tagInputValue}
                  onChange={(e) => setTagInputValue(e.target.value)}
                  placeholder="Add tag"
                  data-testid="tag-input"
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none text-sm"
                />
                {tagInputValue.trim() && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-sage-mid rounded-lg shadow z-10">
                    <div
                      role="option"
                      data-testid="tag-option"
                      onClick={() => handleAddTag(tagInputValue.trim())}
                      className="px-3 py-2 text-sm cursor-pointer hover:bg-sage-light"
                    >
                      Add “{tagInputValue.trim()}”
                    </div>
                  </div>
                )}
              </div>
            </div>

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
