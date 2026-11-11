import { useEffect, useMemo, useState } from 'react';
import { documentsApi, errorMessage } from '../api';
import { formatMinor, type Tone } from '../lib/format';
import type { StatementAnalysis, StatementCheck, StatementTxn } from '../types';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Card, CardBody, CardHeader } from './ui/Card';
import { Modal } from './ui/Modal';
import { Spinner } from './ui/Spinner';
import { useToast } from './ui/Toast';

const STATUS: Record<string, { tone: Tone; label: string; help: string }> = {
  reconciled: { tone: 'success', label: 'Reconciled', help: 'Every row and the closing balance agree with the printed balances.' },
  reconciled_with_flags: {
    tone: 'info',
    label: 'Reconciled with flags',
    help: 'Balances agree, but some debit/credit directions were inferred from the balance movement.',
  },
  needs_review: { tone: 'warning', label: 'Needs review', help: 'Some rows do not reconcile. Check the flagged rows against the page.' },
  not_checkable: { tone: 'neutral', label: 'Not checkable', help: 'The statement has no running balances to reconcile against.' },
};

const HYPOTHESIS: Record<string, string> = {
  follows_previous_error: 'Knock-on effect of an earlier flagged row',
  direction_suspect: 'Debit/credit direction may be swapped',
  amount_ocr_suspect: 'Amount may be misread (one digit)',
  balance_ocr_suspect: 'Printed balance may be misread',
  missing_row_suspect: 'A transaction may be missing here',
  order_ambiguous: 'Same-day rows may be out of order',
};

function checkLabel(c: StatementCheck): string {
  if (c.scope === 'row') return `Row ${c.seq}`;
  if (c.scope === 'statement') return 'Closing balance';
  if (c.scope === 'opening') return 'Opening balance';
  return c.scope;
}

interface Inspect {
  txn: StatementTxn;
  url: string | null;
}

export default function StatementPanel({ documentId }: { documentId: number }) {
  const [data, setData] = useState<StatementAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const [inspect, setInspect] = useState<Inspect | null>(null);
  const toast = useToast();

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await documentsApi.statement(documentId));
    } catch (e) {
      setError(errorMessage(e, 'Statement analysis failed'));
    } finally {
      setLoading(false);
    }
  };

  const flaggedSeqs = useMemo(
    () => new Set((data?.checks ?? []).filter((c) => c.status === 'fail' && c.seq != null).map((c) => c.seq as number)),
    [data],
  );
  const txns = useMemo(
    () =>
      (data?.transactions ?? []).filter(
        (t) => !onlyFlagged || flaggedSeqs.has(t.seq) || t.direction_source === 'inferred_from_balance',
      ),
    [data, onlyFlagged, flaggedSeqs],
  );

  const open = (txn: StatementTxn) => {
    if (!txn.box) {
      toast.info('No source position', 'This row has no recorded position on the page.');
      return;
    }
    setInspect({ txn, url: null });
    documentsApi
      .pageImage(documentId, txn.page, null, txn.box)
      .then((res) => {
        setInspect((cur) => {
          if (cur && cur.txn.seq === txn.seq) return { txn, url: res.url };
          URL.revokeObjectURL(res.url);
          return cur;
        });
      })
      .catch((e) => {
        toast.error('Could not load page image', errorMessage(e));
        setInspect(null);
      });
  };

  useEffect(() => {
    const url = inspect?.url;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [inspect?.url]);

  const st = data?.status ? (STATUS[data.status] ?? { tone: 'neutral' as Tone, label: data.status, help: '' }) : null;
  const fails = (data?.checks ?? []).filter((c) => c.status === 'fail');
  const s = data?.summary;

  return (
    <Card>
      <CardHeader
        icon="table"
        title="Bank statement"
        description="Transactions and balance reconciliation from the PDF text layer. Values are shown as printed; nothing is corrected."
        actions={
          <Button size="sm" variant={data ? 'ghost' : 'primary'} icon={data ? 'refresh' : 'zap'} loading={loading} onClick={run}>
            {loading ? 'Analysing…' : data ? 'Re-run' : 'Analyse as bank statement'}
          </Button>
        }
      />
      <CardBody className="space-y-4">
        {error ? (
          <p className="text-xs text-rose-600 dark:text-rose-400" role="alert">
            {error}
          </p>
        ) : null}
        {!data && !loading && !error ? (
          <p className="text-xs text-muted">Run the statement engine to list transactions and check every running balance.</p>
        ) : null}
        {loading && !data ? (
          <div className="flex items-center gap-2 text-xs text-muted">
            <Spinner size="sm" /> Reading word positions and reconciling balances…
          </div>
        ) : null}

        {data && !data.is_statement ? (
          <div className="rounded-lg border border-line p-3 text-xs text-muted">
            <p className="font-medium text-fg">No statement table found.</p>
            <p className="mt-1">{(data.warnings ?? []).join('; ') || 'The engine did not find a date / amount / balance header.'}</p>
            <p className="mt-1">Scanned statements are not supported yet.</p>
          </div>
        ) : null}

        {data?.is_statement && s && st ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={st.tone} dot>
                {st.label}
              </Badge>
              <span className="text-xs text-muted">{st.help}</span>
            </div>

            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {(
                [
                  ['Opening', formatMinor(s.opening_minor)],
                  ['Closing', formatMinor(s.closing_minor)],
                  ['Transactions', String(s.transactions)],
                  ['Total debits', formatMinor(s.total_debit_minor)],
                  ['Total credits', formatMinor(s.total_credit_minor)],
                  ['Failed checks', String(s.failed_checks)],
                ] as Array<[string, string]>
              ).map(([label, value]) => (
                <div key={label} className="rounded-lg border border-line p-2.5">
                  <dt className="text-[11px] uppercase tracking-wider text-subtle">{label}</dt>
                  <dd className="mt-0.5 text-sm font-semibold tabular-nums text-fg">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="text-[11px] text-subtle">
              {data.currency ?? 'INR'} · {data.pages ?? '—'} page{data.pages === 1 ? '' : 's'}
              {data.header?.ifsc ? ` · IFSC ${data.header.ifsc}` : ''}
              {data.header?.account ? ` · A/c ${data.header.account}` : ''}
              {s.inferred_directions
                ? ` · ${s.inferred_directions} direction${s.inferred_directions === 1 ? '' : 's'} inferred from balances`
                : ''}
            </p>

            {fails.length ? (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-subtle">Checks that did not pass</h3>
                <ul className="space-y-2">
                  {fails.map((c, i) => (
                    <li key={`${c.scope}-${c.seq}-${i}`} className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-2.5 text-xs">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-fg">{checkLabel(c)}</span>
                        <span className="tabular-nums text-muted">
                          expected {formatMinor(c.expected_minor)} · printed {formatMinor(c.observed_minor)} · difference{' '}
                          {formatMinor(c.diff_minor)}
                        </span>
                        {c.seq != null ? (
                          <Button
                            size="xs"
                            variant="ghost"
                            icon="eye"
                            onClick={() => {
                              const t = data.transactions?.find((x) => x.seq === c.seq);
                              if (t) open(t);
                            }}
                          >
                            View on page
                          </Button>
                        ) : null}
                      </div>
                      {c.hypotheses.length ? (
                        <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-muted">
                          {c.hypotheses.map((h, j) => (
                            <li key={j}>
                              <span className="text-fg">{HYPOTHESIS[h.code] ?? h.code}</span>
                              {h.detail ? ` — ${h.detail}` : ''}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-subtle">
                  Hypotheses are possible explanations for a mismatch, not findings. Confirm each against the original page.
                </p>
              </div>
            ) : null}

            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-subtle">Transactions</h3>
              <Button
                size="xs"
                variant={onlyFlagged ? 'secondary' : 'ghost'}
                aria-pressed={onlyFlagged}
                onClick={() => setOnlyFlagged((v) => !v)}
              >
                Flagged only
              </Button>
            </div>
            <div className="max-h-[28rem] overflow-auto rounded-lg border border-line">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-elevated text-[11px] uppercase tracking-wider text-subtle">
                  <tr>
                    <th className="px-2 py-1.5 text-right">#</th>
                    <th className="px-2 py-1.5 text-left">Date</th>
                    <th className="px-2 py-1.5 text-left">Narration</th>
                    <th className="px-2 py-1.5 text-right">Debit</th>
                    <th className="px-2 py-1.5 text-right">Credit</th>
                    <th className="px-2 py-1.5 text-right">Balance</th>
                    <th className="px-2 py-1.5 text-right">Page</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {txns.map((t) => {
                    const flagged = flaggedSeqs.has(t.seq);
                    return (
                      <tr
                        key={t.seq}
                        tabIndex={0}
                        onClick={() => open(t)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            open(t);
                          }
                        }}
                        title="Show this row on the original page"
                        className={`cursor-pointer hover:bg-elevated/60 focus:bg-elevated/60 focus:outline-none ${flagged ? 'bg-amber-500/10' : ''}`}
                      >
                        <td className="px-2 py-1.5 text-right tabular-nums text-subtle">{t.seq}</td>
                        <td className="whitespace-nowrap px-2 py-1.5 tabular-nums">{t.date}</td>
                        <td className="max-w-[16rem] truncate px-2 py-1.5" title={t.narration}>
                          {t.narration || <span className="text-subtle">—</span>}
                          {t.direction_source === 'inferred_from_balance' ? (
                            <Badge tone="info" className="ml-1.5">
                              inferred
                            </Badge>
                          ) : null}
                        </td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{t.debit_minor ? formatMinor(t.debit_minor) : ''}</td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{t.credit_minor ? formatMinor(t.credit_minor) : ''}</td>
                        <td
                          className={`px-2 py-1.5 text-right tabular-nums ${flagged ? 'font-semibold text-amber-700 dark:text-amber-400' : ''}`}
                        >
                          {formatMinor(t.balance_minor)}
                        </td>
                        <td className="px-2 py-1.5 text-right tabular-nums text-subtle">{t.page}</td>
                      </tr>
                    );
                  })}
                  {txns.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-2 py-3 text-center text-subtle">
                        No flagged rows.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </CardBody>

      <Modal
        open={!!inspect}
        onClose={() => setInspect(null)}
        size="xl"
        title={inspect ? `Row ${inspect.txn.seq} · ${inspect.txn.date} · page ${inspect.txn.page}` : 'Source row'}
        description="The amber box marks where this transaction was read on the original page."
      >
        <div className="flex min-h-[50vh] items-start justify-center bg-elevated/50 p-3 sm:p-5">
          {!inspect?.url ? (
            <div className="flex h-[50vh] items-center justify-center text-muted">
              <Spinner size="lg" className="text-accent" label="Rendering page" />
            </div>
          ) : (
            <img
              src={inspect.url}
              alt={`Page ${inspect.txn.page} with transaction row ${inspect.txn.seq} highlighted`}
              className="max-w-full rounded-md border border-line bg-white shadow-lg"
            />
          )}
        </div>
      </Modal>
    </Card>
  );
}
