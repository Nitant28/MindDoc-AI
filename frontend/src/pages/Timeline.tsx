import { useCallback, useEffect, useId, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { documentsApi, errorMessage, intelApi } from '../api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Select } from '../components/ui/Field';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { Skeleton } from '../components/ui/Spinner';
import { cx } from '../lib/cx';
import { useTitle } from '../lib/useTitle';
import type { DocumentSummary, TimelineItem } from '../types';
import { dueLabel, dueTone, formatDay } from '../lib/dates';

type Range = 'all' | 'upcoming';

function monthKey(iso: string): string {
  const m = /^(\d{4})-(\d{2})/.exec(iso);
  return m ? `${m[1]}-${m[2]}` : 'unknown';
}

function monthLabel(key: string): string {
  if (key === 'unknown') return 'Undated';
  const [y, m] = key.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

function Highlight({ text, term }: { text: string; term?: string | null }) {
  if (!term) return <>{text}</>;
  const i = text.toLowerCase().indexOf(term.toLowerCase());
  if (i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark className="rounded bg-amber-400/25 px-0.5 text-fg">{text.slice(i, i + term.length)}</mark>
      {text.slice(i + term.length)}
    </>
  );
}

export default function Timeline() {
  useTitle('Timeline');
  const [params, setParams] = useSearchParams();
  const docParam = params.get('document');
  const documentId = docParam && /^\d+$/.test(docParam) ? Number(docParam) : null;
  const range: Range = params.get('upcoming') === '1' ? 'upcoming' : 'all';
  const docSelectId = useId();

  const [items, setItems] = useState<TimelineItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

  useEffect(() => {
    documentsApi
      .list()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  const load = useCallback(async () => {
    setItems(null);
    setError(null);
    try {
      const xs = await intelApi.timeline({ document_id: documentId, upcoming_days: range === 'upcoming' ? 90 : null });
      setItems([...xs].sort((a, b) => (a.date ?? '').localeCompare(b.date ?? '')));
    } catch (e) {
      setItems([]);
      setError(errorMessage(e, 'Timeline unavailable'));
    }
  }, [documentId, range]);

  useEffect(() => {
    void load();
  }, [load]);

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const groups = useMemo(() => {
    const m = new Map<string, TimelineItem[]>();
    (items ?? []).forEach((it) => {
      const k = monthKey(it.date ?? '');
      if (!m.has(k)) m.set(k, []);
      m.get(k)?.push(it);
    });
    return [...m.entries()];
  }, [items]);

  const upcomingCount = (items ?? []).filter((i) => i.upcoming).length;

  return (
    <Page className="max-w-5xl">
      <PageHeader
        title="Timeline"
        description="Dates, deadlines and renewals extracted from every document, in chronological order."
        actions={
          <Button icon="refresh" onClick={() => void load()} loading={items === null && !error}>
            Refresh
          </Button>
        }
      />

      <Card className="mb-6 flex flex-wrap items-end gap-3 px-4 py-3 sm:px-5">
        <div>
          <label htmlFor={docSelectId} className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-subtle">
            Document
          </label>
          <Select id={docSelectId} value={documentId ?? ''} onChange={(e) => setParam('document', e.target.value || null)} className="h-8 w-56 text-[13px]">
            <option value="">All documents</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <span className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-subtle">Range</span>
          <Segmented<Range>
            label="Date range"
            value={range}
            onChange={(v) => setParam('upcoming', v === 'upcoming' ? '1' : null)}
            options={[
              { value: 'all', label: 'All dates', icon: 'calendar' },
              { value: 'upcoming', label: 'Upcoming only', icon: 'clock', hint: 'Next 90 days' },
            ]}
          />
        </div>
        {items && items.length > 0 ? (
          <span className="ml-auto text-xs text-subtle">
            {items.length} dates · {upcomingCount} upcoming
          </span>
        ) : null}
      </Card>

      {items === null ? (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : error ? (
        <Card>
          <EmptyState icon="alert" title="Timeline unavailable" description={error} action={<Button size="sm" onClick={() => void load()}>Retry</Button>} />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon="calendar"
            title={range === 'upcoming' ? 'Nothing due in the next 90 days' : 'No dates found'}
            description="Dates are extracted automatically when documents are uploaded."
          />
        </Card>
      ) : (
        <div className="space-y-8">
          {groups.map(([key, list]) => (
            <section key={key} aria-labelledby={`tl-${key}`}>
              <h2 id={`tl-${key}`} className="sticky top-14 z-10 -mx-1 mb-3 bg-bg/90 px-1 py-1.5 text-xs font-semibold uppercase tracking-wider text-subtle backdrop-blur">
                {monthLabel(key)} <span className="font-normal normal-case tracking-normal">· {list.length}</span>
              </h2>
              <ol className="relative ml-2 space-y-3 border-l border-line pl-6">
                {list.map((it, i) => {
                  const upcoming = !!it.upcoming || (it.days_from_now != null && it.days_from_now >= 0);
                  const due = dueLabel(it.days_from_now);
                  return (
                    <li key={`${it.date}-${it.document_id}-${i}`} className="relative">
                      <span
                        className={cx(
                          'absolute -left-[31px] top-4 h-3 w-3 rounded-full border-2 border-bg',
                          upcoming ? (it.days_from_now != null && it.days_from_now <= 14 ? 'bg-rose-500' : 'bg-accent') : 'bg-line-strong',
                        )}
                        aria-hidden="true"
                      />
                      <Card className={cx('p-4', upcoming && 'border-accent/30')}>
                        <div className="flex flex-wrap items-center gap-2">
                          <time dateTime={it.date} className="text-sm font-semibold tabular-nums text-fg">
                            {formatDay(it.date)}
                          </time>
                          {it.text && it.text !== it.date ? <span className="text-xs text-subtle">“{it.text}”</span> : null}
                          {upcoming && due ? (
                            <Badge tone={dueTone(it.days_from_now)} icon="clock">
                              {due}
                            </Badge>
                          ) : !upcoming && due ? (
                            <Badge tone="neutral">{due}</Badge>
                          ) : null}
                        </div>
                        {it.snippet ? (
                          <p className="mt-1.5 text-sm leading-relaxed text-muted">
                            <Highlight text={it.snippet} term={it.text} />
                          </p>
                        ) : null}
                        {it.document_id != null ? (
                          <Link to={`/documents/${it.document_id}`} className="mt-2 inline-flex items-center gap-1.5 text-xs text-subtle hover:text-fg hover:underline">
                            {it.filename ?? `Document #${it.document_id}`}
                            {it.page != null ? <span>· page {it.page}</span> : null}
                          </Link>
                        ) : null}
                      </Card>
                    </li>
                  );
                })}
              </ol>
            </section>
          ))}
        </div>
      )}
    </Page>
  );
}
