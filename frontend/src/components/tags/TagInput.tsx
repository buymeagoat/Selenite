import React, { useMemo, useState, useRef, useEffect } from 'react';
import { Tag, X } from 'lucide-react';
import { TAG_COLOR_PALETTE, getTagColor, getTagTextColor, pickTagColor } from './tagColors';

interface TagInfo {
  id: number;
  name: string;
  color?: string | null;
}

interface TagInputProps {
  availableTags: TagInfo[];
  selectedTags: number[];
  selectedTagOptions?: TagInfo[];
  selectedTagsPosition?: 'above' | 'below';
  onChange: (tagIds: number[]) => void;
  onCreate: (tagName: string, color: string) => Promise<TagInfo>;
  placeholder?: string;
  colorPalette?: string[];
}

export const TagInput: React.FC<TagInputProps> = ({
  availableTags,
  selectedTags,
  selectedTagOptions,
  selectedTagsPosition = 'below',
  onChange,
  onCreate,
  placeholder = 'Add tags...',
  colorPalette = TAG_COLOR_PALETTE
}) => {
  const [inputValue, setInputValue] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const defaultColor = useMemo(() => pickTagColor(availableTags, colorPalette[0]), [availableTags, colorPalette]);
  const [createColor, setCreateColor] = useState(defaultColor);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedTagMap = useMemo(() => {
    const map = new Map<number, TagInfo>();
    availableTags.forEach((tag) => map.set(tag.id, tag));
    (selectedTagOptions ?? []).forEach((tag) => map.set(tag.id, tag));
    return map;
  }, [availableTags, selectedTagOptions]);

  const selectedTagObjects = selectedTags
    .map((id) => selectedTagMap.get(id))
    .filter(Boolean) as TagInfo[];
  const unselectedTags = availableTags.filter(t => !selectedTags.includes(t.id));

  const filteredTags = inputValue.trim()
    ? unselectedTags.filter(t => t.name.toLowerCase().includes(inputValue.toLowerCase()))
    : unselectedTags;

  const exactMatch = availableTags.find(t => t.name.toLowerCase() === inputValue.toLowerCase());
  const showCreateOption = inputValue.trim() && !exactMatch;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!inputValue.trim()) {
      setCreateColor(defaultColor);
    }
  }, [defaultColor, inputValue]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    setShowDropdown(true);
  };

  const handleSelectTag = (tagId: number) => {
    onChange([...selectedTags, tagId]);
    setInputValue('');
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleRemoveTag = (tagId: number) => {
    onChange(selectedTags.filter(id => id !== tagId));
  };

  const handleCreateTag = async () => {
    if (!inputValue.trim() || isCreating) return;
    setIsCreating(true);
    try {
      const newTag = await onCreate(inputValue.trim(), createColor);
      onChange([...selectedTags, newTag.id]);
      setInputValue('');
      setShowDropdown(false);
      setCreateColor(defaultColor);
    } catch {
      return;
    } finally {
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault();
      if (exactMatch) {
        if (!selectedTags.includes(exactMatch.id)) {
          handleSelectTag(exactMatch.id);
        }
        return;
      }
      if (showCreateOption) {
        handleCreateTag();
      }
    }
  };

  const selectedTagsContent = selectedTagObjects.length > 0 && (
    <div className="flex flex-wrap gap-2 mt-2">
      {selectedTagObjects.map(tag => {
        const tagColor = getTagColor(tag);
        const tagTextColor = getTagTextColor(tagColor);
        return (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-3 py-1 rounded text-sm"
            style={{ backgroundColor: tagColor, color: tagTextColor }}
          >
            {tag.name}
            <button
              type="button"
              onClick={() => handleRemoveTag(tag.id)}
              aria-label={`Remove ${tag.name}`}
              className="ml-1 hover:opacity-75"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        );
      })}
    </div>
  );

  return (
    <div className="w-full" ref={containerRef}>
      {selectedTagsPosition === 'above' && selectedTagsContent}
      <div className="relative">
        <div className="flex items-center border border-sage-mid rounded-lg px-3 py-2 bg-white focus-within:border-forest-green focus-within:ring-1 focus-within:ring-forest-green">
          <Tag className="w-4 h-4 text-pine-mid mr-2" />
          <input
            ref={inputRef}
            type="text"
            role="textbox"
            value={inputValue}
            onChange={handleInputChange}
            onFocus={() => setShowDropdown(true)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="flex-1 outline-none text-sm text-pine-deep placeholder-pine-mid"
          />
        </div>

        {showDropdown && (filteredTags.length > 0 || showCreateOption) && (
          <div
            data-testid="tag-dropdown"
            className="absolute z-20 w-full mt-1 bg-white border border-sage-mid rounded-lg shadow-lg max-h-48 overflow-auto"
            onMouseDown={(e) => e.stopPropagation()}
          >
            {filteredTags.map(tag => (
              <button
                key={tag.id}
                type="button"
                onClick={() => handleSelectTag(tag.id)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-sage-light text-left"
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getTagColor(tag) }}
                />
                <span>{tag.name}</span>
              </button>
            ))}
            {showCreateOption && (
              <div className="border-t border-sage-mid">
                <div className="flex items-center gap-2 px-3 py-2">
                  {colorPalette.map((color) => (
                    <button
                      key={color}
                      type="button"
                      aria-label={`Select ${color}`}
                      onClick={() => setCreateColor(color)}
                      className={`w-4 h-4 rounded-full border ${
                        createColor === color ? 'border-forest-green ring-2 ring-forest-green/40' : 'border-sage-mid'
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
                <button
                  type="button"
                  onClick={handleCreateTag}
                  disabled={isCreating}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-sage-light text-left text-forest-green"
                >
                  <Tag className="w-3 h-3" />
                  <span>Create new tag: <strong>{inputValue}</strong></span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {selectedTagsPosition === 'below' && selectedTagsContent}
    </div>
  );
};
