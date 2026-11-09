import type { ReactNode } from 'react';
import { cx } from '../../lib/cx';
import type { Tone } from '../../lib/format';
import { Icon, type IconName } from './Icon';

export const TONE_BADGE: Record<Tone, string> = {
  neutral: 'bg-elevated text-muted ring-line',
  accent: 'bg-accent/10 text-accent-soft ring-accent/25',
  success: 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-400',
  warning: 'bg-amber-500/10 text-amber-700 ring-amber-500/25 dark:text-amber-400',
  danger: 'bg-rose-500/10 text-rose-700 ring-rose-500/25 dark:text-rose-400',
  info: 'bg-sky-500/10 text-sky-700 ring-sky-500/25 dark:text-sky-400',
};

export const TONE_TEXT: Record<Tone, string> = {
  neutral: 'text-fg',
  accent: 'text-accent-soft',
  success: 'text-emerald-600 dark:text-emerald-400',
  warning: 'text-amber-600 dark:text-amber-400',
  danger: 'text-rose-600 dark:text-rose-400',
  info: 'text-sky-600 dark:text-sky-400',
};

export const TONE_BAR: Record<Tone, string> = {
  neutral: 'bg-subtle',
  accent: 'bg-accent',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-rose-500',
  info: 'bg-sky-500',
};

interface BadgeProps {
  tone?: Tone;
  children: ReactNode;
  dot?: boolean;
  icon?: IconName;
  className?: string;
  title?: string;
  size?: 'sm' | 'md';
}

export function Badge({ tone = 'neutral', children, dot, icon, className, title, size = 'sm' }: BadgeProps) {
  return (
    <span
      title={title}
      className={cx(
        'inline-flex max-w-full items-center gap-1 whitespace-nowrap rounded-md font-medium ring-1 ring-inset',
        size === 'sm' ? 'px-1.5 py-0.5 text-[11px] leading-4' : 'px-2 py-1 text-xs',
        TONE_BADGE[tone],
        className,
      )}
    >
      {dot ? <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" aria-hidden="true" /> : null}
      {icon ? <Icon name={icon} className="h-3 w-3" /> : null}
      {children}
    </span>
  );
}

export default Badge;
