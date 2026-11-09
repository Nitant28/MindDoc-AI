import { cx } from '../../lib/cx';
import { clamp01, scoreTone, type Tone } from '../../lib/format';
import { TONE_BAR } from './Badge';

interface MeterProps {
  value: number;
  max?: number;
  tone?: Tone;
  label?: string;
  className?: string;
  size?: 'xs' | 'sm' | 'md';
}

export function Meter({ value, max = 1, tone, label, className, size = 'sm' }: MeterProps) {
  const r = clamp01(max > 0 ? value / max : 0);
  const t = tone ?? scoreTone(r);
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={Number.isFinite(value) ? value : 0}
      className={cx(
        'w-full overflow-hidden rounded-full bg-elevated',
        size === 'xs' ? 'h-1' : size === 'sm' ? 'h-1.5' : 'h-2.5',
        className,
      )}
    >
      <div className={cx('h-full rounded-full transition-[width] duration-500', TONE_BAR[t])} style={{ width: `${r * 100}%` }} />
    </div>
  );
}

export function IndeterminateBar({ className, label }: { className?: string; label?: string }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-busy="true"
      className={cx('relative h-1.5 w-full overflow-hidden rounded-full bg-elevated', className)}
    >
      <div className="absolute inset-y-0 left-0 w-2/5 animate-indeterminate rounded-full bg-accent" />
    </div>
  );
}

export default Meter;
