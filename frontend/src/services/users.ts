import { apiGet, apiPatch, apiPost } from '../lib/api';

export interface UserListItem {
  id: number;
  username: string;
  email?: string | null;
  is_admin: boolean;
  is_disabled: boolean;
  force_password_reset: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export interface UserListResponse {
  items: UserListItem[];
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
