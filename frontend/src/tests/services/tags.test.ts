import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../lib/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));

import { apiGet, apiPost, apiPut, apiDelete } from '../../lib/api';
import { fetchTags, createTag, updateTag, deleteTag } from '../../services/tags';

describe('tag service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetchTags uses GET /tags', async () => {
    (apiGet as any).mockResolvedValue({});
    await fetchTags();
    expect(apiGet).toHaveBeenCalledWith('/tags', undefined);
  });

  it('createTag posts body to /tags', async () => {
    (apiPost as any).mockResolvedValue({});
    await createTag({ name: 'Urgent', color: '#fff' });
    expect(apiPost).toHaveBeenCalledWith('/tags', { name: 'Urgent', color: '#fff' });
  });

  it('updateTag hits /tags/:id', async () => {
    (apiPut as any).mockResolvedValue({});
    await updateTag(5, { name: 'Renamed' });
    expect(apiPut).toHaveBeenCalledWith('/tags/5', { name: 'Renamed' });
  });

  it('deleteTag deletes /tags/:id', async () => {
    (apiDelete as any).mockResolvedValue({});
    await deleteTag(9);
    expect(apiDelete).toHaveBeenCalledWith('/tags/9');
  });
});
