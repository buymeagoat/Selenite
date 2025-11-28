import React from 'react';

interface StatusBadgeProps {
  status: 'queued' | 'processing' | 'cancelling' | 'completed' | 'failed' | 'cancelled';
  size?: 'sm' | 'md' | 'lg';
}

// High-contrast palette to satisfy WCAG contrast
const statusConfig = {
  queued: { bg: 'bg-gray-200', text: 'text-gray-900', label: 'Queued', pulse: false },
  processing: { bg: 'bg-black', text: 'text-white', label: 'Processing', pulse: false },
  cancelling: { bg: 'bg-black', text: 'text-white', label: 'Cancelling', pulse: false },
  completed: { bg: 'bg-black', text: 'text-white', label: 'Completed', pulse: false },
  failed: { bg: 'bg-black', text: 'text-white', label: 'Failed', pulse: false },
  cancelled: { bg: 'bg-gray-800', text: 'text-white', label: 'Cancelled', pulse: false },
} as const;

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5',
  };

  const config = statusConfig[status];
  const animateClass = config.pulse ? 'animate-pulse' : '';

  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center gap-1 rounded-full font-medium ${config.bg} ${config.text} ${sizeClasses[size]} ${animateClass}`}
    >
      {config.label}
    </span>
  );
};
