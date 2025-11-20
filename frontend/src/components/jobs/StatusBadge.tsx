import React from 'react';

interface StatusBadgeProps {
  status: 'queued' | 'processing' | 'cancelling' | 'completed' | 'failed' | 'cancelled';
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5'
  };

  const statusConfig = {
    queued: {
      bg: 'bg-gray-200',
      text: 'text-gray-700',
      label: 'Queued',
      icon: null
    },
    processing: {
      bg: 'bg-sage-mid',
      text: 'text-pine-deep',
      label: 'Processing',
      icon: '⟳',
      animate: true
    },
    cancelling: {
      bg: 'bg-amber-100',
      text: 'text-amber-800',
      label: 'Cancelling',
      icon: '…',
      animate: true
    },
    completed: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      label: 'Completed',
      icon: '✓'
    },
    failed: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      label: 'Failed',
      icon: '✕'
    },
    cancelled: {
      bg: 'bg-gray-200',
      text: 'text-gray-700',
      label: 'Cancelled',
      icon: '⃠'
    }
  };

  const config = statusConfig[status];
  const animateClass = 'animate' in config && config.animate ? 'animate-pulse' : '';

  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center gap-1 rounded-full font-medium ${config.bg} ${config.text} ${sizeClasses[size]} ${animateClass}`}
    >
      {config.icon && <span>{config.icon}</span>}
      {config.label}
    </span>
  );
};
