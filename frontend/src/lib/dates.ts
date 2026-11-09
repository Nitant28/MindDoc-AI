import type { Tone } from './format';

export function formatDay(iso: string): string {
  const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function dueLabel(days?: number | null): string | null {
  if (days == null || !Number.isFinite(days)) return null;
  if (days === 0) return 'today';
  if (days === 1) return 'tomorrow';
  if (days > 0) return `in ${days} days`;
  return `${Math.abs(days)} days ago`;
}

export function dueTone(days?: number | null): Tone {
  if (days == null) return 'neutral';
  if (days < 0) return 'neutral';
  if (days <= 14) return 'danger';
  if (days <= 45) return 'warning';
  return 'info';
}
