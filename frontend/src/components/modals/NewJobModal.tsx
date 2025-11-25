import React, { useState } from 'react';
import { X } from 'lucide-react';
import { FileDropzone } from '../upload/FileDropzone';

interface NewJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (jobData: {
    file: File;
    model: string;
    language: string;
    enableTimestamps: boolean;
    enableSpeakerDetection: boolean;
    speakerCount?: number | null;
  }) => Promise<void>;
  defaultModel?: string;
  defaultLanguage?: string;
}

export const NewJobModal: React.FC<NewJobModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  defaultModel = 'medium',
  defaultLanguage = 'auto'
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [model, setModel] = useState(defaultModel);
  const [language, setLanguage] = useState(defaultLanguage);
  const [enableTimestamps, setEnableTimestamps] = useState(true);
  const [enableSpeakerDetection, setEnableSpeakerDetection] = useState(false);
  const [speakerCount, setSpeakerCount] = useState<number | 'auto'>('auto');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [fileError, setFileError] = useState<string>('');

  if (!isOpen) return null;

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setFileError('');
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    // Validate file size (2GB max)
    const maxSize = 2 * 1024 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setFileError('File size exceeds maximum allowed (2GB)');
      return;
    }

    // Validate file type
    const validTypes = [
      'audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/flac', 'audio/ogg',
      'video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-matroska'
    ];
    if (!validTypes.includes(selectedFile.type) && 
        !selectedFile.name.match(/\.(mp3|wav|m4a|flac|ogg|mp4|avi|mov|mkv)$/i)) {
      setFileError('Invalid file format. Supported formats: mp3, wav, m4a, flac, ogg, mp4, avi, mov, mkv');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await onSubmit({
        file: selectedFile,
        model,
        language,
        enableTimestamps,
        enableSpeakerDetection,
        speakerCount: enableSpeakerDetection
          ? speakerCount === 'auto'
            ? null
            : speakerCount
          : null
      });
      
      // Reset form on success
      setSelectedFile(null);
      setModel(defaultModel);
      setLanguage(defaultLanguage);
      setEnableTimestamps(true);
      setEnableSpeakerDetection(false);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setSelectedFile(null);
      setError('');
      setFileError('');
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" data-testid="new-job-modal">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200" data-testid="new-job-modal-header">
          <h2 className="text-2xl font-semibold text-pine-deep">New Transcription Job</h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close modal"
            className="text-pine-mid hover:text-pine-deep transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6" data-testid="new-job-form">
          {/* File Upload */}
          <div className="mb-6" data-testid="file-input-section">
            <label className="block text-sm font-medium text-pine-deep mb-2">
              Audio/Video File
            </label>
            <FileDropzone
              onFileSelect={handleFileSelect}
              accept="audio/*,video/*"
              maxSize={2 * 1024 * 1024 * 1024}
              selectedFile={selectedFile}
              error={fileError}
            />
          </div>

          {/* Model Selection */}
          <div className="mb-6">
            <label htmlFor="model" className="block text-sm font-medium text-pine-deep mb-2">
              Model
            </label>
            <select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
              data-testid="model-select"
            >
              <option value="tiny">Tiny - Fastest, lowest accuracy (75MB)</option>
              <option value="base">Base - Fast, moderate accuracy (142MB)</option>
              <option value="small">Small - Balanced speed and accuracy (466MB)</option>
              <option value="medium">Medium - High accuracy, slower (1.5GB)</option>
              <option value="large">Large - Highest accuracy, slowest (2.9GB)</option>
            </select>
          </div>

          {/* Language Selection */}
          <div className="mb-6">
            <label htmlFor="language" className="block text-sm font-medium text-pine-deep mb-2">
              Language
            </label>
            <select
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
              data-testid="language-select"
            >
              <option value="auto">Auto-detect</option>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
              <option value="nl">Dutch</option>
              <option value="ru">Russian</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
            </select>
          </div>

          {/* Options */}
          <div className="mb-6 space-y-3">
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={enableTimestamps}
                    onChange={(e) => setEnableTimestamps(e.target.checked)}
                    disabled={isSubmitting}
                    className="w-4 h-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
                    data-testid="timestamps-checkbox"
                  />
                  <span className="ml-2 text-sm text-pine-deep">Include timestamps</span>
                </label>
              </div>

              <div className="flex flex-col gap-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={enableSpeakerDetection}
                    onChange={(e) => setEnableSpeakerDetection(e.target.checked)}
                    disabled={isSubmitting}
                    className="w-4 h-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
                    data-testid="speakers-checkbox"
                  />
                  <span className="ml-2 text-sm text-pine-deep">Detect speakers</span>
                </label>
                {enableSpeakerDetection && (
                  <div className="flex items-center gap-2 text-sm text-pine-deep flex-wrap">
                    <label className="text-sm text-pine-mid">Speakers:</label>
                    <select
                      value={speakerCount}
                      onChange={(e) =>
                        setSpeakerCount(
                          e.target.value === 'auto' ? 'auto' : Number(e.target.value)
                        )
                      }
                      disabled={isSubmitting}
                      className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
                      data-testid="speaker-count-select"
                    >
                      <option value="auto">Auto-detect</option>
                      {[2, 3, 4, 5, 6, 7, 8].map((n) => (
                        <option key={n} value={n}>
                          {n} speakers
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-pine-deep bg-sage-light hover:bg-sage-mid rounded-lg transition-colors disabled:opacity-50"
              data-testid="cancel-new-job-btn"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || isSubmitting}
              className="px-6 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              data-testid="start-transcription-btn"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                'Start Transcription'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
