import { apiGet } from '../lib/api';

export interface FileEntry {
  name: string;
  is_dir: boolean;
  path: string; // relative to scope root, begins with '/'
}

export interface BrowseResponse {
  scope: string;
  base: string;
  cwd: string; // current directory relative to scope root, begins with '/'
  entries: FileEntry[];
}

export async function browseFiles(scope: 'models' | 'root', path?: string): Promise<BrowseResponse> {
  const params = new URLSearchParams();
  if (scope) params.set('scope', scope);
  if (path) params.set('path', path);
  return apiGet<BrowseResponse>(`/files/browse?${params.toString()}`);
}
