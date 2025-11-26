import { apiGet, apiPost } from '../lib/api';

export interface GPUDevice {
  name?: string;
  memory_gb?: number;
  multi_processor_count?: number;
}

export interface SystemProbe {
  detected_at: string;
  os: {
    system: string;
    release: string;
    version: string;
    machine: string;
  };
  cpu: {
    model?: string;
    architecture?: string;
    cores_physical?: number;
    cores_logical?: number;
    max_frequency_mhz?: number;
  };
  memory: {
    total_gb?: number;
    available_gb?: number;
  };
  gpu: {
    has_gpu: boolean;
    api?: string | null;
    driver?: string | null;
    devices: GPUDevice[];
  };
  storage: {
    database?: DiskUsage | null;
    media: DiskUsage;
    transcripts: DiskUsage;
    project: DiskUsage;
  };
  network: {
    hostname: string;
    interfaces: Array<{ name: string; ipv4: string[] }>;
  };
  runtime: {
    python: string;
    node?: string | null;
  };
  container: {
    is_container: boolean;
    indicators: string[];
  };
  recommendation: {
    suggested_asr_model: string;
    suggested_diarization: string;
    basis: string[];
  };
}

export interface DiskUsage {
  path: string;
  total_gb?: number | null;
  used_gb?: number | null;
  free_gb?: number | null;
}

export async function fetchSystemInfo(): Promise<SystemProbe> {
  return apiGet<SystemProbe>('/system/info');
}

export async function refreshSystemInfo(): Promise<SystemProbe> {
  return apiPost<SystemProbe>('/system/info/detect', {});
}

export interface CapabilityResponse {
  asr: Array<{
    provider: string;
    display_name: string;
    available: boolean;
    models: string[];
    notes: string[];
  }>;
  diarizers: Array<{
    key: string;
    display_name: string;
    requires_gpu: boolean;
    available: boolean;
    notes: string[];
  }>;
}

export async function fetchCapabilities(): Promise<CapabilityResponse> {
  return apiGet<CapabilityResponse>('/system/availability');
}
