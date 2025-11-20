import { apiGet } from '../lib/api';

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface TranscriptResponse {
  job_id: string;
  text: string;
  segments: TranscriptSegment[];
  language: string;
  duration: number;
}

export async function fetchTranscript(jobId: string): Promise<TranscriptResponse> {
  return apiGet<TranscriptResponse>(`/transcripts/${jobId}`);
}
