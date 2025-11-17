import React, { useState, useEffect } from 'react';
import { JobCard } from '../components/jobs/JobCard';
import { NewJobModal } from '../components/modals/NewJobModal';

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
}

export const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNewJobModalOpen, setIsNewJobModalOpen] = useState(false);

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
    console.log('Job clicked:', jobId);
    // TODO: Open job detail modal
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
