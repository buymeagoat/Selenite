import React, { useState, useEffect } from 'react';
import { TagList } from '../components/tags/TagList';
import { Settings as SettingsIcon, ChevronDown, ChevronUp } from 'lucide-react';
import { apiPut, ApiError } from '../lib/api';
import { fetchSettings, updateSettings } from '../services/settings';
import { fetchTags, deleteTag, type Tag } from '../services/tags';
import { useToast } from '../context/ToastContext';

export const Settings: React.FC = () => {
  const { showError, showSuccess } = useToast();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [defaultModel, setDefaultModel] = useState('medium');
  const [defaultLanguage, setDefaultLanguage] = useState('auto');
  const [enableTimestamps, setEnableTimestamps] = useState(true);
  const [enableSpeakerDetection, setEnableSpeakerDetection] = useState(true);
  const [maxConcurrentJobs, setMaxConcurrentJobs] = useState(3);
  const [tagsExpanded, setTagsExpanded] = useState(true);
  const [tags, setTags] = useState<Tag[]>([]);
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);

  const [passwordMessage, setPasswordMessage] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');

  // Load settings and tags on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [settingsData, tagsData] = await Promise.all([
          fetchSettings(),
          fetchTags()
        ]);
        
        setDefaultModel(settingsData.default_model);
        setDefaultLanguage(settingsData.default_language);
        setMaxConcurrentJobs(settingsData.max_concurrent_jobs);
        setTags(tagsData.items);
      } catch (error) {
        console.error('Failed to load settings:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load settings: ${error.message}`);
        } else {
          showError('Failed to load settings. Please refresh the page.');
        }
      } finally {
        setIsLoadingSettings(false);
      }
    };

    loadData();
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

  const handleSaveDefaults = async () => {
    try {
      await updateSettings({
        default_model: defaultModel,
        default_language: defaultLanguage,
        max_concurrent_jobs: maxConcurrentJobs
      });
      showSuccess('Default transcription settings saved');
    } catch (error) {
      console.error('Failed to save defaults:', error);
      if (error instanceof ApiError) {
        showError(`Failed to save settings: ${error.message}`);
      } else {
        showError('Failed to save settings. Please try again.');
      }
    }
  };

  const handleSavePerformance = async () => {
    try {
      await updateSettings({
        default_model: defaultModel,
        default_language: defaultLanguage,
        max_concurrent_jobs: maxConcurrentJobs
      });
      showSuccess('Performance settings saved');
    } catch (error) {
      console.error('Failed to save performance:', error);
      if (error instanceof ApiError) {
        showError(`Failed to save settings: ${error.message}`);
      } else {
        showError('Failed to save settings. Please try again.');
      }
    }
  };

  const handleEditTag = (tagId: number) => {
    console.log('Edit tag:', tagId);
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
      console.error('Failed to delete tag:', error);
      if (error instanceof ApiError) {
        showError(`Failed to delete tag: ${error.message}`);
      } else {
        showError('Failed to delete tag. Please try again.');
      }
    }
  };

  const handleRestartServer = () => {
    const password = prompt('Enter admin password to restart server:');
    if (password) {
      console.log('Restart server (placeholder)');
      alert('Server restart not yet implemented');
    }
  };

  const handleShutdownServer = () => {
    const password = prompt('Enter admin password to shutdown server:');
    if (password && confirm('Are you sure? This will stop all transcriptions.')) {
      console.log('Shutdown server (placeholder)');
      alert('Server shutdown not yet implemented');
    }
  };

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
              <option value="large">Large (1550M)</option>
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
          <div className="flex items-center gap-2">
            <input
              id="default-timestamps"
              type="checkbox"
              checked={enableTimestamps}
              onChange={(e) => setEnableTimestamps(e.target.checked)}
              className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
            />
            <label htmlFor="default-timestamps" className="text-sm text-pine-deep">
              Enable Timestamps
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="default-speaker-detection"
              type="checkbox"
              checked={enableSpeakerDetection}
              onChange={(e) => setEnableSpeakerDetection(e.target.checked)}
              className="w-4 h-4 text-forest-green border-sage-mid rounded focus:ring-forest-green"
            />
            <label htmlFor="default-speaker-detection" className="text-sm text-pine-deep">
              Enable Speaker Detection
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
      <section className="mb-6 bg-white border border-sage-mid rounded-lg">
        <button
          onClick={() => setTagsExpanded(!tagsExpanded)}
          className="w-full flex items-center justify-between p-6 hover:bg-sage-light transition"
        >
          <h2 className="text-lg font-medium text-pine-deep">Tags</h2>
          {tagsExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        {tagsExpanded && (
          <div className="px-6 pb-6">
            <TagList tags={tags} onEdit={handleEditTag} onDelete={handleDeleteTag} />
          </div>
        )}
      </section>

      {/* System */}
      <section className="mb-6 bg-white border border-sage-mid rounded-lg p-6">
        <h2 className="text-lg font-medium text-pine-deep mb-4">System</h2>
        <div className="space-y-3">
          <div className="flex gap-3">
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
          </div>
          <p className="text-xs text-pine-mid">
            Warning: System operations require administrator password and may interrupt ongoing transcriptions.
          </p>
        </div>
      </section>
    </div>
  );
};
