import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { vi } from 'vitest';
import { UserManagement } from '../components/admin/UserManagement';
import { listActiveUsers, listUsers } from '../services/users';

const toastSpies = {
  showToast: vi.fn(),
  showSuccess: vi.fn(),
  showError: vi.fn(),
  showInfo: vi.fn(),
};

vi.mock('../context/ToastContext', () => ({
  useToast: () => toastSpies,
}));

vi.mock('../services/users', () => ({
  listUsers: vi.fn(),
  listActiveUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
}));

const mockUsers = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@selenite.local',
    is_admin: true,
    is_disabled: false,
    force_password_reset: false,
    last_login_at: '2025-12-31T23:59:00',
    created_at: '2025-12-01T00:00:00',
  },
];

describe('UserManagement', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('formats user timestamps with the configured time zone', async () => {
    vi.mocked(listUsers).mockResolvedValue({ items: mockUsers });
    vi.mocked(listActiveUsers).mockResolvedValue({ total: 0, items: [] });
    const formatMock = vi.fn().mockReturnValue('formatted');
    const formatToPartsMock = vi.fn().mockReturnValue([
      { type: 'year', value: '2025' },
      { type: 'month', value: '12' },
      { type: 'day', value: '31' },
    ]);
    const dateTimeSpy = vi
      .spyOn(Intl, 'DateTimeFormat')
      .mockImplementation(() => ({ format: formatMock, formatToParts: formatToPartsMock }) as Intl.DateTimeFormat);

    await act(async () => {
      render(<UserManagement isAdmin timeZone="UTC" />);
    });

    await screen.findAllByText('formatted, formatted');

    const hasTimezone = dateTimeSpy.mock.calls.some((call) => {
      const options = call[1] as Intl.DateTimeFormatOptions | undefined;
      return options?.timeZone === 'UTC';
    });

    expect(hasTimezone).toBe(true);
    dateTimeSpy.mockRestore();
  });
});
