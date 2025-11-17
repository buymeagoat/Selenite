import React from 'react';
import { Edit2, Trash2 } from 'lucide-react';

interface TagWithCount {
  id: number;
  name: string;
  color: string;
  job_count: number;
}

interface TagListProps {
  tags: TagWithCount[];
  onEdit: (tagId: number) => void;
  onDelete: (tagId: number) => void;
}

export const TagList: React.FC<TagListProps> = ({ tags, onEdit, onDelete }) => {
  if (tags.length === 0) {
    return (
      <div className="text-center py-12 border border-sage-mid rounded-lg bg-white">
        <div className="text-5xl mb-3">🏷️</div>
        <p className="text-pine-mid">No tags created yet</p>
        <p className="text-sm text-pine-mid mt-1">Create tags to organize your transcriptions</p>
      </div>
    );
  }

  const isDesktop = typeof window !== 'undefined' ? window.innerWidth >= 768 : true;

  return (
    <div className="bg-white border border-sage-mid rounded-lg overflow-hidden" data-testid="tag-list">
      {/* Desktop table view (only render in desktop to avoid duplicate elements in tests) */}
      {isDesktop && (
      <table role="table" className="w-full">
        <thead className="bg-sage-light border-b border-sage-mid">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider w-12">Color</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider">Name</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider w-24">Jobs</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-pine-deep uppercase tracking-wider w-32">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-sage-mid">
          {tags.map(tag => (
            <tr key={tag.id} className="hover:bg-sage-light">
              <td className="px-4 py-3">
                <div
                  data-testid="tag-color-dot"
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: tag.color }}
                />
              </td>
              <td className="px-4 py-3">
                <span data-testid="tag-name" className="text-sm text-pine-deep">{tag.name}</span>
              </td>
              <td className="px-4 py-3">
                <span className="text-sm text-pine-mid">{tag.job_count}</span>
              </td>
              <td className="px-4 py-3">
                <div className="flex gap-2">
                  <button
                    onClick={() => onEdit(tag.id)}
                    aria-label={`Edit ${tag.name}`}
                    className="p-1 text-pine-mid hover:text-forest-green transition"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDelete(tag.id)}
                    aria-label={`Delete ${tag.name}`}
                    className="p-1 text-pine-mid hover:text-terracotta transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      )}
      {!isDesktop && (
        <div className="divide-y divide-sage-mid">
          {tags.map(tag => (
            <div key={tag.id} className="p-4 hover:bg-sage-light">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <div
                    data-testid="tag-color-dot"
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: tag.color }}
                  />
                  <div>
                    <div data-testid="tag-name" className="text-sm font-medium text-pine-deep">{tag.name}</div>
                    <div className="text-xs text-pine-mid mt-1">{tag.job_count} jobs</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onEdit(tag.id)}
                    aria-label={`Edit ${tag.name}`}
                    className="p-2 text-pine-mid hover:text-forest-green transition"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDelete(tag.id)}
                    aria-label={`Delete ${tag.name}`}
                    className="p-2 text-pine-mid hover:text-terracotta transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
