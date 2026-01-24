/**
 * Job API Service
 * 
 * Functions for interacting with job management endpoints.
 */

import { apiGet, apiUpload, apiPost, apiDelete, apiPatch } from '../lib/api';

export interface Job {
  id: string;
  original_filename: string;
  saved_filename?: string | null;
  file_path?: string | null;
  file_size: number;
  mime_type: string;
  duration: number;
  status:
    | 'queued'
    | 'processing'
    | 'cancelling'
    | 'pausing'
    | 'paused'
    | 'completed'
    | 'failed'
    | 'cancelled';
  progress_percent: number | null;
  progress_stage: string | null;
  estimated_time_left: number | null;
  estimated_total_seconds: number | null;
  processing_seconds?: number | null;
  model_used: string;
  asr_provider_used?: string | null;
  diarizer_used: string | null;
  diarizer_provider_used?: string | null;
  language_detected: string;
  speaker_count: number | null;
  has_timestamps: boolean;
  has_speaker_labels: boolean;
  transcript_path?: string | null;
  error_message?: string | null;
  tags: Array<{
    id: number;
    name: string;
    color: string | null;
  }>;
  owner_user_id?: number | null;
  owner_username?: string | null;
  owner_email?: string | null;
  available_exports?: string[];
  created_at: string;
  updated_at?: string;
  started_at: string | null;
  completed_at: string | null;
  stalled_at?: string | null;
  pause_requested_at?: string | null;
  paused_at?: string | null;
  resume_count?: number | null;
}

export interface JobsResponse {
  total: number;
  limit: number;
  offset: number;
  items: Job[];
}

export interface FetchJobsParams {
  status?:
    | 'queued'
    | 'processing'
    | 'cancelling'
    | 'pausing'
    | 'paused'
    | 'completed'
    | 'failed'
    | 'cancelled';
  date_from?: string;
  date_to?: string;
  tags?: string; // Comma-separated tag IDs
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CreateJobParams {
  file: File;
  job_name?: string;
  provider?: string;
  model?: string;
  language?: string;
  enable_timestamps?: boolean;
  enable_speaker_detection?: boolean;
  speaker_count?: number;
  diarizer?: string;
  extra_flags?: string;
  timestamp_timezone?: 'local' | 'utc';
  timestamp_format?: 'date-time' | 'time-date' | 'time-only';
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

  if (params.provider) {
    formData.append('provider', params.provider);
  }

  if (params.job_name) {
    formData.append('job_name', params.job_name);
  }
  
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
  if (params.speaker_count !== undefined) {
    formData.append('speaker_count', String(params.speaker_count));
  }
  if (params.diarizer) {
    formData.append('diarizer', params.diarizer);
  }
  if (params.extra_flags) {
    formData.append('extra_flags', params.extra_flags);
  }

  if (params.timestamp_timezone) {
    formData.append('timestamp_timezone', params.timestamp_timezone);
  }
  if (params.timestamp_format) {
    formData.append('timestamp_format', params.timestamp_format);
  }
  
  return apiUpload<CreateJobResponse>('/jobs', formData);
}

/**
 * Restart a completed, failed, or cancelled job
 */
export async function restartJob(jobId: string): Promise<CreateJobResponse> {
  return apiPost<CreateJobResponse>(`/jobs/${jobId}/restart`);
}

/**
 * Cancel/stop a queued or processing job
 */
export async function cancelJob(jobId: string): Promise<Job> {
  return apiPost<Job>(`/jobs/${jobId}/cancel`);
}

/**
 * Pause a queued or processing job
 */
export async function pauseJob(jobId: string): Promise<Job> {
  return apiPost<Job>(`/jobs/${jobId}/pause`);
}

/**
 * Resume a paused job
 */
export async function resumeJob(jobId: string): Promise<Job> {
  return apiPost<Job>(`/jobs/${jobId}/resume`);
}

/**
 * Delete a job and its associated files
 */
export async function deleteJob(jobId: string): Promise<void> {
  return apiDelete<void>(`/jobs/${jobId}`);
}

/**
 * Assign a tag to a job
 */
export async function assignTag(jobId: string, tagIds: number | number[]): Promise<Job['tags']> {
  const tag_ids = Array.isArray(tagIds) ? tagIds : [tagIds];
  return apiPost<Job['tags']>(`/jobs/${jobId}/tags`, { tag_ids });
}

/**
 * Remove a tag from a job
 */
export async function removeTag(jobId: string, tagId: number): Promise<Job['tags']> {
  return apiDelete<Job['tags']>(`/jobs/${jobId}/tags/${tagId}`);
}

/**
 * Rename a job (updates the display name and underlying media file)
 */
export async function renameJob(jobId: string, name: string): Promise<Job> {
  return apiPatch<Job>(`/jobs/${jobId}/rename`, { name });
}
