import { apiGet } from '../lib/api';

export interface CurrentUserResponse {
  id: number;
  username: string;
  email?: string | null;
  is_admin: boolean;
  is_disabled: boolean;
  force_password_reset: boolean;
  last_login_at?: string | null;
  created_at: string;
}

export const fetchCurrentUser = async () => apiGet<CurrentUserResponse>('/auth/me');
