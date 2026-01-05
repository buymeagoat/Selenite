import React, { useState, useEffect } from 'react';
import { TagList } from '../components/tags/TagList';
import { Settings as SettingsIcon, ChevronDown, ChevronUp } from 'lucide-react';
import { apiPut, ApiError } from '../lib/api';
import { fetchSettings, updateSettings } from '../services/settings';
import { createTag, fetchTags, deleteTag, type Tag } from '../services/tags';
import { listModelSets, type ModelSetWithWeights } from '../services/modelRegistry';
import { useToast } from '../context/ToastContext';
import { devError, devInfo } from '../lib/debug';
import { getSupportedTimeZones, getBrowserTimeZone } from '../utils/timezones';
import { useAuth } from '../context/AuthContext';
import { TAG_COLOR_PALETTE, pickTagColor } from '../components/tags/tagColors';

export const Settings: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const { showError, showSuccess } = useToast();
  const isAdmin = Boolean(user?.is_admin);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [defaultProvider, setDefaultProvider] = useState('');
  const [defaultModel, setDefaultModel] = useState('');
  const [defaultLanguage, setDefaultLanguage] = useState('auto');
  const [defaultDiarizer, setDefaultDiarizer] = useState('vad');
  const [defaultDiarizerProvider, setDefaultDiarizerProvider] = useState('');
  const [enableTimestamps, setEnableTimestamps] = useState(true);
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [allowAsrOverrides, setAllowAsrOverrides] = useState(false);
  const [allowDiarizerOverrides, setAllowDiarizerOverrides] = useState(false);
  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3);
  const [timeZone, setTimeZone] = useState<string>(getBrowserTimeZone());
  const [allowEmptyWeights, setAllowEmptyWeights] = useState(false);
  const [registrySets, setRegistrySets] = useState<ModelSetWithWeights[]>([]);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [initialAsrProvider, setInitialAsrProvider] = useState<string | null>(null);
  const [initialAsrModel, setInitialAsrModel] = useState<string>('');
  const [initialDiarizerProvider, setInitialDiarizerProvider] = useState<string | null>(null);
  const [initialDiarizer, setInitialDiarizer] = useState<string>('');
  const [hasUserChangedDefaults, setHasUserChangedDefaults] = useState(false);
  const [hasUserChangedDiarizerDefaults, setHasUserChangedDiarizerDefaults] = useState(false);
  const [tagsExpanded, setTagsExpanded] = useState(true);
  const [globalTags, setGlobalTags] = useState<Tag[]>([]);
  const [personalTags, setPersonalTags] = useState<Tag[]>([]);
  const [tagsLoaded, setTagsLoaded] = useState(false);
  const [newPersonalTag, setNewPersonalTag] = useState('');
  const [newPersonalTagColor, setNewPersonalTagColor] = useState<string>(TAG_COLOR_PALETTE[0]);
  const [isCreatingPersonalTag, setIsCreatingPersonalTag] = useState(false);
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const broadcastSettingsUpdated = () => {
    window.dispatchEvent(new CustomEvent('selenite:settings-updated'));
  };

  const [passwordMessage, setPasswordMessage] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');
  const timeZoneOptions = getSupportedTimeZones();
  const browserTimeZone = getBrowserTimeZone();
  const canEditAsrDefaults = isAdmin || allowAsrOverrides;
  const canEditDiarizerDefaults = isAdmin || allowDiarizerOverrides;

  // Load settings and tags on mount
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      let allowRegistryFetch = false;
      try {
        const settingsData = await fetchSettings();
        
        if (!isMounted) {
          return;
        }
        setInitialAsrProvider(settingsData.default_asr_provider);
        setInitialAsrModel(settingsData.default_model);
        setDefaultProvider(settingsData.default_asr_provider ?? '');
        setDefaultModel(settingsData.default_model ?? '');
        setDefaultLanguage(settingsData.default_language);
        setDefaultDiarizerProvider(settingsData.default_diarizer_provider ?? '');
        setDefaultDiarizer(settingsData.default_diarizer);
        setInitialDiarizerProvider(settingsData.default_diarizer_provider);
        setInitialDiarizer(settingsData.default_diarizer);
        setDiarizationEnabled(settingsData.diarization_enabled);
        setAllowAsrOverrides(settingsData.allow_asr_overrides);
        setAllowDiarizerOverrides(settingsData.allow_diarizer_overrides);
        setEnableTimestamps(settingsData.enable_timestamps);
        setMaxConcurrentJobs(settingsData.max_concurrent_jobs);
        setTimeZone(settingsData.time_zone || getBrowserTimeZone());
        setAllowEmptyWeights(settingsData.enable_empty_weights);
        allowRegistryFetch =
          isAdmin || settingsData.allow_asr_overrides || settingsData.allow_diarizer_overrides;
      } catch (error) {
        devError('Failed to load settings:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load settings: ${error.message}`);
        } else {
          showError('Failed to load settings. Please refresh the page.');
        }
        allowRegistryFetch = false;
      } finally {
        if (isMounted) {
          setIsLoadingSettings(false);
        }
      }

      try {
        const [globalTagResponse, personalTagResponse] = await Promise.all([
          fetchTags({ scope: 'global' }),
          fetchTags({ scope: 'personal' }),
        ]);
        if (!isMounted) {
          return;
        }
        setGlobalTags(globalTagResponse.items);
        setPersonalTags(personalTagResponse.items);
        setTagsLoaded(true);
      } catch (error) {
        devError('Failed to load tags:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load tags: ${error.message}`);
        } else {
          showError('Failed to load tags. Please refresh the page.');
        }
      } finally {
        if (isMounted) {
          setTagsLoaded(true);
        }
      }

      if (!allowRegistryFetch) {
        if (isMounted) {
          setRegistrySets([]);
          setRegistryError(null);
          setRegistryLoading(false);
        }
        return;
      }
      try {
        const registryData = await listModelSets();
        if (!isMounted) {
          return;
        }
        setRegistrySets(registryData);
        setRegistryError(null);
      } catch (error) {
        devError('Failed to load model registry:', error);
        setRegistryError('Failed to load model registry.');
      } finally {
        if (isMounted) {
          setRegistryLoading(false);
        }
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [showError, isAdmin]);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMessage('');
    setPasswordError('');

    if (!currentPassword.trim()) {
      setPasswordError('Current password is required');
      return;
    }
    if (newPassword.trim() === '' || confirmPassword.trim() === '') {
      setPasswordError('Enter new password and confirmation');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }
    try {
      const data = await apiPut<{ detail: string }>('/auth/password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      });
      
      setPasswordMessage(data.detail || 'Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      await refreshUser();
    } catch (err) {
      if (err instanceof ApiError) {
        setPasswordError(err.message);
      } else {
        setPasswordError('Network error while changing password');
      }
    }
  };

  const buildSettingsPayload = () => {
    const payload: Record<string, unknown> = {
      time_zone: timeZone || null,
    };
    if (isAdmin) {
      payload.allow_asr_overrides = allowAsrOverrides;
      payload.allow_diarizer_overrides = allowDiarizerOverrides;
      payload.max_concurrent_jobs = maxConcurrentJobs;
    }
    if (canEditAsrDefaults) {
      payload.default_asr_provider = defaultProvider || null;
      payload.default_model = defaultModel || null;
      payload.default_language = defaultLanguage;
      payload.enable_timestamps = enableTimestamps;
    }
    if (canEditDiarizerDefaults) {
      payload.default_diarizer_provider = defaultDiarizerProvider || null;
      payload.default_diarizer = defaultDiarizer;
      payload.diarization_enabled = diarizationEnabled;
    }
    return payload;
  };

  const asrProviders = React.useMemo(
    () => registrySets.filter((set) => set.type === 'asr'),
    [registrySets]
  );
  const providerOptions = React.useMemo(
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

  React.useEffect(() => {
    if (!canEditAsrDefaults) {
      return;
    }
    if (isLoadingSettings || registryLoading || hasUserChangedDefaults) {
      return;
    }
    if (!providerOptions.length) {
      setDefaultProvider('');
      setDefaultModel('');
      return;
    }

    const providerFromSettings = initialAsrProvider
      ? providerOptions.find((opt) => opt.value === initialAsrProvider && opt.isUsable)?.value
      : '';
    const providerFromModel = initialAsrModel
      ? providerOptions.find(
          (opt) => opt.isUsable && opt.weights.some((weight) => weight.name === initialAsrModel)
        )?.value
      : '';
    const fallbackProvider =
      providerOptions.find((opt) => opt.isUsable)?.value || providerOptions[0]?.value || '';
    const resolvedProvider = providerFromSettings || providerFromModel || fallbackProvider || '';
    setDefaultProvider(resolvedProvider);

    const weightsForProvider =
      providerOptions.find((opt) => opt.value === resolvedProvider)?.weights ?? [];
    const preferredWeight = initialAsrModel
      ? weightsForProvider.find(
          (weight) =>
            weight.name === initialAsrModel &&
            weight.enabled &&
            ((weight.has_weights ?? false) || allowEmptyWeights)
        )
      : undefined;
    const firstEnabledWeight = weightsForProvider.find(
      (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
    );
    const fallbackWeight =
      weightsForProvider.find((weight) => (weight.has_weights ?? false) || allowEmptyWeights) ||
      weightsForProvider[0];
    const resolvedModel =
      preferredWeight?.name ||
      firstEnabledWeight?.name ||
      fallbackWeight?.name ||
      initialAsrModel ||
      '';
    setDefaultModel(resolvedModel);
  }, [
    isLoadingSettings,
    registryLoading,
    hasUserChangedDefaults,
    providerOptions,
    initialAsrProvider,
    initialAsrModel,
    allowEmptyWeights,
    canEditAsrDefaults,
  ]);

  const selectedProviderOption = providerOptions.find((opt) => opt.value === defaultProvider);
  const weightOptions = React.useMemo(() => {
    if (!selectedProviderOption) return [];
    return selectedProviderOption.weights.map((weight) => {
      const hasWeights = Boolean(weight.has_weights) || allowEmptyWeights;
      const effectiveEnabled = Boolean(
        selectedProviderOption.isUsable && weight.enabled && hasWeights
      );
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
        isUsable: effectiveEnabled,
      };
    });
  }, [selectedProviderOption, allowEmptyWeights]);

  const diarizerProviders = React.useMemo(
    () => registrySets.filter((set) => set.type === 'diarizer'),
    [registrySets]
  );
  const diarizerProviderOptions = React.useMemo(
    () =>
      diarizerProviders.map((set) => {
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
    [diarizerProviders, allowEmptyWeights]
  );

  React.useEffect(() => {
    if (!canEditDiarizerDefaults) {
      return;
    }
    if (isLoadingSettings || registryLoading || hasUserChangedDiarizerDefaults) {
      return;
    }
    if (!diarizerProviderOptions.length) {
      setDefaultDiarizerProvider('');
      setDefaultDiarizer('');
      return;
    }

    const providerFromSettings = initialDiarizerProvider
      ? diarizerProviderOptions.find(
          (opt) => opt.value === initialDiarizerProvider && opt.isUsable
        )?.value
      : '';
    const providerFromModel = initialDiarizer
      ? diarizerProviderOptions.find(
          (opt) => opt.isUsable && opt.weights.some((weight) => weight.name === initialDiarizer)
        )?.value
      : '';
    const fallbackProvider =
      diarizerProviderOptions.find((opt) => opt.isUsable)?.value ||
      diarizerProviderOptions[0]?.value ||
      '';
    const resolvedProvider = providerFromSettings || providerFromModel || fallbackProvider || '';
    setDefaultDiarizerProvider(resolvedProvider);

    const weightsForProvider =
      diarizerProviderOptions.find((opt) => opt.value === resolvedProvider)?.weights ?? [];
    const preferredWeight = initialDiarizer
      ? weightsForProvider.find(
          (weight) =>
            weight.name === initialDiarizer &&
            weight.enabled &&
            ((weight.has_weights ?? false) || allowEmptyWeights)
        )
      : undefined;
    const firstEnabledWeight = weightsForProvider.find(
      (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
    );
    const fallbackWeight =
      weightsForProvider.find((weight) => (weight.has_weights ?? false) || allowEmptyWeights) ||
      weightsForProvider[0];
    const resolvedDiarizer =
      preferredWeight?.name ||
      firstEnabledWeight?.name ||
      fallbackWeight?.name ||
      initialDiarizer ||
      '';
    setDefaultDiarizer(resolvedDiarizer);
  }, [
    canEditDiarizerDefaults,
    isLoadingSettings,
    registryLoading,
    hasUserChangedDiarizerDefaults,
    diarizerProviderOptions,
    initialDiarizerProvider,
    initialDiarizer,
    allowEmptyWeights,
  ]);

  const selectedDiarizerProviderOption = diarizerProviderOptions.find(
    (opt) => opt.value === defaultDiarizerProvider
  );
  const diarizerWeightOptions = React.useMemo(() => {
    if (!selectedDiarizerProviderOption) return [];
    return selectedDiarizerProviderOption.weights.map((weight) => {
      const hasWeights = Boolean(weight.has_weights) || allowEmptyWeights;
      const effectiveEnabled = Boolean(
        selectedDiarizerProviderOption.isUsable && weight.enabled && hasWeights
      );
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
        isUsable: effectiveEnabled,
      };
    });
  }, [selectedDiarizerProviderOption, allowEmptyWeights]);

  const handleProviderChange = (value: string) => {
    setHasUserChangedDefaults(true);
    setDefaultProvider(value);
    const weightsForProvider = providerOptions.find((opt) => opt.value === value)?.weights ?? [];
    const firstEnabled = weightsForProvider.find(
      (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
    );
    const firstWithFiles = weightsForProvider.find(
      (weight) => (weight.has_weights ?? false) || allowEmptyWeights
    );
    const fallbackWeight = weightsForProvider[0];
    setDefaultModel(firstEnabled?.name || firstWithFiles?.name || fallbackWeight?.name || '');
  };

  const handleSaveDefaults = async () => {
    try {
      await updateSettings(buildSettingsPayload());
      showSuccess('Default transcription settings saved');
      broadcastSettingsUpdated();
    } catch (error) {
      devError('Failed to save defaults:', error);
      if (error instanceof ApiError) {
        showError(`Failed to save settings: ${error.message}`);
      } else {
        showError('Failed to save settings. Please try again.');
      }
    }
  };

  const handleEditTag = (tagId: number) => {
    devInfo('Edit tag:', tagId);
    // TODO: Open edit modal
    alert(`Edit tag ${tagId} (not yet implemented)`);
  };

  const handleDeleteTag = async (tagId: number, scope: 'global' | 'personal') => {
    if (!confirm('Delete this tag? It will be removed from all jobs.')) {
      return;
    }
    
    try {
      const result = await deleteTag(tagId);
      if (scope === 'global') {
        setGlobalTags(globalTags.filter(t => t.id !== tagId));
      } else {
        setPersonalTags(personalTags.filter(t => t.id !== tagId));
      }
      showSuccess(`Tag deleted (removed from ${result.jobs_affected} jobs)`);
    } catch (error) {
      devError('Failed to delete tag:', error);
      if (error instanceof ApiError) {
        showError(`Failed to delete tag: ${error.message}`);
      } else {
        showError('Failed to delete tag. Please try again.');
      }
    }
  };
  const handleCreatePersonalTag = async () => {
    const trimmed = newPersonalTag.trim();
    if (!trimmed) return;
    setIsCreatingPersonalTag(true);
    try {
      const created = await createTag({ name: trimmed, color: newPersonalTagColor, scope: 'personal' });
      setPersonalTags((prev) => {
        const next = [created, ...prev];
        setNewPersonalTagColor(pickTagColor(next, TAG_COLOR_PALETTE[0]));
        return next;
      });
      setNewPersonalTag('');
      showSuccess('Personal tag created');
    } catch (error) {
      devError('Failed to create personal tag:', error);
      if (error instanceof ApiError) {
        showError(`Failed to create tag: ${error.message}`);
      } else {
        showError('Failed to create tag. Please try again.');
      }
    } finally {
      setIsCreatingPersonalTag(false);
    }
  };

  

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="w-7 h-7 text-forest-green" />
          <div>
            <h1 className="text-2xl font-semibold text-pine-deep">Settings</h1>
          </div>
        </div>

        {/* Account Section */}
        <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <h2 className="text-lg font-medium text-pine-deep mb-4">Account</h2>
        {user?.force_password_reset && (
          <div className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            Your password must be reset before continuing.
          </div>
        )}
        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-sm font-medium text-pine-deep mb-1">
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              data-testid="current-password"
              autoComplete="current-password"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-pine-deep mb-1">
              New Password
            </label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              data-testid="new-password"
              autoComplete="new-password"
            />
          </div>
          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium text-pine-deep mb-1">
              Confirm Password
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              data-testid="confirm-password"
              autoComplete="new-password"
            />
          </div>
          {passwordError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-600" data-testid="password-error">
              {passwordError}
            </div>
          )}
          {passwordMessage && (
            <div className="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700" data-testid="password-success">
              {passwordMessage}
            </div>
          )}
          <button
            type="submit"
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
            data-testid="password-save"
          >
            Save
          </button>
        </form>
      </section>

      {/* Default Transcription Options (user-facing) */}
        <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-pine-deep">Default Transcription Options</h2>
          </div>
        <div className="space-y-4">
          <div>
            {canEditAsrDefaults ? (
              <>
                <label htmlFor="default-provider" className="block text-sm font-medium text-pine-deep mb-1">
                  ASR Model Set
                </label>
                <select
                  id="default-provider"
                  value={defaultProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none disabled:bg-gray-100"
                  data-testid="default-provider"
                  disabled={registryLoading || !providerOptions.length}
                >
                  {!providerOptions.length && <option value="">No providers registered</option>}
                  {providerOptions.map((opt) => (
                    <option key={opt.value} value={opt.value} disabled={!opt.isUsable}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <label htmlFor="default-model" className="block text-sm font-medium text-pine-deep mb-1 mt-3">
                  ASR Model Weight
                </label>
                <select
                  id="default-model"
                  value={defaultModel}
                  onChange={(e) => {
                    setHasUserChangedDefaults(true);
                    setDefaultModel(e.target.value);
                  }}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none disabled:bg-gray-100"
                  data-testid="default-model"
                  disabled={registryLoading || !weightOptions.length}
                >
                  {!weightOptions.length && <option value="">No model weights registered</option>}
                  {weightOptions.map((opt) => (
                    <option key={opt.value} value={opt.value} disabled={!opt.isUsable}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {registryError && (
                  <p className="text-xs text-terracotta mt-1">{registryError}</p>
                )}
              </>
            ) : (
              <div className="rounded border border-sage-mid bg-sage-light/40 px-3 py-2 text-sm text-pine-deep">
                <div className="font-medium">ASR defaults</div>
                <div>{defaultProvider || 'Unknown'} / {defaultModel || 'Unknown'}</div>
                <p className="text-xs text-pine-mid mt-1">ASR defaults are managed by the administrator.</p>
              </div>
            )}
          </div>
          <div>
              {canEditDiarizerDefaults ? (
                <>
                  <label htmlFor="default-diarizer-provider" className="block text-sm font-medium text-pine-deep mb-1">
                    Diarizer Model Set
                  </label>
                  <select
                    id="default-diarizer-provider"
                    value={defaultDiarizerProvider}
                    onChange={(e) => {
                      setHasUserChangedDiarizerDefaults(true);
                      setDefaultDiarizerProvider(e.target.value);
                      const weightsForProvider =
                        diarizerProviderOptions.find((opt) => opt.value === e.target.value)?.weights ?? [];
                      const firstEnabled = weightsForProvider.find(
                        (weight) => weight.enabled && ((weight.has_weights ?? false) || allowEmptyWeights)
                      );
                      const firstWithFiles = weightsForProvider.find(
                        (weight) => (weight.has_weights ?? false) || allowEmptyWeights
                      );
                      const fallbackWeight = weightsForProvider[0];
                      setDefaultDiarizer(firstEnabled?.name || firstWithFiles?.name || fallbackWeight?.name || '');
                    }}
                    className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none disabled:bg-gray-100"
                    data-testid="default-diarizer-provider"
                    disabled={registryLoading || !diarizerProviderOptions.length}
                  >
                    {!diarizerProviderOptions.length && <option value="">No diarizer providers registered</option>}
                    {diarizerProviderOptions.map((opt) => (
                      <option key={opt.value} value={opt.value} disabled={!opt.isUsable}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <label htmlFor="default-diarizer" className="block text-sm font-medium text-pine-deep mb-1 mt-3">
                    Diarizer Weight
                  </label>
                  <select
                    id="default-diarizer"
                    value={defaultDiarizer}
                    onChange={(e) => {
                      setHasUserChangedDiarizerDefaults(true);
                      setDefaultDiarizer(e.target.value);
                    }}
                    className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none disabled:bg-gray-100"
                    data-testid="default-diarizer"
                    disabled={registryLoading || !diarizerWeightOptions.length}
                  >
                    {!diarizerWeightOptions.length && <option value="">No diarizer weights registered</option>}
                    {diarizerWeightOptions.map((opt) => (
                      <option key={opt.value} value={opt.value} disabled={!opt.isUsable}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center text-sm text-pine-deep mt-3">
                    <input
                      type="checkbox"
                      checked={diarizationEnabled}
                      onChange={(e) => setDiarizationEnabled(e.target.checked)}
                      className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                      data-testid="default-diarization-enabled"
                    />
                    <span className="ml-2">Enable diarization by default</span>
                  </label>
                </>
              ) : (
                <div className="rounded border border-sage-mid bg-sage-light/40 px-3 py-2 text-sm text-pine-deep">
                  <div className="font-medium">Diarization defaults</div>
                  <div>
                    {diarizationEnabled ? 'Enabled' : 'Disabled by admin'}{' '}
                    {defaultDiarizerProvider ? `${defaultDiarizerProvider} / ` : ''}
                    {defaultDiarizer || 'Unknown'}
                  </div>
                  <p className="text-xs text-pine-mid mt-1">
                    Diarization defaults are managed by the administrator.
                  </p>
                </div>
              )}
            </div>
          <div>
            <label htmlFor="default-language" className="block text-sm font-medium text-pine-deep mb-1">
              Default Language
            </label>
            <select
              id="default-language"
              value={defaultLanguage}
              onChange={(e) => setDefaultLanguage(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              data-testid="default-language"
              disabled={!canEditAsrDefaults}
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
          <div>
            <label htmlFor="time-zone" className="block text-sm font-medium text-pine-deep mb-1">
              Your Time Zone
            </label>
            <select
              id="time-zone"
              value={timeZone}
              onChange={(e) => setTimeZone(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
            >
              <option value="">{`Use browser default (${browserTimeZone})`}</option>
              {timeZoneOptions.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label className="flex items-center text-sm text-pine-deep">
              <input
                type="checkbox"
                checked={enableTimestamps}
                onChange={(e) => setEnableTimestamps(e.target.checked)}
                className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                data-testid="default-timestamps"
                disabled={!canEditAsrDefaults}
              />
              <span className="ml-2">Include timestamps on new jobs</span>
            </label>
          </div>
          <button
            onClick={handleSaveDefaults}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
            data-testid="default-save"
          >
            Save
          </button>
        </div>
      </section>

      {isAdmin && (
        <section className="mb-6 border border-dusty-rose bg-terracotta/5 rounded-lg p-4" data-testid="settings-admin-redirect">
          <p className="text-sm text-pine-deep">
            Need to adjust concurrency limits or inspect storage usage? Those controls now reside on the Admin page.
          </p>
        </section>
      )}

      {/* Tags */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg" data-testid="settings-tags-section">
        <button
          onClick={() => setTagsExpanded(!tagsExpanded)}
          className="w-full flex items-center justify-between p-6 hover:bg-sage-light transition"
          data-testid="settings-tags-toggle"
        >
          <h2 className="text-lg font-medium text-pine-deep">Tags</h2>
          {tagsExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        {tagsExpanded && (
          <div className="px-6 pb-6" data-testid="settings-tags-content">
            {!tagsLoaded ? (
              <div
                data-testid="settings-tags-loading"
                className="text-sm text-pine-mid italic"
              >
                Loading tags...
              </div>
            ) : (
              <div data-testid="settings-tags-loaded" className="space-y-6">
                <div>
                  <div className="text-xs uppercase tracking-wide text-pine-mid mb-2">System tags</div>
                  <TagList
                    tags={globalTags}
                    onEdit={isAdmin ? handleEditTag : undefined}
                    onDelete={isAdmin ? (tagId) => handleDeleteTag(tagId, 'global') : undefined}
                    showActions={isAdmin}
                  />
                </div>

                {!isAdmin && (
                  <div>
                    <div className="text-xs uppercase tracking-wide text-pine-mid mb-2">My tags</div>
                    <div className="flex flex-col md:flex-row gap-2 mb-3">
                      <input
                        type="text"
                        value={newPersonalTag}
                        onChange={(e) => setNewPersonalTag(e.target.value)}
                        placeholder="New personal tag"
                        className="flex-1 px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                        data-testid="personal-tag-name"
                      />
                      <button
                        type="button"
                        onClick={handleCreatePersonalTag}
                        disabled={isCreatingPersonalTag || newPersonalTag.trim().length === 0}
                        className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50"
                        data-testid="personal-tag-create"
                      >
                        {isCreatingPersonalTag ? 'Creating...' : 'Create tag'}
                      </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mb-4">
                      <span className="text-xs text-pine-mid">Tag color</span>
                      {TAG_COLOR_PALETTE.map((color) => (
                        <button
                          key={color}
                          type="button"
                          aria-label={`Select ${color}`}
                          onClick={() => setNewPersonalTagColor(color)}
                          className={`w-6 h-6 rounded-full border ${
                            newPersonalTagColor === color
                              ? 'border-forest-green ring-2 ring-forest-green/40'
                              : 'border-sage-mid'
                          }`}
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                    <TagList
                      tags={personalTags}
                      onEdit={handleEditTag}
                      onDelete={(tagId) => handleDeleteTag(tagId, 'personal')}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
