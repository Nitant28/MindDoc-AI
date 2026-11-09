import type { ReactNode } from 'react';
import { useTheme } from '../lib/theme';
import Logo from './Logo';
import { Button } from './ui/Button';
import { Icon, type IconName } from './ui/Icon';

const FEATURES: Array<{ icon: IconName; title: string; body: string }> = [
  { icon: 'quote', title: 'Cited, page-level answers', body: 'Every claim links back to the passage and page it came from.' },
  { icon: 'target', title: 'Confidence & groundedness', body: 'Answers are scored and verified claim-by-claim against the sources.' },
  { icon: 'trace', title: 'Inspectable reasoning', body: 'See retrieval, re-ranking and verification steps with timings.' },
];

export default function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="grid min-h-screen bg-bg lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden overflow-hidden border-r border-line bg-surface lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="bg-dots pointer-events-none absolute inset-0 opacity-60 [mask-image:linear-gradient(to_bottom,black,transparent_85%)]" aria-hidden="true" />
        <div className="relative">
          <Logo size={36} />
        </div>
        <div className="relative max-w-md">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight text-fg">Document intelligence you can audit.</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            MindDoc reads contracts, papers, invoices and scans, builds a knowledge graph of your workspace, and answers questions as a
            glass box — never a black box.
          </p>
          <ul className="mt-8 space-y-5">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line bg-elevated text-accent">
                  <Icon name={f.icon} className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-medium text-fg">{f.title}</p>
                  <p className="text-xs leading-relaxed text-muted">{f.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-subtle">Workspace-isolated · PII-aware · Prompt-injection aware</p>
      </aside>

      <main className="relative flex items-center justify-center px-4 py-12 sm:px-8">
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-4 top-4"
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          icon={theme === 'dark' ? 'sun' : 'moon'}
        />
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo size={32} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-6 text-center text-sm text-muted">{footer}</div>
        </div>
      </main>
    </div>
  );
}
