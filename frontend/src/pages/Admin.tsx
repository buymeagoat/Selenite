import React, { useEffect, useMemo, useState } from 'react';
import {
  Shield,
  RefreshCw,
  Plus,
  Save,
  Trash2,
  FolderOpen,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../lib/api';
import { fetchSettings, updateAsrSettings, updateDiarizationSettings, updateSettings } from '../services/settings';
import {
  fetchSystemInfo,
  refreshSystemInfo,
  fetchCapabilities,
  restartServer,
  shutdownServer,
  fullRestartServer,
  type SystemProbe,
  type DiskUsage,
  type CapabilityResponse,
} from '../services/system';
import {
  createModelEntry,
  createModelSet,
  deleteModelEntry,
  deleteModelSet,
  listModelSets,
  updateModelEntry,
  updateModelSet,
  type ModelEntry,
  type ModelSetWithEntries,
  type ProviderType,
} from '../services/modelRegistry';
import { devError } from '../lib/debug';
import { getSupportedTimeZones, getBrowserTimeZone } from '../utils/timezones';

type RegistryTab = ProviderType;

const MODELS_ROOT = '/backend/models';

interface SetFormState {
  id: number | null;
  name: string;
  description: string;
  abs_path: string;
  enabled: boolean;
  disable_reason: string;
}

interface EntryFormState {
  id: number | null;
  name: string;
  description: string;
  abs_path: string;
  checksum: string;
  enabled: boolean;
  disable_reason: string;
}

function normalizePath(path: string): string {
  return path.trim().replace(/\\/g, '/');
}

function canonicalPath(path: string): string {
  const norm = normalizePath(path).toLowerCase();
  const idx = norm.indexOf('/backend/models');
  return idx >= 0 ? norm.slice(idx) : norm;
}

function pathStartsWith(base: string, candidate: string): boolean {
  const normBase = canonicalPath(base);
  const normCandidate = canonicalPath(candidate);
  return normCandidate.startsWith(normBase);
}

export const Admin: React.FC = () => {
  const { showError, showSuccess, showInfo } = useToast();
  const { user } = useAuth();
  const isAdmin = Boolean(user?.is_admin);

  const timeZoneOptions = getSupportedTimeZones();
  const browserTimeZone = getBrowserTimeZone();

  const [defaultAsrProvider, setDefaultAsrProvider] = useState('');
  const [defaultModel, setDefaultModel] = useState('');
  const [defaultLanguage, setDefaultLanguage] = useState('auto');
  const [defaultDiarizer, setDefaultDiarizer] = useState('');
  const [enableTimestamps, setEnableTimestamps] = useState(true);
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [allowJobOverrides, setAllowJobOverrides] = useState(false);
  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3);
  const [transcodeToWav, setTranscodeToWav] = useState(true);
  const [userTimeZone, setUserTimeZone] = useState<string>(browserTimeZone);
  const [serverTimeZone, setServerTimeZone] = useState<string>('UTC');
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [systemInfo, setSystemInfo] = useState<SystemProbe | null>(null);
  const [isSystemLoading, setIsSystemLoading] = useState(true);
  const [isDetectingSystem, setIsDetectingSystem] = useState(false);
  const [capabilities, setCapabilities] = useState<CapabilityResponse | null>(null);
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(true);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [registrySets, setRegistrySets] = useState<ModelSetWithEntries[]>([]);
  const [registryTab, setRegistryTab] = useState<RegistryTab>('asr');
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null);
  const [setForm, setSetForm] = useState<SetFormState>({
    id: null,
    name: '',
    description: '',
    abs_path: '',
    enabled: true,
    disable_reason: '',
  });
  const [entryForm, setEntryForm] = useState<EntryFormState>({
    id: null,
    name: '',
    description: '',
    abs_path: '',
    checksum: '',
    enabled: true,
    disable_reason: '',
  });
  const [isSavingSet, setIsSavingSet] = useState(false);
  const [isSavingEntry, setIsSavingEntry] = useState(false);
  const [availabilityNotes, setAvailabilityNotes] = useState<string[]>([]);

  const broadcastSettingsUpdated = () => {
    window.dispatchEvent(new CustomEvent('selenite:settings-updated'));
  };

  const filteredSets = useMemo(
    () => registrySets.filter((set) => set.type === registryTab),
    [registrySets, registryTab]
  );
  const activeSet = filteredSets.find((set) => set.id === selectedSetId) ?? filteredSets[0];
  const activeEntries = activeSet?.entries ?? [];

  const availableAsrModels = useMemo(
    () => capabilities?.asr.flatMap((provider) => provider.models).filter(Boolean) ?? [],
    [capabilities]
  );
  const asrProviders = useMemo(() => capabilities?.asr ?? [], [capabilities]);
  const activeProviderModels = useMemo(() => {
    const match = asrProviders.find((p) => p.provider === defaultAsrProvider);
    return match?.models ?? [];
  }, [asrProviders, defaultAsrProvider]);
  const availableDiarizers = useMemo(
    () => capabilities?.diarizers.filter((opt) => opt.available) ?? [],
    [capabilities]
  );

  useEffect(() => {
    if (!isAdmin) {
      setIsLoadingSettings(false);
      setIsSystemLoading(false);
      setIsLoadingCapabilities(false);
      setRegistryLoading(false);
      return;
    }

    let cancelled = false;
    const loadData = async () => {
      try {
        const [settingsData, systemData, capabilityData, registry] = await Promise.all([
          fetchSettings(),
          fetchSystemInfo(),
          fetchCapabilities(),
          listModelSets(),
        ]);
        if (cancelled) return;
        setDefaultAsrProvider(settingsData.default_asr_provider ?? '');
        setDefaultModel(settingsData.default_model ?? '');
        setDefaultLanguage(settingsData.default_language ?? 'auto');
        setDefaultDiarizer(settingsData.default_diarizer ?? '');
        setDiarizationEnabled(settingsData.diarization_enabled);
        setAllowJobOverrides(settingsData.allow_job_overrides);
        setEnableTimestamps(settingsData.enable_timestamps);
        setMaxConcurrentJobs(settingsData.max_concurrent_jobs);
        setUserTimeZone(settingsData.time_zone || browserTimeZone);
        setServerTimeZone(settingsData.server_time_zone || 'UTC');
        setTranscodeToWav(settingsData.transcode_to_wav ?? true);
        setSystemInfo(systemData);
        setCapabilities(capabilityData);
        setRegistrySets(registry);
        setAvailabilityNotes(collectAvailabilityNotes(capabilityData));
        if (registry.length > 0) {
          const firstSet = registry.find((set) => set.type === registryTab) ?? registry[0];
          setRegistryTab(firstSet.type);
          setSelectedSetId(firstSet.id);
          setSetForm(buildSetForm(firstSet));
        }
      } catch (error) {
        devError('Failed to load admin data:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load admin data: ${error.message}`);
        } else {
          showError('Failed to load admin data. Please refresh the page.');
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSettings(false);
          setIsSystemLoading(false);
          setIsLoadingCapabilities(false);
          setRegistryLoading(false);
        }
      }
    };
    loadData();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  useEffect(() => {
    if (!filteredSets.length) {
      setSelectedSetId(null);
      setSetForm({
        id: null,
        name: '',
        description: '',
        abs_path: '',
        enabled: true,
        disable_reason: '',
      });
      return;
    }
    const match = filteredSets.find((set) => set.id === selectedSetId) ?? filteredSets[0];
    setSelectedSetId(match.id);
    setSetForm(buildSetForm(match));
  }, [filteredSets, selectedSetId]);

  useEffect(() => {
    if (!capabilities) return;

    const providerKeys = asrProviders.map((p) => p.provider);
    if (providerKeys.length && defaultAsrProvider && !providerKeys.includes(defaultAsrProvider)) {
      setDefaultAsrProvider(providerKeys[0]);
    } else if (!defaultAsrProvider && providerKeys.length) {
      setDefaultAsrProvider(providerKeys[0]);
    }

    if (activeProviderModels.length && defaultModel && !activeProviderModels.includes(defaultModel)) {
      setDefaultModel(activeProviderModels[0]);
    } else if (!defaultModel && activeProviderModels.length) {
      setDefaultModel(activeProviderModels[0]);
    }
    if (availableDiarizers.length && defaultDiarizer && !availableDiarizers.find((d) => d.key === defaultDiarizer)) {
      setDefaultDiarizer(availableDiarizers[0].key);
    }
  }, [activeProviderModels, availableDiarizers, asrProviders, capabilities, defaultModel, defaultDiarizer, defaultAsrProvider]);

  const collectAvailabilityNotes = (cap: CapabilityResponse | null): string[] => {
    if (!cap) return [];
    const notes: string[] = [];
    if (!cap.asr.length) {
      notes.push('No ASR models registered. Add an ASR set and entry to enable jobs.');
    }
    cap.asr.forEach((provider) => provider.notes.forEach((note) => notes.push(`${provider.provider}: ${note}`)));
    if (!cap.diarizers.length) {
      notes.push('No diarization entries registered.');
    }
    cap.diarizers.forEach((opt) => opt.notes.forEach((note) => notes.push(`${opt.key}: ${note}`)));
    return notes;
  };

  const buildSetForm = (set: ModelSetWithEntries): SetFormState => ({
    id: set.id,
    name: set.name,
    description: set.description ?? '',
    abs_path: set.abs_path,
    enabled: set.enabled,
    disable_reason: set.disable_reason ?? '',
  });

  const resetEntryForm = () =>
    setEntryForm({
      id: null,
      name: '',
      description: '',
      abs_path: '',
      checksum: '',
      enabled: true,
      disable_reason: '',
    });

  const validatePath = (path: string, scopePath?: string): string | null => {
    if (!path) return 'Path is required.';
    const normalized = normalizePath(path);
    if (!pathStartsWith(MODELS_ROOT, normalized)) {
      return `Path must live under ${MODELS_ROOT}/<set>/<entry>`;
    }
    if (scopePath && !pathStartsWith(scopePath, normalized)) {
      return 'Entry path must live under its model set directory.';
    }
    return null;
  };

  const refreshRegistry = async (preserveSelection = true) => {
    setRegistryLoading(true);
    try {
      const data = await listModelSets();
      setRegistrySets(data);
      if (!data.length) {
        setSelectedSetId(null);
        setSetForm({
          id: null,
          name: '',
          description: '',
          abs_path: '',
          enabled: true,
          disable_reason: '',
        });
        return;
      }
      if (preserveSelection && selectedSetId && data.find((s) => s.id === selectedSetId)) {
        return;
      }
      const first = data.find((s) => s.type === registryTab) ?? data[0];
      setRegistryTab(first.type);
      setSelectedSetId(first.id);
      setSetForm(buildSetForm(first));
    } catch (error) {
      devError('Failed to refresh registry', error);
      showError('Failed to refresh model registry.');
    } finally {
      setRegistryLoading(false);
    }
  };

  const handleSaveSet = async () => {
    if (!isAdmin) return;
    const pathError = validatePath(setForm.abs_path);
    if (pathError) {
      showError(pathError);
      return;
    }
    if (!setForm.enabled && !setForm.disable_reason.trim()) {
      showError('Provide a disable reason when turning off a set.');
      return;
    }
    setIsSavingSet(true);
    try {
      if (setForm.id) {
        await updateModelSet(setForm.id, {
          name: setForm.name,
          description: setForm.description || null,
          abs_path: setForm.abs_path,
          enabled: setForm.enabled,
          disable_reason: setForm.disable_reason || null,
        });
      } else {
        const created = await createModelSet({
          type: registryTab,
          name: setForm.name,
          description: setForm.description || null,
          abs_path: setForm.abs_path,
        });
        setSelectedSetId(created.id);
      }
      showSuccess('Model set saved');
      await refreshRegistry(false);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to save set', error);
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Unable to save model set');
      }
    } finally {
      setIsSavingSet(false);
    }
  };

  const handleDeleteSet = async () => {
    if (!setForm.id) return;
    if (!confirm('Delete this model set and all of its entries?')) return;
    try {
      await deleteModelSet(setForm.id);
      showSuccess('Model set deleted');
      setSelectedSetId(null);
      await refreshRegistry(false);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to delete set', error);
      showError('Unable to delete model set.');
    }
  };

  const handleEditEntry = (entry: ModelEntry) => {
    setEntryForm({
      id: entry.id,
      name: entry.name,
      description: entry.description ?? '',
      abs_path: entry.abs_path,
      checksum: entry.checksum ?? '',
      enabled: entry.enabled,
      disable_reason: entry.disable_reason ?? '',
    });
  };

  const handleSaveEntry = async () => {
    if (!selectedSetId) {
      showError('Select a model set before adding entries.');
      return;
    }
    const pathError = validatePath(entryForm.abs_path, activeSet?.abs_path);
    if (pathError) {
      showError(pathError);
      return;
    }
    if (!entryForm.enabled && !entryForm.disable_reason.trim()) {
      showError('Provide a disable reason when turning off an entry.');
      return;
    }
    setIsSavingEntry(true);
    try {
      if (entryForm.id) {
        await updateModelEntry(entryForm.id, {
          name: entryForm.name,
          description: entryForm.description || null,
          abs_path: entryForm.abs_path,
          checksum: entryForm.checksum || null,
          enabled: entryForm.enabled,
          disable_reason: entryForm.disable_reason || null,
        });
      } else {
        await createModelEntry(selectedSetId, {
          name: entryForm.name,
          description: entryForm.description || null,
          abs_path: entryForm.abs_path,
          checksum: entryForm.checksum || null,
        });
      }
      showSuccess('Model entry saved');
      resetEntryForm();
      await refreshRegistry();
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to save entry', error);
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Unable to save model entry.');
      }
    } finally {
      setIsSavingEntry(false);
    }
  };

  const handleDeleteEntry = async (entryId: number) => {
    if (!confirm('Delete this model entry?')) return;
    try {
      await deleteModelEntry(entryId);
      showSuccess('Model entry deleted');
      resetEntryForm();
      await refreshRegistry();
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to delete entry', error);
      showError('Unable to delete model entry.');
    }
  };

  const handleToggleEntry = async (entry: ModelEntry) => {
    const targetState = !entry.enabled;
    const reason =
      targetState === false ? prompt('Provide a reason for disabling this entry', entry.disable_reason ?? '') : null;
    if (targetState === false && (!reason || !reason.trim())) {
      showError('Disable reason is required.');
      return;
    }
    try {
      await updateModelEntry(entry.id, {
        enabled: targetState,
        disable_reason: targetState ? null : reason,
      });
      showInfo(`Entry ${targetState ? 'enabled' : 'disabled'}`);
      await refreshRegistry();
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to toggle entry', error);
      showError('Unable to update entry state.');
    }
  };

  const handleAvailabilityRefresh = async () => {
    setIsLoadingCapabilities(true);
    try {
      const fresh = await fetchCapabilities();
      setCapabilities(fresh);
      setAvailabilityNotes(collectAvailabilityNotes(fresh));
      showSuccess('Availability refreshed');
    } catch (error) {
      devError('Failed to refresh capabilities', error);
      showError('Failed to refresh availability.');
    } finally {
      setIsLoadingCapabilities(false);
    }
  };

  const handleSaveAsrDefaults = async () => {
    try {
      await updateAsrSettings({
        default_asr_provider: defaultAsrProvider || null,
        default_model: defaultModel || null,
        default_language: defaultLanguage,
        enable_timestamps: enableTimestamps,
        max_concurrent_jobs: maxConcurrentJobs,
      });
      showSuccess('ASR defaults saved');
      broadcastSettingsUpdated();
    } catch (error) {
      devError('Failed to save ASR settings:', error);
      if (error instanceof ApiError) {
        showError(`Failed to save ASR settings: ${error.message}`);
      } else {
        showError('Failed to save ASR settings. Please try again.');
      }
    }
  };

  const handleSaveDiarizationDefaults = async () => {
    try {
      await updateDiarizationSettings({
        default_diarizer: diarizationEnabled ? defaultDiarizer || null : null,
        diarization_enabled: diarizationEnabled,
        allow_job_overrides: allowJobOverrides,
      });
      showSuccess('Diarization defaults saved');
      broadcastSettingsUpdated();
    } catch (error) {
      devError('Failed to save diarization settings:', error);
      if (error instanceof ApiError) {
        showError(`Failed to save diarization settings: ${error.message}`);
      } else {
        showError('Failed to save diarization settings. Please try again.');
      }
    }
  };

  const handleSaveTimeZones = async () => {
    try {
      await updateSettings({
        default_asr_provider: defaultAsrProvider || null,
        default_model: defaultModel || null,
        default_language: defaultLanguage || undefined,
        default_diarizer: diarizationEnabled ? defaultDiarizer || null : null,
        diarization_enabled: diarizationEnabled,
        allow_job_overrides: allowJobOverrides,
        enable_timestamps: enableTimestamps,
        max_concurrent_jobs: maxConcurrentJobs,
        time_zone: userTimeZone || null,
        server_time_zone: serverTimeZone || 'UTC',
        transcode_to_wav: transcodeToWav,
      });
      showSuccess('Time zones saved');
      broadcastSettingsUpdated();
    } catch (error) {
      devError('Failed to save time zones:', error);
      const msg = error instanceof ApiError ? error.message : 'Failed to save time zones. Please try again.';
      showError(msg);
    }
  };

  const handleRestartServer = async () => {
    if (!confirm('Are you sure you want to restart the server? This will briefly interrupt all operations.')) {
      return;
    }

    try {
      const response = await restartServer();
      showSuccess(response.message);
      setTimeout(() => {
        showSuccess('Server should be restarting now. Reload the page in a few seconds.');
      }, 1500);
    } catch (error) {
      devError('Failed to restart server:', error);
      if (error instanceof ApiError) {
        showError(`Failed to restart server: ${error.message}`);
      } else {
        showError('Failed to restart server. Please try again.');
      }
    }
  };

  const handleShutdownServer = async () => {
    if (!confirm('Are you sure you want to shutdown the server? This will stop all transcriptions and you will need to manually restart it.')) {
      return;
    }

    if (!confirm('FINAL WARNING: The server will shutdown completely. You will need physical/SSH access to restart it. Continue?')) {
      return;
    }

    try {
      const response = await shutdownServer();
      showSuccess(response.message);
      setTimeout(() => {
        showSuccess('Server is shutting down. You will need to manually restart it.');
      }, 1500);
    } catch (error) {
      devError('Failed to shutdown server:', error);
      if (error instanceof ApiError) {
        showError(`Failed to shutdown server: ${error.message}`);
      } else {
        showError('Failed to shutdown server. Please try again.');
      }
    }
  };

  const handleFullRestartServer = async () => {
    if (!confirm('Full orchestrated restart will recycle ALL components. Continue?')) {
      return;
    }
    if (!confirm('Confirm again: jobs in progress will be interrupted. Proceed with full restart?')) {
      return;
    }
    try {
      const response = await fullRestartServer();
      showSuccess(response.message);
      setTimeout(() => {
        showSuccess('If watchdog is running, services should come back shortly.');
      }, 2000);
    } catch (error) {
      devError('Failed to request full restart:', error);
      if (error instanceof ApiError) {
        showError(`Failed to request full restart: ${error.message}`);
      } else {
        showError('Failed to request full restart.');
      }
    }
  };

  const handleDetectSystem = async () => {
    setIsDetectingSystem(true);
    try {
      const data = await refreshSystemInfo();
      setSystemInfo(data);
      showSuccess('System information refreshed');
    } catch (error) {
      devError('Failed to refresh system info:', error);
      if (error instanceof ApiError) {
        showError(`Failed to refresh system info: ${error.message}`);
      } else {
        showError('Failed to refresh system info. Please try again.');
      }
    } finally {
      setIsDetectingSystem(false);
    }
  };

  const formatGb = (value?: number | null) => {
    if (value === undefined || value === null) {
      return 'Unknown';
    }
    return `${value.toFixed(1)} GB`;
  };

  const renderDiskUsage = (label: string, usage?: DiskUsage | null) => {
    if (!usage) {
      return (
        <div className="p-3 border border-sage-mid rounded-lg">
          <div className="text-sm font-medium text-pine-deep">{label}</div>
          <div className="text-xs text-pine-mid">Not available</div>
        </div>
      );
    }
    return (
      <div className="p-3 border border-sage-mid rounded-lg" data-testid={`storage-${label.toLowerCase()}`}>
        <div className="text-sm font-medium text-pine-deep">{label}</div>
        <div className="text-xs text-pine-mid font-mono truncate">{usage.path}</div>
        <div className="text-sm text-pine-deep mt-1">
          {formatGb(usage.used_gb)} used / {formatGb(usage.total_gb)}
        </div>
      </div>
    );
  };

  const renderInterfaces = () => {
    if (!systemInfo || systemInfo.network.interfaces.length === 0) {
      return <p className="text-sm text-pine-mid">No active interfaces detected</p>;
    }
    return (
      <ul className="space-y-2 text-sm text-pine-deep" data-testid="system-interfaces">
        {systemInfo.network.interfaces.map((iface) => (
          <li key={iface.name}>
            <span className="font-medium">{iface.name}:</span> {iface.ipv4.join(', ')}
          </li>
        ))}
      </ul>
    );
  };

  const renderAvailabilityNotes = () => {
    if (!availabilityNotes.length) {
      return (
        <div className="flex items-center gap-2 text-sm text-forest-green">
          <CheckCircle2 className="w-4 h-4" />
          <span>Registry is configured. Rescan if you add files on disk.</span>
        </div>
      );
    }
    return (
      <div className="space-y-1 text-sm text-terracotta" data-testid="availability-warnings">
        {availabilityNotes.map((note, idx) => (
          <div className="flex items-start gap-2" key={`${note}-${idx}`}>
            <AlertTriangle className="w-4 h-4 mt-0.5" />
            <span>{note}</span>
          </div>
        ))}
      </div>
    );
  };

  const diarizerOptions = capabilities?.diarizers ?? [];
  const selectedDiarizer = diarizerOptions.find((opt) => opt.key === defaultDiarizer);

  if (!isAdmin) {
    return (
      <div className="p-6 max-w-4xl mx-auto" data-testid="admin-access-guard">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-7 h-7 text-terracotta" />
          <div>
            <h1 className="text-2xl font-semibold text-pine-deep">Administration</h1>
            <p className="text-sm text-pine-mid">Only designated administrators can view these tools.</p>
          </div>
        </div>
        <div
          className="p-4 border border-dusty-rose bg-terracotta/5 rounded-lg text-sm text-pine-deep"
          data-testid="admin-locked"
        >
          Administration tools are limited to designated operators. Contact an administrator if you need access to global diarization controls or model registry management.
        </div>
      </div>
    );
  }

  const storageProject = systemInfo?.storage.project;
  const storagePercent = storageProject && storageProject.total_gb
    ? Math.min(100, Math.max(0, ((storageProject.used_gb ?? 0) / storageProject.total_gb) * 100))
    : null;

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex items-center gap-3 order-0">
        <Shield className="w-7 h-7 text-forest-green" />
        <div>
          <h1 className="text-2xl font-semibold text-pine-deep">Administration</h1>
          <p className="text-sm text-pine-mid">Advanced ASR, diarization, and infrastructure controls</p>
        </div>
      </div>

      <section className="bg-white border border-sage-mid rounded-lg p-6 order-2" data-testid="model-registry-section">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-pine-mid">Model Registry</p>
            <h2 className="text-lg font-medium text-pine-deep">Admin-managed providers</h2>
            <p className="text-sm text-pine-mid">
              Add model sets (providers) and concrete entries that point to files under {MODELS_ROOT}.
            </p>
          </div>
          <button
            onClick={handleAvailabilityRefresh}
            className="px-3 py-2 text-sm border border-sage-mid rounded-lg flex items-center gap-2 hover:border-forest-green transition"
            data-testid="rescan-availability"
          >
            <RefreshCw className="w-4 h-4" />
            Rescan availability
          </button>
        </div>

        {renderAvailabilityNotes()}

        <div className="mt-4">
          <div className="flex gap-2 mb-3">
            {(['asr', 'diarizer'] as RegistryTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => {
                  setRegistryTab(tab);
                  resetEntryForm();
                }}
                className={`px-3 py-2 rounded-lg border ${
                  registryTab === tab ? 'border-forest-green bg-forest-green/10 text-forest-green' : 'border-sage-mid text-pine-deep'
                }`}
                data-testid={`registry-tab-${tab}`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="border border-sage-mid rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-md font-semibold text-pine-deep">Model set</h3>
                <button
                  className="text-xs text-pine-mid flex items-center gap-1"
                  onClick={() => {
                    setSelectedSetId(null);
                    setSetForm({
                      id: null,
                      name: '',
                      description: '',
                      abs_path: '',
                      enabled: true,
                      disable_reason: '',
                    });
                    resetEntryForm();
                  }}
                  data-testid="new-set"
                >
                  <Plus className="w-3 h-3" /> New
                </button>
              </div>

              <label className="text-sm font-medium text-pine-deep">Choose set</label>
              <select
                value={selectedSetId ?? ''}
                onChange={(e) => setSelectedSetId(e.target.value ? Number(e.target.value) : null)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                data-testid="set-select"
                disabled={registryLoading || !filteredSets.length}
              >
                {!filteredSets.length && <option value="">No sets for this type</option>}
                {filteredSets.map((set) => (
                  <option key={set.id} value={set.id}>
                    {set.name}
                  </option>
                ))}
              </select>

              <label className="text-sm font-medium text-pine-deep">Name</label>
              <input
                value={setForm.name}
                onChange={(e) => setSetForm((prev) => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              />

              <label className="text-sm font-medium text-pine-deep">Description</label>
              <textarea
                value={setForm.description}
                onChange={(e) => setSetForm((prev) => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                rows={2}
              />

              <label className="text-sm font-medium text-pine-deep flex items-center gap-2">
                <FolderOpen className="w-4 h-4" />
                Model set path
              </label>
              <input
                value={setForm.abs_path}
                onChange={(e) => setSetForm((prev) => ({ ...prev, abs_path: e.target.value }))}
                placeholder={`${MODELS_ROOT}/<provider>`}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none font-mono text-sm"
              />

              <label className="flex items-center gap-2 text-sm text-pine-deep">
                <input
                  type="checkbox"
                  checked={setForm.enabled}
                  onChange={(e) => setSetForm((prev) => ({ ...prev, enabled: e.target.checked }))}
                  className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                />
                Enable this set
              </label>
              {!setForm.enabled && (
                <input
                  value={setForm.disable_reason}
                  onChange={(e) => setSetForm((prev) => ({ ...prev, disable_reason: e.target.value }))}
                  placeholder="Disable reason (required)"
                  className="w-full px-3 py-2 border border-terracotta rounded-lg text-sm"
                />
              )}

              <div className="flex gap-2 justify-between">
                <button
                  onClick={handleSaveSet}
                  className="flex-1 px-3 py-2 bg-forest-green text-white rounded-lg flex items-center gap-2 justify-center hover:bg-pine-deep transition disabled:opacity-50"
                  disabled={isSavingSet}
                  data-testid="save-set"
                >
                  <Save className="w-4 h-4" /> Save
                </button>
                {setForm.id && (
                  <button
                    onClick={handleDeleteSet}
                    className="px-3 py-2 border border-terracotta text-terracotta rounded-lg flex items-center gap-2 hover:bg-terracotta/10 transition"
                    data-testid="delete-set"
                  >
                    <Trash2 className="w-4 h-4" /> Delete
                  </button>
                )}
              </div>
            </div>


            <div className="lg:col-span-2 border border-sage-mid rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-md font-semibold text-pine-deep">Entries in set</h3>
                <button
                  className="text-xs text-pine-mid flex items-center gap-1"
                  onClick={resetEntryForm}
                  data-testid="new-entry"
                >
                  <Plus className="w-3 h-3" /> New entry
                </button>
              </div>
              {!filteredSets.length ? (
                <p className="text-sm text-pine-mid">Create a model set to add entries.</p>
              ) : activeEntries.length === 0 ? (
                <p className="text-sm text-pine-mid">No entries yet. Point to a model file under this set.</p>
              ) : (
                <div className="space-y-3" data-testid="entry-list">
                  {activeEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="border border-sage-mid rounded-lg p-3 flex flex-col md:flex-row md:items-center justify-between gap-3"
                      data-testid={`entry-${entry.id}`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-pine-deep">{entry.name}</span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${
                              entry.enabled ? 'bg-forest-green/10 text-forest-green' : 'bg-terracotta/10 text-terracotta'
                            }`}
                          >
                            {entry.enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                        <p className="text-xs text-pine-mid font-mono mt-1 truncate">{entry.abs_path}</p>
                        {entry.disable_reason && !entry.enabled && (
                          <p className="text-xs text-terracotta mt-1">Reason: {entry.disable_reason}</p>
                        )}
                      </div>
                      <div className="flex gap-2 flex-wrap">
                        <button
                          onClick={() => handleEditEntry(entry)}
                          className="px-3 py-2 border border-sage-mid rounded-lg text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleToggleEntry(entry)}
                          className="px-3 py-2 border border-sage-mid rounded-lg text-sm"
                          data-testid={`toggle-entry-${entry.id}`}
                        >
                          {entry.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          onClick={() => handleDeleteEntry(entry.id)}
                          className="px-3 py-2 border border-terracotta text-terracotta rounded-lg text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="border-t border-sage-mid pt-3">
                <h4 className="text-sm font-semibold text-pine-deep mb-2">
                  {entryForm.id ? 'Edit entry' : 'Add entry'}
                </h4>
                <div className="grid md:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-pine-deep">Name</label>
                    <input
                      value={entryForm.name}
                      onChange={(e) => setEntryForm((prev) => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                    />
                    <label className="text-sm font-medium text-pine-deep">Description</label>
                    <textarea
                      value={entryForm.description}
                      onChange={(e) => setEntryForm((prev) => ({ ...prev, description: e.target.value }))}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                      rows={2}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-pine-deep flex items-center gap-2">
                      <FolderOpen className="w-4 h-4" />
                      Entry path
                    </label>
                    <input
                      value={entryForm.abs_path}
                      onChange={(e) => setEntryForm((prev) => ({ ...prev, abs_path: e.target.value }))}
                      placeholder={`${MODELS_ROOT}/${activeSet?.name ?? '<set>'}/<entry>/...`}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none font-mono text-sm"
                    />
                    <label className="text-sm font-medium text-pine-deep">Checksum (optional)</label>
                    <input
                      value={entryForm.checksum}
                      onChange={(e) => setEntryForm((prev) => ({ ...prev, checksum: e.target.value }))}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                    />
                    <label className="flex items-center gap-2 text-sm text-pine-deep">
                      <input
                        type="checkbox"
                        checked={entryForm.enabled}
                        onChange={(e) => setEntryForm((prev) => ({ ...prev, enabled: e.target.checked }))}
                        className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                      />
                      Enable this entry
                    </label>
                    {!entryForm.enabled && (
                      <input
                        value={entryForm.disable_reason}
                        onChange={(e) => setEntryForm((prev) => ({ ...prev, disable_reason: e.target.value }))}
                        placeholder="Disable reason (required)"
                        className="w-full px-3 py-2 border border-terracotta rounded-lg text-sm"
                      />
                    )}
                  </div>
                </div>
                <div className="flex justify-end gap-2 mt-3">
                  <button
                    onClick={handleSaveEntry}
                    className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50"
                    disabled={isSavingEntry}
                    data-testid="save-entry"
                  >
                    Save entry
                  </button>
                  <button
                    onClick={resetEntryForm}
                    className="px-4 py-2 border border-sage-mid rounded-lg text-pine-deep"
                  >
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>


      <section className="bg-white border border-sage-mid rounded-lg p-6 order-1" data-testid="admin-advanced-settings">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-pine-mid">Administration</p>
            <h2 className="text-lg font-medium text-pine-deep">Advanced ASR & Diarization</h2>
            <p className="text-sm text-pine-mid">
              Manage global diarization policy, model registry availability, and per-job overrides.
            </p>
          </div>
          <span className="text-xs uppercase tracking-wide text-forest-green">Admin access granted</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="border border-sage-mid rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-md font-semibold text-pine-deep">Diarization Options</h3>
              {isLoadingCapabilities && <span className="text-xs text-pine-mid">Refreshing.</span>}
            </div>
            <label className="flex items-center text-sm text-pine-deep mb-3">
              <input
                type="checkbox"
                checked={diarizationEnabled}
                onChange={(e) => setDiarizationEnabled(e.target.checked)}
                className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                data-testid="default-diarization-enabled"
              />
              <span className="ml-2">Enable diarization globally</span>
            </label>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="default-diarizer" className="block text-sm font-medium text-pine-deep mb-1">
                  Default Diarizer
                </label>
                <select
                  id="default-diarizer"
                  value={defaultDiarizer}
                  onChange={(e) => setDefaultDiarizer(e.target.value)}
                  disabled={isLoadingCapabilities || !diarizationEnabled || !availableDiarizers.length}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                  data-testid="default-diarizer"
                  data-ready={(!isLoadingSettings && !isLoadingCapabilities).toString()}
                >
                  {!availableDiarizers.length && <option value="">No diarizers registered</option>}
                  {availableDiarizers.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.display_name}
                    </option>
                  ))}
                </select>
                {selectedDiarizer && !selectedDiarizer.available && (
                  <p className="text-xs text-terracotta mt-1">
                    {selectedDiarizer.notes.join(', ') || 'Not available on this system'}
                  </p>
                )}
              </div>
          <div>
            <label className="block text-sm font-medium text-pine-deep mb-1">Per-job Overrides</label>
            <label className="flex items-center text-sm text-pine-deep">
              <input
                type="checkbox"
                    checked={allowJobOverrides}
                    onChange={(e) => setAllowJobOverrides(e.target.checked)}
                    disabled={!diarizationEnabled}
                    className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green disabled:opacity-50"
                    data-testid="default-allow-overrides"
                  />
                  <span className="ml-2">Allow users to pick diarizer per job</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={handleSaveDiarizationDefaults}
                className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
              >
                Save Diarization Defaults
              </button>
            </div>
          </div>

          <div className="border border-sage-mid rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-md font-semibold text-pine-deep">ASR Providers</h3>
              <button
                type="button"
                className="text-xs text-pine-mid underline flex items-center gap-1"
                onClick={handleAvailabilityRefresh}
              >
                <RefreshCw className="w-3 h-3" /> Refresh
              </button>
            </div>
            <div className="mb-3">
              <label
                htmlFor="default-asr-provider"
                className="block text-sm font-medium text-pine-deep mb-1"
              >
                Default ASR Provider
              </label>
              <select
                id="default-asr-provider"
                value={defaultAsrProvider}
                onChange={(e) => setDefaultAsrProvider(e.target.value)}
                disabled={isLoadingCapabilities || !asrProviders.length}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                data-testid="default-asr-provider"
              >
                {!asrProviders.length && <option value="">No ASR providers registered</option>}
                {asrProviders.map((provider) => (
                  <option key={provider.provider} value={provider.provider}>
                    {provider.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="mb-3">
              <label
                htmlFor="default-asr-model"
                className="block text-sm font-medium text-pine-deep mb-1"
              >
                Default ASR Model
              </label>
              <select
                id="default-asr-model"
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                disabled={isLoadingCapabilities || !activeProviderModels.length}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                data-testid="default-asr-model"
              >
                {!activeProviderModels.length && <option value="">No ASR models registered</option>}
                {activeProviderModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
              {!activeProviderModels.length && (
                <p className="text-xs text-terracotta mt-1">Register and enable an ASR entry before users can create jobs.</p>
              )}
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {asrProviders.length === 0 && (
                <p className="text-sm text-pine-mid">No ASR providers registered.</p>
              )}
              {asrProviders.map((provider) => (
                <div key={provider.provider} className="p-3 border border-sage-light rounded" data-testid={`asr-provider-${provider.provider}`}>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-pine-deep">{provider.display_name}</p>
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded ${
                        provider.available ? 'bg-forest-green/10 text-forest-green' : 'bg-terracotta/10 text-terracotta'
                      }`}
                    >
                      {provider.available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                  <p className="text-xs text-pine-mid mt-1">Models: {provider.models.join(', ') || 'n/a'}</p>
                  {provider.notes.length > 0 && (
                    <ul className="mt-2 text-xs text-pine-mid list-disc list-inside space-y-1">
                      {provider.notes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-end mt-4">
              <button
                onClick={handleSaveAsrDefaults}
                className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
                data-testid="advanced-save"
              >
                Save ASR Defaults
              </button>
            </div>
          </div>

          <div className="border border-sage-mid rounded-lg p-4" data-testid="admin-throughput-card">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-md font-semibold text-pine-deep">Throughput & Storage</h3>
              <span className="text-xs text-pine-mid">Admin only</span>
            </div>
            <div>
              <label
                htmlFor="admin-max-concurrent"
                className="block text-sm font-medium text-pine-deep mb-1"
                data-testid="max-concurrent-label"
              >
                Max Concurrent Jobs: {maxConcurrentJobs}
              </label>
              <input
                id="admin-max-concurrent"
                type="range"
                min="1"
                max="5"
                value={maxConcurrentJobs}
                onChange={(e) => setMaxConcurrentJobs(Number(e.target.value))}
                className="w-full h-2 bg-sage-mid rounded-lg appearance-none cursor-pointer"
                data-testid="max-concurrent-jobs"
              />
              {/* Hidden numeric control keeps range testable in jsdom */}
              <input
                type="number"
                min="1"
                max="5"
                value={maxConcurrentJobs}
                onChange={(e) => setMaxConcurrentJobs(Number(e.target.value))}
                data-testid="max-concurrent-hidden-input"
                aria-hidden="true"
                tabIndex={-1}
                className="sr-only"
              />
              <div className="flex justify-between text-xs text-pine-mid mt-1">
                <span>1</span>
                <span>2</span>
                <span>3</span>
                <span>4</span>
                <span>5</span>
              </div>
              <p className="text-xs text-pine-mid mt-2">Applies globally; job queue restarts when this value changes.</p>
            </div>

              <div className="mt-4 p-3 border border-sage-light rounded bg-sage-light/40" data-testid="admin-storage-summary">
                <div className="flex items-center justify-between text-sm text-pine-deep">
                  <span className="font-semibold">Storage Used</span>
                  <span>
                    {storageProject && storageProject.total_gb
                    ? `${formatGb(storageProject.used_gb)} / ${formatGb(storageProject.total_gb)}`
                    : 'Detect system info'}
                </span>
              </div>
              <div className="w-full bg-sage-mid rounded-full h-2 mt-2">
                <div
                  className="bg-forest-green h-2 rounded-full transition-all"
                  style={{ width: `${storagePercent ?? 0}%` }}
                ></div>
              </div>
              <div className="flex items-center justify-between text-xs text-pine-mid mt-2">
                <span>Location</span>
                <span className="font-mono text-[11px]">
                  {storageProject?.path ?? 'Run Detect to load path'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>


      <section className="bg-white border border-sage-mid rounded-lg p-6 order-3" data-testid="system-section">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-medium text-pine-deep">System</h2>
            <p className="text-sm text-pine-mid">Host hardware snapshot for administrator decisions</p>
          </div>
          <button
            onClick={handleDetectSystem}
            disabled={isDetectingSystem}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50"
            data-testid="system-detect"
          >
            {isDetectingSystem ? 'Detecting.' : 'Detect'}
          </button>
        </div>
        <div className="border border-sage-mid rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-md font-semibold text-pine-deep">Time Zones</h3>
            <span className="text-xs text-pine-mid">Server + user display</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="server-time-zone" className="block text-sm font-medium text-pine-deep mb-1">
                Server Time Zone (admin)
              </label>
              <select
                id="server-time-zone"
                value={serverTimeZone}
                onChange={(e) => setServerTimeZone(e.target.value)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              >
                {timeZoneOptions.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
              <p className="text-xs text-pine-mid mt-1">
                {new Intl.DateTimeFormat(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  second: '2-digit',
                  timeZone: serverTimeZone || undefined,
                  timeZoneName: 'short',
                }).format(new Date())}
              </p>
            </div>
            <div>
              <label htmlFor="user-time-zone" className="block text-sm font-medium text-pine-deep mb-1">
                Your Display Time Zone
              </label>
              <select
                id="user-time-zone"
                value={userTimeZone}
                onChange={(e) => setUserTimeZone(e.target.value)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              >
                <option value="">{`Use browser default (${browserTimeZone})`}</option>
                {timeZoneOptions.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
              <p className="text-xs text-pine-mid mt-1">
                {new Intl.DateTimeFormat(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  second: '2-digit',
                  timeZone: userTimeZone || undefined,
                  timeZoneName: 'short',
                }).format(new Date())}
              </p>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={handleSaveTimeZones}
              className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
            >
              Save Time Zones
            </button>
          </div>
        </div>
        <div className="border border-sage-mid rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-md font-semibold text-pine-deep">Audio Handling</h3>
            <span className="text-xs text-pine-mid">Transcoding guardrail</span>
          </div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={transcodeToWav}
              onChange={(e) => setTranscodeToWav(e.target.checked)}
              className="mt-1"
            />
            <div>
              <p className="text-sm text-pine-deep font-medium">Transcode uploads to WAV (recommended)</p>
              <p className="text-xs text-pine-mid">
                Converts non-WAV inputs to WAV before transcription/diarization to avoid codec/backend issues on
                CPU-only hosts. Admins can disable this if they prefer raw inputs.
              </p>
            </div>
          </label>
          <div className="flex justify-end mt-4">
            <button
              onClick={handleSaveTimeZones}
              className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
            >
              Save System Settings
            </button>
          </div>
        </div>
        {isSystemLoading ? (
          <p className="text-sm text-pine-mid">Collecting system information.</p>
        ) : systemInfo ? (
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="system-summary">
              <div className="p-3 border border-sage-mid rounded-lg">
                <p className="text-xs uppercase text-pine-mid tracking-wide">OS</p>
                <p className="text-sm text-pine-deep">
                  {systemInfo.os.system} {systemInfo.os.release} ({systemInfo.os.machine})
                </p>
                {systemInfo.container.is_container && (
                  <p className="text-xs text-terracotta mt-1">Running inside container</p>
                )}
              </div>
              <div className="p-3 border border-sage-mid rounded-lg">
                <p className="text-xs uppercase text-pine-mid tracking-wide">CPU</p>
                <p className="text-sm text-pine-deep">
                  {systemInfo.cpu.model || 'Unknown'} · {systemInfo.cpu.cores_physical ?? '?'}c/
                  {systemInfo.cpu.cores_logical ?? '?'}t
                </p>
              </div>
              <div className="p-3 border border-sage-mid rounded-lg">
                <p className="text-xs uppercase text-pine-mid tracking-wide">Memory</p>
                <p className="text-sm text-pine-deep">
                  {formatGb(systemInfo.memory.total_gb)} total · {formatGb(systemInfo.memory.available_gb)} free
                </p>
              </div>
              <div className="p-3 border border-sage-mid rounded-lg" data-testid="system-gpu">
                <p className="text-xs uppercase text-pine-mid tracking-wide">GPU</p>
                {systemInfo.gpu.has_gpu && systemInfo.gpu.devices.length > 0 ? (
                  <ul className="text-sm text-pine-deep space-y-1">
                    {systemInfo.gpu.devices.map((device, index) => (
                      <li key={`${device.name}-${index}`}>
                        {device.name} · {formatGb(device.memory_gb)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-pine-mid">No GPU detected</p>
                )}
              </div>
              <div className="p-3 border border-sage-mid rounded-lg md:col-span-2 bg-sage-light/40">
                <p className="text-xs uppercase text-pine-mid tracking-wide">Recommended defaults</p>
                <p className="text-sm text-pine-deep">
                  ASR: <span className="font-semibold">{systemInfo.recommendation.suggested_asr_model}</span> ·
                  Diarization:{' '}
                  <span className="font-semibold">{systemInfo.recommendation.suggested_diarization}</span>
                </p>
                {systemInfo.recommendation.basis.length > 0 && (
                  <p className="text-xs text-pine-mid mt-1">
                    Basis: {systemInfo.recommendation.basis.join(', ')}
                  </p>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-pine-deep mb-2">Storage</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {renderDiskUsage('Database', systemInfo.storage.database)}
                {renderDiskUsage('Media', systemInfo.storage.media)}
                {renderDiskUsage('Transcripts', systemInfo.storage.transcripts)}
                {renderDiskUsage('Project', systemInfo.storage.project)}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-pine-deep mb-2">Network</h3>
              <div className="p-3 border border-sage-mid rounded-lg">
                <p className="text-sm text-pine-deep">
                  Hostname: <span className="font-mono">{systemInfo.network.hostname}</span>
                </p>
                <div className="mt-2">{renderInterfaces()}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 border border-sage-mid rounded-lg">
                <p className="text-xs uppercase text-pine-mid tracking-wide">Runtime</p>
                <p className="text-sm text-pine-deep">Python: {systemInfo.runtime.python}</p>
                <p className="text-sm text-pine-deep">
                  Node: {systemInfo.runtime.node ?? 'Not installed'}
                </p>
              </div>
              <div className="p-3 border border-sage-mid rounded-lg">
                <p className="text-xs uppercase text-pine-mid tracking-wide">Last detected</p>
                <p className="text-sm text-pine-deep">
                  {new Date(systemInfo.detected_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-pine-mid">System information unavailable.</p>
        )}

        <div className="mt-6 pt-4 border-t border-sage-mid space-y-3">
          <div className="flex gap-3 flex-wrap">
            <button
              onClick={handleRestartServer}
              className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition"
            >
              Restart Server
            </button>
            <button
              onClick={handleShutdownServer}
              className="px-4 py-2 bg-terracotta text-white rounded-lg hover:bg-red-700 transition"
            >
              Shutdown Server
            </button>
            <button
              onClick={handleFullRestartServer}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
            >
              Full Restart (Sentinel)
            </button>
          </div>
          <p className="text-xs text-pine-mid">
            Warning: System operations require administrator password and may interrupt ongoing transcriptions.
          </p>
          <p className="text-xs text-pine-mid">
            Full restart requires watchdog script <code>scripts/watch-restart.ps1</code> running.
          </p>
        </div>
      </section>
    </div>
  );
};
