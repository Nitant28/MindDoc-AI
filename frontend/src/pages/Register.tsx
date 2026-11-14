import { useId, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authApi, errorMessage } from '../api';
import AuthShell from '../components/AuthShell';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Field';
import { useToast } from '../components/ui/Toast';
import { setToken } from '../lib/storage';
import { useTitle } from '../lib/useTitle';
import { PasswordInput } from './Login';

export default function Register() {
  const [params] = useSearchParams();
  const invite = params.get('invite')?.trim() || null;
  useTitle(invite ? 'Join your organisation' : 'Create account');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const toast = useToast();
  const emailId = useId();
  const pwId = useId();
  const confirmId = useId();

  const mismatch = confirm.length > 0 && confirm !== password;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.register({ email: email.trim(), password, invite_token: invite ?? undefined });
      setToken(res.access_token);
      toast.success(
        invite ? 'You joined the organisation' : 'Workspace created',
        invite ? 'Ask a case lead to add you to the cases you work on.' : 'Upload a document to get started.',
      );
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const msg = errorMessage(err, 'Registration failed');
      setError(msg);
      toast.error('Registration failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title={invite ? 'Join your organisation' : 'Create your workspace'}
      subtitle={
        invite
          ? 'You were invited to an organisation. Use the email address the invitation was made for, if it names one.'
          : 'A private, isolated workspace for your documents.'
      }
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-accent-soft hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
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
          <PasswordInput id={pwId} value={password} onChange={setPassword} autoComplete="new-password" />
        </Field>
        <Field label="Confirm password" htmlFor={confirmId} error={mismatch ? 'Passwords do not match.' : undefined}>
          <PasswordInput id={confirmId} value={confirm} onChange={setConfirm} autoComplete="new-password" />
        </Field>
        {error ? (
          <p className="rounded-lg border border-rose-500/30 bg-rose-500/[0.06] px-3 py-2 text-xs text-rose-700 dark:text-rose-300" role="alert">
            {error}
          </p>
        ) : null}
        <Button type="submit" variant="primary" size="lg" className="w-full" loading={loading} disabled={mismatch}>
          {loading ? (invite ? 'Joining…' : 'Creating workspace…') : invite ? 'Join organisation' : 'Create account'}
        </Button>
      </form>
    </AuthShell>
  );
}
