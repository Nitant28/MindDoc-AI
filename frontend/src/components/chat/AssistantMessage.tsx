import { useCallback, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { chatApi, errorMessage } from '../../api';
import { copyText } from '../../lib/clipboard';
import { cx } from '../../lib/cx';
import { fmtMs, isNum, pct, scoreTone, type Tone } from '../../lib/format';
import type { Citation, ClaimCheck, TraceStep } from '../../types';
import { LogoMark } from '../Logo';
import Markdown from '../Markdown';
import { ConfidenceBadge } from '../Signals';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Icon } from '../ui/Icon';
import { Spinner } from '../ui/Spinner';
import { useToast } from '../ui/Toast';
import PageViewer, { isPageUnavailable, useUnavailablePages } from './PageViewer';
import type { UiMessage } from './types';

const SOURCES_PREVIEW = 4;

interface AssistantMessageProps {
  message: UiMessage;
  question?: string;
  onRetry?: () => void;
}

function shortHash(h: string): string {
  return h.replace(/^sha256[:-]?/i, '').slice(0, 12);
}

function Section({
  title,
  icon,
  count,
  open,
  onToggle,
  children,
  right,
}: {
  title: string;
  icon: 'trace' | 'check' | 'quote';
  count?: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
  right?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="rounded-lg border border-line bg-surface">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          aria-controls={id}
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-xs font-medium text-muted hover:text-fg"
        >
          <Icon name="chevron-right" className={cx('h-3.5 w-3.5 transition-transform', open && 'rotate-90')} />
          <Icon name={icon} className="h-3.5 w-3.5 text-subtle" />
          <span className="truncate">{title}</span>
          {count ? <span className="font-normal text-subtle">{count}</span> : null}
        </button>
        {right}
      </div>
      {open ? (
        <div id={id} className="border-t border-line px-3 py-3">
          {children}
        </div>
      ) : null}
    </div>
  );
}

function TraceTimeline({ steps, subQueries }: { steps: TraceStep[]; subQueries: string[] }) {
  const max = Math.max(1, ...steps.map((s) => (isNum(s.ms) ? s.ms : 0)));
  return (
    <div className="space-y-3">
      {subQueries.length > 0 ? (
        <div>
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-subtle">Query decomposition</p>
          <div className="flex flex-wrap gap-1.5">
            {subQueries.map((q, i) => (
              <Badge key={i} tone="accent" className="whitespace-normal text-left">
                {q}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
      {steps.length > 0 ? (
        <ol className="ml-1.5 space-y-2.5 border-l border-line pl-4">
          {steps.map((s, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[22px] top-1 h-2.5 w-2.5 rounded-full border-2 border-surface bg-accent" aria-hidden="true" />
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-mono text-xs font-medium text-fg">{s.step}</span>
                <span className="shrink-0 font-mono text-[11px] tabular-nums text-subtle">{isNum(s.ms) ? fmtMs(s.ms) : ''}</span>
              </div>
              {s.detail ? <p className="mt-0.5 text-xs leading-relaxed text-muted">{s.detail}</p> : null}
              {isNum(s.ms) ? (
                <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-elevated" aria-hidden="true">
                  <div className="h-full rounded-full bg-accent/60" style={{ width: `${Math.max(2, (s.ms / max) * 100)}%` }} />
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-xs text-subtle">No trace recorded for this answer.</p>
      )}
    </div>
  );
}

function claimTone(c: ClaimCheck): Tone {
  if (!c.supported) return 'danger';
  return c.needs_review ? 'warning' : 'success';
}

const ISSUE_LABEL: Record<string, string> = {
  number: 'Number',
  date: 'Date',
  identifier: 'ID',
  frequency: 'Period',
  negation: 'Negation',
  direction: 'Direction',
  party: 'Party',
  roles: 'Roles',
  unsupported_content: 'Not in source',
  nli: 'NLI model',
};

function ClaimList({ claims, onCitation }: { claims: ClaimCheck[]; onCitation: (n: number) => void }) {
  return (
    <ul className="space-y-2">
      {claims.map((c, i) => {
        const tone = claimTone(c);
        return (
          <li key={i} className="flex items-start gap-2.5">
            <span
              className={cx(
                'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full',
                tone === 'success' ? 'bg-emerald-500/15 text-emerald-500' : tone === 'warning' ? 'bg-amber-500/15 text-amber-500' : 'bg-rose-500/15 text-rose-500',
              )}
            >
              <Icon name={tone === 'success' ? 'check' : 'alert'} className="h-2.5 w-2.5" strokeWidth={2.5} />
              <span className="sr-only">{!c.supported ? 'Contradicts the source' : c.needs_review ? 'Check wording' : 'Consistent'}</span>
            </span>
            <div className="min-w-0 flex-1">
              <p className={cx('text-xs leading-relaxed', tone === 'success' ? 'text-fg/90' : 'text-fg')}>{c.text}</p>
              {tone !== 'success' && (c.issues ?? []).length > 0 ? (
                <ul className="mt-1 space-y-0.5">
                  {(c.issues ?? []).map((iss, j) => (
                    <li
                      key={j}
                      className={cx(
                        'text-[11px] leading-snug',
                        iss.severity === 'review' ? 'text-amber-700 dark:text-amber-300' : 'text-rose-700 dark:text-rose-300',
                      )}
                    >
                      <span className="font-semibold">
                        {iss.severity === 'review' ? 'Check wording · ' : ''}
                        {ISSUE_LABEL[iss.kind] ?? iss.kind}:
                      </span>{' '}
                      {iss.detail}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {isNum(c.score) ? (
                  <Badge tone={c.supported ? 'neutral' : tone} title="Similarity to the best-matching source sentence (relevance, not correctness)">
                    {pct(c.score)} similar
                  </Badge>
                ) : null}
                {(c.sources ?? []).map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => onCitation(n)}
                    className="rounded bg-accent/15 px-1.5 font-mono text-[10px] font-semibold leading-4 text-accent-soft hover:bg-accent hover:text-white"
                    aria-label={`Show source ${n}`}
                  >
                    [{n}]
                  </button>
                ))}
                {!c.supported && !(c.sources ?? []).length ? <span className="text-[11px] text-subtle">No supporting source found</span> : null}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default function AssistantMessage({ message, question, onRetry }: AssistantMessageProps) {
  const toast = useToast();
  const meta = message.meta ?? null;
  const streaming = message.status === 'streaming';
  useUnavailablePages();

  const citations = useMemo<Citation[]>(
    () => (meta?.citations ?? []).map((c, i) => ({ ...c, index: isNum(c.index) ? c.index : i + 1 })),
    [meta],
  );
  const citationIndices = useMemo(() => citations.map((c) => c.index), [citations]);
  const g = meta?.groundedness ?? null;
  const claims = g?.claims ?? [];
  const unsupported = g?.unsupported ?? [];
  const trace = meta?.trace?.length ? meta.trace : message.liveTrace ?? [];
  const subQueries = meta?.sub_queries ?? [];
  const totalMs = trace.reduce((s, t) => s + (isNum(t.ms) ? t.ms : 0), 0);

  const [active, setActive] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [claimsOpen, setClaimsOpen] = useState<boolean | null>(null);
  const [viewing, setViewing] = useState<Citation | null>(null);
  const [saving, setSaving] = useState(false);
  const refs = useRef(new Map<number, HTMLLIElement>());
  const timer = useRef<number | undefined>(undefined);

  const onCitation = useCallback(
    (n: number) => {
      const pos = citations.findIndex((c) => c.index === n);
      if (pos < 0) return;
      if (pos >= SOURCES_PREVIEW) setShowAll(true);
      setActive(n);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setActive(null), 2600);
      window.setTimeout(() => refs.current.get(n)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 40);
    },
    [citations],
  );

  const copy = async () => {
    if (await copyText(message.content)) toast.success('Answer copied');
    else toast.error('Copy failed');
  };

  const save = async () => {
    setSaving(true);
    try {
      await chatApi.saveResponse((question ?? 'Saved response').slice(0, 120), message.content);
      toast.success('Response saved', 'Find it under Settings → Saved items.');
    } catch (e) {
      toast.error('Save failed', errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const copyHash = async (hash: string) => {
    if (await copyText(hash)) toast.success('Prompt hash copied', hash);
    else toast.error('Copy failed');
  };

  // Claim-check badge. The v2.1 verifier compares numbers, dates, IDs, periods and party names with the cited
  // source (red = contradicts); negation/direction/role heuristics only ask for review (amber). Passing means "no
  // inconsistency found", not "verified true" — measured rates are in benchmarks/reports/HALLUCINATION_BENCHMARK.md.
  const checks = g?.checks ?? [];
  const checkList = checks.length ? checks.join(', ') : 'similarity';
  const reviewCount = g?.review ?? claims.filter((c) => c.supported && c.needs_review).length;
  let groundBadge: { tone: Tone; label: string } | null = null;
  if (meta?.grounded === true) groundBadge = { tone: 'success', label: 'No inconsistencies found' };
  else if (meta?.grounded === false) {
    const r = g && g.total > 0 ? g.supported / g.total : 0;
    groundBadge = { tone: r >= 0.5 ? 'warning' : 'danger', label: r > 0 ? 'Some claims not supported' : 'Claims not supported' };
  }
  const groundRatio = g && g.total > 0 ? ` ${g.supported}/${g.total}` : '';
  const claimsExpanded = claimsOpen ?? (claims.some((c) => !c.supported) || (claims.length === 0 && unsupported.length > 0));
  const visibleSources = showAll ? citations : citations.slice(0, SOURCES_PREVIEW);
  const done = message.status === 'done' || message.status === 'stopped';

  return (
    <article className="group/msg flex gap-3" aria-label="Assistant answer" aria-busy={streaming || undefined}>
      <LogoMark size={26} className="mt-0.5 hidden sm:block" />
      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-fg">MindDoc</span>
          {message.mode === 'deep' ? (
            <Badge tone="accent" icon="brain">
              Deep
            </Badge>
          ) : null}
          {message.fallback ? (
            <Badge tone="neutral" title="Streaming was unavailable; answered via POST /chat/query">
              Non-streaming
            </Badge>
          ) : null}
          {message.status === 'stopped' ? <Badge tone="neutral">Stopped</Badge> : null}
          {streaming ? (
            <span className="inline-flex items-center gap-1.5 text-subtle" aria-live="polite">
              <Spinner size="xs" className="text-accent" />
              {message.content ? 'Generating' : 'Thinking'}
            </span>
          ) : null}
        </div>

        {message.status === 'error' ? (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/[0.06] p-3 text-sm" role="alert">
            <p className="font-medium text-rose-700 dark:text-rose-300">The answer could not be generated.</p>
            <p className="mt-0.5 text-xs text-rose-700/80 dark:text-rose-300/80">{message.error}</p>
            {onRetry ? (
              <Button size="xs" variant="secondary" className="mt-2" icon="refresh" onClick={onRetry}>
                Retry
              </Button>
            ) : null}
          </div>
        ) : null}

        {streaming && (message.liveTrace?.length || !message.content) ? (
          <ul className="space-y-1 rounded-lg border border-dashed border-line px-3 py-2 text-xs" aria-label="Live pipeline trace">
            {(message.liveTrace ?? []).map((s, i) => (
              <li key={i} className="flex items-center gap-2 text-muted">
                <Icon name="check" className="h-3 w-3 text-emerald-500" strokeWidth={2.5} />
                <span className="font-mono text-fg/80">{s.step}</span>
                {s.detail ? <span className="min-w-0 truncate text-subtle">{s.detail}</span> : null}
                <span className="ml-auto shrink-0 font-mono tabular-nums text-subtle">{isNum(s.ms) ? fmtMs(s.ms) : ''}</span>
              </li>
            ))}
            <li className="flex items-center gap-2 text-subtle">
              <Spinner size="xs" className="text-accent" />
              {message.content ? 'Generating answer…' : (message.liveTrace?.length ?? 0) > 0 ? 'Working…' : 'Retrieving evidence…'}
            </li>
          </ul>
        ) : null}

        {message.content ? (
          <div>
            <Markdown text={message.content} citations={streaming ? undefined : citationIndices} onCitation={onCitation} />
            {streaming ? <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-blink bg-accent" aria-hidden="true" /> : null}
          </div>
        ) : null}

        {done && meta ? (
          <>
            {(isNum(meta.confidence) || groundBadge || meta.abstained) && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span title="Uncalibrated score combining retrieval strength and the claim check — not a probability of correctness.">
                  <ConfidenceBadge value={meta.confidence} label="Evidence score" />
                </span>
                {groundBadge ? (
                  <Badge
                    tone={groundBadge.tone}
                    icon={groundBadge.tone === 'success' ? 'check' : 'alert'}
                    title={
                      unsupported.length
                        ? `Not supported: ${unsupported.join(' | ')}`
                        : `Every sentence passed the checks against its cited source (${checkList}). Heuristic checks: no inconsistency found, not proof of truth.`
                    }
                  >
                    {groundBadge.label}
                    {groundRatio}
                  </Badge>
                ) : null}
                {meta.abstained ? (
                  <Badge tone="warning" icon="info" title="The model declined to answer because the sources do not contain sufficient evidence.">
                    Abstained — not enough evidence
                  </Badge>
                ) : null}
                {subQueries.length > 0 ? <Badge tone="neutral">{subQueries.length} sub-queries</Badge> : null}
              </div>
            )}

            {claims.length > 0 || unsupported.length > 0 ? (
              <Section
                title={`Claim check (${checkList})`}
                icon="check"
                count={
                  claims.length
                    ? `${claims.filter((c) => c.supported).length}/${claims.length} consistent${reviewCount ? ` · ${reviewCount} to check` : ''}`
                    : `${unsupported.length} not supported`
                }
                open={claimsExpanded}
                onToggle={() => setClaimsOpen(!claimsExpanded)}
              >
                {claims.length > 0 ? (
                  <ClaimList claims={claims} onCitation={onCitation} />
                ) : (
                  <ul className="space-y-1.5">
                    {unsupported.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-fg/90">
                        <Icon name="alert" className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </Section>
            ) : null}

            {citations.length > 0 ? (
              <div>
                <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-subtle">
                  <Icon name="quote" className="h-3 w-3" /> Sources ({citations.length})
                </p>
                <ol className="grid gap-2 sm:grid-cols-2">
                  {visibleSources.map((c) => {
                    const canView = c.document_id != null && isNum(c.page) && !isPageUnavailable(c);
                    return (
                      <li
                        key={c.index}
                        ref={(el) => {
                          if (el) refs.current.set(c.index, el);
                          else refs.current.delete(c.index);
                        }}
                        className={cx(
                          'flex flex-col rounded-lg border p-3 transition-all duration-300',
                          active === c.index ? 'border-accent bg-accent/[0.06] ring-2 ring-accent/30' : 'border-line bg-surface',
                        )}
                      >
                        <div className="flex items-center gap-2 text-xs">
                          <span className="flex h-5 min-w-[1.25rem] items-center justify-center rounded bg-accent/15 px-1 font-mono text-[10px] font-semibold text-accent-soft">
                            {c.index}
                          </span>
                          {c.document_id != null ? (
                            <Link to={`/documents/${c.document_id}`} className="min-w-0 truncate font-medium text-fg hover:underline" title={c.filename ?? undefined}>
                              {c.filename ?? `Document #${c.document_id}`}
                            </Link>
                          ) : (
                            <span className="min-w-0 truncate font-medium text-fg">{c.filename ?? 'Source'}</span>
                          )}
                          {isNum(c.page) ? <span className="shrink-0 text-subtle">p. {c.page}</span> : null}
                          {isNum(c.score) ? (
                            <span className={cx('ml-auto shrink-0 font-mono tabular-nums', scoreTone(c.score, 0.6, 0.35) === 'success' ? 'text-emerald-500' : 'text-subtle')} title="Retrieval relevance score">
                              {c.score.toFixed(2)}
                            </span>
                          ) : null}
                        </div>
                        {c.snippet ? <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-muted">{c.snippet}</p> : null}
                        {canView ? (
                          <div className="mt-2">
                            <Button size="xs" variant="ghost" icon="eye" className="-ml-2" onClick={() => setViewing(c)}>
                              View on page
                            </Button>
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </ol>
                {citations.length > SOURCES_PREVIEW ? (
                  <Button size="xs" variant="ghost" className="mt-1.5" onClick={() => setShowAll((v) => !v)}>
                    {showAll ? 'Show fewer sources' : `Show all ${citations.length} sources`}
                  </Button>
                ) : null}
              </div>
            ) : null}

            {trace.length > 0 || subQueries.length > 0 ? (
              <Section
                title="Reasoning trace"
                icon="trace"
                count={`${trace.length} steps${totalMs ? ` · ${fmtMs(totalMs)}` : ''}`}
                open={traceOpen}
                onToggle={() => setTraceOpen((v) => !v)}
              >
                <TraceTimeline steps={trace} subQueries={subQueries} />
              </Section>
            ) : null}
          </>
        ) : null}

        {done && message.content ? (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
            <p className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px] text-subtle">
              {meta?.provider ? <span>{meta.provider}</span> : null}
              {meta?.model ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="font-mono">{meta.model}</span>
                </>
              ) : null}
              {isNum(meta?.latency_ms) ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{fmtMs(meta?.latency_ms)}</span>
                </>
              ) : null}
              {meta?.prompt_hash ? (
                <>
                  <span aria-hidden="true">·</span>
                  <button
                    type="button"
                    onClick={() => copyHash(meta.prompt_hash as string)}
                    title={`Prompt hash (provenance): ${meta.prompt_hash}. Click to copy.`}
                    aria-label="Copy prompt hash"
                    className="inline-flex items-center gap-1 rounded px-1 font-mono hover:bg-elevated hover:text-fg"
                  >
                    <Icon name="fingerprint" className="h-3 w-3" />
                    {shortHash(meta.prompt_hash)}
                  </button>
                </>
              ) : null}
            </p>
            <div className="flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-60 sm:group-hover/msg:opacity-100 sm:focus-within:opacity-100">
              <Button size="xs" variant="ghost" icon="copy" onClick={copy}>
                Copy
              </Button>
              <Button size="xs" variant="ghost" icon="bookmark" onClick={save} loading={saving}>
                Save
              </Button>
            </div>
          </div>
        ) : null}
      </div>
      <PageViewer citation={viewing} onClose={() => setViewing(null)} />
    </article>
  );
}
