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
