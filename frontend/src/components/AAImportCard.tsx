import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { documentsApi, errorMessage } from '../api';
import type { AAImportResponse } from '../types';
import { Button, buttonClass } from './ui/Button';
import { Card, CardBody, CardHeader } from './ui/Card';
import { Input } from './ui/Field';
import { useToast } from './ui/Toast';

/**
 * Import of Account Aggregator deposit data (ADR-0015). MindDoc does not request consent or fetch from an AA: the
 * customer uploads a decrypted ReBIT deposit payload it already holds, and records the consent artefact reference.
 */
export default function AAImportCard({ onImported }: { onImported?: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [consentRef, setConsentRef] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AAImportResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await documentsApi.importAa(file, consentRef);
      setResult(res);
      toast.success(res.created ? 'Account Aggregator data imported' : 'Already imported', `${res.transactions} transactions`);
      onImported?.();
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (e) {
      setError(errorMessage(e, 'Import failed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mt-6">
      <CardHeader
        icon="database"
        title="Import Account Aggregator data"
        description="A decrypted ReBIT deposit payload (JSON or XML) that you already hold. MindDoc does not request consent or contact an AA."
      />
      <CardBody className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
          <input
            ref={inputRef}
            type="file"
            accept=".json,.xml,application/json,application/xml,text/xml"
            aria-label="Account Aggregator payload file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-xs text-muted file:mr-3 file:rounded-md file:border file:border-line file:bg-elevated file:px-2.5 file:py-1.5 file:text-xs file:text-fg"
          />
          <Input
            value={consentRef}
            onChange={(e) => setConsentRef(e.target.value)}
            placeholder="Consent artefact reference (optional)"
            aria-label="Consent artefact reference"
            maxLength={200}
            className="h-8 text-[13px]"
          />
          <Button size="sm" variant="primary" icon="upload" loading={busy} disabled={!file} onClick={submit}>
            {busy ? 'Importing…' : 'Import'}
          </Button>
        </div>
        {error ? (
          <p className="text-xs text-rose-600 dark:text-rose-400" role="alert">
            {error}
          </p>
        ) : null}
        {result ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted" aria-live="polite">
            <span>
              {result.message}: {result.transactions} transactions · {result.status.replace(/_/g, ' ')}
              {result.warnings.length ? ` · ${result.warnings.join('; ')}` : ''}
            </span>
            <Link to={`/documents/${result.document_id}`} className={buttonClass('secondary', 'xs')}>
              Open statement
            </Link>
          </div>
        ) : null}
        <p className="text-[11px] text-subtle">
          The payload is validated against the ReBIT deposit schema before anything is stored. It has no opening balance,
          so the opening is derived from the first transaction and flagged.
        </p>
      </CardBody>
    </Card>
  );
}
