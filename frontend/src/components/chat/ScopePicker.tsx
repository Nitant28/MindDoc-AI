import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { cx } from '../../lib/cx';
import { humanize } from '../../lib/format';
import type { DocumentSummary } from '../../types';
import { buttonClass } from '../ui/Button';
import { Input } from '../ui/Field';
import { Icon } from '../ui/Icon';

interface ScopePickerProps {
  documents: DocumentSummary[];
  value: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
}

export function scopeLabel(documents: DocumentSummary[], value: number[]): string {
  if (value.length === 0) return 'All workspace';
  if (value.length === 1) return documents.find((d) => d.id === value[0])?.filename ?? `Document #${value[0]}`;
  return `${value.length} documents`;
}

export default function ScopePicker({ documents, value, onChange, disabled }: ScopePickerProps) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? documents.filter((d) => d.filename.toLowerCase().includes(needle)) : documents;
  }, [documents, q]);

  const toggle = (id: number) => onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);

  return (
    <div ref={wrapRef} className="relative">
      <button
        ref={btnRef}
        type="button"
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((o) => !o)}
        className={buttonClass('secondary', 'sm', 'max-w-[13rem] gap-1.5 sm:max-w-[16rem]')}
        title="Choose which documents the answer may use"
      >
        <Icon name={value.length ? 'file' : 'database'} className="h-3.5 w-3.5 text-subtle" />
        <span className="truncate text-[13px]">{scopeLabel(documents, value)}</span>
        <Icon name="chevron-down" className="h-3.5 w-3.5 text-subtle" />
      </button>
      {open ? (
        <div
          id={panelId}
          role="dialog"
          aria-label="Document scope"
          className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] animate-slide-up rounded-xl border border-line bg-surface p-2 shadow-xl shadow-black/20"
        >
          <Input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter documents…"
            aria-label="Filter documents"
            className="mb-2 h-8 text-[13px]"
          />
          <button
            type="button"
            onClick={() => onChange([])}
            aria-pressed={value.length === 0}
            className={cx(
              'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm',
              value.length === 0 ? 'bg-accent/10 text-fg' : 'text-muted hover:bg-elevated hover:text-fg',
            )}
          >
            <Icon name="database" className="h-4 w-4 text-subtle" />
            All workspace
            <span className="ml-auto text-[11px] text-subtle">{documents.length} docs</span>
            {value.length === 0 ? <Icon name="check" className="h-3.5 w-3.5 text-accent" /> : null}
          </button>
          <div className="my-2 border-t border-line" />
          <ul className="max-h-64 overflow-y-auto">
            {filtered.map((d) => (
              <li key={d.id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm text-fg hover:bg-elevated">
                  <input
                    type="checkbox"
                    checked={value.includes(d.id)}
                    onChange={() => toggle(d.id)}
                    className="h-3.5 w-3.5 shrink-0 accent-indigo-500"
                  />
                  <span className="min-w-0 truncate">{d.filename}</span>
                  {d.doc_type ? <span className="ml-auto shrink-0 text-[11px] text-subtle">{humanize(d.doc_type)}</span> : null}
                </label>
              </li>
            ))}
          </ul>
          {filtered.length === 0 ? <p className="px-2 py-3 text-center text-xs text-subtle">No documents match.</p> : null}
        </div>
      ) : null}
    </div>
  );
}
