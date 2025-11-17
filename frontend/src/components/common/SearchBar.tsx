import React, { useEffect, useRef, useState } from 'react';
import { Search, X, Loader2 } from 'lucide-react';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
  isLoading?: boolean;
}

// Debounce delay in ms
const DEBOUNCE_MS = 300;

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Search…',
  onClear,
  isLoading = false
}) => {
  const [internalValue, setInternalValue] = useState(value);
  const timerRef = useRef<number | null>(null);

  // Sync external value changes
  useEffect(() => {
    setInternalValue(value);
  }, [value]);

  // Debounce effect for internal value changes
  useEffect(() => {
    // Immediate call for clear action if internalValue === '' and external value not ''
    // We rely on clear button to call onChange synchronously; here only debounce typing
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }
    // Only debounce when internalValue differs from external value and not cleared via button
    if (internalValue !== value) {
      timerRef.current = window.setTimeout(() => {
        onChange(internalValue);
      }, DEBOUNCE_MS);
    }
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, [internalValue, value, onChange]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInternalValue(e.target.value);
  };

  const handleClear = () => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }
    setInternalValue('');
    onChange(''); // immediate (no debounce)
    if (onClear) onClear();
  };

  return (
    <div className="relative w-full max-w-md" role="search">
      <div className="flex items-center bg-white border border-sage-mid rounded-lg px-3 py-2 shadow-sm focus-within:border-forest-green focus-within:ring-1 focus-within:ring-forest-green transition-colors">
        <Search data-testid="search-icon" className="w-4 h-4 text-pine-mid mr-2" />
        <input
          type="text"
          role="searchbox"
          className="flex-1 outline-none text-pine-deep placeholder-pine-mid text-sm"
          placeholder={placeholder}
          value={internalValue}
          onChange={handleInputChange}
          aria-label="Search"
        />
        {isLoading ? (
          <Loader2 data-testid="search-loading" className="w-4 h-4 animate-spin text-pine-mid ml-2" />
        ) : internalValue ? (
          <button
            type="button"
            aria-label="Clear"
            onClick={handleClear}
            className="ml-2 p-1 rounded hover:bg-sage-light text-pine-mid"
          >
            <X className="w-4 h-4" />
          </button>
        ) : null}
      </div>
    </div>
  );
};
