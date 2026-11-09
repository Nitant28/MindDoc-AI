import { useCallback, useEffect, useId, useState, type ReactNode } from 'react';
import { API_BASE_URL, errorMessage, intelApi } from '../api';
import { ConfidenceBadge } from '../components/Signals';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Select } from '../components/ui/Field';
import { Meter } from '../components/ui/Meter';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Spinner';
import { Stat } from '../components/ui/Stat';
import { useToast } from '../components/ui/Toast';
import { copyText } from '../lib/clipboard';
import { cx } from '../lib/cx';
import { fmtMs, fullDate, isNum, pct, relTime, scoreTone } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { AuditEntry, Capabilities, EvalResult } from '../types';

type Status = 'ok' | 'warn' | 'off';

function StatusDot({ status }: { status: Status }) {
  return (
    <span
      className={cx(
        'inline-block h-2 w-2 shrink-0 rounded-full',
        status === 'ok' ? 'bg-emerald-500 shadow-[0_0_0_3px] shadow-emerald-500/15' : status === 'warn' ? 'bg-amber-500' : 'bg-zinc-400 dark:bg-zinc-600',
      )}
      aria-hidden="true"
    />
  );
}

function StatusRow({ label, description, status, value }: { label: string; description?: string; status: Status; value: ReactNode }) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 sm:px-5">
      <div className="flex min-w-0 flex-1 items-center gap-2.5">
        <StatusDot status={status} />
        <div className="min-w-0">
          <p className="text-sm font-medium text-fg">{label}</p>
          {description ? <p className="text-xs text-subtle">{description}</p> : null}
        </div>
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-end gap-1.5 text-xs text-muted">{value}</div>
      <span className="sr-only">Status: {status === 'ok' ? 'available' : status === 'warn' ? 'degraded' : 'unavailable'}</span>
    </li>
  );
}

const truthy = (v: unknown): boolean => v === true || (typeof v === 'string' && v.length > 0 && v !== 'false');

function CompareBar({ label, value, highlight, hint }: { label: string; value?: number | null; highlight?: boolean; hint?: string }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className={cx('font-medium', highlight ? 'text-fg' : 'text-muted')}>
          {label}
          {hint ? <span className="ml-1.5 font-normal text-subtle">{hint}</span> : null}
        </span>
        <span className={cx('tabular-nums', highlight ? 'font-semibold text-fg' : 'text-muted')}>{pct(value, 1)}</span>
      </div>
      <Meter value={isNum(value) ? value : 0} tone={highlight ? 'accent' : 'neutral'} size="md" label={`${label} hit rate`} />
    </div>
  );
}

function shortHash(h?: string | null): string {
  return h ? h.replace(/^sha256[:-]?/i, '').slice(0, 10) : '—';
}

export default function System() {
  useTitle('Evaluation & System');
  const toast = useToast();
  const sampleId = useId();
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [capsError, setCapsError] = useState<string | null>(null);
  const [capsLoading, setCapsLoading] = useState(true);
  const [sample, setSample] = useState(20);
  const [evalRes, setEvalRes] = useState<EvalResult | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);

  const loadCaps = useCallback(async () => {
    setCapsLoading(true);
    setCapsError(null);
    try {
      setCaps(await intelApi.capabilities());
    } catch (e) {
      setCapsError(errorMessage(e, 'Capabilities unavailable'));
    } finally {
      setCapsLoading(false);
    }
  }, []);

  const loadAudit = useCallback(async () => {
    setAuditError(null);
    try {
      setAudit(await intelApi.audit(50));
    } catch (e) {
      setAudit([]);
      setAuditError(errorMessage(e, 'Audit trail unavailable'));
    }
  }, []);

  useEffect(() => {
    void loadCaps();
    void loadAudit();
  }, [loadCaps, loadAudit]);

  const runEval = async () => {
    setEvalLoading(true);
    try {
      const r = await intelApi.evaluate({ sample_size: sample });
      setEvalRes(r);
      toast.success('Evaluation complete', `${r.n} synthetic queries · hit@5 ${pct(r.hit_rate_at_5)}`);
    } catch (e) {
      toast.error('Evaluation failed', errorMessage(e));
    } finally {
      setEvalLoading(false);
    }
  };

  const providers = caps?.llm_providers ?? [];
  const embeddings = caps?.embeddings ?? null;
  const embedFallback = !!embeddings && /fallback|hashing/i.test(embeddings);
  const ocr = caps?.ocr_engines ?? [];
  const best = evalRes ? Math.max(evalRes.dense_only_hit_rate ?? 0, evalRes.bm25_only_hit_rate ?? 0) : 0;
  const lift = evalRes ? (evalRes.hit_rate_at_5 - best) * 100 : 0;

  return (
    <Page>
      <PageHeader
        title="Evaluation & system"
        description="What is powering the answers, how well retrieval performs, and a full audit trail of every query."
        actions={
          <Button icon="refresh" onClick={() => void Promise.all([loadCaps(), loadAudit()])} loading={capsLoading}>
            Refresh
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader icon="cpu" title="Capabilities" description={<span className="font-mono">{API_BASE_URL}</span>} />
          {capsLoading ? (
            <div className="space-y-2 p-5">
              {[0, 1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : capsError ? (
            <EmptyState icon="alert" title="Backend unreachable" description={capsError} compact action={<Button size="sm" onClick={() => void loadCaps()}>Retry</Button>} />
          ) : (
            <ul className="divide-y divide-line">
              {providers.length === 0 ? (
                <StatusRow label="LLM providers" status="off" value="None configured" />
              ) : (
                providers.map((p) => (
                  <StatusRow
                    key={p.name}
                    label={`LLM · ${p.name}`}
                    description={p.available ? 'Available' : 'Not configured / unreachable'}
                    status={p.available ? 'ok' : 'off'}
                    value={p.model ? <span className="font-mono">{p.model}</span> : '—'}
                  />
                ))
              )}
              <StatusRow
                label="Embeddings"
                description={embedFallback ? 'Offline fallback in use — semantic recall is reduced' : 'Dense vector encoder'}
                status={!embeddings ? 'off' : embedFallback ? 'warn' : 'ok'}
                value={<span className="max-w-[16rem] truncate font-mono" title={embeddings ?? undefined}>{embeddings ?? 'Unavailable'}</span>}
              />
              <StatusRow
                label="Cross-encoder re-ranker"
                description="Re-scores retrieved passages for precision"
                status={truthy(caps?.reranker) ? 'ok' : 'off'}
                value={typeof caps?.reranker === 'string' ? <span className="font-mono">{caps.reranker}</span> : truthy(caps?.reranker) ? 'Enabled' : 'Disabled'}
              />
              <StatusRow label="OpenCV" description="Image preprocessing & layout analysis" status={caps?.opencv ? 'ok' : 'off'} value={caps?.opencv ? 'Installed' : 'Not installed'} />
              <StatusRow
                label="OCR engines"
                description="Text recognition for scans & images"
                status={ocr.length ? 'ok' : 'off'}
                value={ocr.length ? ocr.map((o) => <Badge key={o}>{o}</Badge>) : 'None'}
              />
              <StatusRow
                label="Vision LLM"
                description="Multimodal captioning & page understanding"
                status={truthy(caps?.vision_llm) ? 'ok' : 'off'}
                value={typeof caps?.vision_llm === 'string' ? <span className="font-mono">{caps.vision_llm}</span> : truthy(caps?.vision_llm) ? 'Available' : 'Unavailable'}
              />
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader
            icon="target"
            title="Retrieval evaluation"
            description="Self-supervised: synthetic questions generated from random chunks"
            actions={
              <div className="flex items-center gap-2">
                <label htmlFor={sampleId} className="sr-only">
                  Sample size
                </label>
                <Select id={sampleId} value={sample} onChange={(e) => setSample(Number(e.target.value))} className="h-8 w-auto text-[13px]" disabled={evalLoading}>
                  {[10, 20, 50, 100].map((n) => (
                    <option key={n} value={n}>
                      {n} queries
                    </option>
                  ))}
                </Select>
                <Button variant="primary" size="sm" icon="activity" loading={evalLoading} onClick={runEval}>
                  {evalLoading ? 'Running…' : 'Run evaluation'}
                </Button>
              </div>
            }
          />
          <CardBody>
            {!evalRes ? (
              <EmptyState
                icon="activity"
                title={evalLoading ? 'Evaluating retrieval…' : 'No evaluation run yet'}
                description="Measures how often the chunk a question was generated from is retrieved in the top 5 (hit rate) and how high it ranks (MRR)."
                compact
              />
            ) : (
              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Stat label="Hit rate @5" value={pct(evalRes.hit_rate_at_5, 1)} tone={scoreTone(evalRes.hit_rate_at_5, 0.85, 0.6)} />
                  <Stat label="MRR" value={isNum(evalRes.mrr) ? evalRes.mrr.toFixed(3) : '—'} tone={scoreTone(evalRes.mrr, 0.7, 0.45)} />
                  <Stat label="Queries" value={String(evalRes.n)} />
                  <Stat label="Runtime" value={fmtMs(evalRes.ms)} />
                </div>
                <div className="space-y-3">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-subtle">Retriever comparison · hit rate @5</p>
                  <CompareBar label="Dense only" hint="embeddings" value={evalRes.dense_only_hit_rate} />
                  <CompareBar label="BM25 only" hint="lexical" value={evalRes.bm25_only_hit_rate} />
                  <CompareBar label="Hybrid" hint="BM25 + dense (production)" value={evalRes.hit_rate_at_5} highlight />
                </div>
                {isNum(evalRes.dense_only_hit_rate) || isNum(evalRes.bm25_only_hit_rate) ? (
                  <p className="text-xs text-muted">
                    Hybrid retrieval is{' '}
                    <span className={cx('font-semibold', lift >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400')}>
                      {lift >= 0 ? '+' : ''}
                      {lift.toFixed(1)} pts
                    </span>{' '}
                    versus the best single retriever on this sample.
                  </p>
                ) : null}
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader
          icon="fingerprint"
          title="Audit trail"
          description="Last 50 queries with provenance — every answer is reproducible from its prompt hash and chunk IDs"
          actions={
            <Button size="xs" variant="ghost" icon="refresh" onClick={() => void loadAudit()}>
              Reload
            </Button>
          }
        />
        {audit === null ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8" />
            ))}
          </div>
        ) : auditError ? (
          <EmptyState icon="alert" title="Audit trail unavailable" description={auditError} compact />
        ) : audit.length === 0 ? (
          <EmptyState icon="fingerprint" title="No queries logged yet" description="Ask a question in Chat and it will appear here." compact />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full whitespace-nowrap text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-wider text-subtle">
                  <th scope="col" className="px-5 py-2.5 font-medium">
                    Time
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Query
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Mode
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Provider / model
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right font-medium">
                    Latency
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Confidence
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Grounded
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right font-medium">
                    Citations
                  </th>
                  <th scope="col" className="px-5 py-2.5 font-medium">
                    Prompt hash
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {audit.map((a) => (
                  <tr key={a.id} className="hover:bg-elevated/50">
                    <td className="px-5 py-2.5 text-xs text-muted" title={fullDate(a.created_at)}>
                      {relTime(a.created_at)}
                    </td>
                    <td className="max-w-[18rem] truncate px-3 py-2.5 text-fg" title={a.query}>
                      {a.query}
                    </td>
                    <td className="px-3 py-2.5">{a.mode ? <Badge tone={a.mode === 'deep' ? 'accent' : 'neutral'}>{a.mode}</Badge> : <span className="text-subtle">—</span>}</td>
                    <td className="px-3 py-2.5 text-xs text-muted">
                      {a.provider ?? '—'}
                      {a.model ? <span className="ml-1 font-mono text-subtle">{a.model}</span> : null}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted">{fmtMs(a.latency_ms)}</td>
                    <td className="px-3 py-2.5">{isNum(a.confidence) ? <ConfidenceBadge value={a.confidence} label="" /> : <span className="text-subtle">—</span>}</td>
                    <td className="px-3 py-2.5">
                      {a.grounded === true ? (
                        <Badge tone="success" icon="check">
                          Yes
                        </Badge>
                      ) : a.grounded === false ? (
                        <Badge tone="warning" icon="alert">
                          No
                        </Badge>
                      ) : (
                        <span className="text-subtle">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted" title={a.chunk_ids?.length ? `Chunks: ${a.chunk_ids.join(', ')}` : undefined}>
                      {isNum(a.n_citations) ? a.n_citations : '—'}
                    </td>
                    <td className="px-5 py-2.5">
                      {a.prompt_hash ? (
                        <button
                          type="button"
                          onClick={async () => {
                            if (await copyText(a.prompt_hash ?? '')) toast.success('Prompt hash copied', a.prompt_hash ?? undefined);
                          }}
                          className="rounded px-1 font-mono text-xs text-muted hover:bg-elevated hover:text-fg"
                          title={`${a.prompt_hash} — click to copy`}
                          aria-label="Copy prompt hash"
                        >
                          {shortHash(a.prompt_hash)}
                        </button>
                      ) : (
                        <span className="text-subtle">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </Page>
  );
}
