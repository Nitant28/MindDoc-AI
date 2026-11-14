import type { ReactNode } from 'react';
import { useTheme } from '../lib/theme';
import Logo from './Logo';
import { Button } from './ui/Button';
import { Icon, type IconName } from './ui/Icon';

const FEATURES: Array<{ icon: IconName; title: string; body: string }> = [
  { icon: 'table', title: 'Bank statements, reconciled', body: 'Every row read with its page region; balances checked, never adjusted.' },
  { icon: 'target', title: 'Leads with their evidence', body: 'Fund diversion, round trips and cash structuring surfaced for review, never as verdicts.' },
  { icon: 'lock', title: 'Findings that hold up', body: 'Versioned findings, frozen reports with a SHA-256, and disclosure copies with reasons.' },
];

export default function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="grid min-h-screen bg-bg lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative m-3 hidden overflow-hidden rounded-[28px] bg-accent-container lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-accent/20 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-accent/10 blur-3xl" aria-hidden="true" />
        <div className="relative">
          <Logo size={36} />
        </div>
        <div className="relative max-w-md">
          <h2 className="text-[40px] font-normal leading-[1.1] tracking-tight text-accent-on-container">Evidence you can stand behind.</h2>
          <p className="mt-4 text-[15px] leading-relaxed text-accent-on-container/80">
            MindDoc reads bank statements and documents, links the parties, surfaces the patterns worth a second look, and keeps every
            finding tied to the page it came from.
          </p>
          <ul className="mt-8 space-y-5">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface/70 text-accent-soft dark:bg-black/20">
                  <Icon name={f.icon} className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-sm font-medium text-accent-on-container">{f.title}</p>
                  <p className="text-[13px] leading-relaxed text-accent-on-container/75">{f.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-accent-on-container/70">Organisation-isolated · Case-level access · Every change audited</p>
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
          <h1 className="text-[32px] font-normal tracking-tight text-fg">{title}</h1>
          <p className="mt-2 text-[15px] text-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-6 text-center text-sm text-muted">{footer}</div>
        </div>
      </main>
    </div>
  );
}
