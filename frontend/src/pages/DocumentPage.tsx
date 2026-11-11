import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { documentsApi, errorMessage, httpStatus } from '../api';
import ExtractionPanel from '../components/ExtractionPanel';
import StatementPanel from '../components/StatementPanel';
import { FlagList, InjectionBanner } from '../components/SecurityFlags';
import { DocTypeBadge } from '../components/Signals';
import { Badge } from '../components/ui/Badge';
import { Button, LinkButton } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Meter } from '../components/ui/Meter';
import { Banner, Page, PageHeader } from '../components/ui/PageHeader';
import { PageLoader } from '../components/ui/Spinner';
import { useConfirm } from '../components/ui/Dialog';
import { useToast } from '../components/ui/Toast';
import { cx } from '../lib/cx';
import { entityColor, entityLabel, normType } from '../lib/entities';
import { fullDate, isNum, num, pct, qualityTone, scoreTone } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { DocumentDetail } from '../types';

const ENTITY_PREVIEW = 20;

export default function DocumentPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const id = idParam && /^\d+$/.test(idParam) ? Number(idParam) : NaN;
  const navigate = useNavigate();
  const toast = useToast();
  const confirm = useConfirm();

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [limited, setLimited] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entityType, setEntityType] = useState<string | null>(null);
  const [showAllEntities, setShowAllEntities] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  useTitle(doc?.filename ?? 'Document');

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError('Invalid document id.');
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(null);
    documentsApi
      .get(id)
      .then((d) => {
        if (!alive) return;
        setDoc(d);
        setLimited(false);
      })
      .catch(async (e) => {
        // Fallback for v1 backends without GET /documents/{id}: use the list entry.
        try {
          const list = await documentsApi.list();
          const hit = list.find((x) => x.id === id);
          if (!alive) return;
          if (hit && httpStatus(e) !== 403) {
            setDoc({
              id: hit.id,
              filename: hit.filename,
              created_at: hit.created_at,
              doc_type: hit.doc_type,
              summary: hit.summary,
              stats: { pages: hit.pages, chunks: hit.chunk_count },
              vision: isNum(hit.quality_score) ? { overall_quality: hit.quality_score } : null,
              pii: isNum(hit.pii_count) ? { count: hit.pii_count, types: {} } : null,
            });
            setLimited(true);
          } else {
            setError(httpStatus(e) === 404 ? 'Document not found in this workspace.' : errorMessage(e, 'Failed to load document'));
          }
        } catch {
          if (alive) setError(errorMessage(e, 'Failed to load document'));
        }
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id]);

  const entities = useMemo(() => [...(doc?.entities ?? [])].sort((a, b) => (b.count ?? 0) - (a.count ?? 0)), [doc]);
  const entityTypes = useMemo(() => {
    const m = new Map<string, number>();
    entities.forEach((e) => m.set(normType(e.type), (m.get(normType(e.type)) ?? 0) + 1));
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [entities]);
  const filteredEntities = entityType ? entities.filter((e) => normType(e.type) === entityType) : entities;
  const shownEntities = showAllEntities ? filteredEntities : filteredEntities.slice(0, ENTITY_PREVIEW);
  const keywords = doc?.keywords ?? [];
  const maxKw = Math.max(0.0001, ...keywords.map((k) => k.score ?? 0));

  const del = async () => {
    if (!doc) return;
    const ok = await confirm({
      title: 'Delete document?',
      description: `“${doc.filename}” and all derived data will be permanently removed. This cannot be undone.`,
      confirmLabel: 'Delete document',
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await documentsApi.remove(doc.id);
      toast.success('Document deleted', doc.filename);
      navigate('/upload', { replace: true });
    } catch (e) {
      toast.error('Delete failed', errorMessage(e));
    }
  };

  if (loading) return <PageLoader label="Loading document analysis…" />;
  if (error || !doc) {
    return (
      <Page>
        <Card>
          <EmptyState
            icon="alert"
            title="Document unavailable"
            description={error ?? 'Unknown error'}
            action={
              <LinkButton to="/upload" size="sm">
                Back to documents
              </LinkButton>
            }
          />
        </Card>
      </Page>
    );
  }

  const stats = doc.stats ?? {};
  const vision = doc.vision ?? null;
  const pages = vision?.pages ?? [];
  const pii = doc.pii ?? null;
  const flags = doc.security_flags ?? [];

  const statItems: Array<[string, string]> = [
    ['Pages', num(stats.pages)],
    ['Words', num(stats.words)],
    ['Characters', num(stats.characters)],
    ['Chunks', num(stats.chunks)],
    ['Reading time', isNum(stats.reading_time_min) ? `${num(stats.reading_time_min)} min` : '—'],
    ['Readability', isNum(stats.readability) ? num(stats.readability, 1) : '—'],
  ];

  return (
    <Page>
      <PageHeader
        eyebrow={
          <Link to="/upload" className="inline-flex items-center gap-1 text-xs text-subtle hover:text-fg">
            ← Documents
          </Link>
        }
        title={doc.filename}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <DocTypeBadge type={doc.doc_type} confidence={doc.doc_type_confidence} />
            <span className="text-xs text-subtle">Uploaded {fullDate(doc.created_at)}</span>
            <span className="text-xs text-subtle">· ID {doc.id}</span>
          </span>
        }
        actions={
          <>
            <LinkButton to={`/chat?document=${doc.id}`} variant="primary" icon="chat">
              Chat with this document
            </LinkButton>
            <LinkButton to={`/graph?document=${doc.id}`} icon="graph">
              View in graph
            </LinkButton>
            <LinkButton to={`/timeline?document=${doc.id}`} icon="calendar" aria-label="View timeline">
              <span className="hidden sm:inline">Timeline</span>
            </LinkButton>
            <Button variant="danger-ghost" icon="trash" onClick={del} aria-label="Delete document" />
          </>
        }
      />

      <div className="space-y-6">
        {limited ? (
          <Banner tone="info" title="Limited analysis">
            The connected backend does not provide per-document analysis (GET /documents/{'{id}'}). Showing list metadata only.
          </Banner>
        ) : null}
        <InjectionBanner flags={flags} />

        <div className="grid gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <Card>
              <CardHeader icon="sparkles" title="Summary" description="Generated on upload" />
              <CardBody>
                {doc.summary ? <p className="text-sm leading-relaxed text-fg/90">{doc.summary}</p> : <p className="text-sm text-subtle">No summary available.</p>}
                {keywords.length > 0 ? (
                  <div className="mt-5">
                    <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-subtle">Keywords</p>
                    <div className="flex flex-wrap items-baseline gap-1.5">
                      {keywords.map((k) => {
                        const w = Math.max(0, Math.min(1, (k.score ?? 0) / maxKw));
                        return (
                          <span
                            key={k.term}
                            title={`TF-IDF weight ${(k.score ?? 0).toFixed(3)}`}
                            className="rounded-md border border-accent/20 px-2 py-0.5 text-accent-soft"
                            style={{ fontSize: `${11 + w * 6}px`, backgroundColor: `rgb(var(--accent) / ${0.04 + w * 0.16})`, fontWeight: w > 0.6 ? 600 : 500 }}
                          >
                            {k.term}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                icon="tag"
                title="Entities"
                description={`${entities.length} named entities extracted`}
                actions={
                  <LinkButton to={`/graph?document=${doc.id}`} size="xs" variant="ghost" icon="graph">
                    Graph
                  </LinkButton>
                }
              />
              {entities.length === 0 ? (
                <EmptyState icon="tag" title="No entities" description="Entity extraction was not run for this document." compact />
              ) : (
                <>
                  <div className="flex flex-wrap gap-1.5 border-b border-line px-4 py-2.5 sm:px-5" role="group" aria-label="Filter entities by type">
                    <button
                      type="button"
                      onClick={() => setEntityType(null)}
                      aria-pressed={entityType === null}
                      className={cx('rounded-md px-2 py-0.5 text-xs', entityType === null ? 'bg-elevated font-medium text-fg' : 'text-muted hover:text-fg')}
                    >
                      All {entities.length}
                    </button>
                    {entityTypes.map(([t, n]) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setEntityType(entityType === t ? null : t)}
                        aria-pressed={entityType === t}
                        className={cx('inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs', entityType === t ? 'bg-elevated font-medium text-fg' : 'text-muted hover:text-fg')}
                      >
                        <span className="h-2 w-2 rounded-full" style={{ background: entityColor(t) }} aria-hidden="true" />
                        {entityLabel(t)} {n}
                      </button>
                    ))}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-line text-[11px] uppercase tracking-wider text-subtle">
                          <th scope="col" className="px-5 py-2 font-medium">
                            Entity
                          </th>
                          <th scope="col" className="px-3 py-2 font-medium">
                            Type
                          </th>
                          <th scope="col" className="px-5 py-2 text-right font-medium">
                            Mentions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {shownEntities.map((e, i) => (
                          <tr key={`${e.name}-${i}`} className="hover:bg-elevated/50">
                            <td className="max-w-[20rem] truncate px-5 py-2 text-fg" title={e.name}>
                              {e.name}
                            </td>
                            <td className="px-3 py-2">
                              <span className="inline-flex items-center gap-1.5 text-xs text-muted">
                                <span className="h-2 w-2 rounded-full" style={{ background: entityColor(e.type) }} aria-hidden="true" />
                                {entityLabel(e.type)}
                              </span>
                            </td>
                            <td className="px-5 py-2 text-right tabular-nums text-muted">{num(e.count)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {filteredEntities.length > ENTITY_PREVIEW ? (
                    <div className="border-t border-line px-4 py-2 sm:px-5">
                      <Button size="xs" variant="ghost" onClick={() => setShowAllEntities((v) => !v)}>
                        {showAllEntities ? 'Show fewer' : `Show all ${filteredEntities.length}`}
                      </Button>
                    </div>
                  ) : null}
                </>
              )}
            </Card>

            <Card>
              <CardHeader
                icon="eye"
                title="Vision pipeline"
                description="Per-page extraction method and image quality"
                actions={
                  vision ? (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {isNum(vision.overall_quality) ? <Badge tone={scoreTone(vision.overall_quality)}>Quality {pct(vision.overall_quality)}</Badge> : null}
                      {isNum(vision.ocr_pages) ? <Badge tone={vision.ocr_pages > 0 ? 'info' : 'neutral'}>{vision.ocr_pages} OCR pages</Badge> : null}
                    </div>
                  ) : null
                }
              />
              {pages.length === 0 ? (
                <EmptyState icon="eye" title="No per-page data" description="Page-level vision analysis is available for documents uploaded with v2." compact />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full whitespace-nowrap text-left text-sm">
                    <thead>
                      <tr className="border-b border-line text-[11px] uppercase tracking-wider text-subtle">
                        <th scope="col" className="px-5 py-2 font-medium">
                          Page
                        </th>
                        <th scope="col" className="px-3 py-2 font-medium">
                          Method
                        </th>
                        <th scope="col" className="px-3 py-2 font-medium">
                          OCR conf.
                        </th>
                        <th scope="col" className="px-3 py-2 text-right font-medium" title="Variance of Laplacian; higher is sharper">
                          Blur score
                        </th>
                        <th scope="col" className="px-3 py-2 font-medium">
                          Quality
                        </th>
                        <th scope="col" className="px-3 py-2 text-right font-medium">
                          Skew
                        </th>
                        <th scope="col" className="px-3 py-2 text-right font-medium">
                          Tables
                        </th>
                        <th scope="col" className="px-5 py-2 text-right font-medium">
                          Figures
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {pages.map((p) => (
                        <tr key={p.page} className="hover:bg-elevated/50">
                          <td className="px-5 py-2 tabular-nums text-fg">{p.page}</td>
                          <td className="px-3 py-2">
                            <Badge tone={p.method === 'ocr' ? 'info' : 'neutral'}>{p.method ?? '—'}</Badge>
                          </td>
                          <td className="px-3 py-2">
                            {isNum(p.ocr_confidence) ? (
                              <div className="flex items-center gap-2">
                                <Meter value={p.ocr_confidence} size="xs" className="w-12" label="OCR confidence" />
                                <span className="text-xs tabular-nums text-muted">{pct(p.ocr_confidence)}</span>
                              </div>
                            ) : (
                              <span className="text-subtle">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-right tabular-nums text-muted">{isNum(p.blur_score) ? num(p.blur_score, 1) : '—'}</td>
                          <td className="px-3 py-2">{p.quality ? <Badge tone={qualityTone(p.quality)}>{p.quality}</Badge> : <span className="text-subtle">—</span>}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-muted">{isNum(p.skew_angle) ? `${p.skew_angle.toFixed(1)}°` : '—'}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-muted">{num(p.tables_detected)}</td>
                          <td className="px-5 py-2 text-right tabular-nums text-muted">{num(p.figures_detected)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {!limited ? <ExtractionPanel documentId={doc.id} docType={doc.doc_type} /> : null}

            {!limited && /\.(pdf|json|xml)$/i.test(doc.filename ?? '') ? <StatementPanel documentId={doc.id} autoLoad={doc.doc_type === 'bank_statement'} /> : null}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader icon="layers" title="Statistics" />
              <CardBody>
                <dl className="grid grid-cols-2 gap-3">
                  {statItems.map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-line p-2.5">
                      <dt className="text-[11px] uppercase tracking-wider text-subtle">{label}</dt>
                      <dd className="mt-0.5 text-base font-semibold tabular-nums text-fg">{value}</dd>
                    </div>
                  ))}
                </dl>
              </CardBody>
            </Card>

            <Card>
              <CardHeader icon="shield" title="PII summary" description="Personally identifiable information detected" />
              <CardBody>
                {pii ? (
                  <>
                    <p className={cx('text-2xl font-semibold tabular-nums', pii.count > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-fg')}>{num(pii.count)}</p>
                    <p className="text-xs text-muted">{pii.count > 0 ? 'items found — review before sharing or sending to cloud models' : 'No PII detected'}</p>
                    {Object.keys(pii.types ?? {}).length > 0 ? (
                      <ul className="mt-3 space-y-2">
                        {Object.entries(pii.types)
                          .sort((a, b) => b[1] - a[1])
                          .map(([t, n]) => (
                            <li key={t}>
                              <div className="mb-1 flex justify-between text-xs">
                                <span className="font-mono text-fg">{t}</span>
                                <span className="tabular-nums text-muted">{n}</span>
                              </div>
                              <Meter value={n} max={Math.max(1, pii.count)} tone="warning" size="xs" label={`${t}: ${n}`} />
                            </li>
                          ))}
                      </ul>
                    ) : null}
                  </>
                ) : (
                  <p className="text-sm text-subtle">PII scan not available for this document.</p>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader icon="alert" title="Security flags" description="Prompt-injection & content risk scan" />
              <CardBody>{limited ? <p className="text-sm text-subtle">Not available.</p> : <FlagList flags={flags} />}</CardBody>
            </Card>

            {doc.preview ? (
              <Card>
                <CardHeader
                  icon="file"
                  title="Text preview"
                  actions={
                    <Button size="xs" variant="ghost" onClick={() => setPreviewOpen((v) => !v)} aria-expanded={previewOpen}>
                      {previewOpen ? 'Collapse' : 'Expand'}
                    </Button>
                  }
                />
                <CardBody>
                  <pre className={cx('whitespace-pre-wrap break-words font-mono text-[12px] leading-relaxed text-muted', !previewOpen && 'line-clamp-[10]')}>{doc.preview}</pre>
                </CardBody>
              </Card>
            ) : null}
          </div>
        </div>
      </div>
    </Page>
  );
}
