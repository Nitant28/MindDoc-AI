import { useState, type ReactNode } from 'react';
import { documentsApi, errorMessage } from '../api';
import { copyText } from '../lib/clipboard';
import { uid } from '../lib/format';
import type { ExtractResponse } from '../types';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Card, CardBody, CardHeader } from './ui/Card';
import { Input } from './ui/Field';
import { useToast } from './ui/Toast';

interface Row {
  key: string;
  name: string;
  description: string;
}

const PRESETS: Record<string, Array<[string, string]>> = {
  legal_contract: [
    ['parties', 'Names of the contracting parties'],
    ['effective_date', 'Date the agreement takes effect'],
    ['total_value', 'Total contract value with currency'],
  ],
  invoice: [
    ['vendor', 'Company issuing the invoice'],
    ['invoice_number', 'Invoice identifier'],
    ['total_due', 'Total amount due with currency'],
  ],
  research_paper: [
    ['title', 'Title of the paper'],
    ['authors', 'List of author names'],
    ['key_findings', 'Main findings in one or two sentences each'],
  ],
  resume: [
    ['candidate_name', 'Full name of the candidate'],
    ['skills', 'Key skills listed'],
    ['years_experience', 'Total years of professional experience'],
  ],
};

const DEFAULT: Array<[string, string]> = [
  ['title', 'Title or main subject of the document'],
  ['key_parties', 'People or organizations involved'],
  ['key_dates', 'Important dates and what they refer to'],
];

function presetFor(docType?: string | null): Row[] {
  const p = (docType && PRESETS[docType]) || DEFAULT;
  return p.map(([name, description]) => ({ key: uid(), name, description }));
}

function renderValue(v: unknown): ReactNode {
  if (v === null || v === undefined || v === '') return <span className="text-subtle">—</span>;
  if (typeof v === 'string' || typeof v === 'number') return <span className="whitespace-pre-wrap break-words">{String(v)}</span>;
  if (typeof v === 'boolean') return <Badge tone={v ? 'success' : 'neutral'}>{v ? 'Yes' : 'No'}</Badge>;
  if (Array.isArray(v) && v.every((x) => typeof x === 'string' || typeof x === 'number')) {
    if (v.length === 0) return <span className="text-subtle">None</span>;
    return (
      <div className="flex flex-wrap gap-1">
        {v.map((x, i) => (
          <Badge key={i} tone="accent" className="whitespace-normal">
            {String(x)}
          </Badge>
        ))}
      </div>
    );
  }
  return <pre className="overflow-x-auto rounded-md bg-elevated p-2 font-mono text-[11px] text-muted">{JSON.stringify(v, null, 2)}</pre>;
}

export default function ExtractionPanel({ documentId, docType }: { documentId: number; docType?: string | null }) {
  const [rows, setRows] = useState<Row[]>(() => presetFor(docType));
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [raw, setRaw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const update = (key: string, patch: Partial<Row>) => setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  const names = rows.map((r) => r.name.trim()).filter(Boolean);
  const duplicate = names.find((n, i) => names.indexOf(n) !== i);

  const run = async () => {
    const fields: Record<string, string> = {};
    rows.forEach((r) => {
      const n = r.name.trim().replace(/\s+/g, '_');
      if (n) fields[n] = r.description.trim() || n.replace(/_/g, ' ');
    });
    if (Object.keys(fields).length === 0) {
      setError('Add at least one field to extract.');
      return;
    }
    if (duplicate) {
      setError(`Field “${duplicate}” is defined twice.`);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await documentsApi.extract(documentId, fields);
      setResult({ ...res, data: res.data ?? {} });
      toast.success('Extraction complete', `${Object.keys(res.data ?? {}).length} fields returned`);
    } catch (e) {
      const msg = errorMessage(e, 'Extraction failed');
      setError(msg);
      toast.error('Extraction failed', msg);
    } finally {
      setLoading(false);
    }
  };

  const json = result ? JSON.stringify(result.data, null, 2) : '';

  return (
    <Card>
      <CardHeader
        icon="table"
        title="Structured extraction"
        description="Define a schema; the model returns typed JSON grounded in this document."
        actions={
          <Button variant="ghost" size="xs" onClick={() => setRows(presetFor(docType))}>
            Reset examples
          </Button>
        }
      />
      <CardBody className="space-y-4">
        <div className="space-y-2">
          <div className="hidden grid-cols-[minmax(0,10rem)_minmax(0,1fr)_2rem] gap-2 px-0.5 text-[11px] font-medium uppercase tracking-wider text-subtle sm:grid">
            <span>Field</span>
            <span>Description</span>
            <span />
          </div>
          {rows.map((r, i) => (
            <div key={r.key} className="grid grid-cols-[minmax(0,1fr)_2rem] gap-2 sm:grid-cols-[minmax(0,10rem)_minmax(0,1fr)_2rem]">
              <Input
                value={r.name}
                onChange={(e) => update(r.key, { name: e.target.value })}
                placeholder="field_name"
                aria-label={`Field ${i + 1} name`}
                className="h-8 font-mono text-[12px]"
              />
              <Input
                value={r.description}
                onChange={(e) => update(r.key, { description: e.target.value })}
                placeholder="What should be extracted?"
                aria-label={`Field ${i + 1} description`}
                className="order-3 col-span-2 h-8 text-[13px] sm:order-none sm:col-span-1"
              />
              <Button
                variant="ghost"
                size="icon-sm"
                className="mt-0.5 hover:!text-rose-500"
                aria-label={`Remove field ${r.name || i + 1}`}
                onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}
                icon="x"
              />
            </div>
          ))}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button size="sm" icon="plus" onClick={() => setRows((rs) => [...rs, { key: uid(), name: '', description: '' }])}>
              Add field
            </Button>
            <Button size="sm" variant="primary" icon="sparkles" loading={loading} onClick={run} disabled={rows.length === 0}>
              {loading ? 'Extracting…' : 'Extract'}
            </Button>
          </div>
          {error ? (
            <p className="text-xs text-rose-600 dark:text-rose-400" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        {result ? (
          <div className="space-y-2 border-t border-line pt-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-subtle">
                Result{result.provider ? ` · ${result.provider}` : ''}
                {result.model ? <span className="font-mono"> · {result.model}</span> : null}
              </p>
              <div className="flex items-center gap-1">
                <Button size="xs" variant={raw ? 'secondary' : 'ghost'} icon="code" aria-pressed={raw} onClick={() => setRaw((v) => !v)}>
                  Raw JSON
                </Button>
                <Button
                  size="xs"
                  variant="ghost"
                  icon="copy"
                  onClick={async () => {
                    if (await copyText(json)) toast.success('JSON copied');
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            {raw ? (
              <pre className="max-h-96 overflow-auto rounded-lg border border-line bg-elevated/60 p-3 font-mono text-[12px] leading-relaxed text-fg">{json}</pre>
            ) : Object.keys(result.data).length === 0 ? (
              <p className="text-sm text-subtle">The model returned no fields.</p>
            ) : (
              <div className="overflow-hidden rounded-lg border border-line">
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-line">
                    {Object.entries(result.data).map(([k, v]) => (
                      <tr key={k}>
                        <th scope="row" className="w-40 bg-elevated/50 px-3 py-2 text-left align-top font-mono text-[12px] font-medium text-muted">
                          {k}
                        </th>
                        <td className="px-3 py-2 align-top text-fg">{renderValue(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}
