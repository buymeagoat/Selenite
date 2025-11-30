import React, { useState, useEffect } from 'react';
import { TagList } from '../components/tags/TagList';
import { Settings as SettingsIcon, ChevronDown, ChevronUp } from 'lucide-react';
import { apiPut, ApiError } from '../lib/api';
import { fetchSettings, updateSettings } from '../services/settings';
import { fetchTags, deleteTag, type Tag } from '../services/tags';
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
import { useToast } from '../context/ToastContext';
import { devError, devInfo } from '../lib/debug';

export const Settings: React.FC = () => {
  const { showError, showSuccess } = useToast();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [defaultModel, setDefaultModel] = useState('medium');
  const [defaultLanguage, setDefaultLanguage] = useState('auto');
  const [defaultDiarizer, setDefaultDiarizer] = useState('vad');
  const [enableTimestamps, setEnableTimestamps] = useState(true);
  const [diarizationEnabled, setDiarizationEnabled] = useState(false);
  const [allowJobOverrides, setAllowJobOverrides] = useState(false);
  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3);
  const [tagsExpanded, setTagsExpanded] = useState(true);
  const [tags, setTags] = useState<Tag[]>([]);
  const [tagsLoaded, setTagsLoaded] = useState(false);
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [systemInfo, setSystemInfo] = useState<SystemProbe | null>(null);
  const [isSystemLoading, setIsSystemLoading] = useState(true);
  const [isDetectingSystem, setIsDetectingSystem] = useState(false);
  const [capabilities, setCapabilities] = useState<CapabilityResponse | null>(null);
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(true);
  const broadcastSettingsUpdated = () => {
    window.dispatchEvent(new CustomEvent('selenite:settings-updated'));
  };

  const [passwordMessage, setPasswordMessage] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');

  // Load settings and tags on mount
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const [settingsData, tagsData, systemData, capabilityData] = await Promise.all([
          fetchSettings(),
          fetchTags(),
          fetchSystemInfo(),
          fetchCapabilities()
        ]);
        
        if (!isMounted) {
          return;
        }
        setDefaultModel(settingsData.default_model);
        setDefaultLanguage(settingsData.default_language);
        setDefaultDiarizer(settingsData.default_diarizer);
        setDiarizationEnabled(settingsData.diarization_enabled);
        setAllowJobOverrides(settingsData.allow_job_overrides);
        setEnableTimestamps(settingsData.enable_timestamps);
        setMaxConcurrentJobs(settingsData.max_concurrent_jobs);
        setTags(tagsData.items);
        setTagsLoaded(true);
        setSystemInfo(systemData);
        setIsSystemLoading(false);
        setCapabilities(capabilityData);
        setIsLoadingCapabilities(false);
      } catch (error) {
        devError('Failed to load settings:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load settings: ${error.message}`);
        } else {
          showError('Failed to load settings. Please refresh the page.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingSettings(false);
          setTagsLoaded(true);
          setIsSystemLoading(false);
          setIsLoadingCapabilities(false);
        }
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [showError]);

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
    } catch (err) {
      if (err instanceof ApiError) {
        setPasswordError(err.message);
      } else {
        setPasswordError('Network error while changing password');
      }
    }
  };

  const buildSettingsPayload = () => ({
    default_model: defaultModel,
    default_language: defaultLanguage,
    default_diarizer: defaultDiarizer,
    diarization_enabled: diarizationEnabled,
    allow_job_overrides: allowJobOverrides,
    enable_timestamps: enableTimestamps,
    max_concurrent_jobs: maxConcurrentJobs,
  });

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

  const handleSavePerformance = async () => {
    try {
      await updateSettings(buildSettingsPayload());
      showSuccess('Performance settings saved');
      broadcastSettingsUpdated();
    } catch (error) {
      devError('Failed to save performance:', error);
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

  const handleDeleteTag = async (tagId: number) => {
    if (!confirm('Delete this tag? It will be removed from all jobs.')) {
      return;
    }
    
    try {
      const result = await deleteTag(tagId);
      setTags(tags.filter(t => t.id !== tagId));
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

  const handleRestartServer = async () => {
    if (!confirm('Are you sure you want to restart the server? This will briefly interrupt all operations.')) {
      return;
    }
    
    try {
      const response = await restartServer();
      showSuccess(response.message);
      // The server will restart and the connection will be lost momentarily
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
      // The server will shutdown
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

  const diarizerOptions =
    capabilities?.diarizers ?? [
      { key: 'whisperx', display_name: 'WhisperX', requires_gpu: true, available: true, notes: [] },
      { key: 'pyannote', display_name: 'Pyannote', requires_gpu: true, available: false, notes: ['GPU required'] },
      { key: 'vad', display_name: 'VAD + clustering', requires_gpu: false, available: true, notes: [] },
    ];
  const selectedDiarizer = diarizerOptions.find((opt) => opt.key === defaultDiarizer);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="w-7 h-7 text-forest-green" />
        <h1 className="text-2xl font-semibold text-pine-deep">Settings</h1>
      </div>

      {/* Account Section */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <h2 className="text-lg font-medium text-pine-deep mb-4">Account</h2>
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

      {/* Default Transcription Options */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <h2 className="text-lg font-medium text-pine-deep mb-4">Default Transcription Options</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="default-model" className="block text-sm font-medium text-pine-deep mb-1">
              Default Model
            </label>
            <select
              id="default-model"
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              data-testid="default-model"
            >
              <option value="tiny">Tiny (39M)</option>
              <option value="base">Base (74M)</option>
              <option value="small">Small (244M)</option>
              <option value="medium">Medium (769M)</option>
              <option value="large">Large (1550M v2)</option>
              <option value="large-v3">Large-v3 (latest)</option>
            </select>
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
            <label htmlFor="default-diarizer" className="block text-sm font-medium text-pine-deep mb-1">
              Default Diarizer
            </label>
            <select
              id="default-diarizer"
              value={defaultDiarizer}
              onChange={(e) => setDefaultDiarizer(e.target.value)}
              disabled={isLoadingCapabilities || !diarizationEnabled}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              data-testid="default-diarizer"
              data-ready={(!isLoadingSettings && !isLoadingCapabilities).toString()}
            >
              {diarizerOptions.map((option) => (
                <option key={option.key} value={option.key} disabled={!option.available}>
                  {option.display_name}
                  {!option.available
                    ? option.notes.length
                      ? ` (${option.notes.join(', ')})`
                      : ' (unavailable)'
                    : ''}
                </option>
              ))}
            </select>
            {isLoadingCapabilities && (
              <p className="text-xs text-pine-mid mt-1">Checking diarization availability...</p>
            )}
            {selectedDiarizer && !selectedDiarizer.available && (
              <p className="text-xs text-terracotta mt-1">
                {selectedDiarizer.notes.join(', ') || 'Not available on this system'}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label className="flex items-center text-sm text-pine-deep">
              <input
                type="checkbox"
                checked={enableTimestamps}
                onChange={(e) => setEnableTimestamps(e.target.checked)}
                className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                data-testid="default-timestamps"
              />
              <span className="ml-2">Include timestamps on new jobs</span>
            </label>
            <label className="flex items-center text-sm text-pine-deep">
              <input
                type="checkbox"
                checked={diarizationEnabled}
                onChange={(e) => setDiarizationEnabled(e.target.checked)}
                className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
                data-testid="default-diarization-enabled"
                data-ready={(!isLoadingSettings).toString()}
              />
              <span className="ml-2">Enable diarization</span>
            </label>
            <label className="flex items-center text-sm text-pine-deep pl-6">
              <input
                type="checkbox"
                checked={allowJobOverrides}
                onChange={(e) => setAllowJobOverrides(e.target.checked)}
                disabled={!diarizationEnabled}
                className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green disabled:opacity-50"
                data-testid="default-allow-overrides"
              />
              <span className="ml-2">
                Allow per-job overrides {diarizationEnabled ? '' : '(enable diarization first)'}
              </span>
            </label>
          </div>
          <button
            onClick={handleSaveDefaults}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
          >
            Save
          </button>
        </div>
      </section>

      {/* Performance */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <h2 className="text-lg font-medium text-pine-deep mb-4">Performance</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="max-concurrent" className="block text-sm font-medium text-pine-deep mb-1">
              Max Concurrent Jobs: {maxConcurrentJobs}
            </label>
            <input
              id="max-concurrent"
              type="range"
              min="1"
              max="5"
              value={maxConcurrentJobs}
              onChange={(e) => setMaxConcurrentJobs(Number(e.target.value))}
              className="w-full h-2 bg-sage-mid rounded-lg appearance-none cursor-pointer"
              data-testid="max-concurrent-jobs"
            />
            <div className="flex justify-between text-xs text-pine-mid mt-1">
              <span>1</span>
              <span>2</span>
              <span>3</span>
              <span>4</span>
              <span>5</span>
            </div>
          </div>
          <button
            onClick={handleSavePerformance}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
          >
            Save
          </button>
        </div>
      </section>

      {/* Storage */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <h2 className="text-lg font-medium text-pine-deep mb-4">Storage</h2>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-pine-mid">Used Space:</span>
            <span className="text-pine-deep font-medium">2.3 GB / 50 GB</span>
          </div>
          <div className="w-full bg-sage-mid rounded-full h-2">
            <div className="bg-forest-green h-2 rounded-full" style={{ width: '4.6%' }}></div>
          </div>
          <div className="flex justify-between text-sm mt-3">
            <span className="text-pine-mid">Location:</span>
            <span className="text-pine-deep font-mono text-xs">/storage</span>
          </div>
        </div>
      </section>

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
              <div data-testid="settings-tags-loaded">
                <TagList tags={tags} onEdit={handleEditTag} onDelete={handleDeleteTag} />
              </div>
            )}
          </div>
        )}
      </section>

      {/* System */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6" data-testid="system-section">
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
            {isDetectingSystem ? 'Detecting…' : 'Detect'}
          </button>
        </div>
        {isSystemLoading ? (
          <p className="text-sm text-pine-mid">Collecting system information…</p>
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
