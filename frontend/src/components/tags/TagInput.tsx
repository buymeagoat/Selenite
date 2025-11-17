import React, { useState, useRef, useEffect } from 'react';
import { Tag, X } from 'lucide-react';

interface TagInfo {
  id: number;
  name: string;
  color: string;
}

interface TagInputProps {
  availableTags: TagInfo[];
  selectedTags: number[];
  onChange: (tagIds: number[]) => void;
  onCreate: (tagName: string) => Promise<TagInfo>;
  placeholder?: string;
}

export const TagInput: React.FC<TagInputProps> = ({
  availableTags,
  selectedTags,
  onChange,
  onCreate,
  placeholder = 'Add tags...'
}) => {
  const [inputValue, setInputValue] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedTagObjects = availableTags.filter(t => selectedTags.includes(t.id));
  const unselectedTags = availableTags.filter(t => !selectedTags.includes(t.id));

  const filteredTags = inputValue.trim()
    ? unselectedTags.filter(t => t.name.toLowerCase().includes(inputValue.toLowerCase()))
    : unselectedTags;

  const exactMatch = filteredTags.find(t => t.name.toLowerCase() === inputValue.toLowerCase());
  const showCreateOption = inputValue.trim() && !exactMatch && filteredTags.length === 0;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (inputRef.current && !inputRef.current.parentElement?.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      const newTag = await onCreate(inputValue.trim());
      onChange([...selectedTags, newTag.id]);
      setInputValue('');
      setShowDropdown(false);
    } finally {
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      if (filteredTags.length === 1) {
        handleSelectTag(filteredTags[0].id);
      } else if (showCreateOption) {
        handleCreateTag();
      }
    }
  };

  return (
    <div className="w-full">
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
          <div data-testid="tag-dropdown" className="absolute z-20 w-full mt-1 bg-white border border-sage-mid rounded-lg shadow-lg max-h-48 overflow-auto">
            {filteredTags.map(tag => (
              <button
                key={tag.id}
                type="button"
                onClick={() => handleSelectTag(tag.id)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-sage-light text-left"
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: tag.color }}
                />
                <span>{tag.name}</span>
              </button>
            ))}
            {showCreateOption && (
              <button
                type="button"
                onClick={handleCreateTag}
                disabled={isCreating}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-sage-light text-left text-forest-green border-t border-sage-mid"
              >
                <Tag className="w-3 h-3" />
                <span>Create new tag: <strong>{inputValue}</strong></span>
              </button>
            )}
          </div>
        )}
      </div>

      {selectedTagObjects.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {selectedTagObjects.map(tag => (
            <span
              key={tag.id}
              className="inline-flex items-center gap-1 px-3 py-1 rounded text-sm text-white"
              style={{ backgroundColor: tag.color }}
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
          ))}
        </div>
      )}
    </div>
  );
};
