import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { casesApi, documentsApi, errorMessage } from '../api';
import { useLayout } from '../components/Layout';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { useConfirm } from '../components/ui/Dialog';
import { EmptyState } from '../components/ui/EmptyState';
import { Field, Input, Select } from '../components/ui/Field';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Spinner } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { useTitle } from '../lib/useTitle';
import type { CaseDetail, CaseRole, DocumentSummary } from '../types';

const ROLES: CaseRole[] = ['viewer', 'analyst', 'reviewer', 'lead'];
const ROLE_HELP: Record<CaseRole, string> = {
  viewer: 'reads the case',
  analyst: 'uploads, resolves parties, drafts and proposes findings',
  reviewer: 'also approves or rejects findings and issues reports',
  lead: 'also manages members and case settings',
};

function CasePanel({ id, onChanged }: { id: number; onChanged: () => Promise<void> }) {
  const toast = useToast();
  const confirm = useConfirm();
  const [c, setC] = useState<CaseDetail | null>(null);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<CaseRole>('analyst');
  const [visible, setVisible] = useState<DocumentSummary[]>([]);
  const [docToAdd, setDocToAdd] = useState('');

  const load = useCallback(async () => {
    try {
      setC(await casesApi.get(id));
    } catch (e) {
      toast.error('Could not load the case', errorMessage(e));
    }
  }, [id, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const lead = c?.my_role === 'lead';
  const analyst = c?.my_role != null && c.my_role !== 'viewer';

  useEffect(() => {
    if (!analyst) return;
    // every document the user can see, for "add to this case" (explicitly not scoped to the selected case)
    documentsApi.listAll().then(setVisible).catch(() => setVisible([]));
  }, [analyst]);

  const run = async (fn: () => Promise<unknown>, done: string) => {
    try {
      await fn();
      toast.success(done);
      await load();
      await onChanged();
    } catch (e) {
      toast.error('Not changed', errorMessage(e));
    }
  };

  if (!c) return <Spinner />;
  const inCase = new Set(c.document_list.map((d) => d.id));

  return (
    <div className="space-y-5 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={c.status === 'open' ? 'success' : 'neutral'}>{c.status}</Badge>
        <span className="text-subtle">your role: {c.my_role}</span>
        {lead && !c.is_default && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => void run(() => casesApi.update(c.id, { status: c.status === 'open' ? 'closed' : 'open' }), 'Case updated')}
          >
            {c.status === 'open' ? 'Close case' : 'Reopen case'}
          </Button>
        )}
      </div>

      <section>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-subtle">Members</h3>
        {c.open_to_organisation ? (
          <p className="mb-2 text-muted">
            Every member of your organisation can use the General case: admins as lead, others as analysts. Add someone
            here only to give them a higher role.
          </p>
        ) : null}
        {c.members.length > 0 ? (
          <ul className="divide-y divide-line">
            {c.members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between gap-3 py-2">
                <span className="min-w-0 truncate text-fg">{m.email}</span>
                {lead ? (
                  <span className="flex items-center gap-1.5">
                    <Select
                      aria-label={`Role of ${m.email}`}
                      value={m.role}
                      onChange={(e) => void run(() => casesApi.setRole(c.id, m.user_id, e.target.value as CaseRole), 'Role changed')}
                      className="h-7 text-xs"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </Select>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon="x"
                      aria-label={`Remove ${m.email}`}
                      onClick={() => void run(() => casesApi.removeMember(c.id, m.user_id), 'Member removed')}
                    />
                  </span>
                ) : (
                  <Badge>{m.role}</Badge>
                )}
              </li>
            ))}
          </ul>
        ) : (
          !c.open_to_organisation && <p className="text-subtle">No members.</p>
        )}
        {lead && (
          <form
            className="mt-3 space-y-2"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              void run(() => casesApi.addMember(c.id, email.trim(), role), 'Member added').then(() => setEmail(''));
            }}
          >
            <Field label="Add a member of your organisation" htmlFor="case-member-email">
              <Input id="case-member-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="colleague@firm.com" required />
            </Field>
            <div className="flex items-end gap-2">
              <Field label="Role" htmlFor="case-member-role" hint={ROLE_HELP[role]} className="min-w-0 flex-1">
                <Select id="case-member-role" value={role} onChange={(e) => setRole(e.target.value as CaseRole)}>
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button type="submit" icon="plus" className="mb-5">
                Add
              </Button>
            </div>
          </form>
        )}
      </section>

      <section>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-subtle">Documents ({c.document_list.length})</h3>
        {c.document_list.length === 0 ? (
          <p className="text-subtle">No documents yet. Upload with this case selected, or add one you can already see.</p>
        ) : (
          <ul className="divide-y divide-line">
            {c.document_list.map((d) => (
              <li key={d.id} className="flex items-center justify-between gap-3 py-2">
                <Link to={`/documents/${d.id}`} className="min-w-0 truncate text-accent-soft hover:underline">
                  {d.filename}
                </Link>
                <span className="flex items-center gap-2">
                  <span className="text-subtle">{d.doc_type ?? d.status}</span>
                  {analyst && d.cases > 1 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        void confirm({
                          title: 'Remove from this case?',
                          description:
                            'Its claims in this case are closed with a reason; nothing is deleted. A document must stay in at least one case.',
                          confirmLabel: 'Remove',
                          tone: 'danger',
                        }).then((ok) => {
                          if (ok) void run(() => casesApi.unlinkDocument(c.id, d.id), 'Removed from the case');
                        })
                      }
                    >
                      Remove
                    </Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
        {analyst && visible.some((d) => !inCase.has(d.id)) && (
          <form
            className="mt-3 flex items-end gap-2"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              if (docToAdd) void run(() => casesApi.linkDocument(c.id, Number(docToAdd)), 'Added to the case').then(() => setDocToAdd(''));
            }}
          >
            <Field label="Add a document you can see" htmlFor="case-add-doc" className="min-w-0 flex-1">
              <Select id="case-add-doc" value={docToAdd} onChange={(e) => setDocToAdd(e.target.value)}>
                <option value="">Choose…</option>
                {visible
                  .filter((d) => !inCase.has(d.id))
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.filename}
                    </option>
                  ))}
              </Select>
            </Field>
            <Button type="submit" disabled={!docToAdd}>
              Add
            </Button>
          </form>
        )}
      </section>
    </div>
  );
}

export default function Cases() {
  useTitle('Cases');
  const toast = useToast();
  const { cases, currentCase, selectCase, refreshCases } = useLayout();
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(currentCase?.id ?? null);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const c = await casesApi.create(title.trim());
      setTitle('');
      await refreshCases();
      setOpen(c.id);
      toast.success('Case created', 'You are its lead. Select it in the header to work in it.');
    } catch (err) {
      toast.error('Case not created', errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page className="max-w-5xl">
      <PageHeader
        title="Cases"
        description="Each engagement is a case with its own documents, parties, findings and reports. Only its members can see it."
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div className="space-y-4">
          <Card>
            <CardBody>
              <form onSubmit={create} className="flex items-end gap-2">
                <Field label="New case" htmlFor="new-case" className="min-w-0 flex-1">
                  <Input id="new-case" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Borrower review, FY 2025" required maxLength={200} />
                </Field>
                <Button type="submit" variant="primary" icon="plus" loading={busy}>
                  Create
                </Button>
              </form>
            </CardBody>
          </Card>
          {cases.length === 0 ? (
            <EmptyState icon="folder" title="No cases" description="Create one to start an engagement." />
          ) : (
            <ul className="space-y-2">
              {cases.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => setOpen(c.id)}
                    className={`w-full rounded-lg border px-3 py-2.5 text-left text-xs transition ${open === c.id ? 'border-accent bg-accent/[0.06]' : 'border-line bg-surface hover:border-line-strong'}`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium text-fg">{c.title}</span>
                      {currentCase?.id === c.id ? <Badge tone="info">selected</Badge> : null}
                    </span>
                    <span className="mt-1 block text-subtle">
                      {c.my_role} · {c.documents} document{c.documents === 1 ? '' : 's'}
                      {c.members != null ? ` · ${c.members} member${c.members === 1 ? '' : 's'}` : ' · whole organisation'}
                      {c.status === 'closed' ? ' · closed' : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <Card>
          <CardHeader
            icon="folder"
            title={cases.find((c) => c.id === open)?.title ?? 'Choose a case'}
            actions={
              open != null && currentCase?.id !== open ? (
                <Button size="sm" onClick={() => selectCase(open)}>
                  Work in this case
                </Button>
              ) : undefined
            }
          />
          <CardBody>{open != null ? <CasePanel key={open} id={open} onChanged={refreshCases} /> : <p className="text-xs text-subtle">Select a case on the left.</p>}</CardBody>
        </Card>
      </div>
    </Page>
  );
}
