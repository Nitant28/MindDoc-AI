import { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cx } from '../lib/cx';
import { LogoMark } from './Logo';
import { Button } from './ui/Button';
import { Icon, type IconName } from './ui/Icon';

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  section: 'workspace' | 'investigation' | 'insight' | 'account';
  match?: string[];
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Home', icon: 'dashboard', section: 'workspace' },
  { to: '/cases', label: 'Cases', icon: 'folder', section: 'workspace' },
  { to: '/upload', label: 'Documents', icon: 'file', section: 'workspace', match: ['/upload', '/documents'] },
  { to: '/chat', label: 'Ask', icon: 'chat', section: 'workspace' },
  { to: '/discoveries', label: 'Discoveries', icon: 'target', section: 'investigation' },
  { to: '/parties', label: 'Parties & money flow', icon: 'user', section: 'investigation' },
  { to: '/findings', label: 'Findings & reports', icon: 'bookmark', section: 'investigation' },
  { to: '/graph', label: 'Knowledge graph', icon: 'graph', section: 'insight' },
  { to: '/timeline', label: 'Timeline', icon: 'calendar', section: 'insight' },
  { to: '/vision', label: 'Vision lab', icon: 'eye', section: 'insight' },
  { to: '/system', label: 'Evaluation & system', icon: 'activity', section: 'insight' },
  { to: '/settings', label: 'Settings', icon: 'settings', section: 'account' },
];

const SECTIONS: Array<{ id: NavItem['section']; label: string | null }> = [
  { id: 'workspace', label: null },
  { id: 'investigation', label: 'Investigation' },
  { id: 'insight', label: 'Insight' },
  { id: 'account', label: null },
];

export function isNavActive(item: NavItem, pathname: string): boolean {
  return (item.match ?? [item.to]).some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

/** Navigation drawer: a "New" action on top, pill-shaped destinations, quiet section labels. */
export default function Sidebar({ open, onClose }: SidebarProps) {
  const { pathname } = useLocation();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  return (
    <>
      {open ? (
        <div className="fixed inset-0 z-40 animate-fade-in bg-black/40 lg:hidden" onClick={onClose} aria-hidden="true" />
      ) : null}
      <aside
        id="app-sidebar"
        aria-label="Primary"
        className={cx(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-bg transition-[transform,visibility] duration-200 lg:visible lg:w-64 lg:translate-x-0',
          open ? 'visible translate-x-0 elevation-3 lg:shadow-none' : 'invisible -translate-x-full',
        )}
      >
        <div className="flex h-16 shrink-0 items-center justify-between gap-2 px-5">
          <Link to="/dashboard" className="flex min-w-0 items-center gap-2.5 rounded-full">
            <LogoMark size={30} />
            <span className="truncate text-[19px] font-normal tracking-tight text-fg">
              MindDoc <span className="font-medium">AI</span>
            </span>
          </Link>
          <Button ref={closeRef} variant="ghost" size="icon-sm" className="lg:hidden" aria-label="Close navigation" onClick={onClose} icon="x" />
        </div>

        <div className="px-3 pb-2 pt-1">
          <Link
            to="/upload"
            className="elevation-1 hover:elevation-2 inline-flex h-14 items-center gap-3 rounded-2xl bg-surface pl-4 pr-6 text-sm font-medium text-fg transition-shadow dark:bg-elevated"
          >
            <Icon name="plus" className="h-5 w-5 text-accent-soft" />
            New
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 pb-4 pt-2" aria-label="Main navigation">
          {SECTIONS.map((section) => (
            <div key={section.id} className="mb-3">
              {section.label ? (
                <div className="px-4 pb-1 pt-3 text-[11px] font-medium uppercase tracking-[0.08em] text-subtle">{section.label}</div>
              ) : null}
              <ul className="space-y-0.5">
                {NAV_ITEMS.filter((n) => n.section === section.id).map((item) => {
                  const active = isNavActive(item, pathname);
                  return (
                    <li key={item.to}>
                      <Link
                        to={item.to}
                        aria-current={active ? 'page' : undefined}
                        className={cx(
                          'group flex h-10 items-center gap-3.5 rounded-full px-4 text-sm transition-colors',
                          active
                            ? 'bg-accent-container font-medium text-accent-on-container'
                            : 'text-muted hover:bg-fg/[0.06] hover:text-fg',
                        )}
                      >
                        <Icon name={item.icon} className={cx('h-[18px] w-[18px] shrink-0', active ? '' : 'text-subtle group-hover:text-muted')} />
                        <span className="truncate">{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <p className="px-6 pb-5 text-[11px] leading-relaxed text-subtle">
          Every answer cites its sources. Leads are for review, never verdicts.
        </p>
      </aside>
    </>
  );
}
