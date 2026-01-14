import { apiDelete, apiGet, apiPatch, apiPost } from '../lib/api';

export interface UserListItem {
  id: number;
  username: string;
  email?: string | null;
  is_admin: boolean;
  is_disabled: boolean;
  force_password_reset: boolean;
  last_login_at?: string | null;
  last_seen_at?: string | null;
  created_at: string;
}

export interface UserListResponse {
  items: UserListItem[];
}

export interface ActiveUserItem {
  id: number;
  username: string;
  email?: string | null;
  last_seen_at?: string | null;
}

export interface ActiveUsersResponse {
  total: number;
  items: ActiveUserItem[];
}

export interface CreateUserPayload {
  email: string;
  password: string;
  is_admin: boolean;
}

export interface UpdateUserPayload {
  email?: string;
  password?: string;
  is_admin?: boolean;
  is_disabled?: boolean;
  force_password_reset?: boolean;
}

export const listUsers = async () => apiGet<UserListResponse>('/users');

export const createUser = async (payload: CreateUserPayload) =>
  apiPost<UserListItem>('/users', payload);

export const updateUser = async (userId: number, payload: UpdateUserPayload) =>
  apiPatch<UserListItem>(`/users/${userId}`, payload);

export const deleteUser = async (userId: number) =>
  apiDelete<void>(`/users/${userId}`);

export const listActiveUsers = async (windowMinutes?: number) => {
  const params = windowMinutes ? `?window_minutes=${windowMinutes}` : '';
  return apiGet<ActiveUsersResponse>(`/users/active${params}`);
};
