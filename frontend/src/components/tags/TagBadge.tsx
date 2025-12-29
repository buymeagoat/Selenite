import React from 'react';
import { X } from 'lucide-react';
import { getTagColor, getTagTextColor } from './tagColors';

interface Tag {
  id: number;
  name: string;
  color?: string | null;
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

  const tagColor = getTagColor(tag);
  const tagTextColor = getTagTextColor(tagColor);
  const backgroundStyle = {
    backgroundColor: tagColor,
    border: `1px solid ${tagColor}`,
    color: tagTextColor,
  };
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
      className={`inline-flex items-center gap-1 rounded ${sizeClasses[size]} ${clickable}`}
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
