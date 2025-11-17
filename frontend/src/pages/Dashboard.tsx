import React, { useState, useEffect, useMemo } from 'react';
import { JobCard } from '../components/jobs/JobCard';
import { NewJobModal } from '../components/modals/NewJobModal';
import { JobDetailModal } from '../components/modals/JobDetailModal';
import { SearchBar } from '../components/common/SearchBar';
import { JobFilters } from '../components/jobs/JobFilters';
import { SkeletonGrid } from '../components/common/Skeleton';
import { usePolling } from '../hooks/usePolling';
import { fetchJobs, createJob, type Job } from '../services/jobs';
import { ApiError } from '../lib/api';
import { useToast } from '../context/ToastContext';

export const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNewJobModalOpen, setIsNewJobModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<{status?: string; dateRange?: string; tags?: number[]}>({});
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
  const hasProcessingJobs = jobs.some(j => j.status === 'processing' || j.status === 'queued');
  
  const fetchJobUpdates = async () => {
    // Fetch latest job data from API
    try {
      const response = await fetchJobs();
      setJobs(response.items);
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

  const handlePlay = (jobId: string) => {
    console.log('Play job:', jobId);
  };

  const handleDownload = (jobId: string, format: string) => {
    console.log('Download job:', jobId, 'format:', format);
  };

  const handleRestart = (jobId: string) => {
    console.log('Restart job:', jobId);
  };

  const handleDelete = (jobId: string) => {
    console.log('Delete job:', jobId);
    setJobs(prev => prev.filter(j => j.id !== jobId));
    setSelectedJob(null);
  };

  const handleUpdateTags = (jobId: string, tagIds: number[]) => {
    console.log('Update tags for job:', jobId, 'tags:', tagIds);
    setJobs(prev => prev.map(j => j.id === jobId ? { ...j, tags: j.tags.filter(t => tagIds.includes(t.id)) } : j));
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
        data = data.filter(j => j.status === 'queued' || j.status === 'processing');
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
              <JobCard key={job.id} job={job} onClick={handleJobClick} />
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
