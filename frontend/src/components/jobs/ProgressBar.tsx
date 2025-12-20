import React, { useEffect, useMemo, useState } from 'react';

interface ProgressBarProps {
  percent: number;  // 0-100
  stage?: string;
  estimatedTimeLeft?: number;  // seconds
  startedAt?: string | null;
  createdAt?: string | null;
  stalled?: boolean;
  variant?: 'default' | 'success' | 'error';
  indeterminate?: boolean;
  hidePercent?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ 
  percent, 
  stage, 
  estimatedTimeLeft, 
  startedAt,
  createdAt,
  stalled = false,
  variant = 'default',
  indeterminate = false,
  hidePercent = false
}) => {
  const clampedPercent = Math.max(0, Math.min(100, percent));
  const [now, setNow] = useState(() => Date.now());
  const showPercent = !hidePercent && !indeterminate;
  const displayStage = stage || (indeterminate ? 'Processing' : undefined);

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

  const parseTimestamp = (value?: string | null) => {
    if (!value) return null;
    // Normalize "YYYY-MM-DD HH:MM:SS.ssssss" -> "YYYY-MM-DDTHH:MM:SS.sssZ"
    let normalized = value.replace(' ', 'T');
    normalized = normalized.replace(/(\.\d{3})\d+/, '$1'); // trim microseconds to milliseconds
    if (!/Z$/i.test(normalized) && !/[+-]\d{2}:\d{2}$/.test(normalized)) {
        normalized = `${normalized}Z`;
    }
    const ts = Date.parse(normalized);
    return Number.isNaN(ts) ? null : ts;
  };

  const elapsedSeconds = useMemo(() => {
    const startedTs = parseTimestamp(startedAt) ?? parseTimestamp(createdAt);
    if (startedTs === null) return null;
    return Math.max(0, Math.floor((now - startedTs) / 1000));
  }, [now, startedAt, createdAt]);

  const ariaLabel = displayStage
    ? `Progress ${indeterminate ? 'in progress' : `${clampedPercent} percent`}, stage ${displayStage}`
    : `Progress ${indeterminate ? 'in progress' : `${clampedPercent} percent`}`;

  return (
    <div className="w-full">
      {(displayStage || (!indeterminate && estimatedTimeLeft !== undefined) || elapsedSeconds !== null) && (
        <div className="flex justify-between items-center mb-1 text-xs text-pine-mid">
          <span className="flex items-center gap-2">
            {stalled ? 'Stalled - no recent progress' : displayStage}
          </span>
          <span className="flex items-center gap-2">
            {elapsedSeconds !== null && <span>Elapsed {formatTime(elapsedSeconds)}</span>}
            {!indeterminate && typeof estimatedTimeLeft === 'number' && (
              <span>Est. remaining ~{formatTime(Math.max(0, estimatedTimeLeft))}</span>
            )}
            {showPercent && <span>{clampedPercent}%</span>}
          </span>
        </div>
      )}
      <div 
        className="w-full h-2 bg-sage-light rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : clampedPercent}
        aria-valuemin={indeterminate ? undefined : 0}
        aria-valuemax={indeterminate ? undefined : 100}
        aria-valuetext={indeterminate ? 'In progress' : undefined}
        aria-label={ariaLabel}
        data-testid="progress-bar"
      >
        <div
          data-fill
          className={`h-full ${fillColors[variant]} ${indeterminate ? 'animate-pulse' : 'transition-all duration-300 ease-out'}`}
          style={{ width: indeterminate ? '40%' : `${clampedPercent}%` }}
        />
      </div>
    </div>
  );
};
