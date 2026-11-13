import { useId, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { humanize, relTime, fullDate, num, timeOf } from '../lib/format';
import type { DocumentSummary } from '../types';
import { DocTypeBadge, PiiBadge, QualityMeter } from './Signals';
import { Badge } from './ui/Badge';
import { Button, buttonClass } from './ui/Button';
import { Card, CardHeader } from './ui/Card';
import { EmptyState } from './ui/EmptyState';
import { Input, Select } from './ui/Field';
import { Icon } from './ui/Icon';
import { Skeleton } from './ui/Spinner';

type SortKey = 'recent' | 'name' | 'quality' | 'pii';

interface DocumentTableProps {
  documents: DocumentSummary[];
  loading?: boolean;
  error?: string | null;
  onDelete: (doc: DocumentSummary) => void;
  filterIds?: number[] | null;
  filterLabel?: string;
  onClearFilter?: () => void;
  title?: string;
  description?: ReactNode;
  emptyAction?: ReactNode;
}

function RowActions({ doc, onDelete }: { doc: DocumentSummary; onDelete: (d: DocumentSummary) => void }) {
  return (
    <div className="flex items-center justify-end gap-0.5">
      <Link
        to={`/documents/${doc.id}`}
        className={buttonClass('ghost', 'icon-sm')}
        aria-label={`Open ${doc.filename}`}
        title="Open document"
      >
        <Icon name="external" className="h-3.5 w-3.5" />
      </Link>
      <Link
        to={`/chat?document=${doc.id}`}
        className={buttonClass('ghost', 'icon-sm')}
        aria-label={`Chat with ${doc.filename}`}
        title="Chat with this document"
      >
        <Icon name="chat" className="h-3.5 w-3.5" />
      </Link>
      <Button
        variant="ghost"
        size="icon-sm"
        className="hover:!text-rose-500"
        aria-label={`Delete ${doc.filename}`}
        title="Delete document"
        onClick={() => onDelete(doc)}
        icon="trash"
      />
    </div>
  );
}

export default function DocumentTable({
  documents,
  loading,
  error,
  onDelete,
  filterIds,
  filterLabel,
  onClearFilter,
  title = 'Documents',
  description,
  emptyAction,
}: DocumentTableProps) {
  const [q, setQ] = useState('');
  const [sort, setSort] = useState<SortKey>('recent');
  const searchId = useId();
  const sortId = useId();

  const rows = useMemo(() => {
    let r = documents;
    if (filterIds) {
      const set = new Set(filterIds);
      r = r.filter((d) => set.has(d.id));
    }
    const needle = q.trim().toLowerCase();
    if (needle) {
      r = r.filter(
        (d) =>
          d.filename.toLowerCase().includes(needle) ||
          (d.doc_type ?? '').toLowerCase().includes(needle) ||
          (d.summary ?? '').toLowerCase().includes(needle),
      );
    }
    const sorted = [...r];
    switch (sort) {
      case 'name':
        sorted.sort((a, b) => a.filename.localeCompare(b.filename));
        break;
      case 'quality':
        sorted.sort((a, b) => (b.quality_score ?? -1) - (a.quality_score ?? -1));
        break;
      case 'pii':
        sorted.sort((a, b) => (b.pii_count ?? -1) - (a.pii_count ?? -1));
        break;
      default:
        sorted.sort((a, b) => timeOf(b.created_at) - timeOf(a.created_at) || b.id - a.id);
    }
    return sorted;
  }, [documents, filterIds, q, sort]);

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            {title}
            <span className="rounded-md bg-elevated px-1.5 text-[11px] font-medium tabular-nums text-muted">{rows.length}</span>
          </span>
        }
        description={description}
        actions={
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <label htmlFor={searchId} className="sr-only">
              Search documents
            </label>
            <div className="relative w-full sm:w-56">
              <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
              <Input
                id={searchId}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search name, type, summary…"
                className="h-8 pl-8 text-[13px]"
              />
            </div>
            <label htmlFor={sortId} className="sr-only">
              Sort documents
            </label>
            <Select id={sortId} value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="h-8 w-auto text-[13px]">
              <option value="recent">Most recent</option>
              <option value="name">Name</option>
              <option value="quality">Quality</option>
              <option value="pii">PII count</option>
            </Select>
          </div>
        }
      />

      {filterIds && filterLabel ? (
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2 text-xs text-muted sm:px-5">
          <span>Filtered by topic</span>
          <Badge tone="accent">{filterLabel}</Badge>
          {onClearFilter ? (
            <Button variant="ghost" size="xs" onClick={onClearFilter} icon="x">
              Clear
            </Button>
          ) : null}
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-3 p-5" aria-busy="true" aria-label="Loading documents">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : error ? (
        <EmptyState icon="alert" title="Couldn't load documents" description={error} compact />
      ) : rows.length === 0 ? (
        <EmptyState
          icon="file"
          title={documents.length === 0 ? 'No documents yet' : 'No matching documents'}
          description={
            documents.length === 0
              ? 'Upload PDFs, Word files, text or scanned images. Each is classified, summarized, scanned for PII and indexed for cited answers.'
              : 'Try a different search or clear the filter.'
          }
          action={documents.length === 0 ? emptyAction : undefined}
        />
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-wider text-subtle">
                  <th scope="col" className="px-5 py-2.5 font-medium">
                    Document
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Type
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Quality
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    PII
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right font-medium">
                    Chunks
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Added
                  </th>
                  <th scope="col" className="px-5 py-2.5 text-right font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((d) => (
                  <tr key={d.id} className="group transition-colors hover:bg-elevated/50">
                    <td className="max-w-[22rem] px-5 py-3">
                      <div className="flex items-start gap-2.5">
                        <Icon name="file" className="mt-0.5 h-4 w-4 text-subtle" />
                        <div className="min-w-0">
                          <Link
                            to={`/documents/${d.id}`}
                            className="block truncate font-medium text-fg hover:text-accent-soft hover:underline"
                            title={d.filename}
                          >
                            {d.filename}
                          </Link>
                          {d.summary ? (
                            <p className="truncate text-xs text-subtle" title={d.summary}>
                              {d.summary}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      {d.status && d.status !== 'completed' ? (
                        <Badge
                          tone={d.status === 'failed' ? 'danger' : 'accent'}
                          dot
                          title={d.status_detail ?? undefined}
                        >
                          {d.status === 'failed' ? 'Failed' : d.status === 'queued' ? 'Queued' : 'Processing'}
                        </Badge>
                      ) : (
                        <DocTypeBadge type={d.doc_type} />
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <QualityMeter value={d.quality_score} />
                    </td>
                    <td className="px-3 py-3">
                      <PiiBadge count={d.pii_count} />
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums text-muted">{num(d.chunk_count)}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-xs text-muted" title={fullDate(d.created_at)}>
                      {relTime(d.created_at)}
                    </td>
                    <td className="px-5 py-3">
                      <RowActions doc={d} onDelete={onDelete} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile list */}
          <ul className="divide-y divide-line md:hidden">
            {rows.map((d) => (
              <li key={d.id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <Link to={`/documents/${d.id}`} className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{d.filename}</p>
                    <p className="mt-0.5 text-xs text-subtle">
                      {humanize(d.doc_type)} · {num(d.chunk_count)} chunks · {relTime(d.created_at)}
                    </p>
                  </Link>
                  <RowActions doc={d} onDelete={onDelete} />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <QualityMeter value={d.quality_score} />
                  <PiiBadge count={d.pii_count} />
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}
