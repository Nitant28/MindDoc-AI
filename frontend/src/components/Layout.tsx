import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import { authApi, casesApi } from '../api';
import { clearToken, getCaseId, setCaseId } from '../lib/storage';
import { useTheme } from '../lib/theme';
import type { CaseSummary, Me } from '../types';
import CaseSwitcher from './CaseSwitcher';
import Sidebar, { NAV_ITEMS, isNavActive } from './Sidebar';
import { Button } from './ui/Button';
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

export default function Layout() {
  const [open, setOpen] = useState(false);
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
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const current = NAV_ITEMS.find((n) => isNavActive(n, location.pathname));
  const currentCase = cases.find((c) => c.id === caseId) ?? cases.find((c) => c.is_default) ?? null;
  const ctx = useMemo<LayoutContext>(
    () => ({ me, refreshMe, cases, currentCase, selectCase, refreshCases }),
    [me, refreshMe, cases, currentCase, selectCase, refreshCases],
  );
  const initial = (me?.email ?? '?').charAt(0).toUpperCase();
  const workspace = me?.workspace != null && me.workspace !== '' ? String(me.workspace) : 'Workspace';

  const logout = () => {
    clearToken();
    setCaseId(null);
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-bg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-[100] focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>
      <Sidebar open={open} onClose={() => setOpen(false)} />

      <div className="flex min-h-screen flex-col lg:pl-60">
        <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-line bg-bg/80 px-4 backdrop-blur-md sm:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="-ml-2 lg:hidden"
            aria-label="Open navigation"
            aria-expanded={open}
            aria-controls="app-sidebar"
            onClick={() => setOpen(true)}
            icon="menu"
          />
          <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2 text-sm">
            <span className="hidden max-w-[10rem] truncate text-subtle xl:inline">{workspace}</span>
            <span className="hidden text-line-strong xl:inline" aria-hidden="true">
              /
            </span>
            <CaseSwitcher cases={cases} current={currentCase} onSelect={selectCase} />
            <span className="text-line-strong" aria-hidden="true">
              /
            </span>
            <span className="truncate font-medium text-fg" aria-current="page">
              {current?.label ?? 'MindDoc'}
            </span>
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
              icon={theme === 'dark' ? 'sun' : 'moon'}
            />
            <div
              className="hidden items-center gap-2 rounded-lg border border-line bg-surface py-1 pl-1 pr-2.5 sm:flex"
              title={me?.email ?? undefined}
            >
              <span
                className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 text-xs font-semibold text-accent-soft"
                aria-hidden="true"
              >
                {initial}
              </span>
              <span className="max-w-[14rem] truncate text-xs text-muted">
                <span className="sr-only">Signed in as </span>
                {me?.email ?? 'Signed in'}
              </span>
            </div>
            <Button variant="ghost" size="sm" icon="logout" onClick={logout} aria-label="Log out">
              <span className="hidden md:inline">Log out</span>
            </Button>
          </div>
        </header>

        <main id="main" tabIndex={-1} className="min-w-0 flex-1 focus:outline-none">
          <Suspense fallback={<PageLoader />}>
            {/* switching case remounts the page so everything reloads for the new case */}
            <Outlet key={currentCase?.id ?? 0} context={ctx} />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
