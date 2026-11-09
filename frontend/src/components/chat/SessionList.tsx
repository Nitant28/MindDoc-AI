import { useMemo, useRef, useState } from 'react';
import { cx } from '../../lib/cx';
import { relTime, timeOf } from '../../lib/format';
import type { ChatSession } from '../../types';
import { Button } from '../ui/Button';
import { Input } from '../ui/Field';
import { Icon } from '../ui/Icon';
import { Skeleton } from '../ui/Spinner';

interface SessionListProps {
  sessions: ChatSession[];
  activeId: number | null;
  loading: boolean;
  onSelect: (id: number) => void;
  onNew: () => void;
  onRename: (id: number, title: string) => void | Promise<void>;
  onDelete: (session: ChatSession) => void;
}

export default function SessionList({ sessions, activeId, loading, onSelect, onNew, onRename, onDelete }: SessionListProps) {
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [q, setQ] = useState('');
  const editingRef = useRef<number | null>(null);

  const startEdit = (s: ChatSession) => {
    editingRef.current = s.id;
    setEditing(s.id);
    setDraft(s.title ?? '');
  };

  const finishEdit = (s: ChatSession, commit: boolean) => {
    if (editingRef.current !== s.id) return;
    editingRef.current = null;
    setEditing(null);
    const t = draft.trim();
    if (commit && t && t !== s.title) void onRename(s.id, t);
  };

  const sorted = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return [...sessions]
      .sort((a, b) => timeOf(b.created_at) - timeOf(a.created_at) || b.id - a.id)
      .filter((s) => !needle || (s.title ?? '').toLowerCase().includes(needle));
  }, [sessions, q]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="space-y-2 p-3">
        <Button variant="primary" size="sm" className="w-full" icon="plus" onClick={onNew}>
          New chat
        </Button>
        {sessions.length > 5 ? (
          <div className="relative">
            <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search chats"
              aria-label="Search chats"
              className="h-8 pl-8 text-[13px]"
            />
          </div>
        ) : null}
      </div>
      <div className="px-4 pb-1 text-[10px] font-semibold uppercase tracking-wider text-subtle">History</div>
      <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-3" aria-label="Chat sessions">
        {loading ? (
          [0, 1, 2, 3].map((i) => (
            <li key={i} className="px-2 py-1.5">
              <Skeleton className="h-8 w-full" />
            </li>
          ))
        ) : sorted.length === 0 ? (
          <li className="px-2 py-6 text-center text-xs text-subtle">{q ? 'No matching chats' : 'No conversations yet'}</li>
        ) : (
          sorted.map((s) => {
            const active = s.id === activeId;
            return (
              <li key={s.id} className={cx('group relative flex items-center rounded-md', active ? 'bg-elevated' : 'hover:bg-elevated/60')}>
                {editing === s.id ? (
                  <input
                    autoFocus
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onBlur={() => finishEdit(s, true)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        finishEdit(s, true);
                      } else if (e.key === 'Escape') {
                        e.preventDefault();
                        finishEdit(s, false);
                      }
                    }}
                    aria-label="Chat title"
                    maxLength={120}
                    className="m-1 w-full rounded-md border border-accent bg-surface px-2 py-1 text-sm text-fg focus:outline-none focus:ring-2 focus:ring-accent/25"
                  />
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onSelect(s.id)}
                      aria-current={active ? 'true' : undefined}
                      className="min-w-0 flex-1 rounded-md px-2 py-1.5 text-left"
                    >
                      <span className={cx('block truncate text-sm', active ? 'font-medium text-fg' : 'text-muted')}>{s.title || 'Untitled chat'}</span>
                      <span className="block text-[11px] text-subtle">{relTime(s.created_at)}</span>
                    </button>
                    <div className="flex shrink-0 items-center pr-1 sm:opacity-0 sm:focus-within:opacity-100 sm:group-hover:opacity-100">
                      <Button variant="ghost" size="icon-sm" aria-label={`Rename “${s.title}”`} title="Rename" onClick={() => startEdit(s)} icon="edit" />
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Delete “${s.title}”`}
                        title="Delete"
                        onClick={() => onDelete(s)}
                        icon="trash"
                        className="hover:!text-rose-500"
                      />
                    </div>
                  </>
                )}
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}
