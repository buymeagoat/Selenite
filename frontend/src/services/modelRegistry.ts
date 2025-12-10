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

export interface ModelEntry {
  id: number;
  set_id: number;
  type: ProviderType;
  name: string;
  description?: string | null;
  abs_path: string;
  checksum?: string | null;
  enabled: boolean;
  disable_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export type ModelSetWithEntries = ModelSet & { entries: ModelEntry[] };

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

export interface ModelEntryCreatePayload {
  name: string;
  description?: string | null;
  abs_path: string;
  checksum?: string | null;
}

export interface ModelEntryUpdatePayload {
  name?: string;
  description?: string | null;
  abs_path?: string;
  checksum?: string | null;
  enabled?: boolean;
  disable_reason?: string | null;
}

export async function listModelSets(): Promise<ModelSetWithEntries[]> {
  return apiGet<ModelSetWithEntries[]>('/models/providers');
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

export async function createModelEntry(
  setId: number,
  payload: ModelEntryCreatePayload
): Promise<ModelEntry> {
  return apiPost<ModelEntry>(`/models/providers/${setId}/entries`, payload);
}

export async function updateModelEntry(
  entryId: number,
  payload: ModelEntryUpdatePayload
): Promise<ModelEntry> {
  return apiPatch<ModelEntry>(`/models/providers/entries/${entryId}`, payload);
}

export async function deleteModelEntry(entryId: number): Promise<void> {
  await apiDelete(`/models/providers/entries/${entryId}`);
}
