import { apiGet, apiPatch } from '../lib/api';

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
}

export interface TranscriptResponse {
  job_id: string;
  text: string;
  segments: TranscriptSegment[];
  language: string;
  duration: number;
  has_timestamps: boolean;
  has_speaker_labels: boolean;
}

export interface SpeakerLabelsResponse {
  speakers: string[];
}

export interface SpeakerLabelUpdate {
  label: string;
  name: string;
}

export async function fetchTranscript(jobId: string): Promise<TranscriptResponse> {
  return apiGet<TranscriptResponse>(`/transcripts/${jobId}`);
}

export async function fetchSpeakerLabels(jobId: string): Promise<SpeakerLabelsResponse> {
  return apiGet<SpeakerLabelsResponse>(`/transcripts/${jobId}/speakers`);
}

export async function updateSpeakerLabels(
  jobId: string,
  updates: SpeakerLabelUpdate[]
): Promise<SpeakerLabelsResponse> {
  return apiPatch<SpeakerLabelsResponse>(`/transcripts/${jobId}/speakers`, { updates });
}
