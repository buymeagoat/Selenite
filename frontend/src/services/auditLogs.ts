import { apiFetchBlob, apiGet } from '../lib/api';

export interface AuditLogEntry {
  id: number;
  actor_user_id: number | null;
  actor_email: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  total: number;
  items: AuditLogEntry[];
}

export interface AuditLogFilters {
  action?: string;
  actor_id?: number;
  target_type?: string;
  target_id?: string;
  q?: string;
  since?: string;
  until?: string;
  limit?: number;
  offset?: number;
}

export async function fetchAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    params.set(key, String(value));
  });
  const query = params.toString();
  return apiGet<AuditLogListResponse>(`/audit-logs${query ? `?${query}` : ''}`);
}

export async function downloadAuditLogs(filters: AuditLogFilters = {}): Promise<Blob> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    params.set(key, String(value));
  });
  const query = params.toString();
  return apiFetchBlob(`/audit-logs/export${query ? `?${query}` : ''}`);
}
