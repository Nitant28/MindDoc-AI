import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { documentsApi, errorMessage, intelApi } from '../api';
import ForceGraph, { type ForceGraphHandle } from '../components/ForceGraph';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input, Select } from '../components/ui/Field';
import { Icon } from '../components/ui/Icon';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Spinner } from '../components/ui/Spinner';
import { cx } from '../lib/cx';
import { entityColor, entityLabel, normType } from '../lib/entities';
import { humanize } from '../lib/format';
import { useTheme } from '../lib/theme';
import { useTitle } from '../lib/useTitle';
import type { DocumentSummary, GraphData, GraphNode } from '../types';

const LIMITS = [50, 100, 150, 300];

function NodeSearch({ nodes, onPick }: { nodes: GraphNode[]; onPick: (id: string) => void }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const inputId = useId();

  const results = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return [];
    return nodes
      .filter((n) => (n.label ?? '').toLowerCase().includes(needle))
      .sort((a, b) => Number((b.label ?? '').toLowerCase().startsWith(needle)) - Number((a.label ?? '').toLowerCase().startsWith(needle)) || b.weight - a.weight)
      .slice(0, 8);
  }, [nodes, q]);

  const pick = (n: GraphNode) => {
    onPick(n.id);
    setQ(n.label);
    setOpen(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      const n = results[active];
      if (n) {
        e.preventDefault();
        pick(n);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className="relative w-full sm:w-64">
      <label htmlFor={inputId} className="sr-only">
        Search entities
      </label>
      <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
      <Input
        id={inputId}
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && results[active] ? `${listId}-${active}` : undefined}
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
        placeholder="Find an entity…"
        className="h-8 pl-8 text-[13px]"
      />
      {open && results.length > 0 ? (
        <ul id={listId} role="listbox" className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-line bg-surface py-1 shadow-xl">
          {results.map((n, i) => (
            <li
              key={n.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(n);
              }}
              onMouseEnter={() => setActive(i)}
              className={cx('flex cursor-pointer items-center gap-2 px-2.5 py-1.5 text-sm', i === active ? 'bg-elevated text-fg' : 'text-muted')}
            >
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: entityColor(n.type) }} aria-hidden="true" />
              <span className="min-w-0 truncate">{n.label}</span>
              <span className="ml-auto shrink-0 text-[11px] text-subtle">{entityLabel(n.type)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default function GraphPage() {
  useTitle('Knowledge Graph');
  const { theme } = useTheme();
  const [params, setParams] = useSearchParams();
  const docParam = params.get('document');
  const documentId = docParam && /^\d+$/.test(docParam) ? Number(docParam) : null;

  const [limit, setLimit] = useState(150);
  const [data, setData] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [labels, setLabels] = useState(true);
  const graphRef = useRef<ForceGraphHandle>(null);
  const docSelectId = useId();
  const limitId = useId();

  useEffect(() => {
    documentsApi
      .list()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await intelApi.graph({ document_id: documentId, limit }));
      setSelectedId(null);
    } catch (e) {
      setError(errorMessage(e, 'Failed to load the knowledge graph'));
      setData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  }, [documentId, limit]);

  useEffect(() => {
    void load();
  }, [load]);

  const typeCounts = useMemo(() => {
    const m = new Map<string, number>();
    data.nodes.forEach((n) => m.set(normType(n.type), (m.get(normType(n.type)) ?? 0) + 1));
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [data.nodes]);

  const visible = useMemo(() => {
    const nodes = data.nodes.filter((n) => !hidden.has(normType(n.type)));
    const ids = new Set(nodes.map((n) => n.id));
    return { nodes, edges: data.edges.filter((e) => ids.has(e.source) && ids.has(e.target)) };
  }, [data, hidden]);

  const nodeById = useMemo(() => new Map(data.nodes.map((n) => [n.id, n])), [data.nodes]);
  const docName = useMemo(() => new Map(documents.map((d) => [d.id, d.filename])), [documents]);
  const selected = selectedId ? nodeById.get(selectedId) ?? null : null;

  useEffect(() => {
    if (selected && hidden.has(normType(selected.type))) setSelectedId(null);
  }, [hidden, selected]);

  const connections = useMemo(() => {
    if (!selectedId) return [];
    const out: Array<{ node: GraphNode; relation: string; weight: number }> = [];
    for (const e of visible.edges) {
      if (e.source !== selectedId && e.target !== selectedId) continue;
      const other = nodeById.get(e.source === selectedId ? e.target : e.source);
      if (other) out.push({ node: other, relation: e.relation, weight: e.weight });
    }
    return out.sort((a, b) => b.weight - a.weight);
  }, [selectedId, visible.edges, nodeById]);

  const focusNode = (id: string) => {
    const n = nodeById.get(id);
    if (n && hidden.has(normType(n.type))) {
      setHidden((h) => {
        const next = new Set(h);
        next.delete(normType(n.type));
        return next;
      });
    }
    setSelectedId(id);
    window.setTimeout(() => graphRef.current?.focus(id), 30);
  };

  const toggleType = (t: string) =>
    setHidden((h) => {
      const next = new Set(h);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });

  const setDocFilter = (v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set('document', v);
    else next.delete('document');
    setParams(next, { replace: true });
  };

  return (
    <Page wide>
      <PageHeader
        title="Knowledge graph"
        description="Entities extracted from your documents, the relations the documents state, and which names appear together."
        actions={
          <Button icon="refresh" onClick={() => void load()} loading={loading}>
            Refresh
          </Button>
        }
      />

      <Card className="mb-4">
        <CardBody className="flex flex-wrap items-end gap-3 py-3">
          <div>
            <label htmlFor={docSelectId} className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-subtle">
              Document
            </label>
            <Select id={docSelectId} value={documentId ?? ''} onChange={(e) => setDocFilter(e.target.value)} className="h-8 w-56 text-[13px]">
              <option value="">All documents</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
              {documentId != null && !documents.some((d) => d.id === documentId) ? <option value={documentId}>Document #{documentId}</option> : null}
            </Select>
          </div>
          <div>
            <label htmlFor={limitId} className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-subtle">
              Max entities
            </label>
            <Select id={limitId} value={limit} onChange={(e) => setLimit(Number(e.target.value))} className="h-8 w-28 text-[13px]">
              {LIMITS.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </Select>
          </div>
          <NodeSearch nodes={visible.nodes} onPick={focusNode} />
          <label className="flex h-8 items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={labels} onChange={(e) => setLabels(e.target.checked)} className="h-3.5 w-3.5 accent-indigo-500" />
            Labels
          </label>
          <span className="ml-auto text-xs tabular-nums text-subtle">
            {visible.nodes.length} entities · {visible.edges.filter((e) => !e.weak).length} relations ·{' '}
            {visible.edges.filter((e) => e.weak).length} named together
          </span>
        </CardBody>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card className="relative h-[62vh] min-h-[420px] overflow-hidden bg-dots">
          {loading && data.nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted">
              <Spinner size="lg" className="text-accent" label="Loading graph" />
            </div>
          ) : error ? (
            <div className="flex h-full items-center justify-center">
              <EmptyState icon="alert" title="Graph unavailable" description={error} action={<Button size="sm" onClick={() => void load()}>Retry</Button>} />
            </div>
          ) : data.nodes.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <EmptyState
                icon="graph"
                title="No entities yet"
                description="Upload documents and MindDoc will extract people, organizations, dates, amounts and more into a navigable graph."
              />
            </div>
          ) : (
            <>
              <ForceGraph
                ref={graphRef}
                nodes={visible.nodes}
                edges={visible.edges}
                selectedId={selectedId}
                onSelect={setSelectedId}
                dark={theme === 'dark'}
                showLabels={labels}
              />
              <div className="absolute right-3 top-3 flex flex-col gap-1 rounded-lg border border-line bg-surface/90 p-1 shadow-sm backdrop-blur">
                <Button variant="ghost" size="icon-sm" aria-label="Zoom in" title="Zoom in (+)" icon="plus" onClick={() => graphRef.current?.zoomIn()} />
                <Button variant="ghost" size="icon-sm" aria-label="Zoom out" title="Zoom out (−)" icon="minus" onClick={() => graphRef.current?.zoomOut()} />
                <Button variant="ghost" size="icon-sm" aria-label="Fit graph to view" title="Fit (0)" icon="maximize" onClick={() => graphRef.current?.fit()} />
                <Button variant="ghost" size="icon-sm" aria-label="Re-run layout" title="Re-run layout" icon="refresh" onClick={() => graphRef.current?.reheat()} />
              </div>
              <p className="pointer-events-none absolute bottom-2 left-3 hidden text-[11px] text-subtle sm:block">
                Drag nodes · drag background to pan · scroll to zoom · click to inspect
              </p>
              {loading ? (
                <div className="absolute left-3 top-3">
                  <Spinner size="sm" className="text-accent" label="Refreshing" />
                </div>
              ) : null}
            </>
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader
              title="Entity types"
              description="Toggle to filter"
              actions={
                hidden.size > 0 ? (
                  <Button size="xs" variant="ghost" onClick={() => setHidden(new Set())}>
                    Show all
                  </Button>
                ) : null
              }
            />
            <CardBody className="py-3">
              {typeCounts.length === 0 ? (
                <p className="text-xs text-subtle">No types.</p>
              ) : (
                <ul className="grid grid-cols-2 gap-1 lg:grid-cols-1">
                  {typeCounts.map(([t, n]) => (
                    <li key={t}>
                      <label className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs hover:bg-elevated">
                        <input type="checkbox" checked={!hidden.has(t)} onChange={() => toggleType(t)} className="h-3.5 w-3.5 accent-indigo-500" />
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: entityColor(t) }} aria-hidden="true" />
                        <span className={cx('truncate', hidden.has(t) ? 'text-subtle line-through' : 'text-fg')}>{entityLabel(t)}</span>
                        <span className="ml-auto tabular-nums text-subtle">{n}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Inspector" description={selected ? undefined : 'Select a node to inspect it'} />
            {selected ? (
              <CardBody className="space-y-4">
                <div>
                  <p className="break-words text-base font-semibold text-fg">{selected.label}</p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-elevated px-1.5 py-0.5 text-[11px] font-medium text-fg">
                      <span className="h-2 w-2 rounded-full" style={{ background: entityColor(selected.type) }} aria-hidden="true" />
                      {entityLabel(selected.type)}
                    </span>
                    <Badge>weight {selected.weight}</Badge>
                    <Badge>{connections.length} links</Badge>
                  </div>
                </div>

                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-subtle">Connected entities</p>
                  {connections.length === 0 ? (
                    <p className="text-xs text-subtle">No visible connections.</p>
                  ) : (
                    <ul className="max-h-60 space-y-0.5 overflow-y-auto">
                      {connections.map((c) => (
                        <li key={c.node.id}>
                          <button
                            type="button"
                            onClick={() => focusNode(c.node.id)}
                            className="flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left text-xs hover:bg-elevated"
                          >
                            <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: entityColor(c.node.type) }} aria-hidden="true" />
                            <span className="min-w-0 truncate text-fg">{c.node.label}</span>
                            <span className="ml-auto shrink-0 font-mono text-[10px] text-subtle">
                              {humanize(c.relation, 'related')} ×{c.weight}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-subtle">Documents</p>
                  {(selected.documents ?? []).length === 0 ? (
                    <p className="text-xs text-subtle">Unknown.</p>
                  ) : (
                    <ul className="space-y-1">
                      {(selected.documents ?? []).map((d) => (
                        <li key={d}>
                          <Link to={`/documents/${d}`} className="flex items-center gap-2 rounded-md px-1.5 py-1 text-xs text-muted hover:bg-elevated hover:text-fg">
                            <Icon name="file" className="h-3.5 w-3.5 text-subtle" />
                            <span className="truncate">{docName.get(d) ?? `Document #${d}`}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <Button size="xs" variant="ghost" icon="x" onClick={() => setSelectedId(null)}>
                  Clear selection
                </Button>
              </CardBody>
            ) : (
              <CardBody>
                <p className="text-xs leading-relaxed text-muted">
                  Node size reflects how often an entity is mentioned. Solid edges are relations stated in a document; dashed edges only mean two names appear in the same passage, which is not a relationship. Hover to preview, click to
                  pin, or use search to jump to an entity.
                </p>
              </CardBody>
            )}
          </Card>
        </div>
      </div>
    </Page>
  );
}
