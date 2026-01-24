import React, { useEffect, useMemo, useState } from 'react';
import { Archive, Inbox, Mail, Pencil, Trash2, X } from 'lucide-react';
import {
  bulkMessageAction,
  deleteMessage,
  fetchFeedbackAttachment,
  fetchMessageDetail,
  fetchMessages,
  archiveMessage,
  markMessageRead,
  purgeMessage,
  replyToMessage,
  restoreMessage,
  saveDraft,
  sendDraft,
  sendMessage,
  unarchiveMessage,
  updateDraft,
  type FeedbackDetailResponse,
  type FeedbackSubmission,
} from '../../services/feedback';
import { useToast } from '../../context/ToastContext';
import { ApiError } from '../../lib/api';
import { formatDateTime, type DateTimePreferences } from '../../utils/dateTime';

const FOLDERS = [
  { key: 'inbox', label: 'Inbox', icon: Inbox },
  { key: 'archived', label: 'Archived', icon: Archive },
  { key: 'sent', label: 'Sent', icon: Mail },
  { key: 'deleted', label: 'Deleted', icon: Trash2 },
  { key: 'drafts', label: 'Drafts', icon: Pencil },
] as const;

const MAX_ATTACHMENTS = 5;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'text/plain', 'application/pdf'];
const MESSAGES_FOLDER_STORAGE_KEY = 'selenite.admin.messages.folder';

type FolderKey = typeof FOLDERS[number]['key'];
type ComposeMode = 'new' | 'reply' | 'edit-draft';

interface MessagesPanelProps {
  feedbackStoreEnabled: boolean;
  timeZone?: string | null;
  dateFormat?: DateTimePreferences['dateFormat'];
  timeFormat?: DateTimePreferences['timeFormat'];
  locale?: string | null;
}

export const MessagesPanel: React.FC<MessagesPanelProps> = ({
  feedbackStoreEnabled,
  timeZone = null,
  dateFormat = 'locale',
  timeFormat = 'locale',
  locale = null,
}) => {
  const { showError, showSuccess } = useToast();
  const resolveInitialFolder = (): FolderKey => {
    const allowedFolders = new Set<FolderKey>(['inbox', 'archived', 'sent', 'deleted', 'drafts']);
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const param = params.get('messagesFolder');
      if (param && allowedFolders.has(param as FolderKey)) {
        return param as FolderKey;
      }
      const stored = localStorage.getItem(MESSAGES_FOLDER_STORAGE_KEY);
      if (stored && allowedFolders.has(stored as FolderKey)) {
        return stored as FolderKey;
      }
    }
    return 'inbox';
  };
  const [folder, setFolder] = useState<FolderKey>(resolveInitialFolder);
  const [messages, setMessages] = useState<FeedbackSubmission[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [detail, setDetail] = useState<FeedbackDetailResponse | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [composeOpen, setComposeOpen] = useState(false);
  const [composeMode, setComposeMode] = useState<ComposeMode>('new');
  const [composeRecipient, setComposeRecipient] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeMessage, setComposeMessage] = useState('');
  const [composeParentId, setComposeParentId] = useState<number | null>(null);
  const [composeDraftId, setComposeDraftId] = useState<number | null>(null);
  const [composeAttachments, setComposeAttachments] = useState<File[]>([]);
  const [composeExistingAttachments, setComposeExistingAttachments] = useState<string[]>([]);
  const [composeSending, setComposeSending] = useState(false);
  const [composeSaving, setComposeSaving] = useState(false);
  const [composeDeleting, setComposeDeleting] = useState(false);

  const selectedList = useMemo(() => Array.from(selectedIds), [selectedIds]);
  const selectedSingle = selectedList.length === 1 ? selectedList[0] : null;
  const selectedMessage = selectedSingle
    ? messages.find((item) => item.id === selectedSingle) ?? null
    : null;

  const formatMessageDate = (value: string): string => {
    return formatDateTime(value, {
      timeZone,
      dateFormat,
      timeFormat,
      locale,
    });
  };

  const loadMessages = async () => {
    if (!feedbackStoreEnabled) {
      setMessages([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    try {
      const response = await fetchMessages(folder, {
        search: search.trim() || undefined,
      });
      setMessages(response.items);
      setTotal(response.total);
      setSelectedIds(new Set());
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Failed to load messages: ${error.message}`);
      } else {
        showError('Failed to load messages.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [folder]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(MESSAGES_FOLDER_STORAGE_KEY, folder);
    const url = new URL(window.location.href);
    url.searchParams.set('messagesFolder', folder);
    window.history.replaceState(null, '', url.toString());
  }, [folder]);

  const toggleSelectAll = () => {
    if (selectedIds.size === messages.length) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(messages.map((item) => item.id)));
  };

  const toggleSelect = (messageId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const handleBulkAction = async (action: string) => {
    if (!selectedList.length) return;
    try {
      await bulkMessageAction(action, selectedList);
      showSuccess('Messages updated.');
      await loadMessages();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Bulk action failed: ${error.message}`);
      } else {
        showError('Bulk action failed.');
      }
    }
  };

  const openDetail = async (messageId: number) => {
    try {
      const response = await fetchMessageDetail(messageId);
      setDetail(response);
      setDetailOpen(true);
      await markMessageRead(messageId);
      await loadMessages();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Failed to load message: ${error.message}`);
      } else {
        showError('Failed to load message.');
      }
    }
  };

  const closeDetail = () => {
    setDetailOpen(false);
    setDetail(null);
  };

  const openCompose = (mode: ComposeMode, message?: FeedbackSubmission) => {
    setComposeMode(mode);
    if (mode === 'reply' && message) {
      const recipient = message.submitter_email || message.recipient_email || '';
      setComposeRecipient(recipient);
      setComposeSubject(message.subject ? `Re: ${message.subject}` : 'Re: your message');
      setComposeMessage('');
      setComposeParentId(message.id);
      setComposeDraftId(null);
      setComposeExistingAttachments([]);
    } else if (mode === 'edit-draft' && message) {
      setComposeRecipient(message.recipient_email || '');
      setComposeSubject(message.subject || '');
      setComposeMessage(message.message || '');
      setComposeParentId(message.parent_id ?? null);
      setComposeDraftId(message.id);
      setComposeExistingAttachments(message.attachments.map((att) => att.filename));
    } else {
      setComposeRecipient('');
      setComposeSubject('');
      setComposeMessage('');
      setComposeParentId(null);
      setComposeDraftId(null);
      setComposeExistingAttachments([]);
    }
    setComposeAttachments([]);
    setComposeOpen(true);
  };

  const closeCompose = () => {
    setComposeOpen(false);
    setComposeAttachments([]);
    setComposeExistingAttachments([]);
    setComposeRecipient('');
    setComposeSubject('');
    setComposeMessage('');
    setComposeParentId(null);
    setComposeDraftId(null);
    setComposeDeleting(false);
  };

  const handleComposeSend = async () => {
    if (!composeMessage.trim()) {
      showError('Message body cannot be empty.');
      return;
    }
    setComposeSending(true);
    try {
      if (composeMode === 'reply' && composeParentId) {
        await replyToMessage({
          messageId: composeParentId,
          subject: composeSubject,
          message: composeMessage,
          attachments: composeAttachments,
        });
      } else if (composeMode === 'edit-draft' && composeDraftId) {
        await updateDraft(composeDraftId, {
          recipientEmail: composeRecipient,
          subject: composeSubject,
          message: composeMessage,
          attachments: composeAttachments,
          parentId: composeParentId ?? undefined,
        });
        await sendDraft(composeDraftId);
      } else {
        await sendMessage({
          recipientEmail: composeRecipient,
          subject: composeSubject,
          message: composeMessage,
          attachments: composeAttachments,
        });
      }
      showSuccess('Message sent.');
      closeCompose();
      await loadMessages();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Send failed: ${error.message}`);
      } else {
        showError('Send failed.');
      }
    } finally {
      setComposeSending(false);
    }
  };

  const handleComposeSaveDraft = async () => {
    if (!composeSubject.trim() && !composeMessage.trim()) {
      showError('Draft must include a subject or body.');
      return;
    }
    setComposeSaving(true);
    try {
      if (composeMode === 'edit-draft' && composeDraftId) {
        await updateDraft(composeDraftId, {
          recipientEmail: composeRecipient,
          subject: composeSubject,
          message: composeMessage,
          attachments: composeAttachments,
          parentId: composeParentId ?? undefined,
        });
      } else {
        await saveDraft({
          recipientEmail: composeRecipient || undefined,
          subject: composeSubject || undefined,
          message: composeMessage || undefined,
          attachments: composeAttachments,
          parentId: composeParentId ?? undefined,
        });
      }
      showSuccess('Draft saved.');
      closeCompose();
      await loadMessages();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Failed to save draft: ${error.message}`);
      } else {
        showError('Failed to save draft.');
      }
    } finally {
      setComposeSaving(false);
    }
  };

  const handleComposeDeleteDraft = async () => {
    if (!composeDraftId) return;
    setComposeDeleting(true);
    try {
      await deleteMessage(composeDraftId);
      showSuccess('Draft moved to Deleted.');
      closeCompose();
      await loadMessages();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Failed to delete draft: ${error.message}`);
      } else {
        showError('Failed to delete draft.');
      }
    } finally {
      setComposeDeleting(false);
    }
  };

  const handleDownloadAttachment = async (
    submissionId: number,
    attachmentId: number,
    filename: string
  ) => {
    try {
      const blob = await fetchFeedbackAttachment(submissionId, attachmentId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      showError(error instanceof ApiError ? error.message : 'Failed to download attachment.');
    }
  };

  const selectedHasEmail = selectedMessage?.submitter_email || selectedMessage?.recipient_email;

  return (
    <section className="bg-white border border-sage-mid rounded-lg p-6" data-testid="admin-messages">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-medium text-pine-deep">Messages</h2>
          <p className="text-sm text-pine-mid">Shared admin inbox</p>
        </div>
        <button
          type="button"
          className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
          onClick={() => openCompose('new')}
        >
          Compose
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <aside className="border border-sage-mid rounded-lg p-3 bg-sage-light/30">
          <div className="space-y-1">
            {FOLDERS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  type="button"
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded text-sm ${
                    folder === item.key
                      ? 'bg-forest-green text-white'
                      : 'text-pine-deep hover:bg-sage-light'
                  }`}
                  onClick={() => setFolder(item.key)}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </aside>

        <div className="lg:col-span-3 border border-sage-mid rounded-lg p-4">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                aria-label="Select all messages"
                checked={messages.length > 0 && selectedIds.size === messages.length}
                onChange={toggleSelectAll}
              />
              <span className="text-xs text-pine-mid">{selectedIds.size} selected</span>
            </div>
            <input
              type="text"
              placeholder="Search messages"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onBlur={loadMessages}
              className="px-3 py-2 border border-sage-mid rounded-lg text-sm"
            />
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            {folder === 'inbox' && (
              <>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => handleBulkAction('archive')}
                  disabled={!selectedIds.size}
                >
                  Archive
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => handleBulkAction('delete')}
                  disabled={!selectedIds.size}
                >
                  Delete
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => selectedMessage && openCompose('reply', selectedMessage)}
                  disabled={!selectedHasEmail || selectedIds.size !== 1}
                >
                  Reply
                </button>
              </>
            )}
            {folder === 'archived' && (
              <>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => handleBulkAction('restore')}
                  disabled={!selectedIds.size}
                >
                  Unarchive
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => handleBulkAction('delete')}
                  disabled={!selectedIds.size}
                >
                  Delete
                </button>
              </>
            )}
            {folder === 'sent' && (
              <button
                type="button"
                className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                onClick={() => handleBulkAction('delete')}
                disabled={!selectedIds.size}
              >
                Delete
              </button>
            )}
            {folder === 'drafts' && (
              <button
                type="button"
                className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                onClick={() => handleBulkAction('delete')}
                disabled={!selectedIds.size}
              >
                Delete
              </button>
            )}
            {folder === 'deleted' && (
              <>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => handleBulkAction('restore')}
                  disabled={!selectedIds.size}
                >
                  Restore
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-terracotta text-terracotta rounded-lg"
                  onClick={() => handleBulkAction('purge')}
                  disabled={!selectedIds.size}
                >
                  Permanently delete
                </button>
              </>
            )}
          </div>

          {loading ? (
            <p className="text-sm text-pine-mid">Loading messages...</p>
          ) : !feedbackStoreEnabled ? (
            <p className="text-sm text-terracotta">Feedback inbox is disabled in System settings.</p>
          ) : messages.length === 0 ? (
            <p className="text-sm text-pine-mid">No messages in {folder}.</p>
          ) : (
            <div className="divide-y divide-sage-mid">
              {messages.map((item) => {
                const fromLabel =
                  item.direction === 'outgoing'
                    ? `To: ${item.recipient_email || 'Unknown'}`
                    : item.submitter_name || item.submitter_email || 'Anonymous';
                return (
                  <div
                    key={item.id}
                    className={`flex items-center gap-3 py-3 cursor-pointer ${
                      item.is_read ? 'text-pine-mid' : 'text-pine-deep font-semibold'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(item.id)}
                      onChange={() => toggleSelect(item.id)}
                      aria-label={`Select message ${item.id}`}
                    />
                    <div className="flex-1" onClick={() => {
                      if (folder === 'drafts') {
                        openCompose('edit-draft', item);
                      } else {
                        openDetail(item.id);
                      }
                    }}>
                      <div className="flex items-center justify-between">
                        <span className="text-sm">{fromLabel}</span>
                        <span className="text-xs text-pine-mid">{formatMessageDate(item.created_at)}</span>
                      </div>
                      <div className="text-sm">
                        {item.subject || 'No subject'} - {item.message.slice(0, 80)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <div className="text-xs text-pine-mid mt-3">Total: {total}</div>
        </div>
      </div>

      {detailOpen && detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white w-full max-w-3xl rounded-lg shadow-lg border border-sage-mid">
            <div className="flex items-center justify-between border-b border-sage-mid px-5 py-3">
              <div>
                <h3 className="text-lg font-semibold text-pine-deep">Message</h3>
              </div>
              <button
                type="button"
                onClick={closeDetail}
                className="p-1 rounded hover:bg-sage-light"
                aria-label="Close message"
              >
                <X className="w-5 h-5 text-pine-mid" />
              </button>
            </div>
            <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-auto">
              <div className="border border-sage-mid rounded-lg p-3 text-sm text-pine-deep space-y-1">
                <div><span className="font-semibold">Sender:</span> {detail.message.submitter_name || 'Anonymous'}</div>
                <div><span className="font-semibold">Email Address:</span> {detail.message.submitter_email || 'Not provided'}</div>
                <div><span className="font-semibold">Date:</span> {formatMessageDate(detail.message.created_at)}</div>
                <div><span className="font-semibold">Subject:</span> {detail.message.subject || detail.message.category}</div>
                <div className="mt-2">
                  <div className="font-semibold">Message:</div>
                  <p className="whitespace-pre-wrap">{detail.message.message}</p>
                </div>
              </div>
              {detail.thread.map((msg) => (
                <div key={msg.id} className="border border-sage-mid rounded-lg p-3">
                  <div className="flex items-center justify-between text-xs text-pine-mid">
                    <span>
                      {msg.direction === 'outgoing'
                        ? `To: ${msg.recipient_email || 'Unknown'}`
                        : msg.submitter_name || msg.submitter_email || 'Anonymous'}
                    </span>
                    <span>{formatMessageDate(msg.created_at)}</span>
                  </div>
                  <p className="text-sm text-pine-deep mt-2 whitespace-pre-wrap">{msg.message}</p>
                  {msg.attachments.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {msg.attachments.map((attachment) => (
                        <button
                          key={attachment.id}
                          type="button"
                          className="text-forest-green underline"
                          onClick={() =>
                            handleDownloadAttachment(msg.id, attachment.id, attachment.filename)
                          }
                        >
                          {attachment.filename}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-sage-mid px-5 py-3">
              {['inbox', 'archived', 'sent'].includes(detail.message.folder) && (
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => openCompose('reply', detail.message)}
                >
                  Reply
                </button>
              )}
              {['inbox', 'archived', 'sent'].includes(detail.message.folder) && (
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={() => openCompose('reply', detail.message)}
                >
                  Save Draft
                </button>
              )}
              {detail.message.folder === 'inbox' && (
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={async () => {
                    await archiveMessage(detail.message.id);
                    closeDetail();
                    loadMessages();
                  }}
                >
                  Archive
                </button>
              )}
              {detail.message.folder === 'archived' && (
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={async () => {
                    await unarchiveMessage(detail.message.id);
                    closeDetail();
                    loadMessages();
                  }}
                >
                  Unarchive
                </button>
              )}
              {detail.message.folder !== 'deleted' && (
                <button
                  type="button"
                  className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                  onClick={async () => {
                    await deleteMessage(detail.message.id);
                    closeDetail();
                    loadMessages();
                  }}
                >
                  Delete
                </button>
              )}
              {detail.message.folder === 'deleted' && (
                <>
                  <button
                    type="button"
                    className="px-3 py-1.5 text-xs border border-sage-mid rounded-lg"
                    onClick={async () => {
                      await restoreMessage(detail.message.id);
                      closeDetail();
                      loadMessages();
                    }}
                  >
                    Restore
                  </button>
                  <button
                    type="button"
                    className="px-3 py-1.5 text-xs border border-terracotta text-terracotta rounded-lg"
                    onClick={async () => {
                      await purgeMessage(detail.message.id);
                      closeDetail();
                      loadMessages();
                    }}
                  >
                    Permanently delete
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {composeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white w-full max-w-2xl rounded-lg shadow-lg border border-sage-mid">
            <div className="flex items-center justify-between border-b border-sage-mid px-5 py-3">
              <h3 className="text-lg font-semibold text-pine-deep">
                {composeMode === 'edit-draft' ? 'Edit Draft' : composeMode === 'reply' ? 'Reply' : 'New Message'}
              </h3>
              <button
                type="button"
                onClick={closeCompose}
                className="p-1 rounded hover:bg-sage-light"
              >
                <X className="w-5 h-5 text-pine-mid" />
              </button>
            </div>
            <div className="px-5 py-4 space-y-3">
              <div>
                <label className="text-sm font-medium text-pine-mid">To</label>
                <input
                  type="email"
                  value={composeRecipient}
                  onChange={(e) => setComposeRecipient(e.target.value)}
                  disabled={composeMode === 'reply'}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-pine-mid">Subject</label>
                <input
                  type="text"
                  value={composeSubject}
                  onChange={(e) => setComposeSubject(e.target.value)}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-pine-mid">Message</label>
                <textarea
                  rows={6}
                  value={composeMessage}
                  onChange={(e) => setComposeMessage(e.target.value)}
                  className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-pine-mid">Attachments</label>
                <input
                  type="file"
                  multiple
                  accept={ALLOWED_TYPES.join(',')}
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    const next = [...composeAttachments];
                    files.forEach((file) => {
                      if (next.length >= MAX_ATTACHMENTS) {
                        showError(`Only ${MAX_ATTACHMENTS} attachments are allowed.`);
                        return;
                      }
                      if (!ALLOWED_TYPES.includes(file.type)) {
                        showError(`Unsupported file type: ${file.name}`);
                        return;
                      }
                      next.push(file);
                    });
                    setComposeAttachments(next);
                  }}
                />
                {composeExistingAttachments.length > 0 && (
                  <p className="text-xs text-pine-mid mt-1">
                    Existing attachments will stay on this draft.
                  </p>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-sage-mid px-5 py-3">
              <button
                type="button"
                className="px-4 py-2 border border-sage-mid rounded-lg"
                onClick={closeCompose}
              >
                Cancel
              </button>
              {composeMode === 'edit-draft' && (
                <button
                  type="button"
                  className="px-4 py-2 border border-terracotta text-terracotta rounded-lg"
                  onClick={handleComposeDeleteDraft}
                  disabled={composeDeleting}
                >
                  {composeDeleting ? 'Deleting...' : 'Delete Draft'}
                </button>
              )}
              <button
                type="button"
                className="px-4 py-2 border border-sage-mid rounded-lg"
                onClick={handleComposeSaveDraft}
                disabled={composeSaving || composeDeleting}
              >
                {composeSaving ? 'Saving...' : 'Save Draft'}
              </button>
              <button
                type="button"
                className="px-4 py-2 bg-forest-green text-white rounded-lg"
                onClick={handleComposeSend}
                disabled={composeSending || composeDeleting}
              >
                {composeSending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
