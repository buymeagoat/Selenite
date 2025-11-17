import React from 'react';

interface ProgressBarProps {
  percent: number;  // 0-100
  stage?: string;
  estimatedTimeLeft?: number;  // seconds
  variant?: 'default' | 'success' | 'error';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ 
  percent, 
  stage, 
  estimatedTimeLeft, 
  variant = 'default' 
}) => {
  const clampedPercent = Math.max(0, Math.min(100, percent));

  const fillColors = {
    default: 'bg-forest-green',
    success: 'bg-green-500',
    error: 'bg-terracotta'
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds} seconds`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  };

  return (
    <div className="w-full">
      {(stage || estimatedTimeLeft) && (
        <div className="flex justify-between items-center mb-1 text-xs text-pine-mid">
          <span>{stage}</span>
          <span className="flex items-center gap-2">
            <span>{clampedPercent}%</span>
            {estimatedTimeLeft && <span>(~{formatTime(estimatedTimeLeft)} remaining)</span>}
          </span>
        </div>
      )}
      <div 
        className="w-full h-2 bg-sage-light rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={clampedPercent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          data-fill
          className={`h-full ${fillColors[variant]} transition-all duration-300 ease-out`}
          style={{ width: `${clampedPercent}%` }}
        />
      </div>
    </div>
  );
};
