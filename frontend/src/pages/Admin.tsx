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
  X,
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
  createModelWeight,
  createModelSet,
  deleteModelWeight,
  deleteModelSet,
  listModelSets,
  updateModelWeight,
  updateModelSet,
  type ModelWeight,
  type ModelSetWithWeights,
  type ProviderType,
} from '../services/modelRegistry';
import { browseFiles, type FileEntry } from '../services/fileBrowser';
import { devError, devInfo } from '../lib/debug';
import { getSupportedTimeZones, getBrowserTimeZone } from '../utils/timezones';

type RegistryTab = ProviderType;

const MODELS_ROOT = '/backend/models';
const CURATED_HELP = [
  'Providers are pre-seeded (disabled) with folders under /backend/models/<provider>/<weight>/. Drop weights there and enable model sets.',
  'ASR: whisper, faster-whisper, wav2vec2/transformers, nemo conformer-ctc, vosk, coqui-stt.',
  'Diarizers: pyannote pipeline, nemo-diarizer, speechbrain ecapa, resemblyzer clustering.',
];
const LAST_SET_KEY_PREFIX = 'selenite:last-registry-set';
const PROVIDER_EXPECTATIONS: Record<string, string> = {
  whisper: 'Place whisper .pt file (e.g., tiny.pt) inside /backend/models/whisper/<weight>/',
  'faster-whisper': 'Place CTranslate2 model folder inside /backend/models/faster-whisper/<weight>/',
  wav2vec2: 'Place HF checkpoint under /backend/models/wav2vec2/<weight>/',
  transformers: 'Place HF checkpoint under /backend/models/transformers/<weight>/',
  nemo: 'Place NeMo Conformer-CTC files under /backend/models/nemo/<weight>/',
  vosk: 'Place Vosk model folder under /backend/models/vosk/<weight>/',
  'coqui-stt': 'Place Coqui STT model folder under /backend/models/coqui-stt/<weight>/',
  'nemo-diarizer': 'Place NeMo diarization pipeline files under /backend/models/nemo-diarizer/<weight>/',
  pyannote: 'Place pyannote pipeline files under /backend/models/pyannote/<weight>/',
  speechbrain: 'Place SpeechBrain diarization artifacts under /backend/models/speechbrain/<weight>/',
  resemblyzer: 'Place encoder/clustering artifacts under /backend/models/resemblyzer/<weight>/',
};

interface SetFormState {
  id: number | null;
  name: string;
  description: string;
  abs_path: string;
  enabled: boolean;
  disable_reason: string;
}

interface WeightFormState {
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
  const [defaultDiarizerProvider, setDefaultDiarizerProvider] = useState('');
  const [enableTimestamps, setEnableTimestamps] = useState(true);
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [allowJobOverrides, setAllowJobOverrides] = useState(false);
  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3);
  const [transcodeToWav, setTranscodeToWav] = useState(true);
  const [enableEmptyWeights, setEnableEmptyWeights] = useState(false);
  const [userTimeZone, setUserTimeZone] = useState<string>(browserTimeZone);
  const [serverTimeZone, setServerTimeZone] = useState<string>('UTC');
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [systemInfo, setSystemInfo] = useState<SystemProbe | null>(null);
  const [isSystemLoading, setIsSystemLoading] = useState(true);
  const [isDetectingSystem, setIsDetectingSystem] = useState(false);
  const [capabilities, setCapabilities] = useState<CapabilityResponse | null>(null);
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(true);
  const [registryLoading, setRegistryLoading] = useState(true);
  const [registrySets, setRegistrySets] = useState<ModelSetWithWeights[]>([]);
  const [registryTab, setRegistryTab] = useState<RegistryTab>('asr');
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null);
  const [selectedSetName, setSelectedSetName] = useState<string>('');
  const [savedLastAsrSet, setSavedLastAsrSet] = useState<string>('');
  const [savedLastDiarizerSet, setSavedLastDiarizerSet] = useState<string>('');
  const [setForm, setSetForm] = useState<SetFormState>({
    id: null,
    name: '',
    description: '',
    abs_path: '',
    enabled: true,
    disable_reason: '',
  });
  const [weightForm, setWeightForm] = useState<WeightFormState>({
    id: null,
    name: '',
    description: '',
    abs_path: '',
    checksum: '',
    enabled: true,
    disable_reason: '',
  });
  const [isSavingSet, setIsSavingSet] = useState(false);
  const [isSavingWeight, setIsSavingWeight] = useState(false);
  const [isSavingAdminSettings, setIsSavingAdminSettings] = useState(false);
  const [availabilityNotes, setAvailabilityNotes] = useState<string[]>([]);
  const [isFileBrowserOpen, setIsFileBrowserOpen] = useState(false);
  const [fileBrowserScope, setFileBrowserScope] = useState<'models' | 'root'>('root');
  const [fileBrowserTarget, setFileBrowserTarget] = useState<'set' | 'weight' | null>(null);
  const [fileBrowserCwd, setFileBrowserCwd] = useState<string>('/');
  const [fileBrowserEntries, setFileBrowserEntries] = useState<FileEntry[]>([]);
  const [fileBrowserLoading, setFileBrowserLoading] = useState(false);
  const [fileBrowserError, setFileBrowserError] = useState<string | null>(null);
  const [fileBrowserSelected, setFileBrowserSelected] = useState<string>('');

  const toRelativeAppPath = (pathValue: string) => {
    const normalized = normalizePath(pathValue);
    if (!normalized) return normalized;
    const projectRoot = systemInfo?.storage?.project?.path
      ? normalizePath(systemInfo.storage.project.path)
      : '';
    if (projectRoot) {
      const rootLower = projectRoot.toLowerCase();
      const normLower = normalized.toLowerCase();
      if (normLower.startsWith(rootLower)) {
        const rel = normalized.slice(projectRoot.length);
        if (!rel) return '/';
        return rel.startsWith('/') ? rel : `/${rel}`;
      }
    }
    const backendIdx = normalized.toLowerCase().indexOf('/backend/');
    if (backendIdx !== -1) {
      return normalized.slice(backendIdx);
    }
    const storageIdx = normalized.toLowerCase().indexOf('/storage/');
    if (storageIdx !== -1) {
      return normalized.slice(storageIdx);
    }
    return normalized.startsWith('/') ? normalized : `/${normalized}`;
  };

  const broadcastSettingsUpdated = () => {
    window.dispatchEvent(new CustomEvent('selenite:settings-updated'));
  };

  const filteredSets = useMemo(
    () => registrySets.filter((set) => set.type === registryTab),
    [registrySets, registryTab]
  );
  const activeSet = filteredSets.find((set) => set.id === selectedSetId) ?? filteredSets[0];
  const activeWeights = activeSet?.weights ?? [];
  const activeSetHasWeightFiles = activeWeights.some(
    (weight) => (weight.has_weights ?? false) || enableEmptyWeights
  );
  const enableSetBlocked = !setForm.enabled && !activeSetHasWeightFiles;

  const registryAsrSets = useMemo(
    () => registrySets.filter((set) => set.type === 'asr'),
    [registrySets]
  );
  const asrProviderOptions = useMemo(() => {
    return registryAsrSets.map((set) => {
      const weights = set.weights.map((weight) => {
        const hasFiles = (weight.has_weights ?? false) || enableEmptyWeights;
        return {
          name: weight.name,
          enabled: weight.enabled,
          hasFiles,
        };
      });
      return {
        name: set.name,
        enabled: set.enabled,
        weights,
      };
    });
  }, [registryAsrSets, enableEmptyWeights]);
  const asrWeightsForSelectedProvider = useMemo(() => {
    if (!defaultAsrProvider) {
      return [];
    }
    const match = asrProviderOptions.find((provider) => provider.name === defaultAsrProvider);
    return match?.weights ?? [];
  }, [asrProviderOptions, defaultAsrProvider]);
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
        setDefaultDiarizerProvider(settingsData.default_diarizer_provider ?? '');
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
        setSavedLastAsrSet(settingsData.last_selected_asr_set ?? '');
        setSavedLastDiarizerSet(settingsData.last_selected_diarizer_set ?? '');
        debugSelection('loaded-settings', 'asr', {
          last_asr: settingsData.last_selected_asr_set,
          last_diar: settingsData.last_selected_diarizer_set,
        });
        if (registry.length > 0) {
          const storedName = getStoredSetName(registryTab);
          const setsForTab = registry.filter((s) => s.type === registryTab);
          const preferred =
            (storedName ? setsForTab.find((s) => s.name === storedName) : undefined) ??
            setsForTab[0] ??
            registry[0];
          if (preferred) {
            setRegistryTab(preferred.type);
            selectSetForTab(preferred.type, preferred.id, preferred.name);
            setSetForm(buildSetForm(preferred));
            debugSelection('initial-choose', preferred.type, {
              storedName,
              chosenId: preferred.id,
              chosenName: preferred.name,
            });
          }
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

  // Keep selection stable per tab and restore last chosen set for that tab
  useEffect(() => {
    applySelectionForTab(registryTab, registrySets, selectedSetId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registryTab, registrySets, savedLastAsrSet, savedLastDiarizerSet]);

  // Whenever selectedSetId changes, refresh the form to the current set
  useEffect(() => {
    if (!selectedSetId) return;
    const match = registrySets.find((s) => s.id === selectedSetId);
    if (match) {
      setSetForm(buildSetForm(match));
    }
  }, [selectedSetId, registrySets]);

  useEffect(() => {
    if (!capabilities) return;

    // Only fill in defaults when nothing is selected; do not override user choice if provider is missing/unavailable.
    if (!registryAsrSets.length) {
      if (defaultAsrProvider) {
        setDefaultAsrProvider('');
      }
      if (defaultModel) {
        setDefaultModel('');
      }
      return;
    }
    if (!defaultAsrProvider) {
      setDefaultAsrProvider(registryAsrSets[0].name);
      return;
    }
    if (!registryAsrSets.some((provider) => provider.name === defaultAsrProvider)) {
      setDefaultAsrProvider(registryAsrSets[0].name);
    }
  }, [registryAsrSets, capabilities, defaultAsrProvider, defaultModel]);

  useEffect(() => {
    if (!defaultAsrProvider) {
      if (defaultModel) {
        setDefaultModel('');
      }
      return;
    }
    if (!asrWeightsForSelectedProvider.length) {
      if (defaultModel) {
        setDefaultModel('');
      }
      return;
    }
    if (!asrWeightsForSelectedProvider.some((weight) => weight.name === defaultModel)) {
      setDefaultModel(asrWeightsForSelectedProvider[0].name);
    }
  }, [asrWeightsForSelectedProvider, defaultAsrProvider, defaultModel]);

  const collectAvailabilityNotes = (cap: CapabilityResponse | null): string[] => {
    if (!cap) return [];
    const notes: string[] = [];
    if (!cap.asr.length) {
      notes.push('No ASR models registered. Add an ASR set and weight to enable jobs.');
    }
    if (!cap.diarizers.length) {
      notes.push('No diarization weights registered.');
    }
    return notes;
  };

  const buildSetForm = (set: ModelSetWithWeights): SetFormState => ({
    id: set.id,
    name: set.name,
    description: set.description ?? '',
    abs_path: toRelativeAppPath(set.abs_path),
    enabled: set.enabled,
    disable_reason: set.disable_reason ?? '',
  });

  const resetWeightForm = () =>
    setWeightForm({
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
      return `Path must live under ${MODELS_ROOT}/<set>/<weight>`;
    }
    if (scopePath && !pathStartsWith(scopePath, normalized)) {
      return 'Weight path must live under its model set directory.';
    }
    return null;
  };

  const openFileBrowser = async (target: 'set' | 'weight', initialPath?: string) => {
    setFileBrowserTarget(target);
    setIsFileBrowserOpen(true);
    setFileBrowserLoading(true);
    setFileBrowserError(null);
    const startPath = initialPath && initialPath.trim() ? initialPath : MODELS_ROOT;
    try {
      const resp = await browseFiles(fileBrowserScope, startPath);
      setFileBrowserCwd(resp.cwd);
      setFileBrowserEntries(resp.entries);
      setFileBrowserSelected(resp.cwd);
    } catch (err) {
      setFileBrowserError(err instanceof Error ? err.message : 'Unable to browse files.');
    } finally {
      setFileBrowserLoading(false);
    }
  };

  const navigateFileBrowser = async (nextPath: string) => {
    setFileBrowserLoading(true);
    setFileBrowserError(null);
    try {
      const resp = await browseFiles(fileBrowserScope, nextPath);
      setFileBrowserCwd(resp.cwd);
      setFileBrowserEntries(resp.entries);
      setFileBrowserSelected(resp.cwd);
    } catch (err) {
      setFileBrowserError(err instanceof Error ? err.message : 'Unable to browse files.');
    } finally {
      setFileBrowserLoading(false);
    }
  };

  const applyFileBrowserSelection = () => {
    if (!fileBrowserTarget) return;
    const selectedPath = fileBrowserSelected || fileBrowserCwd;
    if (fileBrowserTarget === 'set') {
      setSetForm((prev) => ({ ...prev, abs_path: selectedPath.startsWith('/') ? selectedPath : `/${selectedPath}` }));
    } else {
      setWeightForm((prev) => ({ ...prev, abs_path: selectedPath.startsWith('/') ? selectedPath : `/${selectedPath}` }));
    }
    setIsFileBrowserOpen(false);
  };

  const parentPath = (cwd: string) => {
    if (cwd === '/' || cwd === '') return '/';
    const parts = cwd.split('/').filter(Boolean);
    parts.pop();
    return '/' + parts.join('/');
  };

  const rememberSelectedSet = (tab: RegistryTab, setId: number | null, setName: string | null) => {
    const key = `${LAST_SET_KEY_PREFIX}:${tab}`;
    if (setId && setName) {
      localStorage.setItem(key, setName);
    } else {
      localStorage.removeItem(key);
    }
  };

  const debugSelection = (action: string, tab: RegistryTab, payload: Record<string, unknown>) => {
    const detail = { tab, ...payload };
    devInfo(`[registry-select] ${action}`, detail);
  };

  const persistLastSelectedSet = async (tab: RegistryTab, setName: string | null) => {
    if (!setName) return;
    try {
      if (tab === 'asr') {
        await updateSettings({ last_selected_asr_set: setName || null });
      } else {
        await updateSettings({ last_selected_diarizer_set: setName || null });
      }
      debugSelection('persist', tab, { setName });
    } catch (err) {
      devError('Failed to persist last-selected set', err);
    }
  };

  const selectSetForTab = (tab: RegistryTab, setId: number | null, setName: string | null) => {
    setSelectedSetId(setId);
    setSelectedSetName(setName || '');
    if (setId && setName) {
      if (tab === 'asr') {
        setSavedLastAsrSet(setName);
      } else {
        setSavedLastDiarizerSet(setName);
      }
      rememberSelectedSet(tab, setId, setName);
      void persistLastSelectedSet(tab, setName);
      debugSelection('select', tab, { setId, setName });
    }
  };

  const getStoredSetName = (tab: RegistryTab): string | null => {
    if (tab === 'asr' && savedLastAsrSet) return savedLastAsrSet || null;
    if (tab === 'diarizer' && savedLastDiarizerSet) return savedLastDiarizerSet || null;
    const raw = localStorage.getItem(`${LAST_SET_KEY_PREFIX}:${tab}`);
    return raw || null;
  };

  const applySelectionForTab = (tab: RegistryTab, sets: ModelSetWithWeights[], currentId: number | null) => {
    const setsForTab = sets.filter((s) => s.type === tab);
    if (!setsForTab.length) {
      selectSetForTab(tab, null, '');
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

    const storedName = getStoredSetName(tab);
    const keepCurrent = currentId && setsForTab.some((s) => s.id === currentId) ? currentId : null;
    const chosen =
      setsForTab.find((s) => s.id === keepCurrent) ??
      (storedName ? setsForTab.find((s) => s.name === storedName) : undefined) ??
      (selectedSetName ? setsForTab.find((s) => s.name === selectedSetName) : undefined) ??
      setsForTab[0];

    if (chosen) {
      if (chosen.id !== selectedSetId || chosen.name !== selectedSetName) {
        selectSetForTab(tab, chosen.id, chosen.name);
      }
      debugSelection('apply', tab, {
        storedName,
        selectedSetId,
        selectedSetName,
        chosenId: chosen.id,
        chosenName: chosen.name,
      });
      setSetForm(buildSetForm(chosen));
    }
  };

  const refreshRegistry = async (preserveSelection = true) => {
    setRegistryLoading(true);
    try {
      const data = await listModelSets();
      setRegistrySets(data);
      if (!data.length) {
        selectSetForTab(registryTab, null, '');
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

      const setsForTab = data.filter((s) => s.type === registryTab);
      const preferredName =
        registryTab === 'asr' ? savedLastAsrSet || selectedSetName : savedLastDiarizerSet || selectedSetName;

      const chosen =
        (selectedSetId ? data.find((s) => s.id === selectedSetId) : undefined) ??
        (preferredName ? setsForTab.find((s) => s.name === preferredName) : undefined) ??
        (setsForTab.length ? setsForTab[0] : data[0]);

      if (chosen) {
        setRegistryTab(chosen.type);
        selectSetForTab(chosen.type, chosen.id, chosen.name);
        setSetForm(buildSetForm(chosen));
        debugSelection('refresh-choose', chosen.type, {
          selectedSetId,
          preferredName,
          chosenId: chosen.id,
          chosenName: chosen.name,
        });
      }
    } catch (error) {
      devError('Failed to refresh registry', error);
      showError('Failed to refresh model registry.');
    } finally {
      setRegistryLoading(false);
    }
  };

  const handleSaveSetMetadata = async () => {
    if (!isAdmin) return;
    const pathError = validatePath(setForm.abs_path);
    if (pathError) {
      showError(pathError);
      return;
    }
    setIsSavingSet(true);
    try {
      if (setForm.id) {
        await updateModelSet(setForm.id, {
          name: setForm.name,
          description: setForm.description || null,
          abs_path: setForm.abs_path,
        });
      } else {
        const created = await createModelSet({
          type: registryTab,
          name: setForm.name,
          description: setForm.description || null,
          abs_path: setForm.abs_path,
        });
        selectSetForTab(registryTab, created.id, created.name ?? setForm.name);
      }
      showSuccess('Model set metadata saved');
      await refreshRegistry(true);
    } catch (error) {
      devError('Failed to save set metadata', error);
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Unable to save model set metadata');
      }
    } finally {
      setIsSavingSet(false);
    }
  };

  const handleSaveSetAvailability = async (nextEnabled?: boolean) => {
    if (!isAdmin) return;
    if (!setForm.id) {
      showError('Save the model set metadata before updating availability.');
      return;
    }
    const targetEnabled = typeof nextEnabled === 'boolean' ? nextEnabled : setForm.enabled;
    const originalEnabled = activeSet?.id === setForm.id ? activeSet.enabled : setForm.enabled;
    const togglingSetOff = Boolean(originalEnabled && !targetEnabled);
    const needsDisableReason = togglingSetOff && !setForm.disable_reason.trim();
    if (needsDisableReason) {
      showError('Provide a disable reason when turning off a set.');
      return;
    }
    setIsSavingSet(true);
    try {
      await updateModelSet(setForm.id, {
        enabled: targetEnabled,
        disable_reason: setForm.disable_reason || null,
      });
      setSetForm((prev) => ({
        ...prev,
        enabled: targetEnabled,
        disable_reason: targetEnabled ? '' : prev.disable_reason,
      }));
      showSuccess('Model set availability updated');
      await refreshRegistry(true);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to update set availability', error);
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Unable to update model set availability');
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
      selectSetForTab(registryTab, null, '');
      await refreshRegistry(true);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to delete set', error);
      showError('Unable to delete model set.');
    }
  };

  const handleEditWeight = (entry: ModelWeight) => {
    setWeightForm({
      id: entry.id,
      name: entry.name,
      description: entry.description ?? '',
      abs_path: toRelativeAppPath(entry.abs_path),
      checksum: entry.checksum ?? '',
      enabled: entry.enabled,
      disable_reason: entry.disable_reason ?? '',
    });
  };

  const handleSaveWeightMetadata = async () => {
    if (!selectedSetId) {
      showError('Select a model set before adding entries.');
      return;
    }
    const pathError = validatePath(weightForm.abs_path, activeSet?.abs_path);
    if (pathError) {
      showError(pathError);
      return;
    }
    setIsSavingWeight(true);
    try {
      if (weightForm.id) {
        await updateModelWeight(weightForm.id, {
          name: weightForm.name,
          description: weightForm.description || null,
          abs_path: weightForm.abs_path,
          checksum: weightForm.checksum || null,
        });
      } else {
        await createModelWeight(selectedSetId, {
          name: weightForm.name,
          description: weightForm.description || null,
          abs_path: weightForm.abs_path,
          checksum: weightForm.checksum || null,
        });
      }
      showSuccess('Model weight metadata saved');
      resetWeightForm();
      await refreshRegistry(true);
    } catch (error) {
      devError('Failed to save weight metadata', error);
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Unable to save model weight metadata.');
      }
    } finally {
      setIsSavingWeight(false);
    }
  };

  const handleSaveWeightAvailability = async () => {
    if (!weightForm.id) {
      showError('Save the model weight metadata before updating availability.');
      return;
    }
    const originalWeight = activeSet?.weights?.find((weight) => weight.id === weightForm.id);
    const weightWasEnabled = originalWeight?.enabled ?? true;
    const togglingWeightOff = Boolean(weightWasEnabled && !weightForm.enabled);
    const missingFiles = weightForm.enabled && !selectedWeightHasFiles;
    if (missingFiles && !enableEmptyWeights) {
      showError('Weight files are missing. Enable Empty Weights to allow this.');
      return;
    }
    const requiresReason = togglingWeightOff && !weightForm.disable_reason.trim();
    if (requiresReason) {
      showError('Provide a disable reason when turning off a weight.');
      return;
    }
    setIsSavingWeight(true);
    try {
      await updateModelWeight(weightForm.id, {
        enabled: weightForm.enabled,
        disable_reason: weightForm.disable_reason || null,
      });
      showSuccess('Model weight availability updated');
      await refreshRegistry(true);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to update weight availability', error);
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Unable to update model weight availability.');
      }
    } finally {
      setIsSavingWeight(false);
    }
  };

  const handleDeleteWeight = async (weightId: number) => {
    if (!confirm('Delete this model weight?')) return;
    try {
      await deleteModelWeight(weightId);
      showSuccess('Model weight deleted');
      resetWeightForm();
      await refreshRegistry(true);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to delete weight', error);
      showError('Unable to delete model weight.');
    }
  };

  const handleToggleWeight = async (entry: ModelWeight) => {
    const targetState = !entry.enabled;
    const reason =
      targetState === false ? prompt('Provide a reason for disabling this weight', entry.disable_reason ?? '') : null;
    if (targetState === false && (!reason || !reason.trim())) {
      showError('Disable reason is required.');
      return;
    }
    try {
      await updateModelWeight(entry.id, {
        enabled: targetState,
        disable_reason: targetState ? null : reason,
      });
      showInfo(`Weight ${targetState ? 'enabled' : 'disabled'}`);
      await refreshRegistry(true);
      await handleAvailabilityRefresh();
    } catch (error) {
      devError('Failed to toggle weight', error);
      showError('Unable to update weight state.');
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
      const provider = defaultAsrProvider || null;
      const model = provider ? defaultModel || null : null;
      await updateAsrSettings({
        default_asr_provider: provider,
        default_model: model,
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
      const provider = diarizationEnabled ? defaultDiarizerProvider || null : null;
      const weight = provider ? defaultDiarizer || null : null;
      await updateDiarizationSettings({
        default_diarizer_provider: provider,
        default_diarizer: weight,
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

  const handleSaveAdministrationSettings = async () => {
    setIsSavingAdminSettings(true);
    try {
      const provider = defaultAsrProvider || null;
      const model = provider ? defaultModel || null : null;
      const diarProvider = diarizationEnabled ? defaultDiarizerProvider || null : null;
      const diarWeight = diarProvider ? defaultDiarizer || null : null;
      await updateSettings({
        default_asr_provider: provider,
        default_model: model,
        default_language: defaultLanguage || undefined,
        default_diarizer_provider: diarProvider,
        default_diarizer: diarWeight,
        diarization_enabled: diarizationEnabled,
        allow_job_overrides: allowJobOverrides,
        enable_timestamps: enableTimestamps,
        max_concurrent_jobs: maxConcurrentJobs,
        transcode_to_wav: transcodeToWav,
        enable_empty_weights: enableEmptyWeights,
      });

      showSuccess('Administration settings saved');
      broadcastSettingsUpdated();
    } catch (error) {
      devError('Failed to save administration settings:', error);
      const msg =
        error instanceof ApiError ? error.message : 'Failed to save administration settings. Please try again.';
      showError(msg);
    } finally {
      setIsSavingAdminSettings(false);
    }
  };

  const handleSaveTimeZones = async () => {
    try {
      await updateSettings({
        time_zone: userTimeZone || null,
        server_time_zone: serverTimeZone || 'UTC',
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
        <div className="text-xs text-pine-mid font-mono truncate">{toRelativeAppPath(usage.path)}</div>
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
    const visibleNotes = availabilityNotes.filter(
      (note) =>
        !note.includes('Weights not present') &&
        !note.includes('Missing dependency: nemo_toolkit')
    );
    if (!visibleNotes.length) {
      return (
        <div className="flex items-center gap-2 text-sm text-forest-green">
          <CheckCircle2 className="w-4 h-4" />
          <span>Registry is configured. Rescan if you add files on disk.</span>
        </div>
      );
    }
    return (
      <div className="space-y-1 text-sm text-terracotta" data-testid="availability-warnings">
        {visibleNotes.map((note, idx) => (
          <div className="flex items-start gap-2" key={`${note}-${idx}`}>
            <AlertTriangle className="w-4 h-4 mt-0.5" />
            <span>{note}</span>
          </div>
        ))}
      </div>
    );
  };

  const diarizerOptions = capabilities?.diarizers ?? [];
  const diarizerOptionMap = useMemo(() => {
    const map = new Map<string, CapabilityResponse['diarizers'][number]>();
    diarizerOptions.forEach((option) => map.set(option.key, option));
    return map;
  }, [diarizerOptions]);
  const registryDiarizerSets = useMemo(
    () => registrySets.filter((set) => set.type === 'diarizer'),
    [registrySets]
  );
  const diarizerProviders = useMemo(() => {
    return registryDiarizerSets.map((set) => {
      const weights = set.weights.map((weight) => {
        const weightHasFiles = (weight.has_weights ?? false) || enableEmptyWeights;
        const capability = diarizerOptionMap.get(weight.name);
        const available =
          Boolean(set.enabled && weight.enabled && weightHasFiles) &&
          (capability ? capability.available : true);
        return {
          key: weight.name,
          display_name: capability?.display_name ?? weight.name,
          available,
          notes: capability?.notes ?? [],
        };
      });
      return {
        name: set.name,
        available: weights.some((weight) => weight.available),
        weights,
      };
    });
  }, [registryDiarizerSets, diarizerOptionMap, enableEmptyWeights]);
  const weightsForSelectedProvider = useMemo(() => {
    if (!defaultDiarizerProvider) {
      return [];
    }
    const match = diarizerProviders.find((provider) => provider.name === defaultDiarizerProvider);
    return match?.weights ?? [];
  }, [defaultDiarizerProvider, diarizerProviders]);
  const selectedWeightMeta = activeSet?.weights.find((weight) => weight.id === weightForm.id);
  const selectedWeightHasFiles = Boolean(selectedWeightMeta?.has_weights);
  const selectedDiarizer = diarizerOptionMap.get(defaultDiarizer) ?? null;

  useEffect(() => {
    if (!diarizerProviders.length) {
      setDefaultDiarizerProvider('');
      return;
    }
    const providerFromWeight = defaultDiarizer
      ? diarizerProviders.find((provider) =>
          provider.weights.some((weight) => weight.key === defaultDiarizer)
        )
      : null;
    if (!defaultDiarizerProvider) {
      setDefaultDiarizerProvider((providerFromWeight ?? diarizerProviders[0]).name);
      return;
    }
    if (!diarizerProviders.find((provider) => provider.name === defaultDiarizerProvider)) {
      setDefaultDiarizerProvider(diarizerProviders[0].name);
      return;
    }
    if (providerFromWeight && providerFromWeight.name !== defaultDiarizerProvider) {
      setDefaultDiarizerProvider(providerFromWeight.name);
    }
  }, [defaultDiarizerProvider, defaultDiarizer, diarizerProviders]);

  useEffect(() => {
    if (!defaultDiarizerProvider) {
      if (defaultDiarizer) {
        setDefaultDiarizer('');
      }
      return;
    }
    if (!weightsForSelectedProvider.length) {
      if (defaultDiarizer) {
        setDefaultDiarizer('');
      }
      return;
    }
    if (!weightsForSelectedProvider.some((weight) => weight.key === defaultDiarizer)) {
      const fallback =
        weightsForSelectedProvider.find((weight) => weight.available) ||
        weightsForSelectedProvider[0];
      setDefaultDiarizer(fallback?.key ?? '');
    }
  }, [defaultDiarizerProvider, defaultDiarizer, weightsForSelectedProvider]);

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
    <>
      {isFileBrowserOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-sage-mid">
              <div className="flex flex-col">
                <h3 className="text-lg font-semibold text-pine-deep">Browse files</h3>
                <p className="text-xs text-pine-mid font-mono">{toRelativeAppPath(fileBrowserCwd)}</p>
              </div>
              <button
                className="text-pine-mid hover:text-pine-deep"
                onClick={() => setIsFileBrowserOpen(false)}
                aria-label="Close file browser"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-4 py-2 border-b border-sage-mid flex items-center gap-2 text-sm font-mono">
              <button
                className="px-2 py-1 border border-sage-mid rounded hover:bg-sage-light disabled:opacity-50"
                onClick={() => navigateFileBrowser(parentPath(fileBrowserCwd))}
                disabled={fileBrowserCwd === '/'}
              >
                Up
              </button>
              <span className="text-pine-mid">{toRelativeAppPath(fileBrowserCwd)}</span>
            </div>
            <div className="flex-1 overflow-auto">
              {fileBrowserError && <div className="p-3 text-sm text-terracotta">{fileBrowserError}</div>}
              {fileBrowserLoading ? (
                <div className="p-4 text-sm text-pine-mid">Loading...</div>
              ) : (
                <table className="min-w-full text-sm">
                  <tbody>
                    {fileBrowserEntries.map((entry) => (
                      <tr
                        key={entry.path}
                        className={`cursor-pointer hover:bg-sage-light ${
                          fileBrowserSelected === entry.path ? 'bg-sage-light/70' : ''
                        }`}
                        onClick={() => setFileBrowserSelected(entry.path)}
                        onDoubleClick={() =>
                          entry.is_dir ? navigateFileBrowser(entry.path) : setFileBrowserSelected(entry.path)
                        }
                      >
                        <td className="px-4 py-2 font-mono">
                          {entry.is_dir ? '📁' : '📄'} {entry.name}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="flex justify-end gap-2 px-4 py-3 border-t border-sage-mid">
              <button className="px-4 py-2 border border-sage-mid rounded-lg" onClick={() => setIsFileBrowserOpen(false)}>
                Cancel
              </button>
              <button
                className="px-4 py-2 bg-forest-green text-white rounded-lg disabled:opacity-50"
                onClick={applyFileBrowserSelection}
                disabled={!fileBrowserSelected && !fileBrowserCwd}
              >
                Select path
              </button>
            </div>
          </div>
        </div>
      )}
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
            <ul className="text-xs text-pine-mid mt-2 list-disc list-inside space-y-1">
              {CURATED_HELP.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
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
                  const storedName = getStoredSetName(tab);
                  if (storedName) {
                    const match = registrySets.find((s) => s.type === tab && s.name === storedName);
                    if (match) {
                      selectSetForTab(tab, match.id, match.name);
                    }
                  }
                  resetWeightForm();
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
                <h3 className="text-md font-semibold text-pine-deep">
                  {registryTab === 'asr' ? 'ASR Model Set' : 'Diarizer Model Set'}
                </h3>
                <button
                  className="text-xs text-pine-mid flex items-center gap-1"
                  onClick={() => {
                    selectSetForTab(registryTab, null, '');
                    setSetForm({
                      id: null,
                      name: '',
                      description: '',
                      abs_path: '',
                      enabled: false,
                      disable_reason: '',
                    });
                    resetWeightForm();
                  }}
                  data-testid="new-set"
                >
                  <Plus className="w-3 h-3" /> New
                </button>
              </div>

          <label className="text-sm font-medium text-pine-deep">Choose set</label>
              <select
                value={selectedSetId ?? ''}
                onChange={(e) => {
                  const id = e.target.value ? Number(e.target.value) : null;
                  const match = filteredSets.find((s) => s.id === id);
                  selectSetForTab(registryTab, id, match?.name ?? '');
                }}
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
              <div className="flex gap-2">
                <input
                  value={setForm.abs_path}
                  onChange={(e) => setSetForm((prev) => ({ ...prev, abs_path: e.target.value }))}
                  placeholder={`${MODELS_ROOT}/<provider>`}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none font-mono text-sm"
                />
                <button
                  type="button"
                  className="px-3 py-2 border border-sage-mid rounded-lg text-sm hover:bg-sage-light"
                  onClick={() => openFileBrowser('set', setForm.abs_path || MODELS_ROOT)}
                  data-testid="browse-set-path"
                >
                  Browse
                </button>
              </div>

              <span className="text-xs text-pine-mid">
                Status: <span className="font-medium">{setForm.enabled ? 'Enabled' : 'Disabled'}</span>
              </span>
              {!setForm.enabled && setForm.disable_reason.trim() && (
                <p className="text-xs text-terracotta">Disable reason: {setForm.disable_reason}</p>
              )}
              <input
                value={setForm.disable_reason}
                onChange={(e) => setSetForm((prev) => ({ ...prev, disable_reason: e.target.value }))}
                placeholder="Disable reason (required when disabling)"
                className="w-full px-3 py-2 border border-terracotta rounded-lg text-sm"
              />

              <div className="flex flex-wrap gap-2 justify-between">
                <button
                  onClick={handleSaveSetMetadata}
                  className="flex-1 px-3 py-2 bg-forest-green text-white rounded-lg flex items-center gap-2 justify-center hover:bg-pine-deep transition disabled:opacity-50"
                  disabled={isSavingSet}
                  data-testid="save-set-metadata"
                >
                  <Save className="w-4 h-4" /> Save
                </button>
                <button
                  onClick={() => handleSaveSetAvailability(!setForm.enabled)}
                  className="flex-1 px-3 py-2 border border-forest-green text-forest-green rounded-lg flex items-center gap-2 justify-center hover:bg-forest-green/10 transition disabled:opacity-50"
                  disabled={isSavingSet || !setForm.id || (enableSetBlocked && !setForm.enabled)}
                  data-testid="save-set-availability"
                  title={
                    !setForm.id
                      ? 'Save before updating availability.'
                      : enableSetBlocked && !setForm.enabled
                      ? 'Add at least one model weight (files present under /backend/models/...) before enabling this set.'
                      : undefined
                  }
                >
                  <Save className="w-4 h-4" /> {setForm.enabled ? 'Disable set' : 'Enable set'}
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
                <h3 className="text-md font-semibold text-pine-deep">
                  {registryTab === 'asr' ? 'ASR Model Set Weights' : 'Diarizer Model Set Weights'}
                </h3>
                <button
                  className="text-xs text-pine-mid flex items-center gap-1"
                  onClick={resetWeightForm}
                  data-testid="new-weight"
                >
                  <Plus className="w-3 h-3" /> New weight
                </button>
              </div>
              {!filteredSets.length ? (
                <p className="text-sm text-pine-mid">Create a model set to add entries.</p>
              ) : activeWeights.length === 0 ? (
                <p className="text-sm text-pine-mid">No entries yet. Point to a model file under this set.</p>
              ) : (
                <div className="space-y-3" data-testid="weight-list">
                  {activeWeights.map((entry) => {
                    const weightHasFiles = (entry.has_weights ?? false) || enableEmptyWeights;
                    const toggleBlocked = !entry.enabled && !weightHasFiles && !enableEmptyWeights;
                    return (
                      <div
                        key={entry.id}
                        className="border border-sage-mid rounded-lg p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                        data-testid={`weight-${entry.id}`}
                      >
                        <div className="space-y-1">
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
                          <p className="text-xs text-pine-mid font-mono truncate">
                            {toRelativeAppPath(entry.abs_path)}
                          </p>
                          {entry.disable_reason && !entry.enabled && (
                            <p className="text-xs text-terracotta">Reason: {entry.disable_reason}</p>
                          )}
                          {!weightHasFiles && !enableEmptyWeights && (
                            <p className="text-xs text-pine-mid">
                              Weight files not detected; add files under this path, then re-enable.
                            </p>
                          )}
                          {enableEmptyWeights && !weightHasFiles && (
                            <p className="text-xs text-amber-700">
                              Empty weights allowed. Files missing; jobs may fail until weights are added.
                            </p>
                          )}
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          <button
                            onClick={() => handleEditWeight(entry)}
                            className="px-3 py-2 border border-sage-mid rounded-lg text-sm"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleToggleWeight(entry)}
                            className="px-3 py-2 border border-sage-mid rounded-lg text-sm disabled:opacity-50"
                            data-testid={`toggle-weight-${entry.id}`}
                            disabled={toggleBlocked}
                            title={
                              toggleBlocked
                                ? 'Upload model weight files before enabling, or allow empty weights.'
                                : undefined
                            }
                          >
                            {entry.enabled ? 'Disable' : 'Enable'}
                          </button>
                          <button
                            onClick={() => handleDeleteWeight(entry.id)}
                            className="px-3 py-2 border border-terracotta text-terracotta rounded-lg text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="border-t border-sage-mid pt-3">
                <h4 className="text-sm font-semibold text-pine-deep mb-2">
                  {weightForm.id ? 'Edit weight' : 'Add weight'}
                </h4>
                <div className="grid md:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-pine-deep">Name</label>
                    <input
                      value={weightForm.name}
                      onChange={(e) => setWeightForm((prev) => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                    />
                    <label className="text-sm font-medium text-pine-deep">Description</label>
                    <textarea
                      value={weightForm.description}
                      onChange={(e) => setWeightForm((prev) => ({ ...prev, description: e.target.value }))}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                      rows={2}
                    />
                  </div>
                  <div className="space-y-2">
              <label className="text-sm font-medium text-pine-deep flex items-center gap-2">
                <FolderOpen className="w-4 h-4" />
                Entry path
              </label>
              <div className="flex gap-2">
                <input
                  value={weightForm.abs_path}
                  onChange={(e) => setWeightForm((prev) => ({ ...prev, abs_path: e.target.value }))}
                  placeholder={`${MODELS_ROOT}/${activeSet?.name ?? '<set>'}/<weight>/...`}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none font-mono text-sm"
                />
                <button
                  type="button"
                  className="px-3 py-2 border border-sage-mid rounded-lg text-sm hover:bg-sage-light"
                  onClick={() => openFileBrowser('weight', weightForm.abs_path || activeSet?.abs_path || MODELS_ROOT)}
                  data-testid="browse-weight-path"
                >
                  Browse
                </button>
              </div>
                    <label className="text-sm font-medium text-pine-deep">Checksum (optional)</label>
                    <input
                      value={weightForm.checksum}
                      onChange={(e) => setWeightForm((prev) => ({ ...prev, checksum: e.target.value }))}
                      className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                    />
                    <label className="flex items-center gap-2 text-sm text-pine-deep">
                      <input
                        type="checkbox"
                        checked={weightForm.enabled}
                        onChange={(e) =>
                          setWeightForm((prev) => ({
                            ...prev,
                            enabled: e.target.checked,
                          }))
                        }
                        className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                      />
                      Enable this weight
                    </label>
                    {!weightForm.enabled && (
                      <input
                        value={weightForm.disable_reason}
                        onChange={(e) => setWeightForm((prev) => ({ ...prev, disable_reason: e.target.value }))}
                        placeholder="Disable reason (required)"
                        className="w-full px-3 py-2 border border-terracotta rounded-lg text-sm"
                      />
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap justify-end gap-2 mt-3">
                  <button
                    onClick={handleSaveWeightMetadata}
                    className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50"
                    disabled={isSavingWeight}
                    data-testid="save-weight-metadata"
                  >
                    Save
                  </button>
                  <button
                    onClick={resetWeightForm}
                    className="px-4 py-2 border border-sage-mid rounded-lg text-pine-deep"
                  >
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>

          {!!filteredSets.length && (
            <div className="mt-4" data-testid="registry-set-summary">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-pine-deep">
                  {registryTab === 'asr' ? 'ASR Model Status' : 'Diarizer Model Status'}
                </h3>
                <span className="text-xs text-pine-mid">
                  {filteredSets.length} {filteredSets.length === 1 ? 'model' : 'models'}
                </span>
              </div>
              <div className="border border-sage-mid rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-sage-light text-pine-mid">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Model set</th>
                      <th className="text-left px-3 py-2 font-medium">Path</th>
                      <th className="text-left px-3 py-2 font-medium">Status</th>
                      <th className="text-left px-3 py-2 font-medium">Enabled weights</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSets.map((set) => {
                      const enabledWeights = set.weights.filter((w) => w.enabled);
                      const availableWeights = enabledWeights.filter(
                        (w) => (w.has_weights ?? false) || enableEmptyWeights
                      );
                      const showNames = enabledWeights.length ? enabledWeights.map((w) => w.name).join(', ') : 'None';
                      const statusLabel =
                        set.enabled && availableWeights.length
                          ? 'Available'
                          : set.enabled
                          ? 'Pending files'
                          : 'Unavailable';
                      const statusClass =
                        set.enabled && availableWeights.length
                          ? 'bg-forest-green/10 text-forest-green'
                          : 'bg-terracotta/10 text-terracotta';
                      return (
                        <tr
                          key={set.id}
                          className="border-t border-sage-mid hover:bg-sage-light/40"
                          data-testid={`${registryTab}-provider-${set.name}`}
                        >
                          <td className="px-3 py-2 font-semibold text-pine-deep">{set.name}</td>
                          <td className="px-3 py-2 text-xs text-pine-mid font-mono truncate">
                            {toRelativeAppPath(set.abs_path)}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`text-xs px-2 py-0.5 rounded ${statusClass}`}>{statusLabel}</span>
                          </td>
                          <td className="px-3 py-2 text-xs text-pine-deep">{showNames}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
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
                <label htmlFor="default-diarizer-provider" className="block text-sm font-medium text-pine-deep mb-1">
                  Default Diarizer Set
                </label>
                <select
                  id="default-diarizer-provider"
                  value={defaultDiarizerProvider}
                  onChange={(e) => {
                    const value = e.target.value;
                    setDefaultDiarizerProvider(value);
                    if (value !== defaultDiarizerProvider) {
                      setDefaultDiarizer('');
                    }
                  }}
                  disabled={
                    isLoadingCapabilities || !diarizationEnabled || !diarizerProviders.length
                  }
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                  data-testid="default-diarizer-provider"
                >
                  {!diarizerProviders.length && <option value="">No diarizers registered</option>}
                  {diarizerProviders.map((provider) => (
                    <option key={provider.name} value={provider.name}>
                      {provider.available ? provider.name : `${provider.name} (unavailable)`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="default-diarizer" className="block text-sm font-medium text-pine-deep mb-1">
                  Default Diarizer Weight
                </label>
                <select
                  id="default-diarizer"
                  value={defaultDiarizer}
                  onChange={(e) => setDefaultDiarizer(e.target.value)}
                  disabled={
                    isLoadingCapabilities ||
                    !diarizationEnabled ||
                    !weightsForSelectedProvider.length
                  }
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                  data-testid="default-diarizer"
                  data-ready={(!isLoadingSettings && !isLoadingCapabilities).toString()}
                >
                  {!weightsForSelectedProvider.length && (
                    <option value="">No weights registered</option>
                  )}
                  {weightsForSelectedProvider.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.display_name}
                      {!option.available
                        ? option.notes.length
                          ? ` (${option.notes.join(', ')})`
                          : ' (unavailable)'
                        : ''}
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
                  <div />
                </div>
              </div>

          <div className="border border-sage-mid rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-md font-semibold text-pine-deep">ASR Models</h3>
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
                Default ASR Model
              </label>
              <p className="text-xs text-pine-mid mb-2">
                Global default for all new jobs. The Model Registry tab remembers your last selection separately.
              </p>
              <select
                id="default-asr-provider"
                value={defaultAsrProvider}
                onChange={(e) => setDefaultAsrProvider(e.target.value)}
                disabled={isLoadingCapabilities || !registryAsrSets.length}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                data-testid="default-asr-provider"
              >
                {!registryAsrSets.length && <option value="">No ASR model sets registered</option>}
                {asrProviderOptions.map((provider) => (
                  <option key={provider.name} value={provider.name}>
                    {provider.enabled ? provider.name : `${provider.name} (disabled)`}
                  </option>
                ))}
              </select>
            </div>
            <div className="mb-3">
              <label
                htmlFor="default-asr-model"
                className="block text-sm font-medium text-pine-deep mb-1"
              >
                Default ASR Weight
              </label>
              <select
                id="default-asr-model"
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                disabled={isLoadingCapabilities || !asrWeightsForSelectedProvider.length}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                data-testid="default-asr-model"
              >
                {!asrWeightsForSelectedProvider.length && (
                  <option value="">No ASR weights registered for this set</option>
                )}
                {asrWeightsForSelectedProvider.map((weight) => (
                  <option key={weight.name} value={weight.name}>
                    {weight.enabled ? weight.name : `${weight.name} (disabled)`}
                  </option>
                ))}
              </select>
              {defaultAsrProvider && !asrWeightsForSelectedProvider.length && (
                <p className="text-xs text-terracotta mt-1">
                  No weights registered for this set. Add a weight under /backend/models/{defaultAsrProvider}/.
                </p>
              )}
            </div>
            <div className="flex justify-end mt-4" />
          </div>

          <div className="border border-amber-200 bg-amber-50 rounded-lg p-4" data-testid="admin-empty-weights">
            <h3 className="text-md font-semibold text-amber-900 mb-2">Enable Empty Weights</h3>
            <p className="text-xs text-amber-800">
              When enabled, administrators can turn on weights even if files are missing. Jobs may fail until files are
              added.
            </p>
            <label className="mt-3 flex items-center gap-2 text-sm text-amber-900">
              <input
                type="checkbox"
                checked={enableEmptyWeights}
                onChange={(e) => setEnableEmptyWeights(e.target.checked)}
                className="w-4 h-4 text-amber-700 border-amber-300 rounded focus:ring-amber-400"
              />
              Enable empty weights
            </label>
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
                  {storageProject?.path ? toRelativeAppPath(storageProject.path) : 'Run Detect to load path'}
                </span>
              </div>
            </div>
          </div>

          <div className="border border-sage-mid rounded-lg p-4" data-testid="audio-handling-card">
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
            <div className="flex justify-end mt-4" />
          </div>

        </div>
        <div className="flex justify-end mt-4">
          <button
            onClick={handleSaveAdministrationSettings}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50"
            disabled={isSavingAdminSettings}
            data-testid="admin-save-all"
          >
            {isSavingAdminSettings ? 'Saving...' : 'Save'}
          </button>
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
    </>
  );
};
