import React, { useState, useEffect } from 'react';
import { JobCard } from '../components/jobs/JobCard';
import { NewJobModal } from '../components/modals/NewJobModal';
import { JobDetailModal } from '../components/modals/JobDetailModal';

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

  useEffect(() => {
    // Placeholder: Replace with actual API call
    // For now, set empty array after simulated load
    const timer = setTimeout(() => {
      setJobs([]);
      setIsLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, []);

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
    // TODO: Implement actual API call to POST /jobs
    console.log('Creating new job:', jobData);
    
    // Placeholder: Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // TODO: Add new job to jobs array and refresh list
    alert('Job created successfully! (API integration pending)');

    const handlePlay = (jobId: string) => {
      console.log('Play job:', jobId);
      // TODO: Implement media playback
    };

    const handleDownload = (jobId: string, format: string) => {
      console.log('Download job:', jobId, 'format:', format);
      // TODO: Implement download
    };

    const handleRestart = (jobId: string) => {
      console.log('Restart job:', jobId);
      // TODO: Implement restart
    };

    const handleDelete = (jobId: string) => {
      console.log('Delete job:', jobId);
      // TODO: Implement delete
      setJobs(jobs.filter(j => j.id !== jobId));
    };

    const handleUpdateTags = (jobId: string, tagIds: number[]) => {
      console.log('Update tags for job:', jobId, 'tags:', tagIds);
      // TODO: Implement tag update
    };
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

  if (jobs.length === 0) {
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
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-pine-deep">Transcriptions</h1>
          <button
            onClick={() => setIsNewJobModalOpen(true)}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition-colors"
          >
            + New Job
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} onClick={handleJobClick} />
      
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
          ))}
        </div>
      </div>
      
      <NewJobModal
        isOpen={isNewJobModalOpen}
        onClose={() => setIsNewJobModalOpen(false)}
        onSubmit={handleNewJob}
      />
    </>
  );
};
