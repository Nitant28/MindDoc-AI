/**
 * Dependency-free force-directed graph on <canvas>.
 * Forces: pairwise repulsion (Coulomb) + collision, spring edges (Hooke), centering gravity, velocity damping.
 * Interaction: drag nodes, drag background to pan, wheel / buttons / +- keys to zoom, hover tooltip, click to select.
 */
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from 'react';
import { entityColor, entityLabel } from '../lib/entities';
import type { GraphEdge, GraphNode } from '../types';

export interface ForceGraphHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  fit: () => void;
  focus: (id: string) => void;
  reheat: () => void;
}

interface ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  dark: boolean;
  showLabels?: boolean;
  className?: string;
}

interface SimNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  fixed: boolean;
  node: GraphNode;
}

interface SimEdge {
  s: SimNode;
  t: SimNode;
  w: number;
  dashed: boolean; // weak signal: drawn dashed
}

interface Sim {
  nodes: SimNode[];
  edges: SimEdge[];
  byId: Map<string, SimNode>;
  neighbors: Map<string, Set<string>>;
  alpha: number;
}

interface View {
  x: number;
  y: number;
  k: number;
}

const REPULSION = 900;
const SPRING = 0.05;
const GRAVITY = 0.012;
const DAMPING = 0.6;
const ALPHA_MIN = 0.004;
const ALPHA_DECAY = 0.0228;
const MIN_K = 0.08;
const MAX_K = 6;

function tick(s: Sim): void {
  const alpha = s.alpha;
  const ns = s.nodes;
  const n = ns.length;
  for (let i = 0; i < n; i++) {
    const a = ns[i];
    for (let j = i + 1; j < n; j++) {
      const b = ns[j];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 0.01) {
        dx = Math.random() - 0.5;
        dy = Math.random() - 0.5;
        d2 = dx * dx + dy * dy + 0.01;
      }
      const d = Math.sqrt(d2);
      let f = (REPULSION * (1 + (a.r + b.r) / 24) * alpha) / d2;
      const minD = a.r + b.r + 6;
      if (d < minD) f += ((minD - d) / d) * 0.5 * alpha * d;
      const fx = (dx / d) * f;
      const fy = (dy / d) * f;
      a.vx -= fx;
      a.vy -= fy;
      b.vx += fx;
      b.vy += fy;
    }
  }
  for (const e of s.edges) {
    const dx = e.t.x - e.s.x;
    const dy = e.t.y - e.s.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
    const len = 50 + e.s.r + e.t.r;
    const k = SPRING * Math.min(2, 0.6 + Math.log2(1 + e.w) * 0.4);
    const f = (d - len) * k * alpha;
    const fx = (dx / d) * f;
    const fy = (dy / d) * f;
    e.s.vx += fx;
    e.s.vy += fy;
    e.t.vx -= fx;
    e.t.vy -= fy;
  }
  for (const a of ns) {
    if (a.fixed) {
      a.vx = 0;
      a.vy = 0;
      continue;
    }
    a.vx -= a.x * GRAVITY * alpha;
    a.vy -= a.y * GRAVITY * alpha;
    a.vx = Math.max(-40, Math.min(40, a.vx * DAMPING));
    a.vy = Math.max(-40, Math.min(40, a.vy * DAMPING));
    a.x += a.vx;
    a.y += a.vy;
  }
  s.alpha += (0 - s.alpha) * ALPHA_DECAY;
}

const truncate = (s: string, n = 28) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

const ForceGraph = forwardRef<ForceGraphHandle, ForceGraphProps>(function ForceGraph(
  { nodes, edges, selectedId, onSelect, dark, showLabels = true, className },
  ref,
) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const sim = useRef<Sim>({ nodes: [], edges: [], byId: new Map(), neighbors: new Map(), alpha: 0 });
  const view = useRef<View>({ x: 0, y: 0, k: 1 });
  const target = useRef<View | null>(null);
  const size = useRef({ w: 0, h: 0, dpr: 1 });
  const dirty = useRef(true);
  const fitPending = useRef(true);
  const hoverRef = useRef<string | null>(null);
  const selectedRef = useRef<string | null>(selectedId);
  const opts = useRef({ dark, showLabels, onSelect });
  opts.current = { dark, showLabels, onSelect };
  const drag = useRef<{
    mode: 'node' | 'pan';
    node?: SimNode;
    startX: number;
    startY: number;
    lastX: number;
    lastY: number;
    moved: boolean;
  } | null>(null);
  const [hovered, setHovered] = useState<{ node: GraphNode; degree: number } | null>(null);

  // ── build / merge simulation on data change ───────────────────
  useEffect(() => {
    const prev = sim.current.byId;
    const maxW = Math.max(1, ...nodes.map((n) => (Number.isFinite(n.weight) ? n.weight : 1)));
    const byId = new Map<string, SimNode>();
    let fresh = 0;
    const simNodes = nodes.map((n, i) => {
      const r = 4 + Math.sqrt(Math.max(1, n.weight || 1) / maxW) * 12;
      const old = prev.get(n.id);
      if (old) {
        old.node = n;
        old.r = r;
        byId.set(n.id, old);
        return old;
      }
      fresh++;
      const angle = i * 2.399963; // golden angle spiral
      const rad = 18 * Math.sqrt(i + 1);
      const sn: SimNode = { id: n.id, x: Math.cos(angle) * rad, y: Math.sin(angle) * rad, vx: 0, vy: 0, r, fixed: false, node: n };
      byId.set(n.id, sn);
      return sn;
    });
    const neighbors = new Map<string, Set<string>>();
    const simEdges: SimEdge[] = [];
    for (const e of edges) {
      const s = byId.get(e.source);
      const t = byId.get(e.target);
      if (!s || !t || s === t) continue;
      simEdges.push({ s, t, w: Number.isFinite(e.weight) ? e.weight : 1, dashed: !!e.weak });
      if (!neighbors.has(s.id)) neighbors.set(s.id, new Set());
      if (!neighbors.has(t.id)) neighbors.set(t.id, new Set());
      neighbors.get(s.id)?.add(t.id);
      neighbors.get(t.id)?.add(s.id);
    }
    const next: Sim = { nodes: simNodes, edges: simEdges, byId, neighbors, alpha: fresh > 0 ? 1 : 0.3 };
    if (fresh > simNodes.length / 3) {
      // pre-warm so the first frame is already laid out
      const ticks = simNodes.length > 250 ? 90 : 160;
      for (let i = 0; i < ticks; i++) tick(next);
      fitPending.current = true;
    }
    sim.current = next;
    dirty.current = true;
  }, [nodes, edges]);

  useEffect(() => {
    selectedRef.current = selectedId;
    dirty.current = true;
  }, [selectedId]);

  useEffect(() => {
    dirty.current = true;
  }, [dark, showLabels]);

  // ── view helpers ──────────────────────────────────────────────
  const computeFit = useCallback((): View | null => {
    const { w, h } = size.current;
    const ns = sim.current.nodes;
    if (!w || !h || ns.length === 0) return null;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const n of ns) {
      minX = Math.min(minX, n.x - n.r);
      minY = Math.min(minY, n.y - n.r);
      maxX = Math.max(maxX, n.x + n.r);
      maxY = Math.max(maxY, n.y + n.r);
    }
    const pad = 48;
    const k = Math.max(MIN_K, Math.min(2, Math.min((w - pad * 2) / Math.max(1, maxX - minX), (h - pad * 2) / Math.max(1, maxY - minY))));
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    return { x: w / 2 - cx * k, y: h / 2 - cy * k, k };
  }, []);

  const zoomAt = useCallback((sx: number, sy: number, factor: number) => {
    const v = target.current ?? view.current;
    const k = Math.max(MIN_K, Math.min(MAX_K, v.k * factor));
    const wx = (sx - v.x) / v.k;
    const wy = (sy - v.y) / v.k;
    target.current = { x: sx - wx * k, y: sy - wy * k, k };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      zoomIn: () => zoomAt(size.current.w / 2, size.current.h / 2, 1.35),
      zoomOut: () => zoomAt(size.current.w / 2, size.current.h / 2, 1 / 1.35),
      fit: () => {
        const f = computeFit();
        if (f) target.current = f;
      },
      focus: (id: string) => {
        const n = sim.current.byId.get(id);
        if (!n) return;
        const k = Math.max(view.current.k, 1.4);
        target.current = { x: size.current.w / 2 - n.x * k, y: size.current.h / 2 - n.y * k, k };
      },
      reheat: () => {
        sim.current.alpha = 0.9;
      },
    }),
    [computeFit, zoomAt],
  );

  // ── resize ────────────────────────────────────────────────────
  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;
    const ro = new ResizeObserver(() => {
      const rect = wrap.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const prev = size.current;
      if (prev.w === 0) {
        view.current = { x: rect.width / 2, y: rect.height / 2, k: 1 };
      } else {
        view.current.x += (rect.width - prev.w) / 2;
        view.current.y += (rect.height - prev.h) / 2;
      }
      size.current = { w: rect.width, h: rect.height, dpr };
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      dirty.current = true;
    });
    ro.observe(wrap);
    return () => ro.disconnect();
  }, []);

  // ── render loop ───────────────────────────────────────────────
  useEffect(() => {
    let raf = 0;
    const draw = () => {
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (!canvas || !ctx) return;
      const { w, h, dpr } = size.current;
      const { dark: isDark, showLabels: labels } = opts.current;
      const s = sim.current;
      const v = view.current;
      const C = isDark
        ? { edge: '#52525b', edgeActive: '#818cf8', label: '#e4e4e7', halo: 'rgba(17,17,20,0.92)', ring: '#ffffff', stroke: '#111114' }
        : { edge: '#a1a1aa', edgeActive: '#4f46e5', label: '#27272a', halo: 'rgba(255,255,255,0.92)', ring: '#18181b', stroke: '#ffffff' };

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.save();
      ctx.translate(v.x, v.y);
      ctx.scale(v.k, v.k);

      const focusId = hoverRef.current ?? selectedRef.current;
      const nb = focusId ? s.neighbors.get(focusId) : undefined;

      for (const e of s.edges) {
        const active = !!focusId && (e.s.id === focusId || e.t.id === focusId);
        ctx.globalAlpha = focusId ? (active ? 0.9 : 0.07) : 0.35;
        ctx.strokeStyle = active ? C.edgeActive : C.edge;
        ctx.lineWidth = Math.max(0.6 + Math.log2(1 + e.w) * 0.7, 0.5 / v.k) * (active ? 1.4 : 1);
        ctx.setLineDash(e.dashed ? [5 / v.k, 4 / v.k] : []);
        ctx.beginPath();
        ctx.moveTo(e.s.x, e.s.y);
        ctx.lineTo(e.t.x, e.t.y);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      for (const n of s.nodes) {
        const isFocus = n.id === focusId;
        const isSel = n.id === selectedRef.current;
        const isNb = !!nb?.has(n.id);
        ctx.globalAlpha = focusId && !isFocus && !isNb ? 0.18 : 1;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = entityColor(n.node.type);
        ctx.fill();
        ctx.lineWidth = (isSel ? 3 : 1.5) / v.k;
        ctx.strokeStyle = isSel ? C.ring : C.stroke;
        ctx.stroke();
        if (isSel) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r + 5 / v.k, 0, Math.PI * 2);
          ctx.strokeStyle = C.edgeActive;
          ctx.lineWidth = 1.5 / v.k;
          ctx.stroke();
        }
      }

      if (labels) {
        const fs = 11.5 / v.k;
        ctx.font = `500 ${fs}px Inter, ui-sans-serif, system-ui, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.lineJoin = 'round';
        for (const n of s.nodes) {
          const isFocus = n.id === focusId;
          const isSel = n.id === selectedRef.current;
          const isNb = !!nb?.has(n.id);
          const big = n.r * v.k > 9 || v.k > 1.6;
          if (!(isFocus || isSel || isNb || (big && !focusId))) continue;
          const text = truncate(n.node.label || n.id);
          const y = n.y + n.r + 3 / v.k;
          ctx.globalAlpha = 1;
          ctx.lineWidth = 3.5 / v.k;
          ctx.strokeStyle = C.halo;
          ctx.strokeText(text, n.x, y);
          ctx.fillStyle = C.label;
          ctx.fillText(text, n.x, y);
        }
      }
      ctx.restore();
    };

    const loop = () => {
      const s = sim.current;
      if (s.alpha > ALPHA_MIN) {
        tick(s);
        dirty.current = true;
      }
      if (fitPending.current && size.current.w > 0 && s.nodes.length > 0) {
        const f = computeFit();
        if (f) view.current = f;
        fitPending.current = false;
        dirty.current = true;
      }
      const t = target.current;
      if (t) {
        const v = view.current;
        v.x += (t.x - v.x) * 0.2;
        v.y += (t.y - v.y) * 0.2;
        v.k += (t.k - v.k) * 0.2;
        if (Math.abs(t.x - v.x) < 0.5 && Math.abs(t.y - v.y) < 0.5 && Math.abs(t.k - v.k) < 0.002) {
          view.current = { ...t };
          target.current = null;
        }
        dirty.current = true;
      }
      if (dirty.current) {
        draw();
        dirty.current = false;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [computeFit]);

  // ── pointer interaction ───────────────────────────────────────
  const local = (e: { clientX: number; clientY: number }) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    return { sx: e.clientX - (rect?.left ?? 0), sy: e.clientY - (rect?.top ?? 0) };
  };

  const hit = (sx: number, sy: number): SimNode | null => {
    const v = view.current;
    const wx = (sx - v.x) / v.k;
    const wy = (sy - v.y) / v.k;
    const ns = sim.current.nodes;
    for (let i = ns.length - 1; i >= 0; i--) {
      const n = ns[i];
      const rr = n.r + 4 / v.k;
      const dx = n.x - wx;
      const dy = n.y - wy;
      if (dx * dx + dy * dy <= rr * rr) return n;
    }
    return null;
  };

  const setHover = (n: SimNode | null) => {
    const id = n?.id ?? null;
    if (id === hoverRef.current) return;
    hoverRef.current = id;
    dirty.current = true;
    setHovered(n ? { node: n.node, degree: sim.current.neighbors.get(n.id)?.size ?? 0 } : null);
    if (canvasRef.current) canvasRef.current.style.cursor = n ? 'pointer' : 'grab';
  };

  const moveTip = (sx: number, sy: number) => {
    const tip = tipRef.current;
    if (!tip) return;
    const { w } = size.current;
    const left = Math.min(sx + 14, Math.max(8, w - 230));
    tip.style.transform = `translate(${left}px, ${sy + 14}px)`;
  };

  const onPointerDown = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const { sx, sy } = local(e);
    canvasRef.current?.setPointerCapture(e.pointerId);
    const n = hit(sx, sy);
    target.current = null;
    if (n) {
      n.fixed = true;
      drag.current = { mode: 'node', node: n, startX: sx, startY: sy, lastX: sx, lastY: sy, moved: false };
    } else {
      drag.current = { mode: 'pan', startX: sx, startY: sy, lastX: sx, lastY: sy, moved: false };
      if (canvasRef.current) canvasRef.current.style.cursor = 'grabbing';
    }
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const { sx, sy } = local(e);
    const d = drag.current;
    if (d) {
      if (!d.moved && Math.hypot(sx - d.startX, sy - d.startY) > 4) d.moved = true;
      if (d.mode === 'node' && d.node) {
        const v = view.current;
        d.node.x = (sx - v.x) / v.k;
        d.node.y = (sy - v.y) / v.k;
        if (d.moved) sim.current.alpha = Math.max(sim.current.alpha, 0.25);
      } else {
        view.current.x += sx - d.lastX;
        view.current.y += sy - d.lastY;
      }
      d.lastX = sx;
      d.lastY = sy;
      dirty.current = true;
      moveTip(sx, sy);
      return;
    }
    setHover(hit(sx, sy));
    moveTip(sx, sy);
  };

  const endDrag = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const d = drag.current;
    drag.current = null;
    try {
      canvasRef.current?.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    if (!d) return;
    if (d.mode === 'node' && d.node) {
      d.node.fixed = false;
      if (!d.moved) opts.current.onSelect(d.node.id === selectedRef.current ? null : d.node.id);
    } else if (!d.moved) {
      opts.current.onSelect(null);
    }
    if (canvasRef.current) canvasRef.current.style.cursor = hoverRef.current ? 'pointer' : 'grab';
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const factor = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015));
      zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
    };
    canvas.addEventListener('wheel', onWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', onWheel);
  }, [zoomAt]);

  const onKeyDown = (e: KeyboardEvent<HTMLCanvasElement>) => {
    const { w, h } = size.current;
    const pan = (dx: number, dy: number) => {
      const v = target.current ?? view.current;
      target.current = { ...v, x: v.x + dx, y: v.y + dy };
    };
    switch (e.key) {
      case '+':
      case '=':
        zoomAt(w / 2, h / 2, 1.3);
        break;
      case '-':
      case '_':
        zoomAt(w / 2, h / 2, 1 / 1.3);
        break;
      case '0': {
        const f = computeFit();
        if (f) target.current = f;
        break;
      }
      case 'ArrowLeft':
        pan(60, 0);
        break;
      case 'ArrowRight':
        pan(-60, 0);
        break;
      case 'ArrowUp':
        pan(0, 60);
        break;
      case 'ArrowDown':
        pan(0, -60);
        break;
      case 'Escape':
        opts.current.onSelect(null);
        break;
      default:
        return;
    }
    e.preventDefault();
  };

  return (
    <div ref={wrapRef} className={className ?? 'relative h-full w-full'}>
      <canvas
        ref={canvasRef}
        tabIndex={0}
        role="application"
        aria-roledescription="knowledge graph"
        aria-label={`Knowledge graph with ${nodes.length} entities and ${edges.length} relations. Drag to pan, scroll or press plus and minus to zoom, 0 to fit, Escape to clear selection. Use the search box to focus an entity.`}
        className="block touch-none rounded-[inherit] outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
        style={{ cursor: 'grab' }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={() => {
          if (!drag.current) setHover(null);
        }}
        onKeyDown={onKeyDown}
      />
      <div
        ref={tipRef}
        className="pointer-events-none absolute left-0 top-0 z-10 w-max max-w-[220px] rounded-lg border border-line bg-surface/95 px-2.5 py-2 text-xs shadow-xl backdrop-blur"
        style={{ visibility: hovered && !drag.current ? 'visible' : 'hidden' }}
        aria-hidden="true"
      >
        {hovered ? (
          <>
            <p className="break-words font-semibold text-fg">{hovered.node.label}</p>
            <p className="mt-1 flex items-center gap-1.5 text-muted">
              <span className="h-2 w-2 rounded-full" style={{ background: entityColor(hovered.node.type) }} />
              {entityLabel(hovered.node.type)}
            </p>
            <p className="mt-1 text-subtle">
              weight {hovered.node.weight} · {hovered.degree} links · {hovered.node.documents?.length ?? 0} docs
            </p>
          </>
        ) : null}
      </div>
    </div>
  );
});

export default ForceGraph;
