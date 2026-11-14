/** localStorage wrapped in try/catch: private mode, blocked storage and SSR never throw. */
export const storage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* ignore */
    }
  },
  remove(key: string): void {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

export const TOKEN_KEY = 'token';

export const getToken = (): string | null => storage.get(TOKEN_KEY);
export const setToken = (token: string): void => storage.set(TOKEN_KEY, token);
export const clearToken = (): void => storage.remove(TOKEN_KEY);

/** The case (engagement) the user is working in; case-scoped API calls send it as `case_id` (ADR-0012). */
export const CASE_KEY = 'minddoc.case';

export const getCaseId = (): number | null => {
  const raw = storage.get(CASE_KEY);
  const n = raw == null ? NaN : Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
};
export const setCaseId = (id: number | null): void => (id == null ? storage.remove(CASE_KEY) : storage.set(CASE_KEY, String(id)));
