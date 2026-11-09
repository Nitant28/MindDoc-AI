import { cx } from '../lib/cx';
import { humanize, isNum, pct, ratio, scoreTone, severityTone } from '../lib/format';
import { Badge } from './ui/Badge';
import { Meter } from './ui/Meter';

export function ConfidenceBadge({ value, label = 'Confidence' }: { value?: number | null; label?: string }) {
  if (!isNum(value)) return null;
  return (
    <Badge tone={scoreTone(value)} dot title={`${label}: ${pct(value, 1)}`}>
      {label} {pct(value)}
    </Badge>
  );
}

export function DocTypeBadge({ type, confidence }: { type?: string | null; confidence?: number | null }) {
  if (!type) return <Badge tone="neutral">Unclassified</Badge>;
  return (
    <Badge tone="accent" title={isNum(confidence) ? `Classifier confidence ${pct(confidence, 1)}` : undefined}>
      {humanize(type)}
      {isNum(confidence) ? <span className="opacity-70">· {pct(confidence)}</span> : null}
    </Badge>
  );
}

export function PiiBadge({ count }: { count?: number | null }) {
  if (!isNum(count)) return <span className="text-xs text-subtle">—</span>;
  if (count === 0) return <Badge tone="neutral">None</Badge>;
  return (
    <Badge tone="warning" icon="shield" title={`${count} PII items detected`}>
      {count} PII
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity?: string | null }) {
  return (
    <Badge tone={severityTone(severity)} className="uppercase tracking-wide">
      {severity || 'unknown'}
    </Badge>
  );
}

export function QualityMeter({ value, className }: { value?: number | null; className?: string }) {
  if (!isNum(value)) return <span className="text-xs text-subtle">—</span>;
  return (
    <div className={cx('flex items-center gap-2', className)}>
      <Meter value={ratio(value)} size="xs" className="w-14" label="Extraction quality" />
      <span className="w-9 text-right text-xs tabular-nums text-muted">{pct(value)}</span>
    </div>
  );
}
