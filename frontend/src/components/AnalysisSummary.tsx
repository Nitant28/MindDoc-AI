import { isNum, num, pct, scoreTone } from '../lib/format';
import type { UploadResponse } from '../types';
import { FlagList, InjectionBanner } from './SecurityFlags';
import { DocTypeBadge } from './Signals';
import { Badge, TONE_TEXT } from './ui/Badge';
import { LinkButton } from './ui/Button';

/** Card body shown after each upload: what the pipeline found. */
export default function AnalysisSummary({ result }: { result: UploadResponse }) {
  const a = result.analysis ?? null;
  const id = result.document_id;
  const pages = a?.stats?.pages ?? null;
  const ocr = a?.vision?.ocr_pages ?? null;
  const quality = a?.vision?.overall_quality ?? null;
  const pii = a?.pii ?? null;
  const flags = a?.security_flags ?? [];

  return (
    <div className="space-y-4">
      <InjectionBanner flags={flags} />

      <div className="flex flex-wrap items-center gap-2">
        <DocTypeBadge type={a?.doc_type} confidence={a?.doc_type_confidence} />
        {pages != null ? <Badge>{num(pages)} pages</Badge> : null}
        {isNum(result.characters_extracted) ? <Badge>{num(result.characters_extracted)} chars</Badge> : null}
      </div>

      {a?.summary ? (
        <p className="text-sm leading-relaxed text-fg/90">{a.summary}</p>
      ) : result.preview ? (
        <p className="line-clamp-3 text-sm italic text-muted">“{result.preview}”</p>
      ) : (
        <p className="text-sm text-subtle">No analysis returned by the backend (v1 server). The document is indexed for chat.</p>
      )}

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-line p-2.5">
          <dt className="text-[11px] uppercase tracking-wider text-subtle">Quality</dt>
          <dd className={`mt-0.5 text-base font-semibold tabular-nums ${TONE_TEXT[scoreTone(quality)]}`}>{pct(quality)}</dd>
        </div>
        <div className="rounded-lg border border-line p-2.5">
          <dt className="text-[11px] uppercase tracking-wider text-subtle">Pages OCR’d</dt>
          <dd className="mt-0.5 text-base font-semibold tabular-nums text-fg">
            {ocr != null ? num(ocr) : '—'}
            {ocr != null && pages != null ? <span className="text-xs font-normal text-subtle"> / {pages}</span> : null}
          </dd>
        </div>
        <div className="rounded-lg border border-line p-2.5">
          <dt className="text-[11px] uppercase tracking-wider text-subtle">PII found</dt>
          <dd className={`mt-0.5 text-base font-semibold tabular-nums ${pii && pii.count > 0 ? TONE_TEXT.warning : 'text-fg'}`}>
            {pii ? num(pii.count) : '—'}
          </dd>
        </div>
        <div className="rounded-lg border border-line p-2.5">
          <dt className="text-[11px] uppercase tracking-wider text-subtle">Security flags</dt>
          <dd className={`mt-0.5 text-base font-semibold tabular-nums ${flags.length ? TONE_TEXT.danger : 'text-fg'}`}>{a ? flags.length : '—'}</dd>
        </div>
      </dl>

      {pii && Object.keys(pii.types ?? {}).length > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-subtle">PII types:</span>
          {Object.entries(pii.types).map(([t, n]) => (
            <Badge key={t} tone="warning">
              {t} · {n}
            </Badge>
          ))}
        </div>
      ) : null}

      {flags.some((f) => f.type !== 'prompt_injection') ? <FlagList flags={flags.filter((f) => f.type !== 'prompt_injection')} /> : null}

      <div className="flex flex-wrap gap-2">
        <LinkButton to={`/documents/${id}`} variant="primary" size="sm" icon="external">
          Open document
        </LinkButton>
        <LinkButton to={`/chat?document=${id}`} size="sm" icon="chat">
          Chat with it
        </LinkButton>
      </div>
    </div>
  );
}
