import { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cx } from '../lib/cx';
import { LogoMark } from './Logo';
import { Button, buttonClass } from './ui/Button';
import { Icon, type IconName } from './ui/Icon';

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  section: 'workspace' | 'intelligence' | 'account';
  match?: string[];
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: 'dashboard', section: 'workspace' },
  { to: '/chat', label: 'Chat', icon: 'chat', section: 'workspace' },
  { to: '/upload', label: 'Documents', icon: 'file', section: 'workspace', match: ['/upload', '/documents'] },
  { to: '/parties', label: 'Parties', icon: 'user', section: 'intelligence' },
  { to: '/graph', label: 'Knowledge Graph', icon: 'graph', section: 'intelligence' },
  { to: '/timeline', label: 'Timeline', icon: 'calendar', section: 'intelligence' },
  { to: '/vision', label: 'Vision Lab', icon: 'eye', section: 'intelligence' },
  { to: '/system', label: 'Evaluation & System', icon: 'activity', section: 'intelligence' },
  { to: '/settings', label: 'Settings', icon: 'settings', section: 'account' },
];

const SECTIONS: Array<{ id: NavItem['section']; label: string }> = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'intelligence', label: 'Intelligence' },
  { id: 'account', label: 'Account' },
];

export function isNavActive(item: NavItem, pathname: string): boolean {
  return (item.match ?? [item.to]).some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { pathname } = useLocation();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  return (
    <>
      {open ? (
        <div className="fixed inset-0 z-40 animate-fade-in bg-black/50 backdrop-blur-[1px] lg:hidden" onClick={onClose} aria-hidden="true" />
      ) : null}
      <aside
        id="app-sidebar"
        aria-label="Primary"
        className={cx(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-line bg-surface transition-[transform,visibility] duration-200 lg:visible lg:w-60 lg:translate-x-0',
          open ? 'visible translate-x-0 shadow-2xl lg:shadow-none' : 'invisible -translate-x-full',
        )}
      >
        <div className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-line px-4">
          <Link to="/dashboard" className="flex min-w-0 items-center gap-2.5 rounded-md">
            <LogoMark size={26} />
            <div className="min-w-0 leading-tight">
              <div className="text-sm font-semibold tracking-tight text-fg">MindDoc AI</div>
              <div className="text-[10px] font-medium uppercase tracking-wider text-subtle">Document intelligence</div>
            </div>
          </Link>
          <Button ref={closeRef} variant="ghost" size="icon-sm" className="lg:hidden" aria-label="Close navigation" onClick={onClose} icon="x" />
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Main navigation">
          {SECTIONS.map((section) => (
            <div key={section.id} className="mb-5">
              <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-subtle">{section.label}</div>
              <ul className="space-y-0.5">
                {NAV_ITEMS.filter((n) => n.section === section.id).map((item) => {
                  const active = isNavActive(item, pathname);
                  return (
                    <li key={item.to}>
                      <Link
                        to={item.to}
                        aria-current={active ? 'page' : undefined}
                        className={cx(
                          'group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
                          active ? 'bg-elevated font-medium text-fg' : 'text-muted hover:bg-elevated/70 hover:text-fg',
                        )}
                      >
                        <Icon
                          name={item.icon}
                          className={cx('h-4 w-4', active ? 'text-accent' : 'text-subtle group-hover:text-muted')}
                        />
                        <span className="truncate">{item.label}</span>
                        {active ? <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" /> : null}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-line p-3">
          <Link to="/upload" className={buttonClass('primary', 'sm', 'w-full')}>
            <Icon name="upload" className="h-4 w-4" />
            Upload documents
          </Link>
          <p className="mt-3 px-1 text-[11px] leading-relaxed text-subtle">
            Glass-box AI: every answer ships with sources, an evidence score and a reasoning trace.
          </p>
        </div>
      </aside>
    </>
  );
}
