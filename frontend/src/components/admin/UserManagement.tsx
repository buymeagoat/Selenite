import React, { useEffect, useMemo, useState } from 'react';
import { Plus, RefreshCw } from 'lucide-react';
import { ApiError } from '../../lib/api';
import { useToast } from '../../context/ToastContext';
import { formatDateTime, type DateTimePreferences } from '../../utils/dateTime';
import {
  createUser,
  deleteUser,
  listUsers,
  listActiveUsers,
  updateUser,
  type ActiveUserItem,
  type UserListItem,
} from '../../services/users';

interface UserManagementProps {
  isAdmin: boolean;
  timeZone?: string | null;
  dateFormat?: DateTimePreferences['dateFormat'];
  timeFormat?: DateTimePreferences['timeFormat'];
  locale?: string | null;
}

type UserFormState = {
  email: string;
  password: string;
  is_admin: boolean;
  is_disabled: boolean;
  force_password_reset: boolean;
};

const emptyForm: UserFormState = {
  email: '',
  password: '',
  is_admin: false,
  is_disabled: false,
  force_password_reset: false,
};

export const UserManagement: React.FC<UserManagementProps> = ({
  isAdmin,
  timeZone = null,
  dateFormat = 'locale',
  timeFormat = 'locale',
  locale = null,
}) => {
  const { showError, showSuccess } = useToast();
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [activeUsers, setActiveUsers] = useState<ActiveUserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isActiveLoading, setIsActiveLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [activeUser, setActiveUser] = useState<UserListItem | null>(null);
  const [form, setForm] = useState<UserFormState>(emptyForm);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRootAdmin = useMemo(() => activeUser?.username === 'admin', [activeUser]);

  const loadUsers = async (options?: { silent?: boolean }) => {
    if (!isAdmin) return;
    if (!options?.silent) {
      setIsLoading(true);
    }
    try {
      const response = await listUsers();
      setUsers(response.items);
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Failed to load users: ${error.message}`);
      } else {
        showError('Failed to load users. Please refresh the page.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loadActiveUsers = async (options?: { silent?: boolean }) => {
    if (!isAdmin) return;
    if (!options?.silent) {
      setIsActiveLoading(true);
    }
    try {
      const response = await listActiveUsers();
      setActiveUsers(response.items);
    } catch (error) {
      if (error instanceof ApiError) {
        showError(`Failed to load active users: ${error.message}`);
      } else {
        showError('Failed to load active users. Please refresh the page.');
      }
    } finally {
      setIsActiveLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
    loadActiveUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadUsers({ silent: true });
    await loadActiveUsers({ silent: true });
    setIsRefreshing(false);
  };

  const openCreate = () => {
    setForm(emptyForm);
    setIsCreateOpen(true);
  };

  const openEdit = (user: UserListItem) => {
    setActiveUser(user);
    setForm({
      email: user.email || '',
      password: '',
      is_admin: user.is_admin,
      is_disabled: user.is_disabled,
      force_password_reset: user.force_password_reset,
    });
    setIsEditOpen(true);
  };

  const closeCreate = () => {
    setIsCreateOpen(false);
    setForm(emptyForm);
  };

  const closeEdit = () => {
    setIsEditOpen(false);
    setActiveUser(null);
    setForm(emptyForm);
  };

  const handleCreate = async () => {
    if (!form.email.trim() || !form.password.trim()) {
      showError('Email and password are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await createUser({
        email: form.email.trim(),
        password: form.password,
        is_admin: form.is_admin,
      });
      showSuccess('User created');
      await loadUsers({ silent: true });
      closeCreate();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Failed to create user');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async () => {
    if (!activeUser) return;
    setIsSubmitting(true);
    const hasPassword = Boolean(form.password.trim());
    try {
      const payload: Record<string, unknown> = {
        email: form.email.trim() || undefined,
        is_admin: form.is_admin,
        is_disabled: form.is_disabled,
        force_password_reset: form.force_password_reset,
      };
      if (hasPassword) {
        payload.password = form.password;
      }
      await updateUser(activeUser.id, payload);
      showSuccess(hasPassword ? 'Password updated' : 'User updated');
      await loadUsers({ silent: true });
      closeEdit();
    } catch (error) {
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Failed to update user');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (user: UserListItem) => {
    if (user.username === 'admin') {
      showError('Root admin cannot be deleted');
      return;
    }
    const label = user.email || user.username;
    if (!confirm(`Delete ${label}? This permanently removes the user and all of their data.`)) {
      return;
    }
    try {
      await deleteUser(user.id);
      showSuccess('User deleted');
      await loadUsers({ silent: true });
      await loadActiveUsers({ silent: true });
    } catch (error) {
      if (error instanceof ApiError) {
        showError(error.message);
      } else {
        showError('Failed to delete user');
      }
    }
  };

  if (!isAdmin) {
    return (
      <div className="border border-sage-mid rounded-lg p-6 bg-white">
        <h2 className="text-lg font-semibold text-pine-deep mb-2">Users</h2>
        <p className="text-sm text-pine-mid">Administrator access required.</p>
      </div>
    );
  }

  return (
    <div className="border border-sage-mid rounded-lg p-6 bg-white" data-testid="admin-users-card">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold text-pine-deep">Users</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-xs text-pine-mid underline flex items-center gap-1"
            data-testid="admin-users-refresh"
          >
            <RefreshCw className="w-3 h-3" /> {isRefreshing ? 'Refreshing' : 'Refresh'}
          </button>
          <button
            type="button"
            onClick={openCreate}
            className="px-3 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition"
            data-testid="admin-users-create"
          >
            <Plus className="w-4 h-4 inline-block mr-1" /> New user
          </button>
        </div>
      </div>
      <p className="text-xs text-pine-mid mb-4">
        Create and manage users. Admins can view all jobs or their own.
      </p>
      <div className="border border-sage-mid rounded-lg p-4 bg-sage-light/40 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-pine-deep">Active Users</h3>
          <span className="text-xs text-pine-mid">
            {isActiveLoading ? 'Loading…' : `${activeUsers.length} active`}
          </span>
        </div>
        {isActiveLoading ? (
          <p className="text-sm text-pine-mid">Loading active users…</p>
        ) : activeUsers.length ? (
          <ul className="space-y-1 text-sm text-pine-mid">
            {activeUsers.map((user) => (
              <li key={user.id} className="flex justify-between gap-4">
                <span className="text-pine-deep">{user.email || user.username}</span>
                <span>
                  {formatDateTime(user.last_seen_at, {
                    timeZone,
                    dateFormat,
                    timeFormat,
                    locale,
                  })}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-pine-mid">No active users in the current window.</p>
        )}
      </div>
      {isLoading ? (
        <p className="text-sm text-pine-mid">Loading users...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-sage-light border-b border-sage-mid">
              <tr>
                <th className="px-3 py-2 text-left text-xs uppercase text-pine-mid">Email</th>
                <th className="px-3 py-2 text-left text-xs uppercase text-pine-mid">Role</th>
                <th className="px-3 py-2 text-left text-xs uppercase text-pine-mid">Status</th>
                <th className="px-3 py-2 text-left text-xs uppercase text-pine-mid">Last Login</th>
                <th className="px-3 py-2 text-left text-xs uppercase text-pine-mid">Created</th>
                <th className="px-3 py-2 text-left text-xs uppercase text-pine-mid">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sage-mid">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-sage-light">
                  <td className="px-3 py-2 text-pine-deep">{user.email || user.username}</td>
                  <td className="px-3 py-2 text-pine-mid">
                    {user.is_admin ? 'Admin' : 'User'}
                  </td>
                  <td className="px-3 py-2 text-pine-mid">
                    {user.is_disabled ? 'Disabled' : 'Active'}
                  </td>
                  <td className="px-3 py-2 text-pine-mid">
                    {formatDateTime(user.last_login_at, {
                      timeZone,
                      dateFormat,
                      timeFormat,
                      locale,
                    })}
                  </td>
                  <td className="px-3 py-2 text-pine-mid">
                    {formatDateTime(user.created_at, {
                      timeZone,
                      dateFormat,
                      timeFormat,
                      locale,
                    })}
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => openEdit(user)}
                      className="text-xs text-forest-green underline"
                    >
                      Edit
                    </button>
                    <span className="mx-2 text-pine-mid">|</span>
                    <button
                      type="button"
                      onClick={() => handleDelete(user)}
                      className="text-xs text-red-600 underline disabled:text-pine-mid"
                      disabled={user.username === 'admin'}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-pine-mid">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6" role="dialog" aria-modal="true">
            <h3 className="text-lg font-semibold text-pine-deep mb-4">Create user</h3>
            <label className="text-sm text-pine-deep mb-1 block" htmlFor="create-user-email">
              Email
            </label>
            <input
              id="create-user-email"
              className="w-full px-3 py-2 border border-gray-300 rounded mb-3"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="user@example.com"
            />
            <label className="text-sm text-pine-deep mb-1 block" htmlFor="create-user-password">
              Password
            </label>
            <input
              id="create-user-password"
              type="password"
              className="w-full px-3 py-2 border border-gray-300 rounded mb-3"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Minimum 8 characters"
            />
            <label className="flex items-center gap-2 text-sm text-pine-deep mb-4">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
                className="h-4 w-4 text-forest-green border-gray-300 rounded"
              />
              <span>Grant admin access</span>
            </label>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="px-3 py-2 text-sm border border-gray-300 rounded"
                onClick={closeCreate}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 text-sm bg-forest-green text-white rounded disabled:opacity-50"
                onClick={handleCreate}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {isEditOpen && activeUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6" role="dialog" aria-modal="true">
            <h3 className="text-lg font-semibold text-pine-deep mb-4">Edit user</h3>
            <label className="text-sm text-pine-deep mb-1 block" htmlFor="edit-user-email">
              Email
            </label>
            <input
              id="edit-user-email"
              className="w-full px-3 py-2 border border-gray-300 rounded mb-3"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <label className="text-sm text-pine-deep mb-1 block" htmlFor="edit-user-password">
              Reset password
            </label>
            <input
              id="edit-user-password"
              type="password"
              className="w-full px-3 py-2 border border-gray-300 rounded mb-3"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Leave blank to keep current"
            />
            <label className="flex items-center gap-2 text-sm text-pine-deep mb-2">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
                className="h-4 w-4 text-forest-green border-gray-300 rounded"
                disabled={isRootAdmin}
              />
              <span>Admin access</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-pine-deep mb-2">
              <input
                type="checkbox"
                checked={form.is_disabled}
                onChange={(e) => setForm({ ...form, is_disabled: e.target.checked })}
                className="h-4 w-4 text-forest-green border-gray-300 rounded"
                disabled={isRootAdmin}
              />
              <span>Disable account</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-pine-deep mb-4">
              <input
                type="checkbox"
                checked={form.force_password_reset}
                onChange={(e) => setForm({ ...form, force_password_reset: e.target.checked })}
                className="h-4 w-4 text-forest-green border-gray-300 rounded"
              />
              <span>Force password reset on next login</span>
            </label>
            {isRootAdmin && (
              <p className="text-xs text-pine-mid mb-4">
                Root admin cannot be disabled or demoted.
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="px-3 py-2 text-sm border border-gray-300 rounded"
                onClick={closeEdit}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 text-sm bg-forest-green text-white rounded disabled:opacity-50"
                onClick={handleUpdate}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
