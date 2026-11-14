import type { HTMLAttributes, ReactNode } from 'react';
import { cx } from '../../lib/cx';
import { Icon, type IconName } from './Icon';

export function Card({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx('min-w-0 rounded-3xl border border-line bg-surface', className)} {...rest}>
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
    <div className={cx('flex flex-wrap items-start justify-between gap-3 px-5 pb-2 pt-4 sm:px-6', className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-container text-accent-on-container">
            <Icon name={icon} className="h-4 w-4" />
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 id={id} className="text-base font-medium leading-8 text-fg">
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
    <div className={cx('px-5 pb-5 pt-3 sm:px-6 sm:pb-6', className)} {...rest}>
      {children}
    </div>
  );
}

export default Card;
