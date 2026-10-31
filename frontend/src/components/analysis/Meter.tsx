import React from 'react';

export interface MeterProps {
  /** 0–1 share of the track to fill. */
  fraction: number;
  /** Tailwind background class for the fill. */
  tone?: string;
  /** Track thickness. */
  size?: 'sm' | 'md';
  className?: string;
}

/** A thin horizontal meter. Decorative: the numeric value is always printed beside it. */
export const Meter: React.FC<MeterProps> = ({ fraction, tone = 'bg-jade-300', size = 'sm', className = '' }) => {
  const width = Math.min(1, Math.max(0, fraction)) * 100;
  return (
    <div className={`relative w-full overflow-hidden rounded-full bg-ink-900/10 ${size === 'sm' ? 'h-1' : 'h-1.5'} ${className}`} aria-hidden="true">
      <div className={`absolute inset-y-0 left-0 rounded-full ${tone}`} style={{ width: `${width}%` }} />
    </div>
  );
};

/** Shared `0–max` fraction for a value on a declared scale. */
export const scaleFraction = (value: number, min: number, max: number) => {
  const span = max - min || 1;
  return (value - min) / span;
};

export default Meter;
