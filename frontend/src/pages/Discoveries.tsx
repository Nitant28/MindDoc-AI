import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { discoveriesApi, errorMessage, findingsApi } from '../api';
import { useLayout } from '../components/Layout';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Field, Input, Textarea } from '../components/ui/Field';
import { Icon, type IconName } from '../components/ui/Icon';
import { Modal } from '../components/ui/Modal';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { cx } from '../lib/cx';
import { formatMinor, type Tone } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { DetectorInfo, DiscoveryDetail, DiscoveryList, DiscoveryStatus, DiscoverySummary } from '../types';

const ICONS: Record<string, IconName> = {
  end_use: 'target',
  round_trip: 'refresh',
  structuring: 'layers',
  pass_through: 'zap',
  duplicate_payment: 'copy',
  window_dressing: 'calendar',
};

const STATUS: Record<DiscoveryStatus, { label: string; tone: Tone }> = {
  open: { label: 'To review', tone: 'info' },
  confirmed: { label: 'Pursuing', tone: 'warning' },
  dismissed: { label: 'Dismissed', tone: 'neutral' },
};

function Detail({ id, onChanged }: { id: number; onChanged: () => void }) {
  const toast = useToast();
  const { currentCase } = useLayout();
  const [d, setD] = useState<DiscoveryDetail | null>(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [finding, setFinding] = useState<{ title: string; statement: string } | null>(null);

  useEffect(() => {
    setD(null);
    setReason('');
    discoveriesApi.get(id).then(setD).catch((e) => toast.error('Could not open the lead', errorMessage(e)));
  }, [id, toast]);

  const canAct = currentCase?.my_role != null && currentCase.my_role !== 'viewer';
  const claimIds = useMemo(() => Array.from(new Set((d?.transactions ?? []).map((t) => t.claim_id).filter((x): x is number => x != null))), [d]);

  const dispose = async (status: DiscoveryStatus) => {
    setBusy(true);
    try {
      setD(await discoveriesApi.dispose(id, status, reason));
      setReason('');
      toast.success(status === 'open' ? 'Back to review' : status === 'confirmed' ? 'Marked to pursue' : 'Dismissed');
      onChanged();
    } catch (e) {
      toast.error('Not saved', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const createFinding = async () => {
    if (!finding) return;
    setBusy(true);
    try {
      const f = await findingsApi.create(finding.title, finding.statement, claimIds.map((c) => ({ claim_id: c })));
      toast.success('Finding drafted', `Version ${f.version} with ${f.support.length} claim(s); it needs approval.`);
      setFinding(null);
    } catch (e) {
      toast.error('Finding not created', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!d) {
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    );
  }
  const path = Array.isArray(d.details.path) ? (d.details.path as Array<Record<string, unknown>>) : null;

  return (
    <div className="space-y-6 p-6">
      <div>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge tone={STATUS[d.status].tone}>{STATUS[d.status].label}</Badge>
          {!d.still_detected ? <Badge tone="neutral">no longer detected</Badge> : null}
          <span className="text-xs text-subtle">
            {d.detector} · {d.detector_version} · first seen {new Date(d.first_seen_at).toLocaleDateString()}
          </span>
        </div>
        <h2 className="text-[22px] font-normal leading-snug text-fg">{d.title}</h2>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">{d.summary}</p>
        <p className="mt-2 text-xs text-subtle">{d.description}</p>
      </div>

      {path ? (
        <div className="flex flex-wrap items-center gap-2 rounded-3xl bg-elevated p-4">
          {path.map((hop, i) => (
            <div key={i} className="flex items-center gap-2">
              {i === 0 ? <span className="rounded-full bg-surface px-3 py-1.5 text-sm font-medium text-fg">{String(hop.from_name)}</span> : null}
              <span className="flex flex-col items-center text-[11px] text-subtle">
                <span>{formatMinor(Number(hop.amount_minor))}</span>
                <Icon name="send" className="h-4 w-4 text-accent-soft" />
                <span>{String(hop.date)}</span>
              </span>
              <span className="rounded-full bg-surface px-3 py-1.5 text-sm font-medium text-fg">{String(hop.to_name)}</span>
            </div>
          ))}
        </div>
      ) : null}

      <section>
        <h3 className="mb-2 text-sm font-medium text-fg">Transactions behind this lead</h3>
        <div className="overflow-x-auto rounded-3xl border border-line">
          <table className="w-full text-sm">
            <thead className="bg-elevated text-left text-xs text-subtle">
              <tr>
                <th className="px-4 py-2.5 font-medium">Date</th>
                <th className="px-4 py-2.5 font-medium">Narration</th>
                <th className="px-4 py-2.5 text-right font-medium">Amount</th>
                <th className="px-4 py-2.5 font-medium">Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.transactions.map((t) => (
                <tr key={t.key} className="align-top">
                  <td className="whitespace-nowrap px-4 py-2.5 tabular-nums text-muted">{t.date}</td>
                  <td className="px-4 py-2.5">
                    <div className="max-w-[28rem] truncate text-fg" title={t.narration}>
                      {t.narration}
                    </div>
                    <div className="text-xs text-subtle">
                      {t.channel}
                      {t.counterparty_name ? ` · ${t.counterparty_name}` : ''}
                    </div>
                  </td>
                  <td className={cx('whitespace-nowrap px-4 py-2.5 text-right tabular-nums', t.direction === 'credit' ? 'text-emerald-700 dark:text-emerald-400' : 'text-fg')}>
                    {t.direction === 'credit' ? '+' : '−'}
                    {formatMinor(t.amount_minor)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <Link className="text-accent-soft hover:underline" to={`/documents/${t.document_id}?row=${t.seq ?? ''}`}>
                      row {t.seq}, p. {t.page}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-3xl border border-amber-500/30 bg-amber-500/[0.06] p-4">
        <h3 className="mb-1.5 flex items-center gap-2 text-sm font-medium text-amber-900 dark:text-amber-200">
          <Icon name="info" className="h-4 w-4" /> Rule out first
        </h3>
        <ul className="list-disc space-y-1 pl-6 text-sm text-amber-900/90 dark:text-amber-100/90">
          {d.rule_out.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-amber-900/70 dark:text-amber-100/70">A lead is a pattern for review, not a conclusion about anyone.</p>
      </section>

      {d.disposition_reason ? (
        <p className="text-sm text-muted">
          <span className="font-medium text-fg">Disposition:</span> {d.disposition_reason}
        </p>
      ) : null}

      {canAct ? (
        <section className="space-y-3">
          <Field label="Reason (required to pursue or dismiss)" htmlFor="disp-reason">
            <Textarea id="disp-reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. same amount came back within six days; no invoice on file" />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" icon="check" loading={busy} disabled={reason.trim().length < 3} onClick={() => void dispose('confirmed')}>
              Pursue
            </Button>
            <Button variant="secondary" loading={busy} disabled={reason.trim().length < 3} onClick={() => void dispose('dismissed')}>
              Dismiss as explained
            </Button>
            {d.status !== 'open' ? (
              <Button variant="ghost" loading={busy} onClick={() => void dispose('open')}>
                Reopen
              </Button>
            ) : null}
            <Button
              variant="tonal"
              icon="bookmark"
              disabled={claimIds.length === 0}
              title={claimIds.length === 0 ? 'No transfer claims behind these rows yet' : undefined}
              onClick={() => setFinding({ title: d.title, statement: d.summary })}
            >
              Draft a finding
            </Button>
          </div>
        </section>
      ) : null}

      <Modal open={finding != null} onClose={() => setFinding(null)} title="Draft a finding from this lead" size="md"
        description={`${claimIds.length} transfer claim(s) will be pinned as evidence. You write the finding; it needs a reviewer's approval.`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setFinding(null)}>Cancel</Button>
            <Button variant="primary" loading={busy} onClick={() => void createFinding()}>Create draft</Button>
          </>
        }
      >
        {finding ? (
          <div className="space-y-4 p-5">
            <Field label="Title" htmlFor="f-title">
              <Input id="f-title" value={finding.title} onChange={(e) => setFinding({ ...finding, title: e.target.value })} />
            </Field>
            <Field label="Your statement" htmlFor="f-statement" hint="State what the evidence shows, not intent.">
              <Textarea id="f-statement" rows={5} value={finding.statement} onChange={(e) => setFinding({ ...finding, statement: e.target.value })} />
            </Field>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

export default function Discoveries() {
  useTitle('Discoveries');
  const toast = useToast();
  const { currentCase } = useLayout();
  const [params, setParams] = useSearchParams();
  const [list, setList] = useState<DiscoveryList | null>(null);
  const [detectors, setDetectors] = useState<DetectorInfo[]>([]);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<DiscoveryStatus | 'all'>('open');
  const [detector, setDetector] = useState<string | null>(null);
  const selected = params.get('id') ? Number(params.get('id')) : null;

  const load = useCallback(async () => {
    try {
      setList(await discoveriesApi.list({ status: status === 'all' ? undefined : status, detector: detector ?? undefined }));
    } catch (e) {
      toast.error('Could not load discoveries', errorMessage(e));
    }
  }, [status, detector, toast]);

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    discoveriesApi.detectors().then((r) => setDetectors(r.detectors)).catch(() => setDetectors([]));
  }, []);

  const canRun = currentCase?.my_role != null && currentCase.my_role !== 'viewer';
  const run = useCallback(async () => {
    setRunning(true);
    try {
      const r = await discoveriesApi.run();
      toast.success(`${r.found} lead${r.found === 1 ? '' : 's'} found`, `${r.new} new · ${r.transactions} transactions checked`);
      await load();
    } catch (e) {
      toast.error('Detectors did not run', errorMessage(e));
    } finally {
      setRunning(false);
    }
  }, [load, toast]);

  useEffect(() => {
    if (params.get('run') === '1' && canRun) {
      params.delete('run');
      setParams(params, { replace: true });
      void run();
    }
  }, [params, setParams, run, canRun]);

  const titleOf = (id: string) => detectors.find((x) => x.id === id)?.title ?? id;
  const counts = list?.counts.by_detector ?? {};
  const byStatus = list?.counts.by_status ?? {};

  return (
    <Page wide>
      <PageHeader
        title="Discoveries"
        description="Patterns in this case's bank transactions that deserve a look: loan money reaching group parties, money going round in circles, cash kept just under reporting limits and more. Each one lists its transactions and what to rule out."
        actions={
          canRun ? (
            <Button variant="primary" icon="target" loading={running} onClick={() => void run()}>
              {list?.last_run ? 'Run again' : 'Run detectors'}
            </Button>
          ) : null
        }
      />

      <div className="mb-6 grid grid-cols-3 gap-2 sm:gap-3">
        {(['open', 'confirmed', 'dismissed'] as DiscoveryStatus[]).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatus(s)}
            className={cx(
              'rounded-3xl border p-3 text-left transition-colors sm:p-5',
              status === s ? 'border-transparent bg-accent-container text-accent-on-container' : 'border-line bg-surface hover:bg-fg/[0.03]',
            )}
          >
            <div className="text-2xl font-normal leading-none tabular-nums sm:text-[32px]">{byStatus[s] ?? 0}</div>
            <div className="mt-2 text-xs sm:text-sm">{STATUS[s].label}</div>
          </button>
        ))}
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => setDetector(null)} className={cx('h-8 rounded-lg border px-3 text-sm', detector == null ? 'border-transparent bg-accent-container text-accent-on-container' : 'border-line-strong text-muted hover:bg-fg/[0.04]')}>
          All patterns
        </button>
        {detectors.map((x) => (
          <button
            key={x.id}
            type="button"
            title={x.description}
            onClick={() => setDetector(detector === x.id ? null : x.id)}
            className={cx(
              'flex h-8 items-center gap-1.5 rounded-lg border px-3 text-sm',
              detector === x.id ? 'border-transparent bg-accent-container text-accent-on-container' : 'border-line-strong text-muted hover:bg-fg/[0.04]',
            )}
          >
            <Icon name={ICONS[x.id] ?? 'target'} className="h-4 w-4" />
            {x.title.split(' ').slice(0, 3).join(' ')}
            {counts[x.id] ? <span className="tabular-nums opacity-70">{counts[x.id]}</span> : null}
          </button>
        ))}
        <button type="button" onClick={() => setStatus('all')} className={cx('ml-auto h-8 rounded-lg px-3 text-sm', status === 'all' ? 'text-accent-soft' : 'text-subtle hover:text-fg')}>
          Show all statuses
        </button>
      </div>

      {list?.last_run ? (
        <p className="mb-4 text-xs text-subtle">
          Last run {new Date(list.last_run.started_at).toLocaleString()} · {list.last_run.transactions} transactions checked · detectors{' '}
          {Object.values(list.last_run.version)[0]}
          {list.no_longer_detected ? ` · ${list.no_longer_detected} earlier lead(s) no longer detected` : ''}
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="space-y-2">
          {list === null ? (
            [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 rounded-3xl" />)
          ) : list.discoveries.length === 0 ? (
            <Card>
              <EmptyState
                icon="target"
                title={list.last_run ? 'No leads here' : 'No detector run yet'}
                description={
                  list.last_run
                    ? 'Nothing matches these filters. Dismissed and pursued leads are under their own tabs.'
                    : 'Upload the case’s bank statements, then run the detectors. Parties are resolved first.'
                }
                action={canRun && !list.last_run ? <Button variant="primary" loading={running} onClick={() => void run()}>Run detectors</Button> : undefined}
              />
            </Card>
          ) : (
            list.discoveries.map((x: DiscoverySummary) => (
              <button
                key={x.id}
                type="button"
                onClick={() => setParams({ id: String(x.id) }, { replace: true })}
                className={cx(
                  'flex w-full gap-4 rounded-3xl border p-4 text-left transition-colors',
                  selected === x.id ? 'border-accent bg-accent/[0.05]' : 'border-line bg-surface hover:bg-fg/[0.03]',
                )}
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-container text-accent-on-container">
                  <Icon name={ICONS[x.detector] ?? 'target'} className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-start justify-between gap-3">
                    <span className="text-sm font-medium text-fg">{titleOf(x.detector)}</span>
                    <span className="shrink-0 text-sm tabular-nums text-fg">{formatMinor(x.amount_minor)}</span>
                  </span>
                  <span className="mt-1 line-clamp-2 block text-[13px] leading-snug text-muted">{x.summary}</span>
                  <span className="mt-2 flex items-center gap-2">
                    <Badge tone={STATUS[x.status].tone}>{STATUS[x.status].label}</Badge>
                    <span className="text-xs text-subtle">{x.transactions} transactions</span>
                    {!x.still_detected ? <Badge>no longer detected</Badge> : null}
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
        <Card className="min-h-[24rem] xl:sticky xl:top-20 xl:self-start">
          {selected ? (
            <Detail id={selected} onChanged={() => void load()} />
          ) : (
            <EmptyState icon="target" title="Select a lead" description="Its transactions, the path the money took and what to rule out appear here." />
          )}
        </Card>
      </div>
    </Page>
  );
}
