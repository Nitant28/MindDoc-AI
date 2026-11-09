import { cx } from '../lib/cx';
import { clamp01, type Tone } from '../lib/format';

const STROKE: Record<Tone, string> = {
  neutral: 'stroke-subtle',
  accent: 'stroke-accent',
  success: 'stroke-emerald-500',
  warning: 'stroke-amber-500',
  danger: 'stroke-rose-500',
  info: 'stroke-sky-500',
};

interface GaugeProps {
  /** 0..1 fill ratio. */
  value: number;
  label: string;
  display: string;
  tone?: Tone;
  sublabel?: string;
  size?: number;
  className?: string;
}

/** 270° radial gauge. */
export default function Gauge({ value, label, display, tone = 'accent', sublabel, size = 104, className }: GaugeProps) {
  const r = 40;
  const circ = 2 * Math.PI * r;
  const arc = circ * 0.75;
  const fill = arc * clamp01(value);
  return (
    <div className={cx('flex flex-col items-center text-center', className)}>
      <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={`${label}: ${display}`}>
        <g transform="rotate(135 50 50)">
          <circle cx="50" cy="50" r={r} fill="none" strokeWidth="8" strokeLinecap="round" className="stroke-line" strokeDasharray={`${arc} ${circ}`} />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            strokeWidth="8"
            strokeLinecap="round"
            className={STROKE[tone]}
            strokeDasharray={`${fill} ${circ}`}
            style={{ transition: 'stroke-dasharray 700ms ease' }}
          />
        </g>
        <text x="50" y="55" textAnchor="middle" className="fill-fg font-sans text-[17px] font-semibold tabular-nums">
          {display}
        </text>
      </svg>
      <div className="-mt-3 text-xs font-medium text-fg">{label}</div>
      {sublabel ? <div className="mt-0.5 text-[11px] text-subtle">{sublabel}</div> : null}
    </div>
  );
}
