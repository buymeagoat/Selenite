import { apiDelete, apiPatch, apiPost, apiGet } from '../lib/api';

export type ProviderType = 'asr' | 'diarizer';

export interface ModelSet {
  id: number;
  type: ProviderType;
  name: string;
  description?: string | null;
  abs_path: string;
  enabled: boolean;
  disable_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModelWeight {
  id: number;
  set_id: number;
  type: ProviderType;
  name: string;
  description?: string | null;
  abs_path: string;
  checksum?: string | null;
  enabled: boolean;
  disable_reason?: string | null;
  has_weights?: boolean;
  force_enabled?: boolean;
  created_at: string;
  updated_at: string;
}

export type ModelSetWithWeights = ModelSet & { weights: ModelWeight[] };

export interface ModelSetCreatePayload {
  type: ProviderType;
  name: string;
  description?: string | null;
  abs_path: string;
}

export interface ModelSetUpdatePayload {
  name?: string;
  description?: string | null;
  abs_path?: string;
  enabled?: boolean;
  disable_reason?: string | null;
}

export interface ModelWeightCreatePayload {
  name: string;
  description?: string | null;
  abs_path: string;
  checksum?: string | null;
}

export interface ModelWeightUpdatePayload {
  name?: string;
  description?: string | null;
  abs_path?: string;
  checksum?: string | null;
  enabled?: boolean;
  disable_reason?: string | null;
}

export async function listModelSets(): Promise<ModelSetWithWeights[]> {
  return apiGet<ModelSetWithWeights[]>('/models/providers');
}

export async function createModelSet(payload: ModelSetCreatePayload): Promise<ModelSet> {
  return apiPost<ModelSet>('/models/providers', payload);
}

export async function updateModelSet(setId: number, payload: ModelSetUpdatePayload): Promise<ModelSet> {
  return apiPatch<ModelSet>(`/models/providers/${setId}`, payload);
}

export async function deleteModelSet(setId: number): Promise<void> {
  await apiDelete(`/models/providers/${setId}`);
}

export async function createModelWeight(
  setId: number,
  payload: ModelWeightCreatePayload
): Promise<ModelWeight> {
  return apiPost<ModelWeight>(`/models/providers/${setId}/weights`, payload);
}

export async function updateModelWeight(
  weightId: number,
  payload: ModelWeightUpdatePayload
): Promise<ModelWeight> {
  return apiPatch<ModelWeight>(`/models/providers/weights/${weightId}`, payload);
}

export async function deleteModelWeight(weightId: number): Promise<void> {
  await apiDelete(`/models/providers/weights/${weightId}`);
}
