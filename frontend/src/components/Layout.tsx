import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import { authApi, casesApi } from '../api';
import { clearToken, getCaseId, setCaseId } from '../lib/storage';
import { useTheme } from '../lib/theme';
import type { CaseSummary, Me } from '../types';
import CaseSwitcher from './CaseSwitcher';
import CommandPalette from './CommandPalette';
import Sidebar from './Sidebar';
import { Button } from './ui/Button';
import { Icon } from './ui/Icon';
import { PageLoader } from './ui/Spinner';

export interface LayoutContext {
  me: Me | null;
  refreshMe: () => Promise<void>;
  /** Cases the user can see, and the one case-scoped pages show (ADR-0012). */
  cases: CaseSummary[];
  currentCase: CaseSummary | null;
  selectCase: (id: number) => void;
  refreshCases: () => Promise<void>;
}

export function useLayout(): LayoutContext {
  return useOutletContext<LayoutContext>();
}

function AccountMenu({ me, onLogout }: { me: Me | null; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', esc);
    };
  }, [open]);
  const initial = (me?.email ?? '?').charAt(0).toUpperCase();
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account${me?.email ? `: ${me.email}` : ''}`}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-medium text-accent-fg ring-offset-2 ring-offset-bg transition hover:ring-4 hover:ring-fg/10"
      >
        {initial}
      </button>
      {open ? (
        <div role="menu" className="elevation-3 absolute right-0 top-12 z-50 w-72 animate-scale-in overflow-hidden rounded-[28px] bg-elevated p-2">
          <div className="flex flex-col items-center gap-2 px-4 pb-4 pt-5 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent text-xl text-accent-fg">{initial}</span>
            <div className="max-w-full truncate text-sm font-medium text-fg">{me?.email ?? 'Signed in'}</div>
            <div className="text-xs text-subtle">
              {me?.tenant_role === 'admin' ? 'Organisation admin' : 'Organisation member'}
            </div>
          </div>
          <Link role="menuitem" to="/settings" onClick={() => setOpen(false)} className="flex items-center gap-3 rounded-full px-4 py-2.5 text-sm text-fg hover:bg-fg/[0.06]">
            <Icon name="settings" className="h-4 w-4 text-subtle" /> Settings and organisation
          </Link>
          <button role="menuitem" type="button" onClick={onLogout} className="flex w-full items-center gap-3 rounded-full px-4 py-2.5 text-sm text-fg hover:bg-fg/[0.06]">
            <Icon name="logout" className="h-4 w-4 text-subtle" /> Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default function Layout() {
  const [open, setOpen] = useState(false);
  const [palette, setPalette] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [caseId, setCaseState] = useState<number | null>(getCaseId());
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();

  const refreshMe = useCallback(async () => {
    try {
      setMe(await authApi.me());
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const refreshCases = useCallback(async () => {
    try {
      const list = await casesApi.list();
      setCases(list);
      // a stored case the user can no longer see (or another user's) falls back to General
      const stored = getCaseId();
      if (stored != null && !list.some((c) => c.id === stored)) {
        setCaseId(null);
        setCaseState(null);
      }
    } catch {
      setCases([]);
    }
  }, []);

  useEffect(() => {
    void refreshCases();
  }, [refreshCases]);

  const selectCase = useCallback((id: number) => {
    setCaseId(id);
    setCaseState(id);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPalette((p) => !p);
      } else if (e.key === '/' && !typing) {
        e.preventDefault();
        setPalette(true);
      } else if (e.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const currentCase = cases.find((c) => c.id === caseId) ?? cases.find((c) => c.is_default) ?? null;
  const ctx = useMemo<LayoutContext>(
    () => ({ me, refreshMe, cases, currentCase, selectCase, refreshCases }),
    [me, refreshMe, cases, currentCase, selectCase, refreshCases],
  );

  const logout = () => {
    clearToken();
    setCaseId(null);
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-bg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-[100] focus:rounded-full focus:bg-accent focus:px-4 focus:py-2 focus:text-sm focus:text-accent-fg"
      >
        Skip to content
      </a>
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <CommandPalette open={palette} onClose={() => setPalette(false)} cases={cases} onSelectCase={selectCase} />

      <div className="flex min-h-screen flex-col lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-2 bg-bg/95 px-3 backdrop-blur sm:gap-3 sm:px-4">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
            aria-expanded={open}
            aria-controls="app-sidebar"
            onClick={() => setOpen(true)}
            icon="menu"
          />
          <button
            type="button"
            onClick={() => setPalette(true)}
            className="group flex h-12 min-w-0 flex-1 items-center gap-3 rounded-full bg-elevated px-4 text-left text-[15px] text-subtle transition-colors hover:bg-fg/[0.08] sm:max-w-2xl"
            aria-label="Search pages, cases, documents and actions"
          >
            <Icon name="search" className="h-5 w-5 shrink-0" />
            <span className="truncate">Search in MindDoc</span>
            <span className="ml-auto hidden items-center gap-1 sm:flex">
              <kbd>Ctrl</kbd>
              <kbd>K</kbd>
            </span>
          </button>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <CaseSwitcher cases={cases} current={currentCase} onSelect={selectCase} />
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
              icon={theme === 'dark' ? 'sun' : 'moon'}
            />
            <AccountMenu me={me} onLogout={logout} />
          </div>
        </header>

        <main id="main" tabIndex={-1} className="app-panel mb-0 min-w-0 flex-1 focus:outline-none lg:mb-3 lg:mr-3">
          <Suspense fallback={<PageLoader />}>
            {/* switching case remounts the page so everything reloads for the new case */}
            <Outlet key={currentCase?.id ?? 0} context={ctx} />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
