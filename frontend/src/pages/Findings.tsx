import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { errorMessage, findingsApi, reportsApi } from '../api';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Field, Input } from '../components/ui/Field';
import { Modal } from '../components/ui/Modal';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Spinner } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { formatMinor, type Tone } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { DisclosureParty, DisclosureView, FindingStatus, FindingSummary, FindingView, ReportSummary, ReportView, Robustness } from '../types';

const STATUS_TONE: Record<FindingStatus, Tone> = { draft: 'neutral', proposed: 'info', approved: 'success', rejected: 'danger' };

/** The status moves a reviewer can make from each status (same rules as the server). */
const NEXT: Record<FindingStatus, Array<{ to: FindingStatus; label: string }>> = {
  draft: [{ to: 'proposed', label: 'Propose for approval' }],
  proposed: [
    { to: 'approved', label: 'Approve' },
    { to: 'rejected', label: 'Reject' },
    { to: 'draft', label: 'Back to draft' },
  ],
  approved: [{ to: 'draft', label: 'Back to draft' }],
  rejected: [{ to: 'draft', label: 'Back to draft' }],
};

function short(hash: string | null | undefined): string {
  return hash ? `${hash.slice(0, 10)}…` : '—';
}

function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** Which sources the finding stands or falls on (leave-one-source-out, exact lineage). */
function RobustnessPanel({ r }: { r: Robustness }) {
  const k = r.k_fragility;
  const tone = k == null ? 'danger' : k === 1 ? 'warning' : 'success';
  return (
    <div className="rounded-lg border border-line p-3">
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <h3 className="font-semibold uppercase tracking-wider text-subtle">Robustness</h3>
        <Badge tone={tone}>
          {k == null ? 'cannot be assessed' : k === 1 ? 'rests on one source' : `needs ${k} sources removed to fail`}
        </Badge>
        <span className="text-subtle">{r.method}</span>
      </div>
      <p className="text-muted">{r.explanation}</p>
      <ul className="mt-2 space-y-1">
        {Object.entries(r.sources).map(([label, docs]) => (
          <li key={label} className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-fg">{label}</span>
            {r.essential_sources.includes(label) ? <Badge tone="warning">essential</Badge> : null}
            <span className="text-subtle">responsibility {r.responsibility[label] ?? 0}</span>
            <span className="min-w-0 truncate text-muted">
              {docs.map((d) => d.filename ?? `document ${d.document_id}`).join(' + ')}
              {docs.length > 1 ? ' (copies of one source)' : ''}
            </span>
          </li>
        ))}
      </ul>
      {r.facts.some((f) => f.corroborated_by.length) ? (
        <p className="mt-2 text-muted">
          Corroborated: claim{' '}
          {r.facts
            .filter((f) => f.corroborated_by.length)
            .map((f) => `${f.claim_id} (also in ${f.corroborated_by.map((c) => c.source).join(', ')})`)
            .join(', ')}
          .
        </p>
      ) : null}
      {r.notes.map((n) => (
        <p key={n} className="mt-1 text-amber-700 dark:text-amber-300">
          {n}
        </p>
      ))}
    </div>
  );
}

function FindingDetail({ f, onChanged, onOpen }: { f: FindingView; onChanged: (f: FindingView) => void; onOpen: (id: number) => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const current = !f.superseded_at;

  const act = async (run: () => Promise<FindingView>, done: string) => {
    setBusy(true);
    try {
      onChanged(await run());
      setNote('');
      toast.success(done);
    } catch (e) {
      toast.error('Not saved', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={STATUS_TONE[f.status]}>{f.status}</Badge>
        <span className="text-subtle">
          version {f.version} · {new Date(f.created_at).toLocaleString()}
          {f.change_note ? ` · ${f.change_note}` : ''}
        </span>
        {!current ? <Badge tone="warning">superseded</Badge> : null}
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{f.statement}</p>

      {f.stale && current ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-2">
          <span className="text-amber-700 dark:text-amber-300">
            The evidence changed after this version was written (a row was corrected, re-analysed or its source deleted).
          </span>
          <Button size="xs" icon="refresh" loading={busy} onClick={() => void act(() => findingsApi.refresh(f.id), 'Evidence refreshed; the finding is a draft again')}>
            Refresh evidence
          </Button>
        </div>
      ) : null}

      {current ? (
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-[14rem] flex-1">
            <Field label="Note for this change (optional)" htmlFor="finding-note">
              <Input id="finding-note" value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
          </div>
          {NEXT[f.status].map((n) => (
            <Button
              key={n.to}
              size="sm"
              variant={n.to === 'approved' ? 'primary' : n.to === 'rejected' ? 'danger-ghost' : 'secondary'}
              loading={busy}
              onClick={() => void act(() => findingsApi.revise(f.id, { status: n.to, note }), `Finding ${n.to}`)}
            >
              {n.label}
            </Button>
          ))}
        </div>
      ) : null}

      {f.robustness ? <RobustnessPanel r={f.robustness} /> : null}

      <div>
        <h3 className="mb-1.5 font-semibold uppercase tracking-wider text-subtle">Evidence relied on</h3>
        <div className="overflow-auto rounded-lg border border-line">
          <table className="w-full">
            <thead className="bg-elevated text-left text-subtle">
              <tr>
                <th className="px-2 py-1.5 font-medium">Role</th>
                <th className="px-2 py-1.5 font-medium">Date</th>
                <th className="px-2 py-1.5 font-medium">Claim</th>
                <th className="px-2 py-1.5 text-right font-medium">Amount</th>
                <th className="px-2 py-1.5 font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {f.support.map((s) => {
                const ev = s.evidence[0];
                return (
                  <tr key={s.claim.id} className="align-top">
                    <td className="px-2 py-1.5">{s.role}</td>
                    <td className="whitespace-nowrap px-2 py-1.5 tabular-nums">{s.claim.date ?? '—'}</td>
                    <td className="px-2 py-1.5">
                      <div className="text-fg">
                        {s.claim.subject} {s.claim.kind === 'TRANSFERRED_TO' ? 'paid' : 'received from'} {s.claim.party ?? '—'}
                      </div>
                      <div className="text-subtle">
                        claim version {s.claim.id} · {s.claim.status.replace('_', ' ')}
                      </div>
                      {s.changed_since ? (
                        <div className="text-amber-700 dark:text-amber-300">
                          changed {new Date(s.changed_since.superseded_at).toLocaleString()}: {s.changed_since.reason}
                          {s.changed_since.current_claim_id ? ` (now version ${s.changed_since.current_claim_id})` : ' (retracted)'}
                        </div>
                      ) : null}
                    </td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-right tabular-nums">{formatMinor(s.claim.amount_minor)}</td>
                    <td className="px-2 py-1.5">
                      {ev?.document_id && ev.seq ? (
                        <Link className="text-accent underline" to={`/documents/${ev.document_id}?row=${ev.seq}`}>
                          {ev.filename ?? `document ${ev.document_id}`}, row {ev.seq}, p. {ev.page ?? '—'}
                        </Link>
                      ) : (
                        <span className="text-subtle">{ev?.filename ?? 'source removed'}</span>
                      )}
                      <div className="font-mono text-[10px] text-subtle" title={ev?.source_sha256 ?? ''}>
                        sha256 {short(ev?.source_sha256)}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {f.history?.length ? (
        <div>
          <h3 className="mb-1.5 font-semibold uppercase tracking-wider text-subtle">Versions</h3>
          <ol className="space-y-1">
            {f.history.map((v) => (
              <li key={v.id} className="flex flex-wrap items-center gap-2">
                <button type="button" className="text-accent underline" onClick={() => onOpen(v.id)}>
                  v{v.version}
                </button>
                <Badge tone={STATUS_TONE[v.status]}>{v.status}</Badge>
                <span className="text-subtle">
                  {new Date(v.created_at).toLocaleString()}
                  {v.change_note ? ` · ${v.change_note}` : ''}
                </span>
                {v.id === f.id ? <span className="text-subtle">(shown)</span> : null}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}

function Disclosures({ r }: { r: ReportView }) {
  const toast = useToast();
  const [items, setItems] = useState<DisclosureView[] | null>(null);
  const [parties, setParties] = useState<DisclosureParty[]>([]);
  const [subjects, setSubjects] = useState<Set<number>>(new Set());
  const [recipient, setRecipient] = useState('');
  const [busy, setBusy] = useState(false);
  const [denied, setDenied] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([reportsApi.disclosures(r.id), reportsApi.disclosureParties(r.id)])
      .then(([d, p]) => {
        setItems(d);
        setParties(p);
        setSubjects(new Set(p.filter((x) => x.default_subject).map((x) => x.id)));
      })
      .catch((e) => setDenied(errorMessage(e)));
  }, [r.id]);

  const create = async () => {
    setBusy(true);
    try {
      const d = await reportsApi.disclose(r.id, recipient.trim(), [...subjects]);
      setItems((cur) => [d, ...(cur ?? [])]);
      setRecipient('');
      toast.success('Disclosure copy made', `${d.withheld.length} kind(s) of item withheld; the report itself is unchanged.`);
    } catch (e) {
      toast.error('Not made', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (denied) return <p className="text-subtle">Disclosure copies: {denied}</p>;
  if (!items) return <Spinner />;
  const people = parties.filter((p) => p.kind !== 'org');
  return (
    <div className="space-y-3 rounded-lg border border-line p-3">
      <h3 className="font-semibold uppercase tracking-wider text-subtle">Disclosure copies</h3>
      <p className="text-muted">
        A copy for a recipient (for example the borrower, under SBI v. Amit Iron, 2026) with third parties&apos; personal data
        withheld and every withheld item listed with its reason. Organisations and the subjects you tick stay visible.
      </p>
      {people.length > 0 && (
        <fieldset>
          <legend className="mb-1 text-subtle">Subjects of the report (not withheld)</legend>
          <div className="flex max-h-32 flex-wrap gap-x-4 gap-y-1 overflow-auto">
            {people.map((p) => (
              <label key={p.id} className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  aria-label={`Subject: ${p.name} (party ${p.id})`}
                  checked={subjects.has(p.id)}
                  onChange={(e) =>
                    setSubjects((cur) => {
                      const next = new Set(cur);
                      if (e.target.checked) next.add(p.id);
                      else next.delete(p.id);
                      return next;
                    })
                  }
                />
                {p.name}
                <span className="text-subtle">
                  ({p.kind} · party {p.id})
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <div className="flex flex-wrap items-end gap-2">
        <Field label="Recipient" htmlFor={`recipient-${r.id}`} className="min-w-[14rem] flex-1">
          <Input id={`recipient-${r.id}`} value={recipient} onChange={(e) => setRecipient(e.target.value)} placeholder="e.g. Borrower's counsel" />
        </Field>
        <Button size="sm" variant="primary" loading={busy} disabled={recipient.trim().length < 3} onClick={() => void create()}>
          Make disclosure copy
        </Button>
      </div>
      {items.map((d) => (
        <div key={d.id} className="rounded-md border border-line p-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-fg">{d.recipient}</span>
            <span className="text-subtle">{new Date(d.created_at).toLocaleString()}</span>
            <Badge tone={d.intact ? 'success' : 'danger'}>{d.intact ? 'intact' : 'hash mismatch'}</Badge>
            <span className="font-mono text-[10px] text-subtle" title={d.content_hash}>
              sha256 {short(d.content_hash)}
            </span>
            <Button size="xs" onClick={() => void reportsApi.exportDisclosure(r.id, d.id).then((b) => saveBlob(b, `minddoc-report-${r.id}-disclosure-${d.id}.json`)).catch((e) => toast.error('Download failed', errorMessage(e)))}>
              JSON
            </Button>
            <Button size="xs" onClick={() => void reportsApi.bundle(r.id, d.id).then((b) => saveBlob(b, `minddoc-report-${r.id}-disclosure-${d.id}.zip`)).catch((e) => toast.error('Download failed', errorMessage(e)))}>
              Evidence bundle
            </Button>
          </div>
          {d.withheld.length ? (
            <ul className="mt-1.5 space-y-0.5 text-muted">
              {d.withheld.map((w) => (
                <li key={w.label}>
                  <span className="text-fg">{w.label}</span> ({w.kind}, {w.occurrences}×): {w.reason}
                  <span className="text-subtle"> · withheld: {w.values.join(', ')}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-subtle">Nothing needed withholding.</p>
          )}
        </div>
      ))}
    </div>
  );
}

function ReportDetail({ r }: { r: ReportView }) {
  const toast = useToast();
  const download = async () => {
    try {
      saveBlob(await reportsApi.export(r.id), `minddoc-report-${r.id}.json`);
    } catch (e) {
      toast.error('Download failed', errorMessage(e));
    }
  };
  const bundle = async () => {
    try {
      saveBlob(await reportsApi.bundle(r.id), `minddoc-report-${r.id}.zip`);
    } catch (e) {
      toast.error('Download failed', errorMessage(e));
    }
  };
  return (
    <div className="space-y-3 p-4 text-xs sm:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={r.intact ? 'success' : 'danger'}>{r.intact ? 'snapshot intact' : 'snapshot does not match its hash'}</Badge>
        <span className="text-subtle">frozen {new Date(r.frozen_at).toLocaleString()}</span>
        <span className="font-mono text-[10px] text-subtle" title={r.content_hash}>
          sha256 {short(r.content_hash)}
        </span>
        <Button size="xs" icon="external" onClick={() => void download()}>
          Download snapshot
        </Button>
        <Button size="xs" icon="layers" onClick={() => void bundle()}>
          Evidence bundle
        </Button>
      </div>
      {r.new_evidence_since_report.length ? (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-amber-700 dark:text-amber-300">
          New evidence since this report: {r.new_evidence_since_report.map((n) => n.title).join(' · ')}. The report itself is unchanged.
        </div>
      ) : null}
      <p className="text-muted">{r.snapshot.notice}</p>
      {r.snapshot.findings.map((f) => (
        <div key={f.id} className="rounded-lg border border-line p-2">
          <div className="font-medium text-fg">
            {f.title} <span className="text-subtle">(version {f.version})</span>
            {f.robustness?.k_fragility === 1 ? (
              <span className="ml-2">
                <Badge tone="warning">rests on one source</Badge>
              </span>
            ) : null}
          </div>
          <p className="mt-1 whitespace-pre-wrap text-muted">{f.statement}</p>
          <p className="mt-1 text-subtle">
            {f.support.length} claim version{f.support.length === 1 ? '' : 's'} ·{' '}
            {f.support.map((s) => `${s.claim.date ?? '—'} ${formatMinor(s.claim.amount_minor)}`).join(' · ')}
          </p>
        </div>
      ))}
      <Disclosures r={r} />
    </div>
  );
}

export default function Findings() {
  useTitle('Findings');
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [findings, setFindings] = useState<FindingSummary[] | null>(null);
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [open, setOpen] = useState<FindingView | null>(null);
  const [report, setReport] = useState<ReportView | null>(null);
  const [issuing, setIssuing] = useState<{ title: string; ids: number[] } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [f, r] = await Promise.all([findingsApi.list(), reportsApi.list()]);
      setFindings(f);
      setReports(r);
    } catch (e) {
      toast.error('Could not load findings', errorMessage(e));
    }
  }, [toast]);

  const openFinding = useCallback(
    async (id: number) => {
      try {
        setOpen(await findingsApi.get(id));
        setParams({ id: String(id) }, { replace: true });
      } catch (e) {
        toast.error('Could not open the finding', errorMessage(e));
      }
    },
    [toast, setParams],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const id = Number(params.get('id'));
    if (id && (!open || open.id !== id)) void openFinding(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const approved = (findings ?? []).filter((f) => f.status === 'approved');

  const issue = async () => {
    if (!issuing) return;
    setBusy(true);
    try {
      const r = await reportsApi.issue(issuing.title.trim(), issuing.ids);
      setIssuing(null);
      setReport(r);
      toast.success('Report frozen', `SHA-256 ${short(r.content_hash)}`);
      await load();
    } catch (e) {
      toast.error('Could not issue the report', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page wide>
      <PageHeader
        title="Findings"
        description="Your statements about the case, each tied to the exact claim versions and statement rows it relies on. A change creates a new version; issued reports are frozen with a hash."
        actions={
          <Button variant="primary" icon="lock" disabled={approved.length === 0} onClick={() => setIssuing({ title: '', ids: approved.map((f) => f.id) })}>
            Issue report
          </Button>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader icon="bookmark" title="Findings" description="Create one from selected claims on the Parties page." />
            <CardBody className="space-y-1 text-xs">
              {findings === null ? <Spinner /> : null}
              {findings?.length === 0 ? (
                <EmptyState compact icon="bookmark" title="No findings yet" description="Open a party, select transfer claims, and create a finding." />
              ) : null}
              {findings?.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => void openFinding(f.id)}
                  className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left hover:bg-elevated ${open?.finding_key === f.finding_key ? 'bg-elevated' : ''}`}
                >
                  <span className="min-w-0 truncate text-fg">{f.title}</span>
                  <span className="flex shrink-0 items-center gap-1">
                    {f.stale ? <Badge tone="warning">evidence changed</Badge> : null}
                    <Badge tone={STATUS_TONE[f.status]}>{f.status}</Badge>
                  </span>
                </button>
              ))}
            </CardBody>
          </Card>
          <Card>
            <CardHeader icon="lock" title="Frozen reports" />
            <CardBody className="space-y-1 text-xs">
              {reports?.length === 0 ? <p className="text-muted">No reports issued.</p> : null}
              {reports?.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={async () => {
                    try {
                      setReport(await reportsApi.get(r.id));
                    } catch (e) {
                      toast.error('Could not open the report', errorMessage(e));
                    }
                  }}
                  className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left hover:bg-elevated"
                >
                  <span className="min-w-0 truncate text-fg">{r.title}</span>
                  <span className="shrink-0 text-subtle">{new Date(r.frozen_at).toLocaleDateString()}</span>
                </button>
              ))}
            </CardBody>
          </Card>
        </div>
        <Card>
          <CardHeader icon="layers" title={open ? open.title : 'Select a finding'} />
          <CardBody>
            {open ? (
              <FindingDetail
                f={open}
                onChanged={(f) => {
                  void openFinding(f.id);
                  void load();
                }}
                onOpen={(id) => void openFinding(id)}
              />
            ) : (
              <p className="text-xs text-muted">Choose a finding to see its statement, status, versions and the rows it relies on.</p>
            )}
          </CardBody>
        </Card>
      </div>

      <Modal
        open={!!issuing}
        onClose={() => (busy ? undefined : setIssuing(null))}
        title="Issue a frozen report"
        description="The approved findings you select are frozen with everything they rely on. The report cannot be edited afterwards."
        footer={
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setIssuing(null)} disabled={busy}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="primary"
              loading={busy}
              disabled={!issuing || issuing.title.trim().length < 3 || issuing.ids.length === 0}
              onClick={() => void issue()}
            >
              Freeze report
            </Button>
          </div>
        }
      >
        {issuing ? (
          <div className="space-y-3 p-4 text-xs sm:p-5">
            <Field label="Report title" htmlFor="report-title">
              <Input id="report-title" value={issuing.title} onChange={(e) => setIssuing({ ...issuing, title: e.target.value })} />
            </Field>
            <ul className="space-y-1">
              {approved.map((f) => (
                <li key={f.id}>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={issuing.ids.includes(f.id)}
                      onChange={() =>
                        setIssuing({
                          ...issuing,
                          ids: issuing.ids.includes(f.id) ? issuing.ids.filter((i) => i !== f.id) : [...issuing.ids, f.id],
                        })
                      }
                    />
                    <span className="text-fg">{f.title}</span>
                    {f.stale ? <Badge tone="warning">evidence changed</Badge> : null}
                  </label>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Modal>

      <Modal open={!!report} onClose={() => setReport(null)} size="xl" title={report?.title ?? 'Report'}>
        {report ? <ReportDetail r={report} /> : null}
      </Modal>
    </Page>
  );
}
