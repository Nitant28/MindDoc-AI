import type { ReactNode } from 'react';
import { cx } from '../../lib/cx';

export function Page({ children, className, wide }: { children: ReactNode; className?: string; wide?: boolean }) {
  return (
    <div className={cx('mx-auto w-full animate-fade-in px-4 py-6 sm:px-8 lg:px-10 lg:py-9', wide ? 'max-w-[1600px]' : 'max-w-7xl', className)}>
      {children}
    </div>
  );
}

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, eyebrow, className }: PageHeaderProps) {
  return (
    <div className={cx('mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between', className)}>
      <div className="min-w-0">
        {eyebrow ? <div className="mb-2">{eyebrow}</div> : null}
        <h1 className="break-words text-[26px] font-normal leading-tight tracking-tight text-fg sm:text-[32px]">{title}</h1>
        {description ? <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function Banner({
  tone = 'info',
  title,
  children,
  className,
}: {
  tone?: 'info' | 'warning' | 'danger';
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  const styles = {
    info: 'border-sky-500/25 bg-sky-500/[0.06] text-sky-800 dark:text-sky-300',
    warning: 'border-amber-500/30 bg-amber-500/[0.07] text-amber-800 dark:text-amber-300',
    danger: 'border-rose-500/40 bg-rose-500/[0.08] text-rose-800 dark:text-rose-300',
  }[tone];
  return (
    <div role={tone === 'danger' ? 'alert' : 'status'} className={cx('rounded-2xl border px-4 py-3 text-sm', styles, className)}>
      {title ? <p className="font-semibold">{title}</p> : null}
      {children ? <div className={cx(title ? 'mt-1' : '', 'text-[13px] opacity-90')}>{children}</div> : null}
    </div>
  );
}

export default PageHeader;
