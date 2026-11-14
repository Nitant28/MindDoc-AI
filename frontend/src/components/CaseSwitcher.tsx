import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { cx } from '../lib/cx';
import type { CaseSummary } from '../types';
import { Icon } from './ui/Icon';

/** Header chip: which case (engagement) case-scoped pages show, with a menu to switch or manage cases. */
export default function CaseSwitcher({
  cases,
  current,
  onSelect,
}: {
  cases: CaseSummary[];
  current: CaseSummary | null;
  onSelect: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', esc);
    };
  }, [open]);
  if (cases.length === 0) return null;
  return (
    <div ref={ref} className="relative">
      <button
        id="case-switcher"
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={current ? `${current.title} · your role: ${current.my_role ?? '—'}` : 'Choose a case'}
        className="flex h-10 max-w-[11rem] items-center gap-2 rounded-full border border-line-strong px-3 text-sm text-fg transition-colors hover:bg-fg/[0.06] sm:max-w-[16rem]"
      >
        <Icon name="folder" className="h-4 w-4 shrink-0 text-accent-soft" />
        <span className="truncate">{current?.title ?? 'Case'}</span>
        <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-subtle" aria-hidden="true">
          <path d="m7 10 5 5 5-5z" fill="currentColor" />
        </svg>
      </button>
      {open ? (
        <div role="listbox" aria-label="Cases" className="elevation-3 absolute right-0 top-12 z-50 w-80 animate-scale-in overflow-hidden rounded-3xl bg-elevated p-2">
          <div className="px-3 pb-1 pt-2 text-[11px] font-medium uppercase tracking-[0.08em] text-subtle">Work in case</div>
          <ul className="max-h-72 overflow-y-auto">
            {cases.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={c.id === current?.id}
                  onClick={() => {
                    onSelect(c.id);
                    setOpen(false);
                  }}
                  className={cx(
                    'flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left text-sm',
                    c.id === current?.id ? 'bg-accent-container text-accent-on-container' : 'text-fg hover:bg-fg/[0.06]',
                  )}
                >
                  <Icon name="folder" className="h-4 w-4 shrink-0 opacity-70" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">
                      {c.title}
                      {c.status === 'closed' ? ' (closed)' : ''}
                    </span>
                    <span className="block text-xs opacity-70">
                      {c.my_role} · {c.documents} document{c.documents === 1 ? '' : 's'}
                    </span>
                  </span>
                  {c.id === current?.id ? <Icon name="check" className="h-4 w-4" /> : null}
                </button>
              </li>
            ))}
          </ul>
          <Link
            to="/cases"
            onClick={() => setOpen(false)}
            className="mt-1 flex items-center gap-3 rounded-full px-3 py-2.5 text-sm font-medium text-accent-soft hover:bg-accent/[0.08]"
          >
            <Icon name="settings" className="h-4 w-4" /> Manage cases and members
          </Link>
        </div>
      ) : null}
    </div>
  );
}
