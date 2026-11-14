import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { documentsApi } from '../api';
import { cx } from '../lib/cx';
import { useTheme } from '../lib/theme';
import type { CaseSummary, DocumentSummary } from '../types';
import { NAV_ITEMS } from './Sidebar';
import { Icon, type IconName } from './ui/Icon';

interface Item {
  id: string;
  group: 'Go to' | 'Actions' | 'Cases' | 'Documents';
  label: string;
  hint?: string;
  icon: IconName;
  run: () => void;
}

/** Search everything the user can reach: pages, actions, cases and documents (Ctrl/⌘ K or "/"). */
export default function CommandPalette({
  open,
  onClose,
  cases,
  onSelectCase,
}: {
  open: boolean;
  onClose: () => void;
  cases: CaseSummary[];
  onSelectCase: (id: number) => void;
}) {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const [q, setQ] = useState('');
  const [active, setActive] = useState(0);
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (!open) return;
    setQ('');
    setActive(0);
    window.setTimeout(() => inputRef.current?.focus(), 0);
    documentsApi.listAll().then(setDocs).catch(() => setDocs([]));
  }, [open]);

  const go = useCallback(
    (to: string) => () => {
      navigate(to);
      onClose();
    },
    [navigate, onClose],
  );

  const items = useMemo<Item[]>(() => {
    const all: Item[] = [
      ...NAV_ITEMS.map((n) => ({ id: `nav:${n.to}`, group: 'Go to' as const, label: n.label, icon: n.icon, run: go(n.to) })),
      { id: 'act:upload', group: 'Actions', label: 'Upload documents', icon: 'upload', run: go('/upload') },
      { id: 'act:case', group: 'Actions', label: 'Create a case', icon: 'folder', run: go('/cases') },
      { id: 'act:discover', group: 'Actions', label: 'Run the detectors on this case', icon: 'target', run: go('/discoveries?run=1') },
      { id: 'act:ask', group: 'Actions', label: 'Ask a question about the documents', icon: 'chat', run: go('/chat') },
      { id: 'act:invite', group: 'Actions', label: 'Invite a colleague', icon: 'mail', run: go('/settings') },
      {
        id: 'act:theme',
        group: 'Actions',
        label: theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme',
        icon: theme === 'dark' ? 'sun' : 'moon',
        run: () => {
          toggle();
          onClose();
        },
      },
      ...cases.map((c) => ({
        id: `case:${c.id}`,
        group: 'Cases' as const,
        label: c.title,
        hint: `${c.my_role ?? ''} · ${c.documents} document${c.documents === 1 ? '' : 's'}`,
        icon: 'folder' as IconName,
        run: () => {
          onSelectCase(c.id);
          onClose();
        },
      })),
      ...docs.map((d) => ({
        id: `doc:${d.id}`,
        group: 'Documents' as const,
        label: d.filename,
        hint: d.doc_type ?? undefined,
        icon: 'file' as IconName,
        run: go(`/documents/${d.id}`),
      })),
    ];
    const needle = q.trim().toLowerCase();
    if (!needle) return all.filter((i) => i.group !== 'Documents').slice(0, 14).concat(all.filter((i) => i.group === 'Documents').slice(0, 5));
    const words = needle.split(/\s+/);
    return all
      .map((i) => {
        const hay = `${i.label} ${i.hint ?? ''} ${i.group}`.toLowerCase();
        if (!words.every((w) => hay.includes(w))) return null;
        const score = (i.label.toLowerCase().startsWith(needle) ? 0 : 1) + (i.group === 'Go to' ? 0 : 0.5);
        return { i, score };
      })
      .filter((x): x is { i: Item; score: number } => x !== null)
      .sort((a, b) => a.score - b.score)
      .slice(0, 30)
      .map((x) => x.i);
  }, [q, cases, docs, go, theme, toggle, onClose, onSelectCase]);

  useEffect(() => setActive(0), [q]);
  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  if (!open) return null;

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
    else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(items.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      items[active]?.run();
    }
  };

  let last = '';
  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-start justify-center px-3 pt-[12vh]" onKeyDown={onKeyDown}>
      <div className="absolute inset-0 animate-fade-in bg-black/40" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-label="Search MindDoc" className="elevation-3 relative w-full max-w-2xl animate-scale-in overflow-hidden rounded-[28px] bg-surface">
        <div className="flex h-16 items-center gap-3 border-b border-line px-5">
          <Icon name="search" className="h-5 w-5 text-subtle" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search pages, cases, documents and actions"
            aria-label="Search"
            aria-controls="palette-results"
            aria-activedescendant={items[active] ? `pi-${items[active].id}` : undefined}
            className="h-full flex-1 bg-transparent text-base text-fg placeholder:text-subtle focus:outline-none"
          />
          <kbd>Esc</kbd>
        </div>
        <ul id="palette-results" ref={listRef} role="listbox" className="max-h-[56vh] overflow-y-auto p-2">
          {items.length === 0 ? (
            <li className="px-4 py-10 text-center text-sm text-subtle">Nothing matches “{q}”.</li>
          ) : (
            items.map((it, idx) => {
              const header = it.group !== last ? it.group : null;
              last = it.group;
              return (
                <li key={it.id}>
                  {header ? <div className="px-3 pb-1 pt-3 text-[11px] font-medium uppercase tracking-[0.08em] text-subtle">{header}</div> : null}
                  <button
                    id={`pi-${it.id}`}
                    data-index={idx}
                    role="option"
                    aria-selected={idx === active}
                    type="button"
                    onMouseMove={() => setActive(idx)}
                    onClick={it.run}
                    className={cx(
                      'flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left text-sm',
                      idx === active ? 'bg-accent-container text-accent-on-container' : 'text-fg',
                    )}
                  >
                    <Icon name={it.icon} className="h-[18px] w-[18px] shrink-0 opacity-80" />
                    <span className="min-w-0 flex-1 truncate">{it.label}</span>
                    {it.hint ? <span className="shrink-0 truncate text-xs opacity-70">{it.hint}</span> : null}
                  </button>
                </li>
              );
            })
          )}
        </ul>
        <div className="flex items-center gap-4 border-t border-line px-5 py-2.5 text-[11px] text-subtle">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> move
          </span>
          <span>
            <kbd>Enter</kbd> open
          </span>
          <span className="ml-auto">
            <kbd>Ctrl</kbd> <kbd>K</kbd> anywhere
          </span>
        </div>
      </div>
    </div>,
    document.body,
  );
}
