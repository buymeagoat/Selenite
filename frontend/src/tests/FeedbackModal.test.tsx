import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeedbackModal } from '../components/modals/FeedbackModal';

const submitFeedbackMock = vi.fn().mockResolvedValue({});

vi.mock('../services/feedback', () => ({
  submitFeedback: (...args: any[]) => submitFeedbackMock(...args),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
  }),
}));

vi.mock('../context/ToastContext', () => ({
  useToast: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn(),
    showInfo: vi.fn(),
  }),
}));

describe('FeedbackModal', () => {
  it('submits feedback payload', async () => {
    const onClose = vi.fn();
    render(<FeedbackModal isOpen onClose={onClose} />);

    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: 'Found a bug in the uploader.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => expect(submitFeedbackMock).toHaveBeenCalledTimes(1));
    expect(submitFeedbackMock).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'comment',
        message: 'Found a bug in the uploader.',
      })
    );
  });
});
