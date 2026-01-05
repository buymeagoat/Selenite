import React, { useState, useEffect, useMemo, useRef } from 'react';
import JSZip from 'jszip';
import { JobCard } from '../components/jobs/JobCard';
import { NewJobModal } from '../components/modals/NewJobModal';
import { JobDetailModal } from '../components/modals/JobDetailModal';
import { SearchBar } from '../components/common/SearchBar';
import { JobFilters } from '../components/jobs/JobFilters';
import { SkeletonGrid } from '../components/common/Skeleton';
import { usePolling } from '../hooks/usePolling';
import {
  fetchJobs,
  createJob,
  cancelJob,
  pauseJob,
  resumeJob,
  deleteJob,
  assignTag,
  renameJob,
  type Job,
} from '../services/jobs';
import { createTag, fetchTags, type Tag } from '../services/tags';
import { TAG_COLOR_PALETTE, pickTagColor } from '../components/tags/tagColors';
import { ApiError, API_BASE_URL } from '../lib/api';
import { useToast } from '../context/ToastContext';
import { useAdminSettings } from '../context/SettingsContext';
import { devError } from '../lib/debug';
import { updateSettings } from '../services/settings';
import { useAuth } from '../context/AuthContext';

type RestartPrefill = {
  file: File;
  jobName?: string;
  provider?: string | null;
  model?: string | null;
  language?: string | null;
  enableTimestamps?: boolean;
  enableSpeakerDetection?: boolean;
  diarizer?: string | null;
  diarizerProvider?: string | null;
  speakerCount?: number | null;
  extraFlags?: string;
};

export const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNewJobModalOpen, setIsNewJobModalOpen] = useState(false);
  const [restartPrefill, setRestartPrefill] = useState<RestartPrefill | null>(null);
  const [isRestartPreparing, setIsRestartPreparing] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkTagSelection, setBulkTagSelection] = useState<string>('');
  const [isBulkDownloadSubmitting, setIsBulkDownloadSubmitting] = useState(false);
  const [isBulkDownloadModalOpen, setIsBulkDownloadModalOpen] = useState(false);
  const [bulkDownloadFormat, setBulkDownloadFormat] = useState('txt');
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [renameError, setRenameError] = useState('');
  const [isRenameSubmitting, setIsRenameSubmitting] = useState(false);
  const [isBulkTagModalOpen, setIsBulkTagModalOpen] = useState(false);
  const [customTagName, setCustomTagName] = useState('');
  const [customTagColor, setCustomTagColor] = useState<string>(TAG_COLOR_PALETTE[0]);
  const [bulkTagError, setBulkTagError] = useState('');
  const [isBulkTagSubmitting, setIsBulkTagSubmitting] = useState(false);
  const [isCustomRangeOpen, setIsCustomRangeOpen] = useState(false);
  const [customRangeStartDate, setCustomRangeStartDate] = useState('');
  const [customRangeStartTime, setCustomRangeStartTime] = useState('');
  const [customRangeStartMeridiem, setCustomRangeStartMeridiem] = useState<'AM' | 'PM'>('AM');
  const [customRangeEndDate, setCustomRangeEndDate] = useState('');
  const [customRangeEndTime, setCustomRangeEndTime] = useState('');
  const [customRangeEndMeridiem, setCustomRangeEndMeridiem] = useState<'AM' | 'PM'>('AM');
  const [customRangeError, setCustomRangeError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<{status?: string; dateRange?: string; tags?: number[]}>({});
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const selectAllRef = useRef<HTMLInputElement | null>(null);
  const [audioJobId, setAudioJobId] = useState<string | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioPosition, setAudioPosition] = useState(0);
  const [audioRate, setAudioRate] = useState(1);
  const [streamActive, setStreamActive] = useState(false);
  const [streamStale, setStreamStale] = useState(false);
  const streamRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const lastStreamEventRef = useRef(0);
  const { showError, showSuccess } = useToast();
  const { user } = useAuth();
  const isAdmin = Boolean(user?.is_admin);
  const {
    settings: adminSettings,
    error: adminSettingsError,
    refresh: refreshSettings,
  } = useAdminSettings();
  const effectiveTimeZone = adminSettings?.time_zone || adminSettings?.server_time_zone || null;
  const downloadTimeZone = adminSettings?.time_zone || null;
  const [showAllJobs, setShowAllJobs] = useState(false);
  const settingsErrorNotified = useRef(false);

  useEffect(() => {
    if (adminSettingsError && !settingsErrorNotified.current) {
      showError(`Failed to load admin settings: ${adminSettingsError}`);
      settingsErrorNotified.current = true;
    }
    if (!adminSettingsError) {
      settingsErrorNotified.current = false;
    }
  }, [adminSettingsError, showError]);

  useEffect(() => {
    if (adminSettings && typeof adminSettings.show_all_jobs === 'boolean') {
      setShowAllJobs(adminSettings.show_all_jobs);
    }
  }, [adminSettings]);

  useEffect(() => {
    // Load jobs from API
    const loadJobs = async () => {
      setIsLoading(true);
      try {
        const [jobResp, tagResp] = await Promise.all([fetchJobs(), fetchTags()]);
        setJobs(jobResp.items);
        setTags(tagResp.items);
      } catch (error) {
        devError('Failed to load jobs:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load jobs: ${error.message}`);
        } else {
          showError('Failed to load jobs. Please check your connection.');
        }
        // Set empty array on error to show empty state
        setJobs([]);
        setTags([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadJobs();
  }, [showError]);

  useEffect(() => {
    if (!customTagName.trim()) {
      setCustomTagColor(pickTagColor(tags));
    }
  }, [customTagName, tags]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('EventSource' in window)) {
      return;
    }
    const token = localStorage.getItem('auth_token');
    if (!token) {
      return;
    }

    const streamUrl = `${API_BASE_URL}/jobs/stream?token=${encodeURIComponent(token)}`;
    const retryBaseMs = 1000;
    const retryMaxMs = 30000;
    const heartbeatTimeoutMs = 12000;
    const heartbeatCheckMs = 3000;
    let disposed = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const closeStream = () => {
      if (streamRef.current) {
        streamRef.current.close();
        streamRef.current = null;
      }
    };

    const handleHeartbeat = () => {
      lastStreamEventRef.current = Date.now();
      if (!disposed) {
        setStreamStale(false);
      }
    };

    function connectStream() {
      closeStream();
      setStreamActive(false);
      setStreamStale(false);

      const source = new EventSource(streamUrl);
      streamRef.current = source;

      source.onopen = () => {
        if (disposed) return;
        reconnectAttemptRef.current = 0;
        lastStreamEventRef.current = Date.now();
        setStreamActive(true);
        setStreamStale(false);
      };

      source.addEventListener('jobs', (event) => {
        lastStreamEventRef.current = Date.now();
        if (!disposed) {
          setStreamStale(false);
        }
        try {
          const payload = JSON.parse((event as MessageEvent).data);
          if (payload?.items) {
            setJobs(payload.items);
          }
        } catch (error) {
          devError('Failed to parse job stream payload:', error);
        }
      });

      source.addEventListener('heartbeat', handleHeartbeat);

      source.addEventListener('error', () => {
        if (disposed) return;
        setStreamActive(false);
        setStreamStale(true);
        closeStream();
        scheduleReconnect();
      });
    }

    function scheduleReconnect() {
      if (disposed || reconnectTimerRef.current) return;
      const attempt = reconnectAttemptRef.current + 1;
      reconnectAttemptRef.current = attempt;
      const delay = Math.min(retryMaxMs, retryBaseMs * Math.pow(2, attempt - 1));
      const jitter = Math.floor(Math.random() * 500);
      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        connectStream();
      }, delay + jitter);
    }

    connectStream();

    const heartbeatTimer = window.setInterval(() => {
      if (disposed || !streamRef.current || !lastStreamEventRef.current) {
        return;
      }
      const ageMs = Date.now() - lastStreamEventRef.current;
      if (ageMs > heartbeatTimeoutMs) {
        setStreamActive(false);
        setStreamStale(true);
        closeStream();
        scheduleReconnect();
      }
    }, heartbeatCheckMs);

    return () => {
      disposed = true;
      clearReconnectTimer();
      window.clearInterval(heartbeatTimer);
      closeStream();
    };
  }, []);

  // Poll for job updates (fast when active, slow when idle)
  const hasProcessingJobs = jobs.some(
    (j) => ['processing', 'queued', 'cancelling', 'pausing'].includes(j.status)
  );
  const shouldPoll = !streamActive || streamStale;
  const pollingIntervalMs = hasProcessingJobs ? 2000 : 15000;
  
  const fetchJobUpdates = async () => {
    // Fetch latest job data from API
    try {
      const response = await fetchJobs();
      setJobs(response.items);
      setSelectedIds((prev) => {
        if (!prev.size) return prev;
        const visibleIds = new Set(response.items.map((job) => job.id));
        return new Set([...prev].filter((id) => visibleIds.has(id)));
      });
    } catch (error) {
      devError('Failed to poll job updates:', error);
      // Continue polling on error (don't stop polling for temporary failures)
    }
  };

  usePolling(fetchJobUpdates, {
    enabled: !isLoading && shouldPoll,
    interval: pollingIntervalMs
  });

  const handleJobClick = (jobId: string) => {
    // TODO: Fetch full job details from API
    const job = jobs.find(j => j.id === jobId);
    if (job) {
      setSelectedJob({
        ...job,
        file_size: job.file_size || 15728640,
        duration: job.duration || 1834,
        model_used: job.model_used || 'medium',
        language_detected: job.language_detected || 'English',
        speaker_count: job.speaker_count || 1,
        completed_at: job.completed_at || job.created_at
      });
    }
  };

  const handleNewJob = async (jobData: {
    file: File;
    provider?: string;
    model?: string;
    language?: string;
    jobName?: string;
    enableTimestamps: boolean;
    enableSpeakerDetection: boolean;
    diarizer?: string | null;
    speakerCount?: number | null;
    extraFlags?: string;
  }) => {
    try {
      const response = await createJob({
        file: jobData.file,
        job_name: jobData.jobName?.trim() || undefined,
        provider: jobData.provider,
        model: jobData.model,
        language: jobData.language,
        enable_timestamps: jobData.enableTimestamps,
        enable_speaker_detection: jobData.enableSpeakerDetection,
        diarizer: jobData.diarizer ?? undefined,
        speaker_count: jobData.speakerCount ?? undefined,
        extra_flags: jobData.extraFlags,
      });
      
      showSuccess(`Job created successfully: ${response.original_filename}`);
      
      // Refresh job list to show new job
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
    } catch (error) {
      devError('Failed to create job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to create job: ${error.message}`);
      } else {
        showError('Failed to create job. Please try again.');
      }
      throw error; // Re-throw so modal can handle the error state
    }
  };

  const handleToggleAllJobs = async (nextValue: boolean) => {
    if (!isAdmin) return;
    setShowAllJobs(nextValue);
    try {
      await updateSettings({ show_all_jobs: nextValue });
      await refreshSettings({ force: true });
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
    } catch (error) {
      devError('Failed to update job visibility:', error);
      showError('Failed to update job visibility. Please try again.');
      setShowAllJobs((prev) => !prev);
    }
  };

  const cleanupAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    setIsAudioPlaying(false);
    setAudioJobId(null);
    setAudioPosition(0);
    setAudioDuration(0);
  };

  const handlePlay = async (jobId: string) => {
    // Toggle if same job
    if (audioJobId === jobId && audioRef.current) {
      if (audioRef.current.paused) {
        await audioRef.current.play();
        setIsAudioPlaying(true);
      } else {
        audioRef.current.pause();
        setIsAudioPlaying(false);
      }
      return;
    }

    cleanupAudio();
    const token = localStorage.getItem('auth_token');
    const url = `${API_BASE_URL}/jobs/${jobId}/media`;
    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error('Unable to fetch media');
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const audio = new Audio(objectUrl);
      audio.playbackRate = audioRate;
      audio.addEventListener('timeupdate', () => {
        setAudioPosition(audio.currentTime);
        setAudioDuration(audio.duration || 0);
      });
      audio.addEventListener('loadedmetadata', () => {
        setAudioDuration(audio.duration || 0);
      });
      audio.addEventListener('ended', () => {
        setIsAudioPlaying(false);
      });
      audioRef.current = audio;
      setAudioJobId(jobId);
      await audio.play();
      setIsAudioPlaying(true);
      showSuccess('Playing media');
    } catch (error: any) {
      devError('Play failed:', error);
      showError(error?.message || 'Failed to play media');
    }
  };

  const handleStopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsAudioPlaying(false);
    setAudioPosition(0);
  };

  const handleSeekAudio = (jobId: string, percent: number) => {
    if (audioRef.current && audioJobId === jobId && audioDuration) {
      const newTime = (percent / 100) * audioDuration;
      audioRef.current.currentTime = newTime;
      setAudioPosition(newTime);
    }
  };

  const handleSpeedAudio = (jobId: string) => {
    if (!audioRef.current || audioJobId !== jobId) return;
    const speeds = [0.5, 1, 2, 4];
    const next = speeds[(speeds.indexOf(audioRate) + 1) % speeds.length];
    setAudioRate(next);
    audioRef.current.playbackRate = next;
    showSuccess(`Speed: ${next}x`);
  };

  const handleDownload = async (jobId: string, format: string) => {
    const token = localStorage.getItem('auth_token');
    const url = `${API_BASE_URL}/jobs/${jobId}/export?format=${format}`;
    try {
      const { blob, filename } = await fetchTranscriptExport(url, token, format);
      triggerBrowserDownload(blob, filename);
      showSuccess(`Transcript downloaded as ${filename}`);
    } catch (error: any) {
      devError('Download failed:', error);
      showError(`Failed to download transcript: ${error?.message || 'Unknown error'}`);
    }
  };

  const handleDownloadDefault = (jobId: string) => handleDownload(jobId, 'txt');

  const fetchTranscriptExport = async (url: string, token: string | null, format: string) => {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error('Download failed');
    }
    const blob = await response.blob();
    const cd = response.headers.get('Content-Disposition') || '';
    const match = cd.match(/filename="?([^";]+)"?/i);
    const filename = match ? match[1] : `transcript.${format}`;
    return { blob, filename };
  };

  const triggerBrowserDownload = (blob: Blob, filename: string) => {
    const link = document.createElement('a');
    const downloadUrl = window.URL.createObjectURL(blob);
    link.href = downloadUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  };

  const formatZipFilename = (timeZone: string | null) => {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, '0');
    const formatParts = (zone?: string) => {
      const formatter = new Intl.DateTimeFormat('en-GB', {
        timeZone: zone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
      const parts = formatter.formatToParts(now);
      const lookup = (type: string) => parts.find((part) => part.type === type)?.value || '';
      return {
        year: lookup('year'),
        month: lookup('month'),
        day: lookup('day'),
        hour: lookup('hour'),
        minute: lookup('minute'),
        second: lookup('second'),
      };
    };

    let parts;
    try {
      parts = formatParts(timeZone || undefined);
    } catch {
      parts = formatParts();
    }
    const datePart = `${parts.year}${parts.month}${parts.day}`;
    const timePart = `${parts.hour}${parts.minute}${parts.second}`;
    if (datePart.length === 8 && timePart.length === 6) {
      return `Selenite_${datePart}_${timePart}.zip`;
    }
    const fallbackDate = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
    const fallbackTime = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `Selenite_${fallbackDate}_${fallbackTime}.zip`;
  };

  const ensureUniqueFilename = (filename: string, used: Set<string>, jobId: string) => {
    if (!used.has(filename)) {
      used.add(filename);
      return filename;
    }
    const dotIndex = filename.lastIndexOf('.');
    const base = dotIndex >= 0 ? filename.slice(0, dotIndex) : filename;
    const ext = dotIndex >= 0 ? filename.slice(dotIndex) : '';
    const candidate = `${base}-${jobId}${ext}`;
    used.add(candidate);
    return candidate;
  };

  const handleBulkDownload = async (format: string) => {
    if (selectedIds.size === 0 || isBulkDownloadSubmitting) return;
    const ids = Array.from(selectedIds);
    setIsBulkDownloadSubmitting(true);
    try {
      if (ids.length === 1) {
        await handleDownload(ids[0], format);
        return;
      }
      const token = localStorage.getItem('auth_token');
      const zip = new JSZip();
      const usedNames = new Set<string>();
      for (const jobId of ids) {
        const url = `${API_BASE_URL}/jobs/${jobId}/export?format=${format}`;
        const { blob, filename } = await fetchTranscriptExport(url, token, format);
        const uniqueName = ensureUniqueFilename(filename, usedNames, jobId);
        zip.file(uniqueName, blob);
      }
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const zipName = formatZipFilename(downloadTimeZone);
      triggerBrowserDownload(zipBlob, zipName);
      showSuccess(`Downloaded ${ids.length} transcripts`);
    } catch (error: any) {
      devError('Bulk download failed:', error);
      showError(`Failed to download transcripts: ${error?.message || 'Unknown error'}`);
    } finally {
      setIsBulkDownloadSubmitting(false);
    }
  };

  const handleBulkDownloadConfirm = async () => {
    const format = bulkDownloadFormat || 'txt';
    await handleBulkDownload(format);
    resetBulkDownloadModal();
  };

  const refreshJobsAfterRename = async () => {
    const jobsResponse = await fetchJobs();
    setJobs(jobsResponse.items);
    if (selectedJob) {
      const updatedJob = jobsResponse.items.find((item) => item.id === selectedJob.id);
      if (updatedJob) {
        setSelectedJob(updatedJob);
      }
    }
  };

  const handleRenameJob = async (jobId: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) {
      throw new Error('Enter a job name.');
    }
    await renameJob(jobId, trimmed);
    await refreshJobsAfterRename();
  };

  const handleBulkRenameConfirm = async () => {
    const trimmed = stripExtension(renameValue.trim());
    if (!trimmed) {
      setRenameError('Enter a job name.');
      return;
    }
    if (hasActiveSelection) {
      setRenameError('Active jobs cannot be renamed.');
      return;
    }
    setIsRenameSubmitting(true);
    setRenameError('');
    try {
      if (selectedJobs.length === 1) {
        await handleRenameJob(selectedJobs[0].id, trimmed);
      } else {
        const existingBases = new Set(
          jobs.map((job) => stripExtension(job.original_filename).toLowerCase())
        );
        selectedJobs.forEach((job) =>
          existingBases.delete(stripExtension(job.original_filename).toLowerCase())
        );
        let counter = 1;
        for (const job of selectedJobs) {
          let candidate = '';
          let found = false;
          while (!found) {
            candidate = `${trimmed}-${String(counter).padStart(2, '0')}`;
            counter += 1;
            if (!existingBases.has(candidate.toLowerCase())) {
              existingBases.add(candidate.toLowerCase());
              found = true;
            }
          }
          await renameJob(job.id, candidate);
        }
        await refreshJobsAfterRename();
      }
      showSuccess(
        selectedJobs.length === 1
          ? 'Job renamed successfully'
          : `Renamed ${selectedJobs.length} job(s)`
      );
      resetRenameModal();
    } catch (error) {
      devError('Bulk rename failed:', error);
      showError('Failed to rename job(s). Please try again.');
      setRenameError('Rename failed. Please try again.');
    } finally {
      setIsRenameSubmitting(false);
    }
  };

  const handleRestart = async (jobId: string) => {
    if (isRestartPreparing) {
      return;
    }
    const job = selectedJob?.id === jobId ? selectedJob : jobs.find((item) => item.id === jobId);
    if (!job) {
      showError('Job not found.');
      return;
    }
    const token = localStorage.getItem('auth_token');
    if (!token) {
      showError('You are not authenticated. Please log in again.');
      return;
    }

    setIsRestartPreparing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/media`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Unable to load the original file for restart.');
      }
      const blob = await response.blob();
      const fileType = blob.type || job.mime_type || 'application/octet-stream';
      const file = new File([blob], job.original_filename, { type: fileType });
      const languageCandidate = job.language_detected?.toLowerCase();
      const languagePrefill =
        languageCandidate && languageCandidate.length <= 3 ? languageCandidate : undefined;

      setRestartPrefill({
        file,
        jobName: stripExtension(job.original_filename),
        provider: job.asr_provider_used ?? undefined,
        model: job.model_used ?? undefined,
        language: languagePrefill,
        enableTimestamps: job.has_timestamps,
        enableSpeakerDetection: job.has_speaker_labels,
        diarizer: job.diarizer_used ?? undefined,
        diarizerProvider: job.diarizer_provider_used ?? undefined,
        speakerCount: job.speaker_count ?? null,
      });
      setIsNewJobModalOpen(true);
      setSelectedJob(null);
    } catch (error) {
      devError('Failed to prepare restart job:', error);
      showError('Failed to load the original file for restart. Please try again.');
    } finally {
      setIsRestartPreparing(false);
    }
  };

  const handleDelete = async (jobId: string) => {
    try {
      await deleteJob(jobId);
      showSuccess('Job deleted successfully');
      
      // Remove from local state
      setJobs(prev => prev.filter(j => j.id !== jobId));
      setSelectedJob(null);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });
    } catch (error) {
      devError('Failed to delete job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to delete job: ${error.message}`);
      } else {
        showError('Failed to delete job. Please try again.');
      }
    }
  };

  const handleStop = async (jobId: string) => {
    try {
      await cancelJob(jobId);
      showSuccess('Job stopped successfully');
      
      // Refresh job list to show updated status
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      
      // Update selected job if it's the one that was stopped
      if (selectedJob && selectedJob.id === jobId) {
        const updatedJob = jobsResponse.items.find(j => j.id === jobId);
        if (updatedJob) {
          setSelectedJob({
            ...updatedJob,
            file_size: updatedJob.file_size || selectedJob.file_size,
            duration: updatedJob.duration || selectedJob.duration,
            model_used: updatedJob.model_used || selectedJob.model_used,
            language_detected: updatedJob.language_detected || selectedJob.language_detected,
            speaker_count: updatedJob.speaker_count || selectedJob.speaker_count,
            completed_at: updatedJob.completed_at || selectedJob.completed_at
          });
        }
      }
    } catch (error) {
      devError('Failed to stop job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to stop job: ${error.message}`);
      } else {
        showError('Failed to stop job. Please try again.');
      }
    }
  };

  const handlePause = async (jobId: string) => {
    try {
      await pauseJob(jobId);
      showSuccess('Pause requested');
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      if (selectedJob && selectedJob.id === jobId) {
        const updatedJob = jobsResponse.items.find((j) => j.id === jobId);
        if (updatedJob) {
          setSelectedJob({
            ...updatedJob,
            file_size: updatedJob.file_size || selectedJob.file_size,
            duration: updatedJob.duration || selectedJob.duration,
            model_used: updatedJob.model_used || selectedJob.model_used,
            language_detected: updatedJob.language_detected || selectedJob.language_detected,
            speaker_count: updatedJob.speaker_count || selectedJob.speaker_count,
            completed_at: updatedJob.completed_at || selectedJob.completed_at,
          });
        }
      }
    } catch (error) {
      devError('Failed to pause job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to pause job: ${error.message}`);
      } else {
        showError('Failed to pause job. Please try again.');
      }
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await resumeJob(jobId);
      showSuccess('Job resumed');
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      if (selectedJob && selectedJob.id === jobId) {
        const updatedJob = jobsResponse.items.find((j) => j.id === jobId);
        if (updatedJob) {
          setSelectedJob({
            ...updatedJob,
            file_size: updatedJob.file_size || selectedJob.file_size,
            duration: updatedJob.duration || selectedJob.duration,
            model_used: updatedJob.model_used || selectedJob.model_used,
            language_detected: updatedJob.language_detected || selectedJob.language_detected,
            speaker_count: updatedJob.speaker_count || selectedJob.speaker_count,
            completed_at: updatedJob.completed_at || selectedJob.completed_at,
          });
        }
      }
    } catch (error) {
      devError('Failed to resume job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to resume job: ${error.message}`);
      } else {
        showError('Failed to resume job. Please try again.');
      }
    }
  };

  const toggleSelect = (jobId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(jobId);
      } else {
        next.delete(jobId);
      }
      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    try {
      for (const id of ids) {
        await deleteJob(id);
      }
      showSuccess(`Deleted ${ids.length} job(s)`);
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      clearSelection();
    } catch (error) {
      devError('Bulk delete failed:', error);
      showError('Failed to delete selected jobs. Please try again.');
    }
  };

  const handleBulkPause = async () => {
    if (selectedIds.size === 0) return;
    const pausable = Array.from(selectedIds)
      .map((id) => jobs.find((job) => job.id === id))
      .filter((job): job is Job => Boolean(job))
      .filter(
        (job) => ['queued', 'processing'].includes(job.status) && job.progress_stage !== 'diarizing'
      );

    if (!pausable.length) {
      showError('No selected jobs can be paused.');
      return;
    }

    try {
      for (const job of pausable) {
        await pauseJob(job.id);
      }
      showSuccess(`Pause requested for ${pausable.length} job(s)`);
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      clearSelection();
    } catch (error) {
      devError('Bulk pause failed:', error);
      showError('Failed to pause selected jobs. Please try again.');
    }
  };

  const resetBulkTagModal = () => {
    setIsBulkTagModalOpen(false);
    setCustomTagName('');
    setBulkTagError('');
    setBulkTagSelection('');
    setCustomTagColor(pickTagColor(tags));
  };

  const resetBulkDownloadModal = () => {
    setIsBulkDownloadModalOpen(false);
    setBulkDownloadFormat('txt');
  };

  const resetRenameModal = () => {
    setIsRenameModalOpen(false);
    setRenameValue('');
    setRenameError('');
  };

  const openRenameModal = () => {
    if (selectedJobs.length === 0) return;
    const defaultName = stripExtension(selectedJobs[0].original_filename);
    setRenameValue(defaultName);
    setRenameError('');
    setIsRenameModalOpen(true);
  };

  const applyTagToSelection = async (tagId: number) => {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      const job = jobs.find((item) => item.id === id);
      if (!job) {
        continue;
      }
      const tagIds = new Set(job.tags.map((tag) => tag.id));
      tagIds.add(tagId);
      await assignTag(id, Array.from(tagIds));
    }
    showSuccess(`Applied tag to ${ids.length} job(s)`);
    const [jobsResponse, tagsResponse] = await Promise.all([fetchJobs(), fetchTags()]);
    setJobs(jobsResponse.items);
    setTags(tagsResponse.items);
    clearSelection();
  };

  const handleBulkTag = async () => {
    if (!bulkTagSelection || bulkTagSelection === 'custom' || selectedIds.size === 0) return;
    const tagId = Number(bulkTagSelection);
    if (!tagId) return;
    setIsBulkTagSubmitting(true);
    try {
      await applyTagToSelection(tagId);
      setBulkTagSelection('');
    } catch (error) {
      devError('Bulk tag failed:', error);
      showError('Failed to apply tag to selected jobs.');
    } finally {
      setIsBulkTagSubmitting(false);
    }
  };

  const handleCustomTagApply = async () => {
    if (selectedIds.size === 0) {
      resetBulkTagModal();
      return;
    }
    const trimmed = customTagName.trim();
    if (!trimmed) {
      setBulkTagError('Enter a tag name.');
      return;
    }
    setIsBulkTagSubmitting(true);
    setBulkTagError('');
    try {
      let tagToUse = tags.find((tag) => tag.name.toLowerCase() === trimmed.toLowerCase());
      if (!tagToUse) {
        tagToUse = await createTag({ name: trimmed, color: customTagColor || pickTagColor(tags) });
      }
      await applyTagToSelection(tagToUse.id);
      resetBulkTagModal();
    } catch (error) {
      devError('Custom tag apply failed:', error);
      showError('Failed to create or apply the custom tag.');
    } finally {
      setIsBulkTagSubmitting(false);
    }
  };

  const handleViewTranscript = (jobId: string) => {
    const token = localStorage.getItem('auth_token') || '';
    const url = new URL(window.location.origin + `/transcripts/${jobId}`);
    if (token) {
      url.searchParams.set('token', token);
    }
    window.open(url.toString(), '_blank', 'noopener,noreferrer');
  };

  const handleUpdateTags = async (jobId: string, tagIds: number[]) => {
    try {
      await assignTag(jobId, tagIds);

      // Refresh job list and tag catalog to get updated tags
      const [jobsResponse, tagsResponse] = await Promise.all([fetchJobs(), fetchTags()]);
      setJobs(jobsResponse.items);
      setTags(tagsResponse.items);

      if (selectedJob && selectedJob.id === jobId) {
        const updatedJob = jobsResponse.items.find(j => j.id === jobId);
        if (updatedJob) {
          setSelectedJob(updatedJob);
        }
      }
      
      showSuccess('Tags updated successfully');
    } catch (error) {
      devError('Failed to update tags:', error);
      if (error instanceof ApiError) {
        showError(`Failed to update tags: ${error.message}`);
      } else {
        showError('Failed to update tags. Please try again.');
      }
    }
  };

  const availableTags = tags;

  const stripExtension = (name: string) => name.replace(/\.[^/.]+$/, '');
  const selectedJobs = useMemo(
    () => jobs.filter((job) => selectedIds.has(job.id)),
    [jobs, selectedIds]
  );
  const hasActiveSelection = selectedJobs.some((job) =>
    ['processing', 'cancelling', 'pausing'].includes(job.status)
  );
  const hasPausableSelection = selectedJobs.some((job) =>
    ['queued', 'processing'].includes(job.status)
  );

  const filteredJobs = useMemo(() => {
    let data = [...jobs];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      data = data.filter(j => j.original_filename.toLowerCase().includes(q));
    }
    if (filters.status) {
      if (filters.status === 'in_progress') {
        data = data.filter(j => ['queued', 'processing', 'cancelling', 'pausing'].includes(j.status));
      } else {
        data = data.filter(j => j.status === filters.status);
      }
    }
    if (filters.dateRange) {
      const now = Date.now();
      const createdMs = (iso: string) => new Date(iso).getTime();
      switch (filters.dateRange) {
        case 'today':
          data = data.filter(j => (now - createdMs(j.created_at)) < 86400_000);
          break;
        case 'this_week':
          data = data.filter(j => (now - createdMs(j.created_at)) < 7 * 86400_000);
          break;
        case 'this_month':
          data = data.filter(j => (now - createdMs(j.created_at)) < 30 * 86400_000);
          break;
        case 'custom_range': {
          const startValue = toLocalDateTime(
            customRangeStartDate,
            customRangeStartTime,
            customRangeStartMeridiem
          );
          const endValue = toLocalDateTime(
            customRangeEndDate,
            customRangeEndTime,
            customRangeEndMeridiem
          );
          if (startValue && endValue) {
            const startMs = new Date(startValue).getTime();
            const endMs = new Date(endValue).getTime();
            if (!Number.isNaN(startMs) && !Number.isNaN(endMs)) {
              data = data.filter(j => {
                const created = createdMs(j.created_at);
                return created >= startMs && created <= endMs;
              });
            }
          }
          break;
        }
        default:
          break;
      }
    }
    if (filters.tags && filters.tags.length) {
      data = data.filter(j => j.tags.some(t => filters.tags!.includes(t.id)));
    }
    return data;
  }, [
    jobs,
    searchQuery,
    filters,
    customRangeStartDate,
    customRangeStartTime,
    customRangeStartMeridiem,
    customRangeEndDate,
    customRangeEndTime,
    customRangeEndMeridiem,
  ]);

  const visibleJobIds = useMemo(() => filteredJobs.map((job) => job.id), [filteredJobs]);
  const allVisibleSelected =
    visibleJobIds.length > 0 && visibleJobIds.every((id) => selectedIds.has(id));
  const someVisibleSelected = visibleJobIds.some((id) => selectedIds.has(id));

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someVisibleSelected && !allVisibleSelected;
    }
  }, [someVisibleSelected, allVisibleSelected]);

  const handleFilterChange = (f: {status?: string; dateRange?: string; tags?: number[]}) => {
    setFilters(f);
    if (f.dateRange && f.dateRange !== 'custom_range') {
      setCustomRangeStartDate('');
      setCustomRangeStartTime('');
      setCustomRangeStartMeridiem('AM');
      setCustomRangeEndDate('');
      setCustomRangeEndTime('');
      setCustomRangeEndMeridiem('AM');
    }
  };

  const handleResetFilters = () => {
    setFilters({});
    setCustomRangeStartDate('');
    setCustomRangeStartTime('');
    setCustomRangeStartMeridiem('AM');
    setCustomRangeEndDate('');
    setCustomRangeEndTime('');
    setCustomRangeEndMeridiem('AM');
    setCustomRangeError('');
  };

  const handleSelectAllToggle = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(visibleJobIds));
      return;
    }
    clearSelection();
  };

  const toLocalDateTime = (date: string, time: string, meridiem: 'AM' | 'PM') => {
    if (!date || !time) return null;
    const [hourText, minuteText] = time.split(':');
    const hourNumber = Number(hourText);
    const minuteNumber = Number(minuteText);
    if (!Number.isFinite(hourNumber) || !Number.isFinite(minuteNumber)) return null;
    const clampedHour = Math.min(Math.max(hourNumber, 1), 12);
    const clampedMinute = Math.min(Math.max(minuteNumber, 0), 59);
    const hour24 =
      meridiem === 'PM'
        ? (clampedHour === 12 ? 12 : clampedHour + 12)
        : (clampedHour === 12 ? 0 : clampedHour);
    const hourValue = String(hour24).padStart(2, '0');
    const minuteValue = String(clampedMinute).padStart(2, '0');
    return `${date}T${hourValue}:${minuteValue}:00`;
  };

  const handleCustomRangeApply = () => {
    const startValue = toLocalDateTime(
      customRangeStartDate,
      customRangeStartTime,
      customRangeStartMeridiem
    );
    const endValue = toLocalDateTime(
      customRangeEndDate,
      customRangeEndTime,
      customRangeEndMeridiem
    );
    if (!startValue || !endValue) {
      setCustomRangeError('Select a start and end date.');
      return;
    }
    const startMs = new Date(startValue).getTime();
    const endMs = new Date(endValue).getTime();
    if (Number.isNaN(startMs) || Number.isNaN(endMs)) {
      setCustomRangeError('Enter a valid date range.');
      return;
    }
    if (endMs < startMs) {
      setCustomRangeError('End date must be after start date.');
      return;
    }
    setCustomRangeError('');
    setIsCustomRangeOpen(false);
    setFilters(prev => ({ ...prev, dateRange: 'custom_range' }));
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          <h1 className="text-2xl font-semibold text-pine-deep">Transcriptions</h1>
          {isAdmin && (
            <label className="flex items-center gap-2 text-sm text-pine-deep">
              <input
                type="checkbox"
                className="h-4 w-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
                checked={showAllJobs}
                onChange={(event) => handleToggleAllJobs(event.target.checked)}
                aria-label="Show all jobs"
              />
              <span>Show all jobs</span>
            </label>
          )}
        </div>
        <SkeletonGrid />
      </div>
    );
  }

  if (!isLoading && jobs.length === 0) {
    return (
      <>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
            <h1 className="text-2xl font-semibold text-pine-deep">Transcriptions</h1>
            <div className="flex items-center gap-4 flex-wrap">
              {isAdmin && (
                <label className="flex items-center gap-2 text-sm text-pine-deep">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
                    checked={showAllJobs}
                    onChange={(event) => handleToggleAllJobs(event.target.checked)}
                    aria-label="Show all jobs"
                  />
                  <span>Show all jobs</span>
                </label>
              )}
              <button
                data-testid="new-job-btn"
                onClick={() => {
                  setRestartPrefill(null);
                  setIsNewJobModalOpen(true);
                }}
                className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
              >
                + New Job
              </button>
            </div>
          </div>
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📝</div>
            <h2 className="text-xl font-medium text-pine-deep mb-2">No transcriptions yet</h2>
            <p className="text-pine-mid mb-6">Get started by creating your first transcription job</p>
            <button
              data-testid="create-first-job-btn"
              onClick={() => setIsNewJobModalOpen(true)}
              className="px-6 py-3 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
            >
              Create First Job
            </button>
          </div>
        </div>
        
        <NewJobModal
          isOpen={isNewJobModalOpen}
          onClose={() => setIsNewJobModalOpen(false)}
          onSubmit={handleNewJob}
          defaultModel={adminSettings?.default_model}
          defaultLanguage={adminSettings?.default_language}
          defaultDiarizer={adminSettings?.default_diarizer}
          defaultDiarizerProvider={adminSettings?.default_diarizer_provider ?? undefined}
        />
      </>
    );
  }

  return (
    <>
      <div className="p-6">
        <div className="flex flex-col gap-4 mb-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <h1 className="text-2xl font-semibold text-pine-deep">Transcriptions</h1>
            <div className="flex items-center gap-4 flex-wrap">
              {isAdmin && (
                <label className="flex items-center gap-2 text-sm text-pine-deep">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
                    checked={showAllJobs}
                    onChange={(event) => handleToggleAllJobs(event.target.checked)}
                    aria-label="Show all jobs"
                  />
                  <span>Show all jobs</span>
                </label>
              )}
              <button
                data-testid="new-job-btn"
                onClick={() => setIsNewJobModalOpen(true)}
                className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
              >
                + New Job
              </button>
            </div>
          </div>
          <div className="flex flex-col md:flex-row gap-4 md:items-center">
            <SearchBar value={searchQuery} onChange={setSearchQuery} placeholder="Search jobs" />
              <JobFilters
                currentFilters={filters}
                availableTags={availableTags}
                onFilterChange={handleFilterChange}
                onCustomRange={() => {
                  setIsCustomRangeOpen(true);
                  setCustomRangeError('');
                  setCustomRangeStartMeridiem('AM');
                  setCustomRangeEndMeridiem('AM');
                }}
                onReset={handleResetFilters}
              />
          </div>
          {filteredJobs.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-pine-deep">
              <input
                ref={selectAllRef}
                type="checkbox"
                className="h-4 w-4 text-forest-green border-gray-300 rounded focus:ring-forest-green"
                checked={allVisibleSelected}
                onChange={(event) => handleSelectAllToggle(event.target.checked)}
                aria-label="Select all jobs"
              />
              <span>Select all</span>
            </label>
          )}
          {selectedIds.size > 0 && (
            <div className="flex flex-col md:flex-row gap-3 md:items-center bg-sage-light border border-sage-mid rounded-md p-3">
              <span className="text-sm text-pine-deep">{selectedIds.size} selected</span>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={handleBulkDelete}
                  className="px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
                >
                  Delete
                </button>
                <button
                  onClick={handleBulkPause}
                  className="px-3 py-2 bg-sage-light text-pine-deep rounded hover:bg-sage-mid text-sm disabled:opacity-50"
                  disabled={!hasPausableSelection}
                >
                  Pause
                </button>
                <button
                  onClick={() => setIsBulkDownloadModalOpen(true)}
                  className="px-3 py-2 bg-forest-green text-white rounded hover:bg-pine-deep text-sm disabled:opacity-50"
                  disabled={isBulkDownloadSubmitting}
                >
                  {isBulkDownloadSubmitting ? 'Downloading...' : 'Download'}
                </button>
                <button
                  onClick={openRenameModal}
                  className="px-3 py-2 bg-sage-light text-pine-deep rounded hover:bg-sage-mid text-sm disabled:opacity-50"
                  disabled={isRenameSubmitting || hasActiveSelection}
                >
                  Rename
                </button>
                <div className="flex items-center gap-2">
                  <select
                    className="px-3 py-2 border border-gray-300 rounded"
                    value={bulkTagSelection}
                    onChange={(e) => {
                      const nextValue = e.target.value;
                      setBulkTagSelection(nextValue);
                      if (nextValue === 'custom') {
                        setIsBulkTagModalOpen(true);
                        setCustomTagName('');
                        setBulkTagError('');
                        setCustomTagColor(pickTagColor(tags));
                      }
                    }}
                  >
                    <option value="">Apply tag...</option>
                    {availableTags.map((t) => (
                      <option key={t.id} value={String(t.id)}>
                        #{t.name}
                      </option>
                    ))}
                    <option value="custom">Custom...</option>
                  </select>
                  <button
                    onClick={handleBulkTag}
                    className="px-3 py-2 bg-forest-green text-white rounded hover:bg-pine-deep text-sm disabled:opacity-50"
                    disabled={!bulkTagSelection || bulkTagSelection === 'custom' || isBulkTagSubmitting}
                  >
                    Apply
                  </button>
                </div>
                <button
                  onClick={clearSelection}
                  className="text-sm text-pine-deep underline"
                >
                  Clear selection
                </button>
              </div>
            </div>
          )}
        </div>
        {filteredJobs.length === 0 ? (
          <div className="text-center py-12 border border-sage-mid rounded-lg bg-white">
            <p className="text-pine-mid mb-2">No jobs match your search or filters.</p>
            <button
              onClick={handleResetFilters}
              className="text-sm text-forest-green hover:underline"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredJobs.map(job => (
                <JobCard
                  key={job.id}
                  job={job}
                  onClick={handleJobClick}
                  selectionMode
                  selected={selectedIds.has(job.id)}
                  onSelectToggle={toggleSelect}
                  onPlay={handlePlay}
                  onStop={handleStopAudio}
                  onSeek={handleSeekAudio}
                  onSpeed={handleSpeedAudio}
                  isActive={audioJobId === job.id}
                  isPlaying={isAudioPlaying && audioJobId === job.id}
                  currentTime={audioJobId === job.id ? audioPosition : 0}
                  playbackRate={audioJobId === job.id ? audioRate : 1}
                  onDownload={handleDownloadDefault}
                  onView={handleViewTranscript}
                  timeZone={effectiveTimeZone}
                  showOwnerLabel={isAdmin && showAllJobs}
                />
            ))}
          </div>
        )}
      </div>
      {selectedJob && (
      <JobDetailModal
        isOpen={!!selectedJob}
        onClose={() => setSelectedJob(null)}
        job={selectedJob as any}
        onPlay={handlePlay}
        onDownload={handleDownload}
        onRestart={handleRestart}
        onDelete={handleDelete}
        onStop={handleStop}
        onPause={handlePause}
        onResume={handleResume}
        onRename={handleRenameJob}
        onViewTranscript={handleViewTranscript}
        onUpdateTags={handleUpdateTags}
        availableTags={availableTags}
        timeZone={effectiveTimeZone}
        asrProviderHint={adminSettings?.default_asr_provider || null}
        defaultDiarizerHint={adminSettings?.default_diarizer || null}
      />
    )}
      <NewJobModal
        isOpen={isNewJobModalOpen}
        onClose={() => {
          setIsNewJobModalOpen(false);
          setRestartPrefill(null);
        }}
        onSubmit={handleNewJob}
        prefill={restartPrefill ?? undefined}
        defaultModel={adminSettings?.default_model}
        defaultLanguage={adminSettings?.default_language}
        defaultDiarizer={adminSettings?.default_diarizer}
        defaultDiarizerProvider={adminSettings?.default_diarizer_provider ?? undefined}
      />
      {isBulkTagModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="bg-white rounded-lg shadow-lg w-full max-w-md p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="bulk-custom-tag-title"
          >
            <h2 id="bulk-custom-tag-title" className="text-lg font-semibold text-pine-deep mb-4">
              Custom tag
            </h2>
            <label className="text-sm text-pine-deep mb-2 block" htmlFor="bulk-custom-tag">
              Tag name
            </label>
            <input
              id="bulk-custom-tag"
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
              value={customTagName}
              onChange={(e) => {
                setCustomTagName(e.target.value);
                if (bulkTagError) {
                  setBulkTagError('');
                }
              }}
              placeholder="Enter a tag name"
            />
            {bulkTagError && <p className="text-sm text-red-600 mt-2">{bulkTagError}</p>}
            <div className="flex flex-wrap items-center gap-2 mt-3">
              <span className="text-xs text-pine-mid">Tag color</span>
              {TAG_COLOR_PALETTE.map((color) => (
                <button
                  key={color}
                  type="button"
                  aria-label={`Select ${color}`}
                  onClick={() => setCustomTagColor(color)}
                  className={`w-6 h-6 rounded-full border ${
                    customTagColor === color ? 'border-forest-green ring-2 ring-forest-green/40' : 'border-sage-mid'
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="px-3 py-2 text-sm rounded border border-gray-300 text-pine-deep"
                onClick={resetBulkTagModal}
                disabled={isBulkTagSubmitting}
              >
                Cancel
              </button>
              <button
                className="px-3 py-2 text-sm rounded bg-forest-green text-white disabled:opacity-50"
                onClick={handleCustomTagApply}
                disabled={!customTagName.trim() || isBulkTagSubmitting}
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
      {isBulkDownloadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="bg-white rounded-lg shadow-lg w-full max-w-md p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="bulk-download-title"
          >
            <h2 id="bulk-download-title" className="text-lg font-semibold text-pine-deep mb-4">
              Export transcripts
            </h2>
            <label className="text-sm text-pine-deep mb-2 block" htmlFor="bulk-download-format">
              Export format
            </label>
            <select
              id="bulk-download-format"
              className="w-full px-3 py-2 border border-gray-300 rounded"
              value={bulkDownloadFormat}
              onChange={(event) => setBulkDownloadFormat(event.target.value)}
            >
              <option value="txt">Plain text (.txt)</option>
              <option value="srt">SubRip (.srt)</option>
              <option value="vtt">WebVTT (.vtt)</option>
              <option value="json">JSON (.json)</option>
              <option value="docx">Word (.docx)</option>
              <option value="md">Markdown (.md)</option>
            </select>
            <p className="text-xs text-pine-mid mt-2">
              Multiple selections will download as a zip bundle.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
                onClick={resetBulkDownloadModal}
              >
                Cancel
              </button>
              <button
                className="px-3 py-2 text-sm bg-forest-green text-white rounded hover:bg-pine-deep disabled:opacity-50"
                onClick={handleBulkDownloadConfirm}
                disabled={isBulkDownloadSubmitting}
              >
                {isBulkDownloadSubmitting ? 'Downloading...' : 'Download'}
              </button>
            </div>
          </div>
        </div>
      )}
      {isRenameModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="bg-white rounded-lg shadow-lg w-full max-w-md p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="rename-jobs-title"
          >
            <h2 id="rename-jobs-title" className="text-lg font-semibold text-pine-deep mb-4">
              Rename job{selectedJobs.length > 1 ? 's' : ''}
            </h2>
            <label className="text-sm text-pine-deep mb-2 block" htmlFor="rename-jobs-input">
              New name
            </label>
            <input
              id="rename-jobs-input"
              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
              value={renameValue}
              onChange={(event) => {
                setRenameValue(event.target.value);
                if (renameError) {
                  setRenameError('');
                }
              }}
              placeholder="Enter a name"
            />
            <p className="text-xs text-pine-mid mt-2">
              File extensions stay the same.{' '}
              {selectedJobs.length > 1
                ? 'Multiple jobs will be numbered automatically.'
                : 'Your job name will be updated.'}
            </p>
            {hasActiveSelection && (
              <p className="text-xs text-amber-700 mt-2">
                Active jobs cannot be renamed while processing.
              </p>
            )}
            {renameError && <p className="text-sm text-red-600 mt-2">{renameError}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="px-3 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
                onClick={resetRenameModal}
                disabled={isRenameSubmitting}
              >
                Cancel
              </button>
              <button
                className="px-3 py-2 text-sm bg-forest-green text-white rounded hover:bg-pine-deep disabled:opacity-50"
                onClick={handleBulkRenameConfirm}
                disabled={isRenameSubmitting || hasActiveSelection}
              >
                {isRenameSubmitting ? 'Renaming...' : 'Rename'}
              </button>
            </div>
          </div>
        </div>
      )}
      {isCustomRangeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            className="bg-white rounded-lg shadow-lg w-full max-w-md p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="custom-range-title"
          >
            <h2 id="custom-range-title" className="text-lg font-semibold text-pine-deep mb-4">
              Custom range
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-pine-deep mb-2 block" htmlFor="custom-range-start-date">
                  Start date
                </label>
                <div className="flex flex-wrap gap-2">
                  <input
                    id="custom-range-start-date"
                    type="date"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
                    value={customRangeStartDate}
                    onChange={(e) => {
                      setCustomRangeStartDate(e.target.value);
                      if (customRangeError) {
                        setCustomRangeError('');
                      }
                    }}
                  />
                  <input
                    id="custom-range-start-time"
                    type="time"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
                    value={customRangeStartTime}
                    onChange={(e) => {
                      setCustomRangeStartTime(e.target.value);
                      if (customRangeError) {
                        setCustomRangeError('');
                      }
                    }}
                  />
                  <label className="sr-only" htmlFor="custom-range-start-meridiem">
                    Start meridiem
                  </label>
                  <select
                    id="custom-range-start-meridiem"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
                    value={customRangeStartMeridiem}
                    onChange={(e) => setCustomRangeStartMeridiem(e.target.value === 'PM' ? 'PM' : 'AM')}
                  >
                    <option value="AM">AM</option>
                    <option value="PM">PM</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-sm text-pine-deep mb-2 block" htmlFor="custom-range-end-date">
                  End date
                </label>
                <div className="flex flex-wrap gap-2">
                  <input
                    id="custom-range-end-date"
                    type="date"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
                    value={customRangeEndDate}
                    onChange={(e) => {
                      setCustomRangeEndDate(e.target.value);
                      if (customRangeError) {
                        setCustomRangeError('');
                      }
                    }}
                  />
                  <input
                    id="custom-range-end-time"
                    type="time"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
                    value={customRangeEndTime}
                    onChange={(e) => {
                      setCustomRangeEndTime(e.target.value);
                      if (customRangeError) {
                        setCustomRangeError('');
                      }
                    }}
                  />
                  <label className="sr-only" htmlFor="custom-range-end-meridiem">
                    End meridiem
                  </label>
                  <select
                    id="custom-range-end-meridiem"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-forest-green"
                    value={customRangeEndMeridiem}
                    onChange={(e) => setCustomRangeEndMeridiem(e.target.value === 'PM' ? 'PM' : 'AM')}
                  >
                    <option value="AM">AM</option>
                    <option value="PM">PM</option>
                  </select>
                </div>
              </div>
            </div>
            {customRangeError && <p className="text-sm text-red-600 mt-3">{customRangeError}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="px-3 py-2 text-sm rounded border border-gray-300 text-pine-deep"
                onClick={() => setIsCustomRangeOpen(false)}
              >
                Cancel
              </button>
              <button
                className="px-3 py-2 text-sm rounded bg-forest-green text-white disabled:opacity-50"
                onClick={handleCustomRangeApply}
                disabled={!customRangeStartDate || !customRangeEndDate}
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};



