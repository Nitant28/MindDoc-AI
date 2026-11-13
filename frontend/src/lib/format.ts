export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** Values in the contract are 0..1; tolerate already-percent values. */
export function ratio(v: number): number {
  return v > 1 ? v / 100 : v;
}

export function pct(v: number | null | undefined, digits = 0): string {
  if (!isNum(v)) return '—';
  return `${(ratio(v) * 100).toFixed(digits)}%`;
}

export function fmtMs(v: number | null | undefined): string {
  if (!isNum(v)) return '—';
  if (v < 1000) return `${Math.round(v)} ms`;
  return `${(v / 1000).toFixed(v < 10_000 ? 2 : 1)} s`;
}

export function num(v: number | null | undefined, digits = 0): string {
  if (!isNum(v)) return '—';
  return v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function bytes(n: number): string {
  if (!isNum(n)) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** Backend timestamps are naive UTC (no offset); treat them as UTC. */
export function parseDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const s = /([zZ]|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function timeOf(iso?: string | null): number {
  return parseDate(iso)?.getTime() ?? 0;
}

export function relTime(iso?: string | null): string {
  const d = parseDate(iso);
  if (!d) return '—';
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 45) return 'just now';
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.round(diff / 3600)}h ago`;
  if (diff < 86_400 * 7) return `${Math.round(diff / 86_400)}d ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export function fullDate(iso?: string | null): string {
  const d = parseDate(iso);
  return d ? d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—';
}

export function humanize(s?: string | null, fallback = 'Unclassified'): string {
  if (!s) return fallback;
  const t = s.replace(/[_-]+/g, ' ').trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : fallback;
}

export function scoreTone(v: number | null | undefined, good = 0.75, fair = 0.5): Tone {
  if (!isNum(v)) return 'neutral';
  const x = ratio(v);
  if (x >= good) return 'success';
  if (x >= fair) return 'warning';
  return 'danger';
}

export function qualityTone(q?: string | null): Tone {
  switch ((q ?? '').toLowerCase()) {
    case 'good':
      return 'success';
    case 'fair':
      return 'warning';
    case 'poor':
      return 'danger';
    default:
      return 'neutral';
  }
}

export function severityTone(s?: string | null): Tone {
  switch ((s ?? '').toLowerCase()) {
    case 'critical':
    case 'high':
      return 'danger';
    case 'medium':
      return 'warning';
    case 'low':
      return 'info';
    default:
      return 'neutral';
  }
}

export const clamp01 = (v: number): number => (Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : 0);

export function uid(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 9)}`;
}

/** Paise → "1,23,456.78" (Indian grouping). Integer arithmetic only; never goes through floats. */
export function formatMinor(minor: number | null | undefined): string {
  if (minor == null) return '—';
  const neg = minor < 0;
  const abs = Math.abs(minor);
  const rupees = Math.floor(abs / 100).toString();
  const paise = (abs % 100).toString().padStart(2, '0');
  const last3 = rupees.slice(-3);
  const rest = rupees.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return `${neg ? '-' : ''}${rest ? `${rest},` : ''}${last3}.${paise}`;
}
