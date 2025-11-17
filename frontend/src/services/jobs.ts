/**
 * Job API Service
 * 
 * Functions for interacting with job management endpoints.
 */

import { apiGet, apiUpload } from '../lib/api';

export interface Job {
  id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  duration: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_percent: number | null;
  progress_stage: string | null;
  estimated_time_left: number | null;
  model_used: string;
  language_detected: string;
  speaker_count: number | null;
  has_timestamps: boolean;
  has_speaker_labels: boolean;
  tags: Array<{
    id: number;
    name: string;
    color: string;
  }>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface JobsResponse {
  total: number;
  limit: number;
  offset: number;
  items: Job[];
}

export interface FetchJobsParams {
  status?: 'queued' | 'processing' | 'completed' | 'failed';
  date_from?: string;
  date_to?: string;
  tags?: string; // Comma-separated tag IDs
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CreateJobParams {
  file: File;
  model?: string;
  language?: string;
  enable_timestamps?: boolean;
  enable_speaker_detection?: boolean;
}

export interface CreateJobResponse {
  id: string;
  original_filename: string;
  status: 'queued';
  created_at: string;
}

/**
 * Fetch all jobs with optional filtering and pagination
 */
export async function fetchJobs(params?: FetchJobsParams): Promise<JobsResponse> {
  return apiGet<JobsResponse>('/jobs', params);
}

/**
 * Fetch a single job by ID
 */
export async function fetchJob(jobId: string): Promise<Job> {
  return apiGet<Job>(`/jobs/${jobId}`);
}

/**
 * Create a new transcription job by uploading a file
 */
export async function createJob(params: CreateJobParams): Promise<CreateJobResponse> {
  const formData = new FormData();
  formData.append('file', params.file);
  
  if (params.model) {
    formData.append('model', params.model);
  }
  
  if (params.language) {
    formData.append('language', params.language);
  }
  
  if (params.enable_timestamps !== undefined) {
    formData.append('enable_timestamps', String(params.enable_timestamps));
  }
  
  if (params.enable_speaker_detection !== undefined) {
    formData.append('enable_speaker_detection', String(params.enable_speaker_detection));
  }
  
  return apiUpload<CreateJobResponse>('/jobs', formData);
}
