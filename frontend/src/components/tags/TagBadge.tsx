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

// Helper to determine if color is light (needs dark text)
const isLightColor = (hex: string): boolean => {
  const rgb = parseInt(hex.slice(1), 16);
  const r = (rgb >> 16) & 0xff;
  const g = (rgb >> 8) & 0xff;
  const b = (rgb >> 0) & 0xff;
  const luma = 0.299 * r + 0.587 * g + 0.114 * b;
  return luma > 186;
};

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

  const textColor = isLightColor(tag.color) ? 'text-pine-deep' : 'text-white';
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
      style={{ backgroundColor: tag.color }}
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
