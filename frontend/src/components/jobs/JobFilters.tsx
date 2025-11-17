import React, { useState, useEffect } from 'react';
import { Filter, ChevronDown, X } from 'lucide-react';

interface TagInfo { id: number; name: string; color: string; }
interface JobFiltersProps {
  currentFilters: { status?: string; dateRange?: string; tags?: number[] };
  availableTags: TagInfo[];
  onFilterChange: (filters: { status?: string; dateRange?: string; tags?: number[] }) => void;
  onReset: () => void;
}

export const JobFilters: React.FC<JobFiltersProps> = ({ currentFilters, availableTags, onFilterChange, onReset }) => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [localTags, setLocalTags] = useState<number[]>(currentFilters.tags || []);

  useEffect(() => {
    setLocalTags(currentFilters.tags || []);
  }, [currentFilters.tags]);

  const toggleDropdown = (key: string) => {
    setOpenDropdown(prev => prev === key ? null : key);
  };

  const selectStatus = (status?: string) => {
    onFilterChange({ ...currentFilters, status });
    setOpenDropdown(null);
  };

  const selectDateRange = (dateRange?: string) => {
    onFilterChange({ ...currentFilters, dateRange });
    setOpenDropdown(null);
  };

  const toggleTag = (id: number) => {
    const next = localTags.includes(id) ? localTags.filter(t => t !== id) : [...localTags, id];
    setLocalTags(next);
    onFilterChange({ ...currentFilters, tags: next });
  };

  const clearAllTags = () => {
    setLocalTags([]);
    onFilterChange({ ...currentFilters, tags: [] });
  };

  const anyFiltersApplied = Boolean(currentFilters.status || currentFilters.dateRange || (currentFilters.tags && currentFilters.tags.length));

  const badgeCount = [
    currentFilters.status ? 1 : 0,
    currentFilters.dateRange ? 1 : 0,
    currentFilters.tags && currentFilters.tags.length ? 1 : 0
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-wrap gap-3 items-center" aria-label="Job filters">
      <button
        type="button"
        onClick={() => toggleDropdown('status')}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-sage-mid rounded-lg text-sm hover:border-forest-green hover:bg-sage-light transition"
        aria-haspopup="true"
      >
        <span>Status</span>
        <ChevronDown className="w-4 h-4" />
      </button>
      {openDropdown === 'status' && (
        <div className="absolute z-20 mt-1 bg-white border border-sage-mid rounded-lg shadow-md p-2 w-40">
          {['All','In Progress','Completed','Failed'].map(label => (
            <button
              key={label}
              className="w-full text-left px-2 py-1 rounded text-sm hover:bg-sage-light"
              onClick={() => selectStatus(label === 'All' ? undefined : label.toLowerCase().replace(' ', '_'))}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={() => toggleDropdown('date')}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-sage-mid rounded-lg text-sm hover:border-forest-green hover:bg-sage-light transition"
        aria-haspopup="true"
      >
        <span>Date</span>
        <ChevronDown className="w-4 h-4" />
      </button>
      {openDropdown === 'date' && (
        <div className="absolute z-20 mt-1 bg-white border border-sage-mid rounded-lg shadow-md p-2 w-44">
          {['All Time','Today','This Week','This Month','Custom Range'].map(label => (
            <button
              key={label}
              className="w-full text-left px-2 py-1 rounded text-sm hover:bg-sage-light"
              onClick={() => selectDateRange(label === 'All Time' ? undefined : label.toLowerCase().replace(' ', '_'))}
            >
              {label}
            </button>
          ))}
          {/* Placeholder for custom range modal trigger */}
        </div>
      )}

      <button
        type="button"
        onClick={() => toggleDropdown('tags')}
        className="flex items-center gap-2 px-3 py-2 bg-white border border-sage-mid rounded-lg text-sm hover:border-forest-green hover:bg-sage-light transition"
        aria-haspopup="true"
      >
        <span>Tags</span>
        <ChevronDown className="w-4 h-4" />
      </button>
      {openDropdown === 'tags' && (
        <div className="absolute z-20 mt-1 bg-white border border-sage-mid rounded-lg shadow-md p-2 w-56">
          <div className="max-h-48 overflow-auto">
            {availableTags.length === 0 && (
              <div className="px-2 py-1 text-xs text-pine-mid">No tags available</div>
            )}
            {availableTags.map(tag => (
              <label key={tag.id} className="flex items-center gap-2 px-2 py-1 rounded text-sm hover:bg-sage-light cursor-pointer">
                <input
                  type="checkbox"
                  aria-label={tag.name}
                  checked={localTags.includes(tag.id)}
                  onChange={() => toggleTag(tag.id)}
                />
                <span>{tag.name}</span>
              </label>
            ))}
          </div>
          {localTags.length > 0 && (
            <button
              type="button"
              className="mt-2 w-full text-left text-xs text-pine-mid hover:text-forest-green"
              onClick={clearAllTags}
            >
              Clear All
            </button>
          )}
        </div>
      )}

      {currentFilters.tags && currentFilters.tags.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {availableTags.filter(t => currentFilters.tags!.includes(t.id)).map(t => (
            <span key={t.id} className="flex items-center gap-1 px-2 py-1 bg-sage-light rounded-full text-xs" style={{ color: t.color }}>
              {t.name}
              <button
                type="button"
                aria-label={`Remove ${t.name}`}
                onClick={() => toggleTag(t.id)}
                className="text-pine-mid hover:text-forest-green"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {anyFiltersApplied && (
        <button
          type="button"
          className="ml-auto px-3 py-2 bg-white border border-sage-mid rounded-lg text-sm hover:border-terracotta hover:bg-sage-light transition"
          onClick={onReset}
        >
          Reset Filters
        </button>
      )}

      {badgeCount > 0 && (
        <div className="flex items-center gap-1 text-xs text-pine-mid" aria-label="Active filters count">
          <Filter className="w-3 h-3" />
          <span>{badgeCount} active</span>
        </div>
      )}
    </div>
  );
};
