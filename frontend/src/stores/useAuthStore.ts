import { create } from 'zustand';
import api from '../api';

interface AuthState {
  token: string | null;
  user: any | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string | null) => void;
}

export const useAuthStore = create<AuthState>((set) => {
  // Initialize token from localStorage
  const savedToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

  return {
    token: savedToken,
    user: null,
    loading: false,
    error: null,

    login: async (email: string, password: string) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post('/auth/login', { email, password });
        const { access_token } = response.data;
        localStorage.setItem('token', access_token);
        set({ token: access_token, loading: false });
      } catch (error: any) {
        const errorMessage = error.response?.data?.detail || 'Login failed';
        set({ error: errorMessage, loading: false });
        throw error;
      }
    },

    register: async (email: string, password: string) => {
      set({ loading: true, error: null });
      try {
        const response = await api.post('/auth/register', { email, password });
        const { access_token } = response.data;
        localStorage.setItem('token', access_token);
        set({ token: access_token, loading: false });
      } catch (error: any) {
        const errorMessage = error.response?.data?.detail || 'Registration failed';
        set({ error: errorMessage, loading: false });
        throw error;
      }
    },

    logout: () => {
      localStorage.removeItem('token');
      set({ token: null, user: null });
    },

    setToken: (token: string | null) => {
      if (token) {
        localStorage.setItem('token', token);
      } else {
        localStorage.removeItem('token');
      }
      set({ token });
    },
  };
});
