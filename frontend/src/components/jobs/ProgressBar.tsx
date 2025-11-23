import React, { useEffect, useMemo, useState } from 'react';

interface ProgressBarProps {
  percent: number;  // 0-100
  stage?: string;
  estimatedTimeLeft?: number;  // seconds
  startedAt?: string | null;
  stalled?: boolean;
  variant?: 'default' | 'success' | 'error';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ 
  percent, 
  stage, 
  estimatedTimeLeft, 
  startedAt,
  stalled = false,
  variant = 'default' 
}) => {
  const clampedPercent = Math.max(0, Math.min(100, percent));
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!startedAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  const fillColors = {
    default: 'bg-forest-green',
    success: 'bg-green-500',
    error: 'bg-terracotta'
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes < 60) return `${minutes}m ${secs.toString().padStart(2, '0')}s`;
    const hours = Math.floor(minutes / 60);
    const remMinutes = minutes % 60;
    return `${hours}h ${remMinutes}m`;
  };

  const elapsedSeconds = useMemo(() => {
    if (!startedAt) return null;
    const started = new Date(startedAt).getTime();
    if (Number.isNaN(started)) return null;
    return Math.max(0, Math.floor((now - started) / 1000));
  }, [now, startedAt]);

  return (
    <div className="w-full">
      {(stage || estimatedTimeLeft !== undefined || elapsedSeconds !== null) && (
        <div className="flex justify-between items-center mb-1 text-xs text-pine-mid">
          <span className="flex items-center gap-2">
            {stalled ? 'Stalled — no recent progress' : stage}
          </span>
          <span className="flex items-center gap-2">
            {elapsedSeconds !== null && <span>Elapsed {formatTime(elapsedSeconds)}</span>}
            {typeof estimatedTimeLeft === 'number' && (
              <span>Est. remaining ~{formatTime(Math.max(0, estimatedTimeLeft))}</span>
            )}
            <span>{clampedPercent}%</span>
          </span>
        </div>
      )}
      <div 
        className="w-full h-2 bg-sage-light rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={clampedPercent}
        aria-valuemin={0}
        aria-valuemax={100}
        data-testid="progress-bar"
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
