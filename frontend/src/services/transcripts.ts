import { apiGet } from '../lib/api';

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

export async function fetchTranscript(jobId: string): Promise<TranscriptResponse> {
  return apiGet<TranscriptResponse>(`/transcripts/${jobId}`);
}
