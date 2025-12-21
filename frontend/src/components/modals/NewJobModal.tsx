import React, { useEffect, useMemo, useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { FileDropzone } from '../upload/FileDropzone';
import { useAdminSettings } from '../../context/SettingsContext';
import { fetchCapabilities, type CapabilityResponse } from '../../services/system';
import { listModelSets, type ModelSetWithWeights } from '../../services/modelRegistry';

type DiarizerWeightOption = {
  key: string;
  display_name: string;
  available: boolean;
  notes: string[];
};

type DiarizerProviderGroup = {
  name: string;
  available: boolean;
  weights: DiarizerWeightOption[];
};

interface NewJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (jobData: {
    file: File;
    provider?: string;
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
  defaultDiarizerProvider?: string;
}

export const NewJobModal: React.FC<NewJobModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  defaultModel,
  defaultLanguage,
  defaultDiarizer,
  defaultDiarizerProvider,
}) => {
  const { settings: adminSettings } = useAdminSettings();
  const allowEmptyWeights = adminSettings?.enable_empty_weights ?? false;

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const resolvedDefaults = useMemo(
    () => ({
      provider: adminSettings?.default_asr_provider ?? '',
      model: adminSettings?.default_model ?? defaultModel ?? '',
      language: adminSettings?.default_language ?? defaultLanguage ?? 'auto',
      diarizerProvider: adminSettings?.default_diarizer_provider ?? defaultDiarizerProvider ?? '',
      diarizer: adminSettings?.default_diarizer ?? defaultDiarizer ?? '',
      timestamps: true,
    }),
    [adminSettings, defaultModel, defaultLanguage, defaultDiarizer, defaultDiarizerProvider]
  );

  const [model, setModel] = useState(resolvedDefaults.model);
  const [language, setLanguage] = useState(resolvedDefaults.language);
  const [enableTimestamps, setEnableTimestamps] = useState(resolvedDefaults.timestamps);
  const [enableSpeakerDetection, setEnableSpeakerDetection] = useState(true);
  const [speakerCount, setSpeakerCount] = useState<number | 'auto'>('auto');
  const [diarizer, setDiarizer] = useState(resolvedDefaults.diarizer);
  const [diarizerProvider, setDiarizerProvider] = useState(resolvedDefaults.diarizerProvider);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [fileError, setFileError] = useState<string>('');
  const [capabilities, setCapabilities] = useState<CapabilityResponse | null>(null);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);
  const [registrySets, setRegistrySets] = useState<ModelSetWithWeights[]>([]);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [isInitialized, setIsInitialized] = useState(false);

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
    const loadRegistry = async () => {
      try {
        const data = await listModelSets();
        if (cancelled) return;
        setRegistrySets(data);
        setRegistryError(null);
      } catch (err) {
        if (cancelled) return;
        setRegistryError(err instanceof Error ? err.message : 'Unable to load model registry');
      } finally {
        if (!cancelled) {
          setRegistryLoading(false);
        }
      }
    };
    loadCapabilities();
    loadRegistry();
    return () => {
      cancelled = true;
    };
  }, []);

  const diarizerCapabilities = useMemo(() => capabilities?.diarizers ?? [], [capabilities]);
  const diarizerCapabilityMap = useMemo(() => {
    const map = new Map<string, CapabilityResponse['diarizers'][number]>();
    diarizerCapabilities.forEach((option) => map.set(option.key, option));
    return map;
  }, [diarizerCapabilities]);
  const registryDiarizerSets = useMemo(
    () => registrySets.filter((set) => set.type === 'diarizer'),
    [registrySets]
  );
  const diarizerProviderGroups = useMemo<DiarizerProviderGroup[]>(() => {
    return registryDiarizerSets.map((set) => {
      const weights = set.weights.map((weight) => {
        const capability = diarizerCapabilityMap.get(weight.name);
        const hasWeights = (weight.has_weights ?? false) || allowEmptyWeights;
        const available =
          Boolean(set.enabled && weight.enabled && hasWeights) &&
          (capability ? capability.available : true);
        return {
          key: weight.name,
          display_name: capability?.display_name ?? weight.name,
          available,
          notes: capability?.notes ?? [],
        } as DiarizerWeightOption;
      });
      return {
        name: set.name,
        available: weights.some((weight) => weight.available),
        weights,
      };
    });
  }, [registryDiarizerSets, diarizerCapabilityMap, allowEmptyWeights]);
  const diarizerWeightsForProvider = useMemo<DiarizerWeightOption[]>(() => {
    if (!diarizerProvider) return [];
    return diarizerProviderGroups.find((group) => group.name === diarizerProvider)?.weights ?? [];
  }, [diarizerProvider, diarizerProviderGroups]);
  const availableDiarizerWeights = useMemo(
    () => diarizerProviderGroups.flatMap((group) => group.weights.filter((weight) => weight.available)),
    [diarizerProviderGroups]
  );
  const supportsDiarization = availableDiarizerWeights.length > 0;
  const detectSpeakersDisabled = capabilitiesLoading || !supportsDiarization;

  const asrProviders = useMemo(() => registrySets.filter((set) => set.type === 'asr'), [registrySets]);
  const providerOptions = useMemo(
    () =>
      asrProviders.map((set) => {
        const enabledWeights = set.weights.filter(
          (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
        );
        const hasWeights = set.weights.some(
          (weight) => (weight.has_weights ?? false) || allowEmptyWeights
        );
        const isUsable = set.enabled && enabledWeights.length > 0;
        let label = set.name;
        if (!set.enabled) {
          label = `${set.name} (disabled)`;
        } else if (!hasWeights) {
          label = `${set.name} (missing weights)`;
        } else if (!enabledWeights.length) {
          label = `${set.name} (weights disabled)`;
        }
        return {
          value: set.name,
          label,
          enabled: set.enabled,
          weights: set.weights,
          hasWeights,
          hasEnabledWeights: enabledWeights.length > 0,
          isUsable,
        };
      }),
    [asrProviders, allowEmptyWeights]
  );
  const activeProvider = providerOptions.find((p) => p.value === selectedProvider);
  const weightOptions = useMemo(() => {
    if (!activeProvider) return [];
    return activeProvider.weights.map((weight) => {
      const hasWeights = Boolean(weight.has_weights) || allowEmptyWeights;
      const effectiveEnabled = Boolean(activeProvider.isUsable && weight.enabled && hasWeights);
      let label = weight.name;
      if (!weight.enabled) {
        label = `${weight.name} (disabled)`;
      } else if (!hasWeights) {
        label = `${weight.name} (missing files)`;
      }
      return {
        value: weight.name,
        label,
        enabled: effectiveEnabled,
        hasWeights,
        isUsable: effectiveEnabled,
      };
    });
  }, [activeProvider, allowEmptyWeights]);
  const selectedWeightOption = weightOptions.find((opt) => opt.value === model);
  const providerReady = Boolean(activeProvider?.isUsable);
  const weightReady = Boolean(selectedWeightOption?.isUsable);
  const hasEnabledAsrModels = providerReady && weightOptions.some((opt) => opt.isUsable);
  const canSubmit = Boolean(selectedFile && providerReady && weightReady && !isSubmitting);

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
      setIsInitialized(false);
      return;
    }
    if (!providerOptions.length) {
      setSelectedProvider('');
      setModel('');
      return;
    }
    if (isInitialized) {
      return;
    }

    const providerFromSettings = resolvedDefaults.provider
      ? providerOptions.find((p) => p.value === resolvedDefaults.provider && p.isUsable)?.value
      : '';
    const providerFromModel = resolvedDefaults.model
      ? providerOptions.find(
          (p) => p.isUsable && p.weights.some((weight) => weight.name === resolvedDefaults.model)
        )?.value
      : '';
    const fallbackProvider =
      providerOptions.find((p) => p.isUsable)?.value || providerOptions[0]?.value || '';
    const nextProvider = providerFromSettings || providerFromModel || fallbackProvider || '';
    setSelectedProvider(nextProvider);

    const weightsForProvider =
      providerOptions.find((p) => p.value === nextProvider)?.weights ?? [];
    const preferredWeight = resolvedDefaults.model
      ? weightsForProvider.find(
          (weight) =>
            weight.name === resolvedDefaults.model &&
            weight.enabled &&
            ((weight.has_weights ?? false) || allowEmptyWeights)
        )
      : undefined;
    const firstEnabledWeight = weightsForProvider.find(
      (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
    );
    const fallbackWeight =
      weightsForProvider.find(
        (weight) => (weight.has_weights ?? false) || allowEmptyWeights
      ) || weightsForProvider[0];
    const resolvedModelName = preferredWeight?.name || firstEnabledWeight?.name || fallbackWeight?.name || '';
    setModel(resolvedModelName || '');
    setLanguage(resolvedDefaults.language);
    setEnableTimestamps(resolvedDefaults.timestamps);
    let inferredDiarizerProvider = '';
    if (resolvedDefaults.diarizerProvider) {
      const match = diarizerProviderGroups.find((group) => group.name === resolvedDefaults.diarizerProvider);
      if (match) {
        inferredDiarizerProvider = match.name;
      }
    }
    if (!inferredDiarizerProvider && diarizerProviderGroups.length) {
      inferredDiarizerProvider = diarizerProviderGroups[0].name;
    }
    setDiarizerProvider(inferredDiarizerProvider);
    const weightsForSelectedProvider =
      diarizerProviderGroups.find((group) => group.name === inferredDiarizerProvider)?.weights ?? [];
    const preferredDiarizerWeight = resolvedDefaults.diarizer
      ? weightsForSelectedProvider.find((weight) => weight.key === resolvedDefaults.diarizer)
      : undefined;
    const fallbackDiarizerWeight =
      weightsForSelectedProvider.find((weight) => weight.available) || weightsForSelectedProvider[0];
    setDiarizer(preferredDiarizerWeight?.key ?? fallbackDiarizerWeight?.key ?? '');
    setEnableSpeakerDetection(supportsDiarization);
    setSpeakerCount('auto');
    setIsInitialized(true);
  }, [isOpen, resolvedDefaults, diarizerProviderGroups, supportsDiarization, providerOptions, isInitialized]);

  useEffect(() => {
    if (!enableSpeakerDetection) {
      setSpeakerCount('auto');
    }
  }, [enableSpeakerDetection]);

  useEffect(() => {
    if (!diarizerProviderGroups.length) {
      if (diarizerProvider) {
        setDiarizerProvider('');
      }
      if (diarizer) {
        setDiarizer('');
      }
      return;
    }
    if (!diarizerProvider) {
      setDiarizerProvider(diarizerProviderGroups[0].name);
      return;
    }
    if (!diarizerProviderGroups.find((group) => group.name === diarizerProvider)) {
      setDiarizerProvider(diarizerProviderGroups[0].name);
      return;
    }
    if (!diarizerWeightsForProvider.length) {
      if (diarizer) {
        setDiarizer('');
      }
      return;
    }
    if (!diarizerWeightsForProvider.some((weight) => weight.key === diarizer)) {
      const fallback =
        diarizerWeightsForProvider.find((weight) => weight.available) ||
        diarizerWeightsForProvider[0];
      setDiarizer(fallback?.key ?? '');
    }
  }, [diarizerProviderGroups, diarizerProvider, diarizerWeightsForProvider, diarizer]);

  if (!isOpen) return null;

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setFileError('');
    setError('');
  };

  const handleProviderChange = (value: string) => {
    setSelectedProvider(value);
    const weightsForProvider =
      providerOptions.find((p) => p.value === value)?.weights ?? [];
    const firstEnabled = weightsForProvider.find(
      (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
    );
    const firstWithFiles = weightsForProvider.find(
      (weight) => (weight.has_weights ?? false) || allowEmptyWeights
    );
    const firstAny = weightsForProvider[0];
    setModel(firstEnabled?.name || firstWithFiles?.name || firstAny?.name || '');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

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

    const selectedWeight = weightOptions.find((opt) => opt.value === model);

    if (!selectedProvider) {
      setError('Select a model set before starting a job.');
      return;
    }
    if (!providerReady) {
      setError('Selected model set is unavailable. Choose an enabled set.');
      return;
    }
    if (!hasEnabledAsrModels) {
      setError('No ASR weights available. Contact admin to register a weight.');
      return;
    }
    if (!selectedWeight) {
      setError('Select a model weight before starting a job.');
      return;
    }
    if (!selectedWeight.isUsable) {
      setError('Selected model weight is unavailable. Choose an enabled weight.');
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
        provider: selectedProvider,
        model: modelOverride,
        language: languageOverride,
        enableTimestamps,
        enableSpeakerDetection: diarizationActive,
        diarizer: diarizationActive ? diarizerOverride : undefined,
        speakerCount: diarizationActive && speakerCount !== 'auto' ? speakerCount : null,
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

          <div className="mb-6 space-y-3">
            <label
              htmlFor="provider"
              className="block text-sm font-medium text-pine-deep mb-2"
            >
              ASR Model
            </label>
            <select
              id="provider"
              value={selectedProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              disabled={isSubmitting || registryLoading || !providerOptions.length}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
              data-testid="provider-select"
            >
              {!providerOptions.length && <option value="">No providers registered</option>}
              {providerOptions.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={!opt.isUsable}>
                  {opt.label}
                </option>
              ))}
            </select>
            <label
              htmlFor="model"
              className="block text-sm font-medium text-pine-deep mb-2"
            >
              ASR Model Weight
            </label>
            <select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={
                isSubmitting ||
                !selectedProvider ||
                registryLoading ||
                !providerReady ||
                !weightOptions.length
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
              data-testid="model-select"
            >
            {!weightOptions.length && <option value="">No model weights registered</option>}
            {weightOptions.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={!opt.isUsable}>
                  {opt.label}
                </option>
              ))}
            </select>
            {!providerReady && selectedProvider && (
              <p className="text-xs text-terracotta mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Selected ASR model set is unavailable.
                Enable the set and add weights.
              </p>
            )}
            {!weightOptions.length && providerReady && (
              <p className="text-xs text-terracotta mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Contact admin to register a model weight.
              </p>
            )}
            {registryError && (
              <p className="text-xs text-terracotta mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> {registryError}
              </p>
            )}
            {providerReady && selectedWeightOption && !weightReady && (
              <p className="text-xs text-terracotta mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Selected weight cannot be used. Choose an enabled weight with
                files.
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
                      <label className="text-sm text-pine-mid">Diarizer set</label>
                      <select
                        value={diarizerProvider}
                        onChange={(e) => setDiarizerProvider(e.target.value)}
                        disabled={detectSpeakersDisabled || !diarizerProviderGroups.length}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
                        data-testid="diarizer-provider-select"
                      >
                        {!diarizerProviderGroups.length && <option value="">No diarizers registered</option>}
                        {diarizerProviderGroups.map((group) => (
                          <option key={group.name} value={group.name}>
                            {group.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex flex-col gap-2 text-sm text-pine-deep">
                      <label className="text-sm text-pine-mid">Diarizer weight</label>
                      <select
                        value={diarizer}
                        onChange={(e) => setDiarizer(e.target.value)}
                        disabled={detectSpeakersDisabled || !diarizerWeightsForProvider.length}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-forest-green focus:border-transparent disabled:bg-gray-100"
                        data-testid="diarizer-select"
                      >
                        {!diarizerWeightsForProvider.length && (
                          <option value="">No weights in this set</option>
                        )}
                        {diarizerWeightsForProvider.map((option) => (
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
            {!availableDiarizerWeights.find((option) => option.key === diarizer) && diarizer && (
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
              disabled={!canSubmit}
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
