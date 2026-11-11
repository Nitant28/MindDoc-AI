import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { errorMessage, partiesApi } from '../api';
import ForceGraph, { type ForceGraphHandle } from '../components/ForceGraph';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Textarea } from '../components/ui/Field';
import { Modal } from '../components/ui/Modal';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { Spinner } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { formatMinor } from '../lib/format';
import { useTheme } from '../lib/theme';
import { useTitle } from '../lib/useTitle';
import type { FlowGraph, GraphEdge, GraphNode, PartyDetail, PartyReviewItem, PartySummary, ResolveResult } from '../types';

type Tab = 'review' | 'parties' | 'graph';

const SCHEME_LABEL: Record<string, string> = { PAN: 'PAN', GSTIN: 'GSTIN', UPI_VPA: 'UPI', ACCOUNT_IFSC: 'A/c' };
const LEVEL_TONE: Record<string, 'success' | 'info' | 'warning' | 'neutral'> = {
  exact: 'success',
  'same tokens': 'success',
  'truncated prefix': 'info',
  'jw>=0.95': 'info',
  'initial+surname': 'warning',
  'jw>=0.88': 'warning',
  other: 'neutral',
  missing: 'neutral',
};

function methodLabel(m: string): string {
  if (m === 'human') return 'Reviewer';
  if (m.startsWith('rule:')) return `Rule: same ${m.slice(5).toUpperCase()}`;
  return `Model (${m})`;
}

function Identifiers({ ids }: { ids: PartySummary['identifiers'] }) {
  if (!ids.length) return <span className="text-subtle">—</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {ids.map((i) => (
        <Badge key={`${i.scheme}:${i.value}`} tone="neutral" className="font-mono">
          {SCHEME_LABEL[i.scheme] ?? i.scheme} {i.value}
        </Badge>
      ))}
    </span>
  );
}

/** "Why linked": the evidence recorded with a merge or a review suggestion. */
function Evidence({ features, probability }: { features: Record<string, unknown>; probability: number | null }) {
  const splink = features.splink as { levels?: Record<string, string>; weights?: Record<string, number> } | undefined;
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
      {probability != null ? <Badge tone="accent">p = {probability.toFixed(3)}</Badge> : null}
      {typeof features.identifier === 'string' ? (
        <Badge tone="success">
          same {String(features.identifier).toUpperCase()} {typeof features.value === 'string' ? features.value : ''}
        </Badge>
      ) : null}
      {features.conflict ? <Badge tone="danger">conflict: {String(features.conflict)}</Badge> : null}
      {splink?.levels
        ? Object.entries(splink.levels)
            .filter(([, lvl]) => lvl !== 'missing')
            .map(([k, lvl]) => (
              <Badge key={k} tone={LEVEL_TONE[lvl] ?? 'neutral'} title={splink.weights?.[k] != null ? `match weight ${splink.weights[k]}` : undefined}>
                {k}: {lvl}
              </Badge>
            ))
        : null}
    </div>
  );
}

function PartyCard({ p }: { p: PartySummary | null }) {
  if (!p) return <div className="text-xs text-subtle">—</div>;
  return (
    <div className="min-w-0 space-y-1 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-fg">{p.name}</span>
        <Badge tone="neutral">{p.kind}</Badge>
      </div>
      {p.names.length > 1 ? <div className="truncate text-muted" title={p.names.join(' · ')}>also: {p.names.slice(1).join(' · ')}</div> : null}
      <Identifiers ids={p.identifiers} />
      <div className="tabular-nums text-muted">
        {p.transactions} txn · out {formatMinor(p.debit_minor)} · in {formatMinor(p.credit_minor)}
      </div>
    </div>
  );
}

interface Pending {
  title: string;
  confirm: string;
  danger?: boolean;
  conflict?: boolean;
  run: (reason: string, override: boolean) => Promise<void>;
}

export default function Parties() {
  useTitle('Parties');
  const toast = useToast();
  const { theme } = useTheme();
  const [tab, setTab] = useState<Tab>('review');
  const [parties, setParties] = useState<PartySummary[] | null>(null);
  const [reviews, setReviews] = useState<PartyReviewItem[] | null>(null);
  const [graph, setGraph] = useState<FlowGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [last, setLast] = useState<ResolveResult | null>(null);
  const [detail, setDetail] = useState<PartyDetail | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [reason, setReason] = useState('');
  const [override, setOverride] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const graphRef = useRef<ForceGraphHandle>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, r, g] = await Promise.all([partiesApi.list(), partiesApi.reviews(), partiesApi.graph()]);
      setParties(p);
      setReviews(r);
      setGraph(g);
    } catch (e) {
      toast.error('Could not load parties', errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const resolve = async () => {
    setRunning(true);
    try {
      const res = await partiesApi.resolve();
      setLast(res);
      toast.success('Resolution complete', `${res.auto_merges} automatic merges · ${res.review_items} for review`);
      await load();
    } catch (e) {
      toast.error('Resolution failed', errorMessage(e));
    } finally {
      setRunning(false);
    }
  };

  const openDetail = async (id: number) => {
    try {
      setDetail(await partiesApi.detail(id));
    } catch (e) {
      toast.error('Could not load party', errorMessage(e));
    }
  };

  const ask = (p: Pending) => {
    setReason('');
    setOverride(false);
    setPending(p);
  };

  const confirm = async () => {
    if (!pending) return;
    setBusy(true);
    try {
      await pending.run(reason.trim(), override);
      setPending(null);
      await load();
    } catch (e) {
      toast.error('Action failed', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const graphData = useMemo(() => {
    if (!graph) return { nodes: [] as GraphNode[], edges: [] as GraphEdge[] };
    const deg = new Map<string, number>();
    graph.edges.forEach((e) => {
      const v = e.out_minor + e.in_minor;
      deg.set(e.source, (deg.get(e.source) ?? 0) + v);
      deg.set(e.target, (deg.get(e.target) ?? 0) + v);
    });
    const nodes: GraphNode[] = graph.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type === 'account' ? 'MONEY' : n.kind === 'person' ? 'PERSON' : 'ORG',
      weight: Math.max(1, Math.log10(1 + (deg.get(n.id) ?? 0) / 100)),
      documents: n.document_id ? [n.document_id] : [],
    }));
    const edges: GraphEdge[] = graph.edges.map((e) => ({
      source: e.source,
      target: e.target,
      relation: e.out_minor && e.in_minor ? 'paid and received' : e.out_minor ? 'paid' : 'received',
      weight: Math.max(1, Math.log10(1 + (e.out_minor + e.in_minor) / 100)),
    }));
    return { nodes, edges };
  }, [graph]);

  const selectedEdges = useMemo(
    () => (graph && selected ? graph.edges.filter((e) => e.source === selected || e.target === selected) : []),
    [graph, selected],
  );
  const selectedNode = graph?.nodes.find((n) => n.id === selected) ?? null;
  const openReviews = reviews?.length ?? 0;

  return (
    <Page wide>
      <PageHeader
        title="Parties"
        description="Counterparties resolved across statements. Strong identifiers link automatically, uncertain pairs wait for you, and every merge can be undone."
        actions={
          <Button variant="primary" icon="zap" loading={running} onClick={resolve}>
            {running ? 'Resolving…' : 'Run resolution'}
          </Button>
        }
      />
      {last ? (
        <p className="mb-4 text-xs text-muted">
          Last run: {last.mentions_added} new mentions, {last.parties_created} new records, {last.auto_merges} automatic merges,{' '}
          {last.review_items} new review items{last.skipped_by_human_decision ? `, ${last.skipped_by_human_decision} pairs left as you decided` : ''} ·{' '}
          <span className="font-mono">{last.model}</span>
        </p>
      ) : null}

      <Segmented
        label="View"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'review', label: `Review queue${openReviews ? ` (${openReviews})` : ''}` },
          { value: 'parties', label: `Parties${parties ? ` (${parties.length})` : ''}` },
          { value: 'graph', label: 'Flow graph' },
        ]}
        className="mb-4"
      />

      {loading && !parties ? (
        <div className="flex items-center gap-2 text-sm text-muted">
          <Spinner size="sm" /> Loading…
        </div>
      ) : null}

      {tab === 'review' && reviews ? (
        reviews.length === 0 ? (
          <EmptyState
            icon="check"
            title="Nothing to review"
            description="Run resolution after analysing statements. Pairs the model is unsure about will appear here."
          />
        ) : (
          <div className="space-y-3">
            {reviews.map((r) => (
              <Card key={r.id}>
                <CardBody className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-medium text-fg">{r.reason}</span>
                    <Evidence features={r.features} probability={r.probability} />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <PartyCard p={r.a} />
                    <PartyCard p={r.b} />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="primary"
                      icon="check"
                      onClick={() =>
                        ask({
                          title: `Merge “${r.a?.name}” and “${r.b?.name}”?`,
                          confirm: 'Same party',
                          conflict: /PAN/.test(r.reason) || Boolean(r.features.conflict),
                          run: async (why, ov) => {
                            await partiesApi.decide(r.id, 'merge', why, ov);
                            toast.success('Merged', 'Recorded as a reversible identity event.');
                          },
                        })
                      }
                    >
                      Same party
                    </Button>
                    <Button
                      size="sm"
                      icon="x"
                      onClick={() =>
                        ask({
                          title: `Keep “${r.a?.name}” and “${r.b?.name}” separate?`,
                          confirm: 'Keep separate',
                          run: async (why) => {
                            await partiesApi.decide(r.id, 'keep_separate', why);
                            toast.success('Kept separate', 'Automatic runs will not merge this pair.');
                          },
                        })
                      }
                    >
                      Keep separate
                    </Button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )
      ) : null}

      {tab === 'parties' && parties ? (
        parties.length === 0 ? (
          <EmptyState icon="user" title="No parties yet" description="Analyse a bank statement, then run resolution." />
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-elevated text-[11px] uppercase tracking-wider text-subtle">
                  <tr>
                    <th className="px-3 py-2 text-left">Party</th>
                    <th className="px-3 py-2 text-left">Identifiers</th>
                    <th className="px-3 py-2 text-right">Records</th>
                    <th className="px-3 py-2 text-right">Txns</th>
                    <th className="px-3 py-2 text-right">Paid out</th>
                    <th className="px-3 py-2 text-right">Received</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {parties.map((p) => (
                    <tr key={p.party_id} className="cursor-pointer hover:bg-elevated/60" onClick={() => void openDetail(p.party_id)}>
                      <td className="px-3 py-2">
                        <div className="font-medium text-fg">{p.name}</div>
                        {p.names.length > 1 ? <div className="text-subtle">{p.names.length} name variants</div> : null}
                      </td>
                      <td className="px-3 py-2">
                        <Identifiers ids={p.identifiers} />
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">{p.records}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{p.transactions}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{p.debit_minor ? formatMinor(p.debit_minor) : ''}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{p.credit_minor ? formatMinor(p.credit_minor) : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )
      ) : null}

      {tab === 'graph' && graph ? (
        graph.edges.length === 0 ? (
          <EmptyState icon="graph" title="No flows yet" description="Run resolution after analysing statements." />
        ) : (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <Card className="h-[32rem] overflow-hidden">
              <ForceGraph
                ref={graphRef}
                nodes={graphData.nodes}
                edges={graphData.edges}
                selectedId={selected}
                onSelect={setSelected}
                dark={theme === 'dark'}
                showLabels
                className="h-full w-full"
              />
            </Card>
            <Card>
              <CardHeader icon="layers" title={selectedNode ? selectedNode.label : 'Select a node'} description="Each edge lists the transactions behind it." />
              <CardBody className="space-y-3 text-xs">
                {selectedNode?.party_id ? (
                  <Button size="xs" onClick={() => void openDetail(selectedNode.party_id as number)}>
                    Open party
                  </Button>
                ) : null}
                {selectedEdges.map((e) => {
                  const other = graph.nodes.find((n) => n.id === (e.source === selected ? e.target : e.source));
                  return (
                    <div key={`${e.source}-${e.target}`} className="rounded-lg border border-line p-2">
                      <div className="font-medium text-fg">{other?.label}</div>
                      <div className="tabular-nums text-muted">
                        out {formatMinor(e.out_minor)} · in {formatMinor(e.in_minor)} · {e.transactions.length} txn
                      </div>
                      {other?.document_id || selectedNode?.document_id ? (
                        <Link className="text-accent underline" to={`/documents/${other?.document_id ?? selectedNode?.document_id}`}>
                          Open statement
                        </Link>
                      ) : null}
                    </div>
                  );
                })}
              </CardBody>
            </Card>
          </div>
        )
      ) : null}

      <Modal
        open={!!detail}
        onClose={() => setDetail(null)}
        size="xl"
        title={detail ? detail.name : 'Party'}
        description={detail ? `${detail.records} record(s) · ${detail.transactions} transaction(s)` : undefined}
      >
        {detail ? (
          <div className="space-y-4 p-4 text-xs sm:p-5">
            <Identifiers ids={detail.identifiers} />
            {detail.names.length > 1 ? <p className="text-muted">Printed as: {detail.names.join(' · ')}</p> : null}
            <div>
              <h3 className="mb-1.5 font-semibold uppercase tracking-wider text-subtle">Why these records are one party</h3>
              {detail.events.length === 0 ? <p className="text-muted">A single record — nothing merged.</p> : null}
              <ul className="space-y-2">
                {detail.events.map((e) => (
                  <li key={e.id} className="rounded-lg border border-line p-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={e.kind === 'merge' ? (e.reversed ? 'neutral' : 'success') : 'warning'}>
                        {e.kind}
                        {e.reversed ? ' (undone)' : ''}
                      </Badge>
                      <span className="text-fg">
                        {e.a.name} ↔ {e.b.name}
                      </span>
                      <span className="text-subtle">
                        {methodLabel(e.method)} · {new Date(e.decided_at).toLocaleString()}
                      </span>
                      {e.kind === 'merge' && !e.reversed ? (
                        <Button
                          size="xs"
                          variant="ghost"
                          icon="refresh"
                          onClick={() =>
                            ask({
                              title: `Undo the merge of “${e.a.name}” and “${e.b.name}”?`,
                              confirm: 'Undo merge',
                              danger: true,
                              run: async (why) => {
                                const res = await partiesApi.unmerge(e.id, why);
                                toast.success(
                                  'Merge undone',
                                  res.still_connected ? 'They are still linked through other merges.' : 'Automatic runs will not redo it.',
                                );
                                setDetail(await partiesApi.detail(e.a.id));
                              },
                            })
                          }
                        >
                          Undo
                        </Button>
                      ) : null}
                    </div>
                    <p className="mt-1 text-muted">{e.reason}</p>
                    <div className="mt-1">
                      <Evidence features={e.features} probability={e.probability} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-1.5 font-semibold uppercase tracking-wider text-subtle">Transactions</h3>
              <div className="max-h-72 overflow-auto rounded-lg border border-line">
                <table className="w-full">
                  <tbody className="divide-y divide-line">
                    {detail.mentions.map((m) => (
                      <tr key={`${m.source_type}-${m.source_id}`}>
                        <td className="whitespace-nowrap px-2 py-1.5 tabular-nums">{m.date ?? '—'}</td>
                        <td className="max-w-[18rem] truncate px-2 py-1.5" title={m.text ?? ''}>
                          {m.text}
                        </td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{m.debit_minor ? `−${formatMinor(m.debit_minor)}` : ''}</td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{m.credit_minor ? `+${formatMinor(m.credit_minor)}` : ''}</td>
                        <td className="px-2 py-1.5">
                          {m.document_id ? (
                            <Link className="text-accent underline" to={`/documents/${m.document_id}`} onClick={() => setDetail(null)}>
                              row {m.seq}
                            </Link>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        open={!!pending}
        onClose={() => (busy ? undefined : setPending(null))}
        title={pending?.title ?? ''}
        description="Your reason is stored with the decision in the identity log."
        footer={
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setPending(null)} disabled={busy}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant={pending?.danger ? 'danger' : 'primary'}
              loading={busy}
              disabled={reason.trim().length < 3 || (pending?.conflict && !override)}
              onClick={() => void confirm()}
            >
              {pending?.confirm}
            </Button>
          </div>
        }
      >
        <div className="space-y-3 p-4 sm:p-5">
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why? e.g. same GSTIN on the invoice, KYC shows different people…"
            rows={3}
            aria-label="Reason"
          />
          {pending?.conflict ? (
            <label className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400">
              <input type="checkbox" checked={override} onChange={(e) => setOverride(e.target.checked)} className="mt-0.5" />
              These records carry different PANs. I confirm they are the same party despite that.
            </label>
          ) : null}
        </div>
      </Modal>
    </Page>
  );
}
