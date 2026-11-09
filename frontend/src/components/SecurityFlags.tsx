import { humanize } from '../lib/format';
import type { SecurityFlag } from '../types';
import { SeverityBadge } from './Signals';
import { Icon } from './ui/Icon';

export function hasInjection(flags?: SecurityFlag[] | null): boolean {
  return (flags ?? []).some((f) => f.type === 'prompt_injection');
}

/** Prominent warning when a document contains prompt-injection attempts. */
export function InjectionBanner({ flags }: { flags?: SecurityFlag[] | null }) {
  const hits = (flags ?? []).filter((f) => f.type === 'prompt_injection');
  if (hits.length === 0) return null;
  return (
    <div role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/[0.08] p-4">
      <div className="flex items-start gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/15 text-rose-500">
          <Icon name="shield" className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">Prompt-injection content detected</p>
          <p className="mt-0.5 text-xs text-rose-700/80 dark:text-rose-300/80">
            This document contains text that tries to instruct the AI. Matching phrases are neutralised before the text reaches
            the model, and sources are marked as untrusted data, but review it before trusting answers that cite it.
          </p>
          <ul className="mt-2 space-y-1.5">
            {hits.slice(0, 4).map((f, i) => (
              <li key={i} className="flex flex-wrap items-start gap-2 text-xs">
                <SeverityBadge severity={f.severity} />
                {f.snippet ? <code className="min-w-0 flex-1 break-words font-mono text-[11px] text-rose-800 dark:text-rose-200">“{f.snippet}”</code> : null}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export function FlagList({ flags }: { flags?: SecurityFlag[] | null }) {
  const list = flags ?? [];
  if (list.length === 0) {
    return (
      <p className="flex items-center gap-2 text-xs text-muted">
        <Icon name="check" className="h-3.5 w-3.5 text-emerald-500" /> No security flags raised.
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {list.map((f, i) => (
        <li key={i} className="rounded-lg border border-line bg-elevated/40 p-2.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-fg">{humanize(f.type)}</span>
            <SeverityBadge severity={f.severity} />
          </div>
          {f.snippet ? <p className="mt-1 break-words font-mono text-[11px] text-muted">“{f.snippet}”</p> : null}
        </li>
      ))}
    </ul>
  );
}
