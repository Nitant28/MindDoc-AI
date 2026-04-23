import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((s: any) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess(false);
    try {
      if (!email || !password) {
        setError('Please enter email and password.');
        setLoading(false);
        return;
      }
      await login(email, password);
      setSuccess(true);
      setTimeout(() => navigate('/dashboard'), 1200);
    } catch (err) {
      setError('Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg1">
      <div className="w-full max-w-md p-8 glass rounded-2xl border border-bg3">
        <h2 className="text-3xl font-bold mb-6 gradient-text text-center">Welcome Back</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-300">Email</label>
            <input
              className="w-full px-4 py-3 rounded-lg bg-bg2 text-white border border-bg3 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-300">Password</label>
            <input
              className="w-full px-4 py-3 rounded-lg bg-bg2 text-white border border-bg3 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-gradient-to-r from-primary via-accent to-green text-white font-bold text-lg shadow-glow hover:shadow-lg hover:scale-105 transition-all disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        {error && <div className="text-red-400 mt-4 text-center text-sm">{error}</div>}
        {success && <div className="text-green-400 mt-4 text-center text-sm font-semibold">Login successful! Redirecting...</div>}
        <div className="mt-6 text-center text-gray-400 text-sm">
          Don't have an account?{' '}
          <button type="button" className="text-accent hover:text-primary underline font-medium transition" onClick={() => navigate('/register')}>
            Register
          </button>
        </div>
      </div>
    </div>
  );
}