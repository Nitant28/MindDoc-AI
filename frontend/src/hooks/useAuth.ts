import { useState, useEffect } from 'react';

export interface User {
  email: string;
  name?: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Simulate auth state from localStorage or API
    const stored = localStorage.getItem('user');
    if (stored) setUser(JSON.parse(stored));
  }, []);

  function login(user: User) {
    setUser(user);
    localStorage.setItem('user', JSON.stringify(user));
  }

  function logout() {
    setUser(null);
    localStorage.removeItem('user');
    window.location.href = '/login';
  }

  return { user, login, logout };
}
