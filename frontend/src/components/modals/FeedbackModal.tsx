import React, { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { submitFeedback } from '../../services/feedback';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';

const CATEGORY_OPTIONS = [
  { value: 'bug', label: 'Bug' },
  { value: 'suggestion', label: 'Suggestion' },
  { value: 'comment', label: 'Comment' },
];

const MAX_ATTACHMENTS = 5;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'text/plain', 'application/pdf'];

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose }) => {
  const { showError, showSuccess } = useToast();
  const { user } = useAuth();
  const [category, setCategory] = useState('comment');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitterName, setSubmitterName] = useState('');
  const [submitterEmail, setSubmitterEmail] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setMessage('');
    setSubject('');
    if (user) {
      setSubmitterName(user.username || '');
      setSubmitterEmail(user.email || '');
    } else {
      setSubmitterName('');
      setSubmitterEmail('');
    }
  }, [isOpen, user]);

  const attachmentInfo = useMemo(
    () =>
      attachments.map((file) => ({
        name: file.name,
        sizeKb: Math.round(file.size / 1024),
      })),
    [attachments]
  );

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    const next = [...attachments];
    for (const file of Array.from(files)) {
      if (next.length >= MAX_ATTACHMENTS) {
        showError(`Only ${MAX_ATTACHMENTS} attachments are allowed.`);
        break;
      }
      if (!ALLOWED_TYPES.includes(file.type)) {
        showError(`Unsupported file type: ${file.name}`);
        continue;
      }
      next.push(file);
    }
    setAttachments(next);
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!message.trim()) {
      showError('Please enter a message before submitting.');
      return;
    }
    setIsSubmitting(true);
    try {
      await submitFeedback({
        category,
        subject: subject.trim() || undefined,
        message: message.trim(),
        submitterName: submitterName.trim() || undefined,
        submitterEmail: submitterEmail.trim() || undefined,
        attachments,
      });
      showSuccess('Feedback submitted. Thank you!');
      setAttachments([]);
      setMessage('');
      setSubject('');
      onClose();
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to submit feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="bg-white w-full max-w-xl rounded-lg shadow-lg border border-sage-mid">
        <div className="flex items-center justify-between border-b border-sage-mid px-5 py-3">
          <h2 className="text-lg font-semibold text-pine-deep">Send Feedback</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-sage-light"
            aria-label="Close feedback"
          >
            <X className="w-5 h-5 text-pine-mid" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-pine-mid" htmlFor="feedback-category">
                Category
              </label>
              <select
                id="feedback-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green"
              >
                {CATEGORY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-pine-mid" htmlFor="feedback-subject">
                Subject (optional)
              </label>
              <input
                id="feedback-subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green"
                placeholder="Short summary"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-pine-mid" htmlFor="feedback-message">
              Message
            </label>
            <textarea
              id="feedback-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green"
              rows={4}
              placeholder="Describe the issue or suggestion."
            />
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-pine-mid" htmlFor="feedback-name">
                Your name (optional)
              </label>
              <input
                id="feedback-name"
                value={submitterName}
                onChange={(e) => setSubmitterName(e.target.value)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-pine-mid" htmlFor="feedback-email">
                Email (optional)
              </label>
              <input
                id="feedback-email"
                type="email"
                value={submitterEmail}
                onChange={(e) => setSubmitterEmail(e.target.value)}
                className="w-full px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-pine-mid" htmlFor="feedback-attachments">
              Attachments (optional)
            </label>
            <input
              id="feedback-attachments"
              type="file"
              multiple
              accept={ALLOWED_TYPES.join(',')}
              onChange={(e) => handleFiles(e.target.files)}
              className="block w-full text-sm text-pine-mid file:mr-4 file:py-2 file:px-3 file:rounded file:border-0 file:bg-sage-light file:text-pine-deep"
            />
            <p className="text-xs text-pine-mid mt-1">
              Allowed: PNG, JPG, WEBP, TXT, PDF. Max {MAX_ATTACHMENTS} files.
            </p>
            {attachmentInfo.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-pine-deep">
                {attachmentInfo.map((file, index) => (
                  <li key={`${file.name}-${index}`} className="flex items-center justify-between">
                    <span>
                      {file.name} ({file.sizeKb} KB)
                    </span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(index)}
                      className="text-terracotta underline"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-sage-mid">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-sage-mid rounded-lg text-pine-deep"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-forest-green text-white rounded-lg disabled:opacity-50"
            >
              {isSubmitting ? 'Sending...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
