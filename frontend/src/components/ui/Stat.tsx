import type { ReactNode } from 'react';
import { cx } from '../../lib/cx';
import type { Tone } from '../../lib/format';
import { TONE_TEXT } from './Badge';
import { Card } from './Card';
import { Icon, type IconName } from './Icon';
import { Skeleton } from './Spinner';

interface StatProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: IconName;
  tone?: Tone;
  loading?: boolean;
  className?: string;
}

export function Stat({ label, value, hint, icon, tone = 'neutral', loading, className }: StatProps) {
  return (
    <Card className={cx('p-4', className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[11px] font-medium uppercase tracking-wider text-subtle">{label}</span>
        {icon ? <Icon name={icon} className="h-4 w-4 text-subtle" /> : null}
      </div>
      <div className={cx('mt-2 text-2xl font-semibold tabular-nums tracking-tight', TONE_TEXT[tone])}>
        {loading ? <Skeleton className="h-8 w-20" /> : value}
      </div>
      {hint ? <div className="mt-1 truncate text-xs text-muted">{hint}</div> : null}
    </Card>
  );
}

export default Stat;
