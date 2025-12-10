import React, { useEffect, useMemo, useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { FileDropzone } from '../upload/FileDropzone';
import { useAdminSettings } from '../../context/SettingsContext';
import { fetchCapabilities, type CapabilityResponse } from '../../services/system';

interface NewJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (jobData: {
    file: File;
    model?: string;
    language?: string;
    enableTimestamps: boolean;
    enableSpeakerDetection: boolean;
    diarizer?: string | null;
    speakerCount?: number | null;
  }) => Promise<void>;
  defaultModel?: string;
  defaultLanguage?: string;
  defaultDiarizer?: string;
}

export const NewJobModal: React.FC<NewJobModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  defaultModel,
  defaultLanguage,
  defaultDiarizer,
}) => {
  const { settings: adminSettings } = useAdminSettings();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const resolvedDefaults = useMemo(
    () => ({
      model: adminSettings?.default_model ?? defaultModel ?? '',
      language: adminSettings?.default_language ?? defaultLanguage ?? 'auto',
      diarizer: adminSettings?.default_diarizer ?? defaultDiarizer ?? '',
      timestamps: true,
    }),
    [adminSettings, defaultModel, defaultLanguage, defaultDiarizer]
  );

  const [model, setModel] = useState(resolvedDefaults.model);
  const [language, setLanguage] = useState(resolvedDefaults.language);
  const [enableTimestamps, setEnableTimestamps] = useState(resolvedDefaults.timestamps);
  const [enableSpeakerDetection, setEnableSpeakerDetection] = useState(true);
  const [speakerCount, setSpeakerCount] = useState<number | 'auto'>('auto');
  const [diarizer, setDiarizer] = useState(resolvedDefaults.diarizer);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [fileError, setFileError] = useState<string>('');
  const [capabilities, setCapabilities] = useState<CapabilityResponse | null>(null);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadCapabilities = async () => {
      try {
        const data = await fetchCapabilities();
        if (cancelled) return;
        setCapabilities(data);
        setCapabilitiesError(null);
      } catch (err) {
        if (cancelled) return;
        setCapabilitiesError(
          err instanceof Error ? err.message : 'Unable to load diarization capabilities'
        );
      } finally {
        if (!cancelled) {
          setCapabilitiesLoading(false);
        }
      }
    };
    loadCapabilities();
    return () => {
      cancelled = true;
    };
  }, []);

  const diarizerOptions = useMemo(() => capabilities?.diarizers ?? [], [capabilities]);
  const availableDiarizers = diarizerOptions.filter((option) => option.available);
  const supportsDiarization = availableDiarizers.length > 0;
  const detectSpeakersDisabled = capabilitiesLoading || !supportsDiarization;

  const asrModelOptions = useMemo(() => {
    if (!capabilities?.asr?.length) return [];
    return capabilities.asr.flatMap((provider) =>
      provider.models.map((model) => ({
        value: model,
        label: `${model} (${provider.provider})`,
      }))
    );
  }, [capabilities]);

  const hasAsrModels = asrModelOptions.length > 0;

  const detectSpeakersHelpText = useMemo(() => {
    if (capabilitiesLoading) {
      return 'Checking diarization availability...';
    }
    if (capabilitiesError) {
      return 'Unable to verify diarization availability; using safe defaults.';
    }
    if (!supportsDiarization) {
      return 'No compatible diarization models are available on this system.';
    }
    return undefined;
  }, [capabilitiesLoading, capabilitiesError, supportsDiarization]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const availableModelValues = asrModelOptions.map((opt) => opt.value);
    const resolvedModel = availableModelValues.includes(resolvedDefaults.model)
      ? resolvedDefaults.model
      : availableModelValues[0] ?? '';
    setModel(hasAsrModels ? resolvedModel : '');
    setLanguage(resolvedDefaults.language);
    setEnableTimestamps(resolvedDefaults.timestamps);
    const preferred = resolvedDefaults.diarizer;
    const preferredAvailable = diarizerOptions.find(
      (option) => option.key === preferred && option.available
    );
    const fallbackAvailable = diarizerOptions.find((option) => option.available);
    const fallbackAny = diarizerOptions[0];
    setDiarizer(preferredAvailable?.key ?? fallbackAvailable?.key ?? fallbackAny?.key ?? preferred);
    setEnableSpeakerDetection(supportsDiarization);
    setSpeakerCount('auto');
  }, [isOpen, resolvedDefaults, diarizerOptions, supportsDiarization, hasAsrModels, asrModelOptions]);

  useEffect(() => {
    if (!enableSpeakerDetection) {
      setSpeakerCount('auto');
    }
  }, [enableSpeakerDetection]);

  if (!isOpen) return null;

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setFileError('');
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!hasAsrModels) {
      setError('No ASR models available. Contact admin to register a model.');
      return;
    }

    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    const maxSize = 2 * 1024 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setFileError('File size exceeds maximum allowed (2GB)');
      return;
    }

    const validTypes = [
      'audio/mpeg',
      'audio/wav',
      'audio/x-m4a',
      'audio/flac',
      'audio/ogg',
      'video/mp4',
      'video/x-msvideo',
      'video/quicktime',
      'video/x-matroska',
    ];
    if (
      !validTypes.includes(selectedFile.type) &&
      !selectedFile.name.match(/\.(mp3|wav|m4a|flac|ogg|mp4|avi|mov|mkv)$/i)
    ) {
      setFileError(
        'Invalid file format. Supported formats: mp3, wav, m4a, flac, ogg, mp4, avi, mov, mkv'
      );
      return;
    }

    setIsSubmitting(true);
    setError('');

    const diarizationActive = enableSpeakerDetection && supportsDiarization;

    // Only send model/language/diarizer if they differ from saved defaults
    // This allows backend to use user's saved preferences unless explicitly overridden
    const modelOverride = model !== resolvedDefaults.model ? model : undefined;
    const languageOverride = language !== resolvedDefaults.language ? language : undefined;
    const diarizerOverride = diarizer !== resolvedDefaults.diarizer ? diarizer : undefined;

    try {
      await onSubmit({
        file: selectedFile,
        model: modelOverride,
        language: languageOverride,
        enableTimestamps,
        enableSpeakerDetection: diarizationActive,
        diarizer: diarizationActive ? diarizerOverride : undefined,
        speakerCount:
          diarizationActive && speakerCount !== 'auto' ? speakerCount : null,
      });

      setSelectedFile(null);
      setModel(resolvedDefaults.model);
      setLanguage(resolvedDefaults.language);
      setEnableTimestamps(resolvedDefaults.timestamps);
      setEnableSpeakerDetection(supportsDiarization);
      setSpeakerCount('auto');
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Upload failed. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setSelectedFile(null);
      setError('');
      setFileError('');
      setEnableSpeakerDetection(supportsDiarization);
      setSpeakerCount('auto');
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      data-testid="new-job-modal"
    >
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={handleClose}
      />

      <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div
          className="flex items-center justify-between p-6 border-b border-gray-200"
          data-testid="new-job-modal-header"
        >
          <h2 className="text-2xl font-semibold text-pine-deep">
            New Transcription Job
          </h2>
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

        <form onSubmit={handleSubmit} className="p-6" data-testid="new-job-form">
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

          <div className="mb-6">
            <label
              htmlFor="model"
              className="block text-sm font-medium text-pine-deep mb-2"
            >
              Model
            </label>
            <select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={isSubmitting || !hasAsrModels}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
              data-testid="model-select"
            >
              {!hasAsrModels && <option value="">No models registered</option>}
              {asrModelOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {!hasAsrModels && (
              <p className="text-xs text-terracotta mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Contact admin to register a model.
              </p>
            )}
          </div>

          <div className="mb-6">
            <label
              htmlFor="language"
              className="block text-sm font-medium text-pine-deep mb-2"
            >
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
                  <span className="ml-2 text-sm text-pine-deep">
                    Include timestamps
                  </span>
                </label>
              </div>

              <div className="flex flex-col gap-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={enableSpeakerDetection && supportsDiarization}
                    onChange={(e) => setEnableSpeakerDetection(e.target.checked)}
                    disabled={detectSpeakersDisabled}
                    className="w-4 h-4 text-forest-green border-gray-300 rounded focus:ring-forest-green disabled:opacity-50"
                    data-testid="speakers-checkbox"
                  />
                  <span className="ml-2 text-sm text-pine-deep">Detect speakers</span>
                </label>
                {detectSpeakersHelpText && (
                  <p className="text-xs text-pine-mid pl-6">{detectSpeakersHelpText}</p>
                )}
                {enableSpeakerDetection && supportsDiarization && (
                  <>
                    <div className="flex flex-col gap-2 text-sm text-pine-deep">
                      <label className="text-sm text-pine-mid">Speaker labeling method</label>
                      <select
                        value={diarizer}
                        onChange={(e) => setDiarizer(e.target.value)}
                        disabled={detectSpeakersDisabled}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
                        data-testid="diarizer-select"
                      >
                        {diarizerOptions.map((option) => (
                          <option key={option.key} value={option.key} disabled={!option.available}>
                            {option.display_name}
                            {!option.available && option.notes.length
                              ? ` (${option.notes.join(', ')})`
                              : !option.available
                                ? ' (unavailable)'
                                : ''}
                          </option>
                        ))}
                      </select>
                      {!availableDiarizers.find((option) => option.key === diarizer) && (
                        <p className="text-xs text-terracotta">
                          Selected diarization model is unavailable; choose another option.
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-pine-deep flex-wrap">
                      <label className="text-sm text-pine-mid">Speakers:</label>
                      <select
                        value={speakerCount}
                        onChange={(e) =>
                          setSpeakerCount(
                            e.target.value === 'auto' ? 'auto' : Number(e.target.value)
                          )
                        }
                        disabled={detectSpeakersDisabled}
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
                  </>
                )}
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

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
              disabled={!selectedFile || isSubmitting || !hasAsrModels}
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
