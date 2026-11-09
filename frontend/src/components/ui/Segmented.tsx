import { useRef, type KeyboardEvent } from 'react';
import { cx } from '../../lib/cx';
import { Icon, type IconName } from './Icon';

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
  icon?: IconName;
  hint?: string;
}

interface SegmentedProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentedOption<T>[];
  label: string;
  disabled?: boolean;
  className?: string;
}

/** Accessible radio-group styled as a segmented control (roving tabindex, arrow keys). */
export function Segmented<T extends string>({ value, onChange, options, label, disabled, className }: SegmentedProps<T>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const idx = Math.max(0, options.findIndex((o) => o.value === value));
    let next = idx;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (idx - 1 + options.length) % options.length;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (idx + 1) % options.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = options.length - 1;
    onChange(options[next].value);
    refs.current[next]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cx('inline-flex rounded-lg border border-line bg-elevated p-0.5', className)}
    >
      {options.map((o, i) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            title={o.hint}
            disabled={disabled}
            onClick={() => onChange(o.value)}
            className={cx(
              'inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors disabled:opacity-50',
              active ? 'bg-surface text-fg shadow-sm ring-1 ring-line' : 'text-muted hover:text-fg',
            )}
          >
            {o.icon ? <Icon name={o.icon} className={cx('h-3.5 w-3.5', active && 'text-accent')} /> : null}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export default Segmented;
