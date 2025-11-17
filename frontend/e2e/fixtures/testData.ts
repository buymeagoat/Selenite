import { APIRequestContext } from '@playwright/test';

/**
 * Test data helpers for E2E tests.
 * These create entities via API calls to speed up test setup.
 */

export interface CreateJobOptions {
  filename?: string;
  model?: string;
  language?: string;
  speakerDetection?: boolean;
  timestamps?: boolean;
}

/**
 * Create a transcription job via API.
 * Note: Backend may require multipart/form-data with actual file.
 * For now, this is a placeholder that matches the POST /jobs contract.
 */
export async function createJob(
  request: APIRequestContext,
  options: CreateJobOptions = {}
): Promise<{ id: number; filename: string }> {
  const {
    filename = 'test-audio.mp3',
    model = 'base',
    language = 'auto',
    speakerDetection = false,
    timestamps = true
  } = options;

  // TODO: Replace with actual multipart upload when backend is ready
  // For now, return mock data matching expected response
  return {
    id: Math.floor(Math.random() * 10000),
    filename
  };
}

export interface CreateTagOptions {
  name: string;
  color?: string;
}

/**
 * Create a tag via API.
 */
export async function createTag(
  request: APIRequestContext,
  options: CreateTagOptions
): Promise<{ id: number; name: string; color: string }> {
  const response = await request.post('/api/tags', {
    data: {
      name: options.name,
      color: options.color || '#4CAF50'
    }
  });

  if (!response.ok()) {
    throw new Error(`Failed to create tag: ${response.status()}`);
  }

  return await response.json();
}

/**
 * Assign tags to a job via API.
 */
export async function assignTagsToJob(
  request: APIRequestContext,
  jobId: number,
  tagIds: number[]
): Promise<void> {
  const response = await request.put(`/api/jobs/${jobId}/tags`, {
    data: { tag_ids: tagIds }
  });

  if (!response.ok()) {
    throw new Error(`Failed to assign tags: ${response.status()}`);
  }
}

/**
 * Delete a job via API (cleanup helper).
 */
export async function deleteJob(
  request: APIRequestContext,
  jobId: number
): Promise<void> {
  await request.delete(`/api/jobs/${jobId}`);
}

/**
 * Delete a tag via API (cleanup helper).
 */
export async function deleteTag(
  request: APIRequestContext,
  tagId: number
): Promise<void> {
  await request.delete(`/api/tags/${tagId}`);
}
