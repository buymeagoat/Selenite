import React, { useState, useEffect } from 'react';
import { TagList } from '../components/tags/TagList';
import { Settings as SettingsIcon, ChevronDown, ChevronUp } from 'lucide-react';
import { apiPut, ApiError } from '../lib/api';
import { fetchSettings, updateSettings } from '../services/settings';
import { fetchTags, deleteTag, type Tag } from '../services/tags';
import { useToast } from '../context/ToastContext';
import { devError, devInfo } from '../lib/debug';
import { getSupportedTimeZones, getBrowserTimeZone } from '../utils/timezones';

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
  const [allowAsrOverrides, setAllowAsrOverrides] = useState(false);
  const [allowDiarizerOverrides, setAllowDiarizerOverrides] = useState(false);
  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3);
  const [timeZone, setTimeZone] = useState<string>(getBrowserTimeZone());
  const [tagsExpanded, setTagsExpanded] = useState(true);
  const [tags, setTags] = useState<Tag[]>([]);
  const [tagsLoaded, setTagsLoaded] = useState(false);
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const broadcastSettingsUpdated = () => {
    window.dispatchEvent(new CustomEvent('selenite:settings-updated'));
  };

  const [passwordMessage, setPasswordMessage] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');
  const timeZoneOptions = getSupportedTimeZones();
  const browserTimeZone = getBrowserTimeZone();

  // Load settings and tags on mount
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const [settingsData, tagsData] = await Promise.all([
          fetchSettings(),
          fetchTags()
        ]);
        
        if (!isMounted) {
          return;
        }
        setDefaultModel(settingsData.default_model);
        setDefaultLanguage(settingsData.default_language);
        setDefaultDiarizer(settingsData.default_diarizer);
        setDiarizationEnabled(settingsData.diarization_enabled);
        setAllowAsrOverrides(settingsData.allow_asr_overrides);
        setAllowDiarizerOverrides(settingsData.allow_diarizer_overrides);
        setEnableTimestamps(settingsData.enable_timestamps);
        setMaxConcurrentJobs(settingsData.max_concurrent_jobs);
        setTimeZone(settingsData.time_zone || getBrowserTimeZone());
        setTags(tagsData.items);
        setTagsLoaded(true);
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
    allow_asr_overrides: allowAsrOverrides,
    allow_diarizer_overrides: allowDiarizerOverrides,
    enable_timestamps: enableTimestamps,
    max_concurrent_jobs: maxConcurrentJobs,
    time_zone: timeZone || null,
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

  

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="w-7 h-7 text-forest-green" />
        <div>
          <h1 className="text-2xl font-semibold text-pine-deep">Settings</h1>
          <p className="text-sm text-pine-mid">Workspace defaults visible to every user plus a gated administration area.</p>
        </div>
      </div>

      <div className="mb-4" data-testid="workspace-settings-header">
        <p className="text-xs uppercase tracking-wide text-pine-mid">Workspace</p>
        <h2 className="text-lg font-semibold text-pine-deep">Shared Defaults</h2>
        <p className="text-sm text-pine-mid">
          Applies to new jobs for every account. Throughput limits and storage telemetry now live under the Admin console.
        </p>
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

      {/* Default Transcription Options (user-facing) */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-pine-deep">Default Transcription Options</h2>
          <span className="text-xs uppercase tracking-wide text-pine-mid">Visible to all users</span>
        </div>
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

      <section className="mb-6 border border-dusty-rose bg-terracotta/5 rounded-lg p-4" data-testid="settings-admin-redirect">
        <p className="text-sm text-pine-deep">
          Need to adjust concurrency limits or inspect storage usage? Those controls now reside on the Admin page.
        </p>
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
    </div>
  );
};
