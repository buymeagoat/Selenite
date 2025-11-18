/**
 * Tags API Service
 * 
 * Functions for managing tags and tag assignments.
 */

import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api';

export interface Tag {
  id: number;
  name: string;
  color: string;
  job_count: number;
  created_at: string;
}

export interface TagsResponse {
  total: number;
  items: Tag[];
}

export interface CreateTagParams {
  name: string;
  color: string;
}

export interface UpdateTagParams {
  name?: string;
  color?: string;
}

/**
 * Fetch all tags with job counts
 */
export async function fetchTags(): Promise<TagsResponse> {
  return apiGet<TagsResponse>('/tags');
}

/**
 * Create a new tag
 */
export async function createTag(params: CreateTagParams): Promise<Tag> {
  return apiPost<Tag>('/tags', params);
}

/**
 * Update an existing tag
 */
export async function updateTag(tagId: number, params: UpdateTagParams): Promise<Tag> {
  return apiPut<Tag>(`/tags/${tagId}`, params);
}

/**
 * Delete a tag (removes from all jobs)
 */
export async function deleteTag(tagId: number): Promise<{ message: string; id: number; jobs_affected: number }> {
  return apiDelete<{ message: string; id: number; jobs_affected: number }>(`/tags/${tagId}`);
}
