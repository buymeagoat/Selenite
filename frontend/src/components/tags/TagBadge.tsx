import React from 'react';
import { X } from 'lucide-react';

interface Tag {
  id: number;
  name: string;
  color: string;
}

interface TagBadgeProps {
  tag: Tag;
  size?: 'sm' | 'md';
  onRemove?: (tagId: number) => void;
  onClick?: (tagId: number) => void;
}

export const TagBadge: React.FC<TagBadgeProps> = ({
  tag,
  size = 'md',
  onRemove,
  onClick
}) => {
  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1'
  };

  // Force consistent high-contrast style regardless of tag color
  const textColor = 'text-gray-900';
  const backgroundStyle = { backgroundColor: '#EEF1EA', border: '1px solid #CBD5E1' };
  const clickable = onClick ? 'cursor-pointer hover:opacity-90' : '';

  const handleClick = () => {
    if (onClick) onClick(tag.id);
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onRemove) onRemove(tag.id);
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded ${sizeClasses[size]} ${textColor} ${clickable}`}
      style={backgroundStyle}
      onClick={handleClick}
    >
      {tag.name}
      {onRemove && (
        <button
          type="button"
          onClick={handleRemove}
          aria-label={`Remove ${tag.name}`}
          className="ml-1 hover:opacity-75 transition"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </span>
  );
};
