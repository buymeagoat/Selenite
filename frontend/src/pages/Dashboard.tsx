import React, { useState, useEffect, useMemo, useRef } from 'react';
import { JobCard } from '../components/jobs/JobCard';
import { NewJobModal } from '../components/modals/NewJobModal';
import { JobDetailModal } from '../components/modals/JobDetailModal';
import { SearchBar } from '../components/common/SearchBar';
import { JobFilters } from '../components/jobs/JobFilters';
import { SkeletonGrid } from '../components/common/Skeleton';
import { usePolling } from '../hooks/usePolling';
import { fetchJobs, createJob, restartJob, cancelJob, deleteJob, assignTag, removeTag, type Job } from '../services/jobs';
import { ApiError, API_BASE_URL } from '../lib/api';
import { useToast } from '../context/ToastContext';

export const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNewJobModalOpen, setIsNewJobModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkTagId, setBulkTagId] = useState<number | ''>('' as any);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<{status?: string; dateRange?: string; tags?: number[]}>({});
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioJobId, setAudioJobId] = useState<string | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioPosition, setAudioPosition] = useState(0);
  const [audioRate, setAudioRate] = useState(1);
  const { showError, showSuccess } = useToast();

  useEffect(() => {
    // Load jobs from API
    const loadJobs = async () => {
      setIsLoading(true);
      try {
        const response = await fetchJobs();
        setJobs(response.items);
      } catch (error) {
        console.error('Failed to load jobs:', error);
        if (error instanceof ApiError) {
          showError(`Failed to load jobs: ${error.message}`);
        } else {
          showError('Failed to load jobs. Please check your connection.');
        }
        // Set empty array on error to show empty state
        setJobs([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadJobs();
  }, [showError]);

  // Poll for job updates (processing jobs only)
  const hasProcessingJobs = jobs.some(j => j.status === 'processing' || j.status === 'queued' || j.status === 'cancelling');
  
  const fetchJobUpdates = async () => {
    // Fetch latest job data from API
    try {
      const response = await fetchJobs();
      setJobs(response.items);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to poll job updates:', error);
      // Continue polling on error (don't stop polling for temporary failures)
    }
  };

  usePolling(fetchJobUpdates, {
    enabled: hasProcessingJobs && !isLoading,
    interval: 2000
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
    model: string;
    language: string;
    enableTimestamps: boolean;
    enableSpeakerDetection: boolean;
  }) => {
    try {
      const response = await createJob({
        file: jobData.file,
        model: jobData.model,
        language: jobData.language,
        enable_timestamps: jobData.enableTimestamps,
        enable_speaker_detection: jobData.enableSpeakerDetection,
      });
      
      showSuccess(`Job created successfully: ${response.original_filename}`);
      
      // Refresh job list to show new job
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
    } catch (error) {
      console.error('Failed to create job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to create job: ${error.message}`);
      } else {
        showError('Failed to create job. Please try again.');
      }
      throw error; // Re-throw so modal can handle the error state
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
      console.error('Play failed:', error);
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
    // Trigger download via export endpoint
    const token = localStorage.getItem('auth_token');
    const url = `${API_BASE_URL}/jobs/${jobId}/export?format=${format}`;
    
    // Create temporary anchor element to trigger download
    const link = document.createElement('a');
    link.href = url;
    // Add auth header by fetching manually so we can honor Content-Disposition filename
    try {
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
      const downloadUrl = window.URL.createObjectURL(blob);
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      showSuccess(`Transcript downloaded as ${filename}`);
    } catch (error: any) {
      console.error('Download failed:', error);
      showError(`Failed to download transcript: ${error?.message || 'Unknown error'}`);
    }
  };

  const handleDownloadDefault = (jobId: string) => handleDownload(jobId, 'txt');

  const handleRestart = async (jobId: string) => {
    try {
      const response = await restartJob(jobId);
      showSuccess(`Job restarted: ${response.original_filename}`);
      
      // Refresh job list to show new job
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
    } catch (error) {
      console.error('Failed to restart job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to restart job: ${error.message}`);
      } else {
        showError('Failed to restart job. Please try again.');
      }
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
      console.error('Failed to delete job:', error);
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
      console.error('Failed to stop job:', error);
      if (error instanceof ApiError) {
        showError(`Failed to stop job: ${error.message}`);
      } else {
        showError('Failed to stop job. Please try again.');
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
      console.error('Bulk delete failed:', error);
      showError('Failed to delete selected jobs. Please try again.');
    }
  };

  const handleBulkTag = async () => {
    if (!bulkTagId || selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    try {
      for (const id of ids) {
        await assignTag(id, bulkTagId as number);
      }
      showSuccess(`Applied tag to ${ids.length} job(s)`);
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      clearSelection();
    } catch (error) {
      console.error('Bulk tag failed:', error);
      showError('Failed to apply tag to selected jobs.');
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
      // Find the job to determine which tags to add/remove
      const job = jobs.find(j => j.id === jobId);
      if (!job) return;
      
      const currentTagIds = job.tags.map(t => t.id);
      const tagsToAdd = tagIds.filter(id => !currentTagIds.includes(id));
      const tagsToRemove = currentTagIds.filter(id => !tagIds.includes(id));
      
      // Add new tags
      for (const tagId of tagsToAdd) {
        await assignTag(jobId, tagId);
      }
      
      // Remove tags
      for (const tagId of tagsToRemove) {
        await removeTag(jobId, tagId);
      }
      
      // Refresh job list to get updated tags
      const jobsResponse = await fetchJobs();
      setJobs(jobsResponse.items);
      
      showSuccess('Tags updated successfully');
    } catch (error) {
      console.error('Failed to update tags:', error);
      if (error instanceof ApiError) {
        showError(`Failed to update tags: ${error.message}`);
      } else {
        showError('Failed to update tags. Please try again.');
      }
    }
  };

  const availableTags = useMemo(() => {
    const tagMap: Record<number, {id:number; name:string; color:string}> = {};
    jobs.forEach(j => j.tags.forEach(t => { tagMap[t.id] = t; }));
    return Object.values(tagMap);
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    let data = [...jobs];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      data = data.filter(j => j.original_filename.toLowerCase().includes(q));
    }
    if (filters.status) {
      if (filters.status === 'in_progress') {
        data = data.filter(j => ['queued', 'processing', 'cancelling'].includes(j.status));
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
        default:
          break;
      }
    }
    if (filters.tags && filters.tags.length) {
      data = data.filter(j => j.tags.some(t => filters.tags!.includes(t.id)));
    }
    return data;
  }, [jobs, searchQuery, filters]);

  const handleFilterChange = (f: {status?: string; dateRange?: string; tags?: number[]}) => {
    setFilters(f);
  };

  const handleResetFilters = () => {
    setFilters({});
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-pine-deep">Transcriptions</h1>
        </div>
        <SkeletonGrid />
      </div>
    );
  }

  if (!isLoading && jobs.length === 0) {
    return (
      <>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-semibold text-pine-deep">Transcriptions</h1>
            <button
              data-testid="new-job-btn"
              onClick={() => setIsNewJobModalOpen(true)}
              className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
            >
              + New Job
            </button>
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
            <button
              data-testid="new-job-btn"
              onClick={() => setIsNewJobModalOpen(true)}
              className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
            >
              + New Job
            </button>
          </div>
          <div className="flex flex-col md:flex-row gap-4 md:items-center">
            <SearchBar value={searchQuery} onChange={setSearchQuery} placeholder="Search jobs" />
            <JobFilters
              currentFilters={filters}
              availableTags={availableTags}
              onFilterChange={handleFilterChange}
              onReset={handleResetFilters}
            />
          </div>
          {selectedIds.size > 0 && (
            <div className="flex flex-col md:flex-row gap-3 md:items-center bg-sage-light border border-sage-mid rounded-md p-3">
              <span className="text-sm text-pine-deep">{selectedIds.size} selected</span>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={handleBulkDelete}
                  className="px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
                >
                  Delete selected
                </button>
                <div className="flex items-center gap-2">
                  <select
                    className="px-3 py-2 border border-gray-300 rounded"
                    value={bulkTagId}
                    onChange={(e) => setBulkTagId(e.target.value ? Number(e.target.value) : '')}
                  >
                    <option value="">Apply tag…</option>
                    {availableTags.map((t) => (
                      <option key={t.id} value={t.id}>
                        #{t.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleBulkTag}
                    className="px-3 py-2 bg-forest-green text-white rounded hover:bg-pine-deep text-sm disabled:opacity-50"
                    disabled={!bulkTagId}
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
                duration={audioJobId === job.id ? audioDuration : 0}
                playbackRate={audioJobId === job.id ? audioRate : 1}
                onDownload={handleDownloadDefault}
                onView={handleViewTranscript}
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
          onViewTranscript={handleViewTranscript}
          onUpdateTags={handleUpdateTags}
        />
      )}
      <NewJobModal
        isOpen={isNewJobModalOpen}
        onClose={() => setIsNewJobModalOpen(false)}
        onSubmit={handleNewJob}
      />
    </>
  );
};
