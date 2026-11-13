import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react';
import { documentsApi, errorMessage } from '../api';
import AAImportCard from '../components/AAImportCard';
import AnalysisSummary from '../components/AnalysisSummary';
import DocumentTable from '../components/DocumentTable';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardHeader } from '../components/ui/Card';
import { Icon } from '../components/ui/Icon';
import { IndeterminateBar, Meter } from '../components/ui/Meter';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { useToast } from '../components/ui/Toast';
import { useDocuments } from '../hooks/useDocuments';
import { cx } from '../lib/cx';
import { bytes, uid } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import { ACCEPTED_EXTENSIONS, type UploadResponse } from '../types';

type Status = 'queued' | 'uploading' | 'processing' | 'done' | 'error';

interface QueueItem {
  id: string;
  file: File;
  status: Status;
  progress: number;
  result?: UploadResponse;
  error?: string;
  /** Live processing stage reported by the background worker (asynchronous ingestion). */
  stage?: string;
  documentId?: number;
  open: boolean;
}

const POLL_MS = 1500;
const POLL_LIMIT_MS = 15 * 60 * 1000;
const sleep = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

const ACCEPT = ACCEPTED_EXTENSIONS.join(',');
const extOf = (name: string): string => {
  const i = name.lastIndexOf('.');
  return i >= 0 ? name.slice(i).toLowerCase() : '';
};
const isAccepted = (f: File) => (ACCEPTED_EXTENSIONS as readonly string[]).includes(extOf(f.name));

const STATUS: Record<Status, { label: string; tone: 'neutral' | 'accent' | 'info' | 'success' | 'danger' }> = {
  queued: { label: 'Queued', tone: 'neutral' },
  uploading: { label: 'Uploading', tone: 'accent' },
  processing: { label: 'Analyzing', tone: 'info' },
  done: { label: 'Analyzed', tone: 'success' },
  error: { label: 'Failed', tone: 'danger' },
};

export default function Upload() {
  useTitle('Documents');
  const toast = useToast();
  const { documents, loading, error, reload, remove } = useDocuments();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const busy = useRef(false);
  const dragDepth = useRef(0);

  const update = useCallback((id: string, patch: Partial<QueueItem>) => {
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  }, []);

  const addFiles = (list: FileList | File[] | null) => {
    if (!list) return;
    const files = Array.from(list);
    const ok = files.filter(isAccepted);
    const rejected = files.filter((f) => !isAccepted(f));
    if (rejected.length) {
      toast.warning(
        `${rejected.length} file${rejected.length > 1 ? 's' : ''} skipped`,
        `Unsupported type: ${rejected.map((f) => f.name).slice(0, 3).join(', ')}${rejected.length > 3 ? '…' : ''}`,
      );
    }
    if (ok.length) {
      setItems((xs) => [...xs, ...ok.map((file) => ({ id: uid(), file, status: 'queued' as Status, progress: 0, open: true }))]);
    }
  };

  const runUpload = useCallback(
    async (item: QueueItem) => {
      busy.current = true;
      update(item.id, { status: 'uploading', progress: 0, error: undefined });
      try {
        let res: UploadResponse;
        if (item.documentId) {
          // Retry after a failed background run: reprocess the stored original instead of uploading again.
          await documentsApi.reprocess(item.documentId);
          res = { message: 'Reprocessing', document_id: item.documentId, filename: item.file.name, status: 'queued' };
        } else {
          res = await documentsApi.upload(item.file, (p) => {
            update(item.id, p >= 100 ? { progress: 100, status: 'processing' } : { progress: p });
          });
        }
        if (res.status === 'failed') throw new Error('This file failed processing earlier. Use Retry to process it again.');
        update(item.id, { documentId: res.document_id, status: 'processing', stage: 'Waiting for a worker' });
        // Asynchronous ingestion: the server queued the file; follow its job until it completes or fails.
        const started = Date.now();
        while (res.status === 'queued' || res.status === 'processing') {
          if (Date.now() - started > POLL_LIMIT_MS) throw new Error('Still processing after 15 minutes. It will finish in the background; check the document list.');
          await sleep(POLL_MS);
          const st = await documentsApi.status(res.document_id);
          const stage = st.job?.progress?.stage ?? (st.status === 'queued' ? 'Waiting for a worker' : st.status);
          update(item.id, { stage: st.job?.progress?.detail ? `${stage} · ${st.job.progress.detail}` : stage });
          if (st.status === 'failed') {
            throw new Error(st.detail || st.job?.last_error || 'Processing failed');
          }
          if (st.status === 'completed') {
            res = { ...res, status: 'completed', analysis: await documentsApi.get(res.document_id) };
          }
        }
        busy.current = false;
        update(item.id, { status: 'done', progress: 100, result: res, stage: undefined });
        const flags = res.analysis?.security_flags ?? [];
        if (flags.some((f) => f.type === 'prompt_injection')) {
          toast.warning('Prompt injection detected', `${res.filename} contains instructions aimed at the AI.`);
        } else {
          toast.success('Document analyzed', res.filename);
        }
        void reload();
      } catch (e) {
        busy.current = false;
        const msg = errorMessage(e, 'Upload failed');
        update(item.id, { status: 'error', error: msg });
        toast.error(`Upload failed: ${item.file.name}`, msg);
      }
    },
    [reload, toast, update],
  );

  // Sequential queue: start the next queued file when nothing is in flight.
  useEffect(() => {
    if (busy.current) return;
    if (items.some((i) => i.status === 'uploading' || i.status === 'processing')) return;
    const next = items.find((i) => i.status === 'queued');
    if (next) void runUpload(next);
  }, [items, runUpload]);

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const pending = items.filter((i) => i.status === 'queued' || i.status === 'uploading' || i.status === 'processing').length;
  const finished = items.filter((i) => i.status === 'done' || i.status === 'error').length;

  return (
    <Page>
      <PageHeader
        title="Documents"
        description="Upload files to classify, summarize, OCR, scan for PII and prompt injection, extract entities and index for cited answers."
      />

      <div
        onDragEnter={(e) => {
          e.preventDefault();
          dragDepth.current++;
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => {
          dragDepth.current = Math.max(0, dragDepth.current - 1);
          if (dragDepth.current === 0) setDragging(false);
        }}
        onDrop={onDrop}
        className={cx(
          'relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors',
          dragging ? 'border-accent bg-accent/[0.06]' : 'border-line-strong bg-surface hover:border-accent/60',
        )}
      >
        <div className={cx('flex h-12 w-12 items-center justify-center rounded-xl border transition-colors', dragging ? 'border-accent bg-accent/15 text-accent' : 'border-line bg-elevated text-muted')}>
          <Icon name="upload" className="h-5 w-5" />
        </div>
        <p className="mt-4 text-sm font-medium text-fg">{dragging ? 'Drop to upload' : 'Drag & drop files here'}</p>
        <p className="mt-1 text-xs text-muted">or</p>
        <Button variant="primary" size="sm" className="mt-2" icon="plus" onClick={() => inputRef.current?.click()}>
          Choose files
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          aria-label="Choose files to upload"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = '';
          }}
        />
        <p className="mt-4 max-w-lg text-[11px] text-subtle">
          Accepted: {ACCEPTED_EXTENSIONS.map((x) => x.slice(1).toUpperCase()).join(' · ')}. Files are uploaded one at a time; scanned pages
          and images go through the OpenCV + OCR pipeline.
        </p>
      </div>

      {items.length > 0 ? (
        <Card className="mt-6">
          <CardHeader
            icon="layers"
            title="Upload queue"
            description={pending ? `${pending} remaining · processed sequentially` : 'All files processed'}
            actions={
              finished > 0 ? (
                <Button size="xs" variant="ghost" onClick={() => setItems((xs) => xs.filter((x) => x.status !== 'done' && x.status !== 'error'))}>
                  Clear finished
                </Button>
              ) : null
            }
          />
          <ul className="divide-y divide-line">
            {items.map((it) => (
              <li key={it.id} className="px-4 py-3 sm:px-5">
                <div className="flex items-center gap-3">
                  <Icon name={/\.(png|jpe?g|tiff|bmp|gif|webp)$/i.test(it.file.name) ? 'image' : 'file'} className="h-4 w-4 text-subtle" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-medium text-fg">{it.file.name}</span>
                      <span className="text-xs text-subtle">{bytes(it.file.size)}</span>
                      <Badge tone={STATUS[it.status].tone} dot>
                        {STATUS[it.status].label}
                        {it.status === 'uploading' ? ` ${it.progress}%` : ''}
                      </Badge>
                    </div>
                    {it.status === 'uploading' ? <Meter value={it.progress} max={100} tone="accent" className="mt-2" label={`Uploading ${it.file.name}`} /> : null}
                    {it.status === 'processing' ? (
                      <div className="mt-2">
                        <IndeterminateBar label={`Analyzing ${it.file.name}`} />
                        <p className="mt-1 text-[11px] text-subtle" aria-live="polite">
                          {it.stage ? `Background processing: ${it.stage}` : 'Uploading…'}
                        </p>
                      </div>
                    ) : null}
                    {it.status === 'error' ? <p className="mt-1 text-xs text-rose-600 dark:text-rose-400">{it.error}</p> : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {it.status === 'error' ? (
                      <Button size="xs" icon="refresh" onClick={() => update(it.id, { status: 'queued', progress: 0, error: undefined })}>
                        Retry
                      </Button>
                    ) : null}
                    {it.status === 'done' ? (
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label={it.open ? 'Collapse analysis' : 'Expand analysis'}
                        aria-expanded={it.open}
                        onClick={() => update(it.id, { open: !it.open })}
                        icon="chevron-down"
                        className={it.open ? 'rotate-180' : ''}
                      />
                    ) : null}
                    {it.status === 'queued' || it.status === 'done' || it.status === 'error' ? (
                      <Button size="icon-sm" variant="ghost" aria-label={`Remove ${it.file.name} from queue`} onClick={() => setItems((xs) => xs.filter((x) => x.id !== it.id))} icon="x" />
                    ) : null}
                  </div>
                </div>
                {it.status === 'done' && it.result && it.open ? (
                  <div className="mt-3 rounded-xl border border-line bg-bg/40 p-4 animate-fade-in">
                    <AnalysisSummary result={it.result} />
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <AAImportCard onImported={() => void reload()} />

      <div className="mt-6">
        <DocumentTable title="Library" documents={documents} loading={loading} error={error} onDelete={(d) => void remove(d)} />
      </div>
    </Page>
  );
}
