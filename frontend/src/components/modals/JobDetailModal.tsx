import React, { useState } from 'react';
import { X, Play, FileText, Download, RotateCw, Trash2, ChevronDown } from 'lucide-react';
import { StatusBadge } from '../jobs/StatusBadge';
import { ConfirmDialog } from './ConfirmDialog';

interface Job {
  id: string;
  original_filename: string;
  file_size: number;
  duration: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  model_used: string;
  language_detected: string;
  speaker_count: number;
  tags: Array<{ id: number; name: string; color: string }>;
  created_at: string;
  completed_at: string;
}

interface JobDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: Job;
  onPlay: (jobId: string) => void;
  onDownload: (jobId: string, format: string) => void;
  onRestart: (jobId: string) => void;
  onDelete: (jobId: string) => void;
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
  onUpdateTags
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);

  if (!isOpen) return null;

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

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
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
            <div className="grid grid-cols-2 gap-4 mb-6">
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

            {/* Tags Section */}
            {job.tags.length > 0 && (
              <div className="mb-6">
                <div className="text-sm text-pine-mid mb-2">Tags</div>
                <div className="flex flex-wrap gap-2">
                  {job.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="text-sm px-3 py-1 rounded-full"
                      style={{ backgroundColor: tag.color + '20', color: tag.color }}
                    >
                      #{tag.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <button
                onClick={() => onPlay(job.id)}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
              >
                <Play className="w-5 h-5" />
                <span>Play Media</span>
              </button>

              <button
                onClick={() => window.open(`/jobs/${job.id}/transcript`, '_blank')}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-sage-light text-pine-deep rounded-lg hover:bg-sage-mid transition-colors"
              >
                <FileText className="w-5 h-5" />
                <span>View Transcript</span>
              </button>

              <div className="relative">
                <button
                  onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-sage-light text-pine-deep rounded-lg hover:bg-sage-mid transition-colors"
                >
                  <Download className="w-5 h-5" />
                  <span>Download Transcript</span>
                  <ChevronDown className="w-4 h-4" />
                </button>
                
                {showDownloadMenu && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
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
                onClick={() => onRestart(job.id)}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-sage-light text-pine-deep rounded-lg hover:bg-sage-mid transition-colors"
              >
                <RotateCw className="w-5 h-5" />
                <span>Restart Transcription</span>
              </button>

              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors col-span-2 md:col-span-1"
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
