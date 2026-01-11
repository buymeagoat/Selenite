import { apiDelete, apiFetchBlob, apiGet, apiPost, apiUpload, API_BASE_URL } from '../lib/api';

export interface FeedbackAttachment {
  id: number;
  filename: string;
  content_type?: string | null;
  size_bytes: number;
}

export interface FeedbackSubmission {
  id: number;
  category: string;
  subject?: string | null;
  message: string;
  submitter_name?: string | null;
  submitter_email?: string | null;
  recipient_email?: string | null;
  is_anonymous: boolean;
  user_id?: number | null;
  sender_user_id?: number | null;
  direction: string;
  folder: string;
  is_read: boolean;
  parent_id?: number | null;
  thread_id?: number | null;
  email_status: string;
  webhook_status: string;
  delivery_error?: string | null;
  sent_at?: string | null;
  read_at?: string | null;
  deleted_at?: string | null;
  created_at: string;
  attachments: FeedbackAttachment[];
}

export interface FeedbackListResponse {
  total: number;
  limit: number;
  offset: number;
  items: FeedbackSubmission[];
}

export interface FeedbackDetailResponse {
  message: FeedbackSubmission;
  thread: FeedbackSubmission[];
}

export interface FeedbackSubmissionParams {
  category: string;
  message: string;
  subject?: string;
  submitterName?: string;
  submitterEmail?: string;
  attachments?: File[];
}

export async function submitFeedback(params: FeedbackSubmissionParams): Promise<FeedbackSubmission> {
  const form = new FormData();
  form.append('category', params.category);
  form.append('message', params.message);
  if (params.subject) {
    form.append('subject', params.subject);
  }
  if (params.submitterName) {
    form.append('submitter_name', params.submitterName);
  }
  if (params.submitterEmail) {
    form.append('submitter_email', params.submitterEmail);
  }
  params.attachments?.forEach((file) => {
    form.append('attachments', file);
  });
  return apiUpload<FeedbackSubmission>('/feedback', form);
}

export async function fetchFeedback(limit = 50, offset = 0): Promise<FeedbackListResponse> {
  return apiGet<FeedbackListResponse>('/feedback', { limit, offset });
}

export function getFeedbackAttachmentUrl(submissionId: number, attachmentId: number): string {
  const base = API_BASE_URL || '';
  return `${base}/feedback/${submissionId}/attachments/${attachmentId}`;
}

export async function fetchFeedbackAttachment(
  submissionId: number,
  attachmentId: number
): Promise<Blob> {
  return apiFetchBlob(`/feedback/${submissionId}/attachments/${attachmentId}`);
}

export async function replyToFeedback(
  submissionId: number,
  message: string,
  subject?: string
): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`/feedback/${submissionId}/reply`, {
    message,
    subject: subject?.trim() || null,
  });
}

export async function deleteFeedback(submissionId: number): Promise<void> {
  return apiDelete<void>(`/feedback/${submissionId}`);
}

export async function fetchMessages(
  folder: string,
  options: { limit?: number; offset?: number; search?: string; unreadOnly?: boolean } = {}
): Promise<FeedbackListResponse> {
  return apiGet<FeedbackListResponse>('/messages', {
    folder,
    limit: options.limit ?? 50,
    offset: options.offset ?? 0,
    search: options.search ?? undefined,
    unread_only: options.unreadOnly ?? undefined,
  });
}

export async function fetchMessageDetail(messageId: number): Promise<FeedbackDetailResponse> {
  return apiGet<FeedbackDetailResponse>(`/messages/${messageId}`);
}

export async function sendMessage(params: {
  recipientEmail: string;
  subject?: string;
  message: string;
  attachments?: File[];
}): Promise<FeedbackSubmission> {
  const form = new FormData();
  form.append('recipient_email', params.recipientEmail);
  form.append('message', params.message);
  if (params.subject) {
    form.append('subject', params.subject);
  }
  params.attachments?.forEach((file) => form.append('attachments', file));
  return apiUpload<FeedbackSubmission>('/messages/send', form);
}

export async function saveDraft(params: {
  recipientEmail?: string;
  subject?: string;
  message?: string;
  attachments?: File[];
  parentId?: number;
}): Promise<FeedbackSubmission> {
  const form = new FormData();
  if (params.recipientEmail) {
    form.append('recipient_email', params.recipientEmail);
  }
  if (params.subject) {
    form.append('subject', params.subject);
  }
  if (params.message) {
    form.append('message', params.message);
  }
  if (params.parentId) {
    form.append('parent_id', String(params.parentId));
  }
  params.attachments?.forEach((file) => form.append('attachments', file));
  return apiUpload<FeedbackSubmission>('/messages/drafts', form);
}

export async function updateDraft(
  messageId: number,
  params: {
    recipientEmail?: string;
    subject?: string;
    message?: string;
    attachments?: File[];
    parentId?: number;
  }
): Promise<FeedbackSubmission> {
  const form = new FormData();
  if (params.recipientEmail !== undefined) {
    form.append('recipient_email', params.recipientEmail);
  }
  if (params.subject !== undefined) {
    form.append('subject', params.subject);
  }
  if (params.message !== undefined) {
    form.append('message', params.message);
  }
  if (params.parentId) {
    form.append('parent_id', String(params.parentId));
  }
  params.attachments?.forEach((file) => form.append('attachments', file));
  return apiUpload<FeedbackSubmission>(`/messages/drafts/${messageId}`, form);
}

export async function sendDraft(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/drafts/${messageId}/send`);
}

export async function replyToMessage(params: {
  messageId: number;
  subject?: string;
  message: string;
  attachments?: File[];
}): Promise<FeedbackSubmission> {
  const form = new FormData();
  form.append('message', params.message);
  if (params.subject) {
    form.append('subject', params.subject);
  }
  params.attachments?.forEach((file) => form.append('attachments', file));
  return apiUpload<FeedbackSubmission>(`/messages/${params.messageId}/reply`, form);
}

export async function archiveMessage(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/${messageId}/archive`);
}

export async function unarchiveMessage(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/${messageId}/unarchive`);
}

export async function deleteMessage(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/${messageId}/delete`);
}

export async function restoreMessage(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/${messageId}/restore`);
}

export async function purgeMessage(messageId: number): Promise<{ status: string }> {
  return apiDelete<{ status: string }>(`/messages/${messageId}`);
}

export async function markMessageRead(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/${messageId}/read`);
}

export async function markMessageUnread(messageId: number): Promise<FeedbackSubmission> {
  return apiPost<FeedbackSubmission>(`/messages/${messageId}/unread`);
}

export async function bulkMessageAction(action: string, ids: number[]): Promise<{ status: string }> {
  const form = new FormData();
  form.append('action', action);
  form.append('ids', ids.join(','));
  return apiUpload<{ status: string }>('/messages/bulk', form);
}
