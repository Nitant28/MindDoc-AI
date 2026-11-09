/**
 * Minimal, safe Markdown renderer for model output.
 * Builds React elements directly (no dangerouslySetInnerHTML); raw HTML in the source is shown as text.
 * Supports: headings, paragraphs, bold/italic/strike, inline code, fenced code, ordered/unordered
 * (nested) lists, blockquotes, horizontal rules, GFM tables, links/autolinks (http/https/mailto only),
 * and inline citation markers like [1] or [1, 2] which become buttons.
 */
import { Fragment, useMemo, useState, type ReactNode } from 'react';
import { copyText } from '../lib/clipboard';
import { cx } from '../lib/cx';
import { Icon } from './ui/Icon';

type Align = 'left' | 'center' | 'right' | null;

type Block =
  | { t: 'p'; text: string }
  | { t: 'h'; level: number; text: string }
  | { t: 'code'; lang: string; code: string }
  | { t: 'hr' }
  | { t: 'quote'; text: string }
  | { t: 'list'; ordered: boolean; start: number; items: string[][] }
  | { t: 'table'; header: string[]; align: Align[]; rows: string[][] };

interface Ctx {
  key: number;
  citations?: Set<number>;
  onCitation?: (n: number) => void;
}

const FENCE = /^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$/;
const HEADING = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
const HR = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
const QUOTE = /^\s{0,3}>\s?(.*)$/;
const LIST = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
const TABLE_SEP = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

const indentOf = (line: string): number => line.length - line.trimStart().length;

function splitRow(line: string): string[] {
  let s = line.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|') && !s.endsWith('\\|')) s = s.slice(0, -1);
  return s.split(/(?<!\\)\|/).map((c) => c.trim().replace(/\\\|/g, '|'));
}

function isTableStart(lines: string[], i: number): boolean {
  return lines[i].includes('|') && i + 1 < lines.length && lines[i + 1].includes('-') && TABLE_SEP.test(lines[i + 1]);
}

function parseBlocks(src: string): Block[] {
  const lines = src.replace(/\r\n?/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }

    let m: RegExpExecArray | null = FENCE.exec(line);
    if (m) {
      const fence = m[1];
      const lang = m[2] || '';
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(fence.slice(0, 3))) {
        buf.push(lines[i]);
        i++;
      }
      i++; // closing fence (or EOF while streaming)
      blocks.push({ t: 'code', lang, code: buf.join('\n') });
      continue;
    }

    m = HEADING.exec(line);
    if (m) {
      blocks.push({ t: 'h', level: m[1].length, text: m[2] });
      i++;
      continue;
    }

    if (HR.test(line)) {
      blocks.push({ t: 'hr' });
      i++;
      continue;
    }

    if (QUOTE.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && lines[i].trim()) {
        const qm = QUOTE.exec(lines[i]);
        buf.push(qm ? qm[1] : lines[i].trim());
        i++;
      }
      blocks.push({ t: 'quote', text: buf.join('\n') });
      continue;
    }

    if (isTableStart(lines, i)) {
      const header = splitRow(line);
      const align: Align[] = splitRow(lines[i + 1]).map((c) => {
        const l = c.startsWith(':');
        const r = c.endsWith(':');
        return l && r ? 'center' : r ? 'right' : l ? 'left' : null;
      });
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim() && lines[i].includes('|')) {
        rows.push(splitRow(lines[i]));
        i++;
      }
      blocks.push({ t: 'table', header, align, rows });
      continue;
    }

    m = LIST.exec(line);
    if (m) {
      const base = m[1].length;
      const ordered = /\d/.test(m[2]);
      const start = ordered ? parseInt(m[2], 10) : 1;
      const items: string[][] = [];
      let cur: string[] | null = null;
      let contentIndent = base + m[2].length + 1;

      while (i < lines.length) {
        const l = lines[i];
        const lm = LIST.exec(l);
        if (lm && lm[1].length <= base + 1 && /\d/.test(lm[2]) === ordered) {
          cur = [lm[3]];
          items.push(cur);
          contentIndent = lm[1].length + lm[2].length + 1;
          i++;
          continue;
        }
        if (lm && lm[1].length <= base + 1) break; // sibling of a different list kind
        if (!l.trim()) {
          let j = i + 1;
          while (j < lines.length && !lines[j].trim()) j++;
          if (cur && j < lines.length) {
            const nl = lines[j];
            const nm = LIST.exec(nl);
            const sibling = nm && nm[1].length <= base + 1 && /\d/.test(nm[2]) === ordered;
            if (sibling || indentOf(nl) > base + 1) {
              cur.push('');
              i++;
              continue;
            }
          }
          break;
        }
        const ind = indentOf(l);
        if (cur && ind > base) {
          cur.push(l.slice(Math.min(ind, contentIndent)));
          i++;
          continue;
        }
        if (cur && !FENCE.test(l) && !HEADING.test(l) && !QUOTE.test(l) && !HR.test(l)) {
          cur.push(l.trim()); // lazy continuation
          i++;
          continue;
        }
        break;
      }
      blocks.push({ t: 'list', ordered, start, items });
      continue;
    }

    const buf = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !FENCE.test(lines[i]) &&
      !HEADING.test(lines[i]) &&
      !HR.test(lines[i]) &&
      !QUOTE.test(lines[i]) &&
      !LIST.test(lines[i]) &&
      !isTableStart(lines, i)
    ) {
      buf.push(lines[i]);
      i++;
    }
    blocks.push({ t: 'p', text: buf.join('\n') });
  }
  return blocks;
}

// ───────────────────────────── Inline ─────────────────────────────

const RE = {
  esc: /\\([\\`*_{}[\]()#+\-.!~|>])/y,
  code: /(`+)([\s\S]*?[^`])\1(?!`)/y,
  bold: /(\*\*|__)(?=\S)([\s\S]*?\S)\1/y,
  strike: /~~(?=\S)([\s\S]*?\S)~~/y,
  emStar: /\*(?=[^\s*])([\s\S]*?[^\s*])\*(?!\*)/y,
  emUnder: /_(?=[^\s_])([\s\S]*?[^\s_])_(?![A-Za-z0-9])/y,
  link: /\[([^\]\n]+)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/y,
  cite: /\[(\d{1,3}(?:\s*[,;]\s*\d{1,3})*)\]/y,
  url: /https?:\/\/[^\s<>"'`)\]]*[^\s<>"'`)\].,;:!?]/y,
};

function exec(re: RegExp, text: string, at: number): RegExpExecArray | null {
  re.lastIndex = at;
  return re.exec(text);
}

function safeHref(url: string): string | null {
  try {
    const u = new URL(url, window.location.origin);
    return ['http:', 'https:', 'mailto:'].includes(u.protocol) ? url : null;
  } catch {
    return null;
  }
}

const nextKey = (c: Ctx): string => `md${c.key++}`;

function inline(text: string, c: Ctx): ReactNode[] {
  const out: ReactNode[] = [];
  let buf = '';
  const flush = () => {
    if (buf) {
      out.push(buf);
      buf = '';
    }
  };
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    const prev = i > 0 ? text[i - 1] : ' ';
    let m: RegExpExecArray | null;

    if (ch === '\\' && (m = exec(RE.esc, text, i))) {
      buf += m[1];
      i += m[0].length;
      continue;
    }
    if (ch === '`' && (m = exec(RE.code, text, i))) {
      flush();
      out.push(
        <code key={nextKey(c)} className="rounded bg-elevated px-1 py-0.5 font-mono text-[0.85em] text-fg ring-1 ring-inset ring-line">
          {m[2].trim() || m[2]}
        </code>,
      );
      i += m[0].length;
      continue;
    }
    if ((ch === '*' || ch === '_') && text[i + 1] === ch && (ch === '*' || !/\w/.test(prev)) && (m = exec(RE.bold, text, i))) {
      flush();
      out.push(
        <strong key={nextKey(c)} className="font-semibold text-fg">
          {inline(m[2], c)}
        </strong>,
      );
      i += m[0].length;
      continue;
    }
    if (ch === '~' && (m = exec(RE.strike, text, i))) {
      flush();
      out.push(<del key={nextKey(c)}>{inline(m[1], c)}</del>);
      i += m[0].length;
      continue;
    }
    if (ch === '*' && (m = exec(RE.emStar, text, i))) {
      flush();
      out.push(<em key={nextKey(c)}>{inline(m[1], c)}</em>);
      i += m[0].length;
      continue;
    }
    if (ch === '_' && !/[A-Za-z0-9]/.test(prev) && (m = exec(RE.emUnder, text, i))) {
      flush();
      out.push(<em key={nextKey(c)}>{inline(m[1], c)}</em>);
      i += m[0].length;
      continue;
    }
    if (ch === '[') {
      if ((m = exec(RE.link, text, i))) {
        const href = safeHref(m[2]);
        flush();
        if (href) {
          const external = /^https?:/i.test(href);
          out.push(
            <a
              key={nextKey(c)}
              href={href}
              className="text-accent-soft underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
              {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
            >
              {inline(m[1], c)}
            </a>,
          );
        } else {
          out.push(<Fragment key={nextKey(c)}>{inline(m[1], c)}</Fragment>);
        }
        i += m[0].length;
        continue;
      }
      if ((m = exec(RE.cite, text, i))) {
        flush();
        const nums = m[1].split(/[,;]/).map((s) => parseInt(s.trim(), 10));
        nums.forEach((n) => out.push(<CitationMarker key={nextKey(c)} n={n} c={c} />));
        i += m[0].length;
        continue;
      }
    }
    if (ch === 'h' && !/[\w/]/.test(prev) && (m = exec(RE.url, text, i))) {
      const href = safeHref(m[0]);
      if (href) {
        flush();
        out.push(
          <a
            key={nextKey(c)}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all text-accent-soft underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
          >
            {m[0]}
          </a>,
        );
        i += m[0].length;
        continue;
      }
    }
    if (ch === '\n') {
      flush();
      out.push(<br key={nextKey(c)} />);
      i++;
      continue;
    }
    buf += ch;
    i++;
  }
  flush();
  return out;
}

function CitationMarker({ n, c }: { n: number; c: Ctx }) {
  const interactive = !!c.onCitation && !!c.citations?.has(n);
  if (!interactive) {
    return <sup className="mx-px font-mono text-[10px] text-subtle">[{n}]</sup>;
  }
  return (
    <button
      type="button"
      onClick={() => c.onCitation?.(n)}
      aria-label={`Show source ${n}`}
      title={`Source ${n}`}
      className="mx-0.5 inline-flex h-[1.15rem] min-w-[1.15rem] -translate-y-[2px] items-center justify-center rounded bg-accent/15 px-1 align-middle font-mono text-[10px] font-semibold leading-none text-accent-soft transition-colors hover:bg-accent hover:text-white"
    >
      {n}
    </button>
  );
}

// ───────────────────────────── Blocks ─────────────────────────────

function CodeBlock({ lang, code }: { lang: string; code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="group/code my-3 overflow-hidden rounded-lg border border-line bg-elevated/60">
      <div className="flex items-center justify-between border-b border-line px-3 py-1 text-[11px] text-subtle">
        <span className="font-mono">{lang || 'text'}</span>
        <button
          type="button"
          onClick={async () => {
            if (await copyText(code)) {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1500);
            }
          }}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-surface hover:text-fg"
          aria-label="Copy code"
        >
          <Icon name={copied ? 'check' : 'copy'} className="h-3 w-3" />
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-[12.5px] leading-relaxed text-fg">
        <code>{code}</code>
      </pre>
    </div>
  );
}

const HEADING_TAG = ['h3', 'h3', 'h4', 'h5', 'h6', 'h6', 'h6'] as const;
const HEADING_CLASS = ['', 'text-base', 'text-[15px]', 'text-sm', 'text-sm', 'text-sm', 'text-sm'];

function renderBlocks(blocks: Block[], c: Ctx, tight = false): ReactNode[] {
  return blocks.map((b, idx) => {
    switch (b.t) {
      case 'p':
        return tight && idx === 0 ? (
          <Fragment key={nextKey(c)}>{inline(b.text, c)}</Fragment>
        ) : (
          <p key={nextKey(c)} className="my-2.5 leading-relaxed first:mt-0 last:mb-0">
            {inline(b.text, c)}
          </p>
        );
      case 'h': {
        const Tag = HEADING_TAG[b.level] ?? 'h6';
        return (
          <Tag key={nextKey(c)} className={cx('mb-2 mt-5 font-semibold tracking-tight text-fg first:mt-0', HEADING_CLASS[b.level])}>
            {inline(b.text, c)}
          </Tag>
        );
      }
      case 'code':
        return <CodeBlock key={nextKey(c)} lang={b.lang} code={b.code} />;
      case 'hr':
        return <hr key={nextKey(c)} className="my-4 border-line" />;
      case 'quote':
        return (
          <blockquote key={nextKey(c)} className="my-3 border-l-2 border-accent/50 pl-3 text-muted">
            {renderBlocks(parseBlocks(b.text), c)}
          </blockquote>
        );
      case 'list': {
        const isTight = b.items.every((it) => !it.includes(''));
        const items = b.items.map((it) => (
          <li key={nextKey(c)} className="pl-1 leading-relaxed">
            {renderBlocks(parseBlocks(it.join('\n')), c, isTight)}
          </li>
        ));
        return b.ordered ? (
          <ol key={nextKey(c)} start={b.start !== 1 ? b.start : undefined} className="my-2.5 list-decimal space-y-1 pl-5 marker:text-subtle">
            {items}
          </ol>
        ) : (
          <ul key={nextKey(c)} className="my-2.5 list-disc space-y-1 pl-5 marker:text-subtle">
            {items}
          </ul>
        );
      }
      case 'table':
        return (
          <div key={nextKey(c)} className="my-3 overflow-x-auto rounded-lg border border-line">
            <table className="w-full border-collapse text-[13px]">
              <thead className="bg-elevated/70">
                <tr>
                  {b.header.map((h, hi) => (
                    <th
                      key={hi}
                      scope="col"
                      className="border-b border-line px-3 py-2 text-left font-semibold text-fg"
                      style={{ textAlign: b.align[hi] ?? undefined }}
                    >
                      {inline(h, c)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {b.rows.map((row, ri) => (
                  <tr key={ri}>
                    {b.header.map((_h, ci) => (
                      <td key={ci} className="px-3 py-2 align-top text-muted" style={{ textAlign: b.align[ci] ?? undefined }}>
                        {inline(row[ci] ?? '', c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      default:
        return null;
    }
  });
}

interface MarkdownProps {
  text: string;
  /** Citation indices that exist; markers for these become clickable. */
  citations?: number[];
  onCitation?: (n: number) => void;
  className?: string;
}

export default function Markdown({ text, citations, onCitation, className }: MarkdownProps) {
  const citeKey = citations ? citations.join(',') : '';
  const nodes = useMemo(() => {
    const ctx: Ctx = { key: 0, citations: citeKey ? new Set(citeKey.split(',').map(Number)) : undefined, onCitation };
    return renderBlocks(parseBlocks(text), ctx);
  }, [text, citeKey, onCitation]);
  return <div className={cx('break-words text-sm text-fg/90', className)}>{nodes}</div>;
}
