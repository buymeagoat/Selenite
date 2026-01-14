import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, act } from '@testing-library/react';
import { AuthProvider } from '../context/AuthContext';
import { fetchCurrentUser } from '../services/auth';

vi.mock('../services/auth', () => ({
  fetchCurrentUser: vi.fn()
}));

const baseUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  is_admin: false,
  is_disabled: false,
  force_password_reset: false,
  is_email_verified: true,
  created_at: new Date().toISOString()
};

describe('AuthProvider', () => {
  const fetchCurrentUserMock = vi.mocked(fetchCurrentUser);

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('refreshes the user profile on an interval when a token exists', async () => {
    localStorage.setItem('auth_token', 'test-token');
    localStorage.setItem('auth_user', JSON.stringify(baseUser));
    fetchCurrentUserMock.mockResolvedValue(baseUser);

    render(
      <AuthProvider>
        <div>child</div>
      </AuthProvider>
    );

    await act(async () => {
      await Promise.resolve();
    });

    const initialCalls = fetchCurrentUserMock.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(60_000);
      await Promise.resolve();
    });

    expect(fetchCurrentUserMock.mock.calls.length).toBeGreaterThan(initialCalls);
  });
});
