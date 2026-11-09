import { cx } from '../lib/cx';

export function LogoMark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={cx('shrink-0', className)} aria-hidden="true">
      <rect width="32" height="32" rx="8" className="fill-accent" />
      <path
        d="M10.5 21.5 16 11.5l5.5 8.5"
        fill="none"
        stroke="#fff"
        strokeOpacity="0.55"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M10.5 21.5h11" fill="none" stroke="#fff" strokeOpacity="0.25" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="10.5" cy="21.5" r="2.4" fill="#fff" />
      <circle cx="16" cy="11.5" r="2.4" fill="#fff" />
      <circle cx="21.5" cy="20" r="2.4" fill="#fff" />
    </svg>
  );
}

interface LogoProps {
  showText?: boolean;
  size?: number;
  tagline?: string;
}

export default function Logo({ showText = true, size = 32, tagline = 'Document intelligence, grounded' }: LogoProps) {
  return (
    <div className="flex items-center gap-3">
      <LogoMark size={size} />
      {showText ? (
        <div className="leading-tight">
          <div className="text-base font-semibold tracking-tight text-fg">MindDoc AI</div>
          <div className="text-xs text-muted">{tagline}</div>
        </div>
      ) : null}
    </div>
  );
}
