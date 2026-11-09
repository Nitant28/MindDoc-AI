import { useId, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authApi, errorMessage } from '../api';
import AuthShell from '../components/AuthShell';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Field';
import { useToast } from '../components/ui/Toast';
import { setToken } from '../lib/storage';
import { useTitle } from '../lib/useTitle';

export function PasswordInput({ id, value, onChange, autoComplete }: { id: string; value: string; onChange: (v: string) => void; autoComplete: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input
        id={id}
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required
        className="h-10 pr-16"
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs font-medium text-muted hover:bg-elevated hover:text-fg"
        aria-label={show ? 'Hide password' : 'Show password'}
        aria-pressed={show}
      >
        {show ? 'Hide' : 'Show'}
      </button>
    </div>
  );
}

export default function Login() {
  useTitle('Sign in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const emailId = useId();
  const pwId = useId();

  const from = (location.state as { from?: string } | null)?.from;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login({ email: email.trim(), password });
      setToken(res.access_token);
      navigate(from && from.startsWith('/') && !from.startsWith('/login') ? from : '/dashboard', { replace: true });
    } catch (err) {
      const msg = errorMessage(err, 'Login failed');
      setError(msg);
      toast.error('Sign in failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your MindDoc workspace."
      footer={
        <>
          Don’t have an account?{' '}
          <Link to="/register" className="font-medium text-accent-soft hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate={false}>
        <Field label="Email" htmlFor={emailId}>
          <Input
            id={emailId}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="you@company.com"
            required
            autoFocus
            className="h-10"
          />
        </Field>
        <Field label="Password" htmlFor={pwId}>
          <PasswordInput id={pwId} value={password} onChange={setPassword} autoComplete="current-password" />
        </Field>
        {error ? (
          <p className="rounded-lg border border-rose-500/30 bg-rose-500/[0.06] px-3 py-2 text-xs text-rose-700 dark:text-rose-300" role="alert">
            {error}
          </p>
        ) : null}
        <Button type="submit" variant="primary" size="lg" className="w-full" loading={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthShell>
  );
}
