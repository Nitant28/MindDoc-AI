import type { HTMLAttributes, ReactNode } from 'react';
import { cx } from '../../lib/cx';
import { Icon, type IconName } from './Icon';

export function Card({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx('rounded-xl border border-line bg-surface shadow-sm shadow-black/[0.03]', className)} {...rest}>
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  icon?: IconName;
  actions?: ReactNode;
  className?: string;
  id?: string;
}

export function CardHeader({ title, description, icon, actions, className, id }: CardHeaderProps) {
  return (
    <div className={cx('flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3 sm:px-5', className)}>
      <div className="flex min-w-0 items-start gap-2.5">
        {icon ? (
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-elevated text-muted">
            <Icon name={icon} className="h-3.5 w-3.5" />
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 id={id} className="text-sm font-semibold leading-6 text-fg">
            {title}
          </h2>
          {description ? <p className="text-xs leading-5 text-muted">{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function CardBody({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx('p-4 sm:p-5', className)} {...rest}>
      {children}
    </div>
  );
}

export default Card;
