import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { errorMessage, intelApi } from '../api';
import DocumentTable from '../components/DocumentTable';
import { ConfidenceBadge } from '../components/Signals';
import { Badge } from '../components/ui/Badge';
import { LinkButton } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Meter } from '../components/ui/Meter';
import { Banner, Page, PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Spinner';
import { Stat } from '../components/ui/Stat';
import { useDocuments } from '../hooks/useDocuments';
import { dueLabel, dueTone, formatDay } from '../lib/dates';
import { fmtMs, fullDate, humanize, num, pct, relTime, scoreTone, type Tone } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { Overview, TimelineItem, Topic } from '../types';
import type { IconName } from '../components/ui/Icon';

function UpcomingDates() {
  const [items, setItems] = useState<TimelineItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    intelApi
      .timeline({ upcoming_days: 90 })
      .then((xs) => {
        if (!alive) return;
        setItems(xs.filter((x) => x.upcoming !== false && (x.days_from_now == null || x.days_from_now >= 0)).slice(0, 5));
      })
      .catch((e) => {
        if (alive) setError(errorMessage(e, 'Timeline unavailable'));
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <Card>
      <CardHeader
        icon="calendar"
        title="Upcoming dates"
        description="Deadlines and renewals in the next 90 days"
        actions={
          <Link to="/timeline?upcoming=1" className="text-xs font-medium text-accent-soft hover:underline">
            Timeline →
          </Link>
        }
      />
      {items === null && !error ? (
        <div className="space-y-2 p-4">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-9" />
          ))}
        </div>
      ) : error ? (
        <EmptyState icon="calendar" title="Timeline unavailable" description={error} compact />
      ) : items && items.length === 0 ? (
        <EmptyState icon="calendar" title="Nothing due soon" description="No dates in the next 90 days were found in your documents." compact />
      ) : (
        <ul className="divide-y divide-line">
          {(items ?? []).map((it, i) => (
            <li key={`${it.date}-${i}`} className="flex items-start gap-3 px-4 py-2.5 sm:px-5">
              <div className="w-16 shrink-0 text-xs font-medium tabular-nums text-fg">{formatDay(it.date)}</div>
              <div className="min-w-0 flex-1">
                <p className="line-clamp-1 text-xs text-muted" title={it.snippet ?? undefined}>
                  {it.snippet ?? it.text ?? it.date}
                </p>
                {it.document_id != null ? (
                  <Link to={`/documents/${it.document_id}`} className="text-[11px] text-subtle hover:text-fg hover:underline">
                    {it.filename ?? `Document #${it.document_id}`}
                    {it.page != null ? ` · p. ${it.page}` : ''}
                  </Link>
                ) : null}
              </div>
              {dueLabel(it.days_from_now) ? <Badge tone={dueTone(it.days_from_now)}>{dueLabel(it.days_from_now)}</Badge> : null}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function Dashboard() {
  useTitle('Dashboard');
  const { documents, loading: docsLoading, error: docsError, remove } = useDocuments();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [ovLoading, setOvLoading] = useState(true);
  const [ovError, setOvError] = useState<string | null>(null);
  const [topic, setTopic] = useState<Topic | null>(null);
  const docsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    intelApi
      .overview()
      .then((o) => alive && setOverview(o))
      .catch((e) => alive && setOvError(errorMessage(e, 'Analytics unavailable')))
      .finally(() => alive && setOvLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const derived = useMemo(() => {
    const types: Record<string, number> = {};
    let chunks = 0;
    let pii = 0;
    documents.forEach((d) => {
      chunks += d.chunk_count ?? 0;
      pii += d.pii_count ?? 0;
      const t = d.doc_type || 'unclassified';
      types[t] = (types[t] ?? 0) + 1;
    });
    return { types, chunks, pii };
  }, [documents]);

  const o = overview;
  const docTypes = Object.entries(o?.doc_types && Object.keys(o.doc_types).length ? o.doc_types : derived.types).sort((a, b) => b[1] - a[1]);
  const maxType = Math.max(1, ...docTypes.map(([, n]) => n));
  const topics = o?.topics ?? [];
  const recent = o?.recent_queries ?? [];
  const piiTotal = o?.pii_total ?? derived.pii;
  const kpiLoading = ovLoading && docsLoading;

  const kpis: Array<{ label: string; value: string; icon: IconName; tone?: Tone; hint?: string }> = [
    { label: 'Documents', value: num(o?.documents ?? documents.length), icon: 'file' },
    { label: 'Chunks', value: num(o?.chunks ?? derived.chunks), icon: 'layers', hint: 'Indexed passages' },
    { label: 'Entities', value: num(o?.entities), icon: 'tag', hint: 'Ontology nodes' },
    { label: 'Relations', value: num(o?.relations), icon: 'graph', hint: 'Ontology edges' },
    { label: 'Queries', value: num(o?.queries), icon: 'chat', hint: 'Answered in this workspace' },
    { label: 'Avg evidence score', value: pct(o?.avg_confidence), icon: 'target', tone: scoreTone(o?.avg_confidence) },
    { label: 'Avg latency', value: fmtMs(o?.avg_latency_ms), icon: 'clock', hint: 'End-to-end answer time' },
    { label: 'PII found', value: num(piiTotal), icon: 'shield', tone: piiTotal > 0 ? 'warning' : 'neutral', hint: 'Emails, phones, IDs…' },
  ];

  const pickTopic = (t: Topic) => {
    setTopic((cur) => (cur?.id === t.id ? null : t));
    window.setTimeout(() => docsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 30);
  };

  return (
    <Page>
      <PageHeader
        title="Overview"
        description="Workspace intelligence at a glance: what you have, what the AI found, and how well it is answering."
        actions={
          <>
            <LinkButton to="/chat" icon="chat">
              Ask a question
            </LinkButton>
            <LinkButton to="/upload" variant="primary" icon="upload">
              Upload
            </LinkButton>
          </>
        }
      />

      {ovError ? (
        <Banner tone="info" className="mb-6" title="Workspace analytics unavailable">
          {ovError} Showing document-level statistics only.
        </Banner>
      ) : null}

      <section aria-label="Key metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {kpis.map((k) => (
          <Stat key={k.label} label={k.label} value={k.value} icon={k.icon} tone={k.tone} hint={k.hint} loading={kpiLoading} />
        ))}
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader icon="layers" title="Document types" description="Auto-classified on upload" />
          <CardBody>
            {docsLoading && ovLoading ? (
              <div className="space-y-3">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-6" />
                ))}
              </div>
            ) : docTypes.length === 0 ? (
              <p className="text-sm text-subtle">No documents classified yet.</p>
            ) : (
              <ul className="space-y-3">
                {docTypes.map(([type, n]) => (
                  <li key={type}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="truncate text-fg">{humanize(type)}</span>
                      <span className="tabular-nums text-muted">{n}</span>
                    </div>
                    <Meter value={n} max={maxType} tone="accent" label={`${humanize(type)}: ${n}`} />
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader icon="sparkles" title="Topic clusters" description="Unsupervised clustering of document content — click a topic to filter documents" />
          <CardBody>
            {ovLoading ? (
              <div className="flex flex-wrap gap-2">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-14 w-40" />
                ))}
              </div>
            ) : topics.length === 0 ? (
              <p className="text-sm text-subtle">Topics appear once a few documents have been indexed.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {topics.map((t) => {
                  const active = topic?.id === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => pickTopic(t)}
                      aria-pressed={active}
                      className={
                        active
                          ? 'rounded-xl border border-accent bg-accent/10 px-3 py-2 text-left'
                          : 'rounded-xl border border-line bg-surface px-3 py-2 text-left transition-colors hover:border-line-strong hover:bg-elevated'
                      }
                    >
                      <span className="flex items-center gap-2 text-sm font-medium text-fg">
                        {t.label}
                        <span className="rounded bg-elevated px-1 text-[10px] tabular-nums text-muted">{t.document_ids?.length ?? 0} docs</span>
                      </span>
                      <span className="mt-1 flex flex-wrap gap-1">
                        {(t.keywords ?? []).slice(0, 5).map((k) => (
                          <span key={k} className="text-[11px] text-subtle">
                            #{k}
                          </span>
                        ))}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            icon="activity"
            title="Recent queries"
            description="Latest questions with their evidence score and latency"
            actions={
              <Link to="/system" className="text-xs font-medium text-accent-soft hover:underline">
                Audit trail →
              </Link>
            }
          />
          {ovLoading ? (
            <div className="space-y-2 p-5">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-8" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <EmptyState icon="chat" title="No queries yet" description="Ask your first question in Chat." compact action={<LinkButton to="/chat" size="sm">Open chat</LinkButton>} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wider text-subtle">
                    <th scope="col" className="px-5 py-2.5 font-medium">
                      Query
                    </th>
                    <th scope="col" className="px-3 py-2.5 font-medium">
                      Evidence score
                    </th>
                    <th scope="col" className="hidden px-3 py-2.5 text-right font-medium sm:table-cell">
                      Latency
                    </th>
                    <th scope="col" className="hidden px-3 py-2.5 font-medium md:table-cell">
                      Provider
                    </th>
                    <th scope="col" className="px-5 py-2.5 font-medium">
                      When
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {recent.slice(0, 8).map((r, i) => (
                    <tr key={i} className="hover:bg-elevated/50">
                      <td className="max-w-[18rem] truncate px-5 py-2.5 text-fg" title={r.query}>
                        {r.query}
                      </td>
                      <td className="px-3 py-2.5">{r.confidence != null ? <ConfidenceBadge value={r.confidence} label="" /> : <span className="text-subtle">—</span>}</td>
                      <td className="hidden px-3 py-2.5 text-right tabular-nums text-muted sm:table-cell">{fmtMs(r.latency_ms)}</td>
                      <td className="hidden px-3 py-2.5 text-xs text-muted md:table-cell">{r.provider ?? '—'}</td>
                      <td className="whitespace-nowrap px-5 py-2.5 text-xs text-subtle" title={fullDate(r.created_at)}>
                        {relTime(r.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <UpcomingDates />
      </div>

      <div ref={docsRef} className="mt-6 scroll-mt-20">
        <DocumentTable
          documents={documents}
          loading={docsLoading}
          error={docsError}
          onDelete={(d) => void remove(d)}
          filterIds={topic?.document_ids ?? null}
          filterLabel={topic?.label}
          onClearFilter={() => setTopic(null)}
          emptyAction={
            <LinkButton to="/upload" variant="primary" size="sm" icon="upload">
              Upload documents
            </LinkButton>
          }
        />
      </div>
    </Page>
  );
}
