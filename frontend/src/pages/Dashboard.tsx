import React, { useState, useEffect, useMemo } from 'react';
import { JobCard } from '../components/jobs/JobCard';
import { NewJobModal } from '../components/modals/NewJobModal';
import { JobDetailModal } from '../components/modals/JobDetailModal';
import { SearchBar } from '../components/common/SearchBar';
import { JobFilters } from '../components/jobs/JobFilters';
import { usePolling } from '../hooks/usePolling';

interface Job {
  id: string;
  original_filename: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  created_at: string;
  duration?: number;
  progress_percent?: number;
  progress_stage?: string;
  estimated_time_left?: number;
  tags: Array<{ id: number; name: string; color: string }>;
  file_size?: number;
  model_used?: string;
  language_detected?: string;
  speaker_count?: number;
  completed_at?: string;
}

export const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNewJobModalOpen, setIsNewJobModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<{status?: string; dateRange?: string; tags?: number[]}>({});

  useEffect(() => {
    // Placeholder: Replace with actual API call
    // For now, set empty array after simulated load
    const timer = setTimeout(() => {
      // Seed with sample jobs (remove when API wired)
      setJobs([
        {
          id: '1',
          original_filename: 'marketing_plan_q4.mp3',
          status: 'completed',
          created_at: new Date().toISOString(),
          tags: [{ id: 2, name: 'marketing', color: '#B5543A' }],
          duration: 534,
        },
        {
          id: '2',
          original_filename: 'customer_interview_alpha.wav',
          status: 'processing',
          created_at: new Date(Date.now() - 3600_000).toISOString(),
          tags: [{ id: 1, name: 'interviews', color: '#0F3D2E' }],
          progress_percent: 42,
          progress_stage: 'transcribing',
          estimated_time_left: 780,
          duration: 1800,
        },
        {
          id: '3',
          original_filename: 'research_brainstorm.mov',
          status: 'failed',
          created_at: new Date(Date.now() - 86400_000).toISOString(),
          tags: [{ id: 3, name: 'research', color: '#C9A227' }],
          duration: 1200,
        },
      ]);
      setIsLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, []);

  // Poll for job updates (processing jobs only)
  const hasProcessingJobs = jobs.some(j => j.status === 'processing' || j.status === 'queued');
  
  const fetchJobUpdates = async () => {
    // TODO: Replace with actual API call to GET /jobs
    // For now, simulate progress update
    console.log('Polling for job updates...');
    setJobs(prevJobs => 
      prevJobs.map(job => {
        if (job.status === 'processing' && job.progress_percent !== undefined) {
          const newPercent = Math.min(100, job.progress_percent + Math.random() * 15);
          const newTimeLeft = job.estimated_time_left ? Math.max(0, job.estimated_time_left - 30) : undefined;
          
          // Complete job when reaching 100%
          if (newPercent >= 100) {
            return {
              ...job,
              status: 'completed' as const,
              progress_percent: 100,
              progress_stage: undefined,
              estimated_time_left: undefined
            };
          }
          
          return {
            ...job,
            progress_percent: newPercent,
            estimated_time_left: newTimeLeft
          };
        }
        return job;
      })
    );
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
    console.log('Creating new job (placeholder):', jobData);
    await new Promise(resolve => setTimeout(resolve, 1000));
    alert('Job created successfully! (API integration pending)');
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
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
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
