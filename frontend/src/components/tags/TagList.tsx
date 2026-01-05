import React, { useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Edit2, Trash2 } from 'lucide-react';
import { getTagColor } from './tagColors';

interface TagWithCount {
  id: number;
  name: string;
  color?: string | null;
  job_count: number;
}

interface TagListProps {
  tags: TagWithCount[];
  onEdit?: (tagId: number) => void;
  onDelete?: (tagId: number) => void;
  showActions?: boolean;
}

export const TagList: React.FC<TagListProps> = ({ tags, onEdit, onDelete, showActions = true }) => {
  const [sortState, setSortState] = useState<{
    key: 'color' | 'name' | 'jobs' | null;
    direction: 'asc' | 'desc';
  }>({ key: null, direction: 'asc' });

  const sortedTags = (() => {
    if (!sortState.key) return tags;
    const sorted = [...tags];
    const direction = sortState.direction === 'asc' ? 1 : -1;
    sorted.sort((a, b) => {
      let comparison = 0;
      if (sortState.key === 'color') {
        comparison = getTagColor(a).localeCompare(getTagColor(b), undefined, {
          sensitivity: 'base',
        });
      } else if (sortState.key === 'name') {
        comparison = a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
      } else {
        comparison = a.job_count - b.job_count;
      }
      if (comparison === 0) {
        comparison = a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
      }
      return comparison * direction;
    });
    return sorted;
  })();

  const isDesktop = typeof window !== 'undefined' ? window.innerWidth >= 768 : true;
  const sortIcon = (key: 'color' | 'name' | 'jobs') => {
    if (sortState.key !== key) {
      return <ArrowUpDown className="w-3 h-3 text-pine-mid" />;
    }
    return sortState.direction === 'asc'
      ? <ArrowUp className="w-3 h-3 text-pine-mid" />
      : <ArrowDown className="w-3 h-3 text-pine-mid" />;
  };
  const toggleSort = (key: 'color' | 'name' | 'jobs') => {
    setSortState((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { key, direction: 'asc' };
    });
  };
  const ariaSort = (key: 'color' | 'name' | 'jobs') => {
    if (sortState.key !== key) return 'none';
    return sortState.direction === 'asc' ? 'ascending' : 'descending';
  };
  const sortAriaLabel = (key: 'color' | 'name' | 'jobs') => {
    const status = sortState.key === key ? sortState.direction : 'none';
    return `Sort by ${key} (${status})`;
  };

  if (tags.length === 0) {
    return (
      <div className="text-center py-12 border border-sage-mid rounded-lg bg-white" data-testid="tag-list">
        <div className="text-5xl mb-3">Tags</div>
        <p className="text-pine-mid">No tags created yet</p>
        <p className="text-sm text-pine-mid mt-1">Create tags to organize your transcriptions</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-sage-mid rounded-lg overflow-hidden" data-testid="tag-list">
      {/* Desktop table view (only render in desktop to avoid duplicate elements in tests) */}
      {isDesktop && (
      <table role="table" className="w-full">
        <thead className="bg-sage-light border-b border-sage-mid">
          <tr>
            <th
              className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider w-12"
              aria-sort={ariaSort('color')}
            >
              <button
                type="button"
                className="flex items-center gap-1 cursor-pointer"
                onClick={() => toggleSort('color')}
                aria-label={sortAriaLabel('color')}
              >
                Color
                {sortIcon('color')}
              </button>
            </th>
            <th
              className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider"
              aria-sort={ariaSort('name')}
            >
              <button
                type="button"
                className="flex items-center gap-1 cursor-pointer"
                onClick={() => toggleSort('name')}
                aria-label={sortAriaLabel('name')}
              >
                Name
                {sortIcon('name')}
              </button>
            </th>
            <th
              className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider w-24"
              aria-sort={ariaSort('jobs')}
            >
              <button
                type="button"
                className="flex items-center gap-1 cursor-pointer"
                onClick={() => toggleSort('jobs')}
                aria-label={sortAriaLabel('jobs')}
              >
                Jobs
                {sortIcon('jobs')}
              </button>
            </th>
            {showActions && (
              <th className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider w-32">
                Actions
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-sage-mid">
          {sortedTags.map(tag => (
            <tr key={tag.id} className="hover:bg-sage-light">
              <td className="px-4 py-3">
                <div
                  data-testid="tag-color-dot"
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: getTagColor(tag) }}
                />
              </td>
              <td className="px-4 py-3">
                <span data-testid="tag-name" className="text-sm text-pine-deep">{tag.name}</span>
              </td>
              <td className="px-4 py-3">
                <span className="text-sm text-pine-mid">{tag.job_count}</span>
              </td>
              {showActions && (
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => onEdit?.(tag.id)}
                      aria-label={`Edit ${tag.name}`}
                      className="p-1 text-pine-mid hover:text-forest-green transition"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete?.(tag.id)}
                      aria-label={`Delete ${tag.name}`}
                      className="p-1 text-pine-mid hover:text-terracotta transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      )}
      {!isDesktop && (
        <div className="divide-y divide-sage-mid">
          {sortedTags.map(tag => (
            <div key={tag.id} className="p-4 hover:bg-sage-light">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <div
                    data-testid="tag-color-dot"
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: getTagColor(tag) }}
                  />
                  <div>
                    <div data-testid="tag-name" className="text-sm font-medium text-pine-deep">{tag.name}</div>
                    <div className="text-xs text-pine-mid mt-1">{tag.job_count} jobs</div>
                  </div>
                </div>
                {showActions && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => onEdit?.(tag.id)}
                      aria-label={`Edit ${tag.name}`}
                      className="p-2 text-pine-mid hover:text-forest-green transition"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete?.(tag.id)}
                      aria-label={`Delete ${tag.name}`}
                      className="p-2 text-pine-mid hover:text-terracotta transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
