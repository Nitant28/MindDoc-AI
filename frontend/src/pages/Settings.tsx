import { useEffect, useId, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, chatApi, errorMessage } from '../api';
import { useLayout } from '../components/Layout';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card, CardBody, CardHeader } from '../components/ui/Card';
import { useConfirm } from '../components/ui/Dialog';
import { EmptyState } from '../components/ui/EmptyState';
import { Field, Input } from '../components/ui/Field';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { Skeleton } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { relTime } from '../lib/format';
import { clearToken } from '../lib/storage';
import { useTheme, type Theme } from '../lib/theme';
import { useTitle } from '../lib/useTitle';
import type { SavedItem } from '../types';
import { PasswordInput } from './Login';

export default function Settings() {
  useTitle('Settings');
  const { me, refreshMe } = useLayout();
  const { theme, setTheme } = useTheme();
  const toast = useToast();
  const confirm = useConfirm();
  const navigate = useNavigate();
  const emailId = useId();
  const pwId = useId();

  const [newEmail, setNewEmail] = useState('');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [saved, setSaved] = useState<SavedItem[]>([]);
  const [savedLoading, setSavedLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    chatApi
      .savedItems()
      .then(setSaved)
      .catch(() => setSaved([]))
      .finally(() => setSavedLoading(false));
  }, []);

  const changeEmail = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await authApi.updateEmail({ new_email: newEmail.trim(), password });
      toast.success('Email updated', `You now sign in as ${newEmail.trim()}.`);
      setNewEmail('');
      setPassword('');
      await refreshMe();
    } catch (err) {
      const msg = errorMessage(err, 'Failed to update email');
      setError(msg);
      toast.error('Update failed', msg);
    } finally {
      setSaving(false);
    }
  };

  const removeSaved = async (item: SavedItem) => {
    const ok = await confirm({
      title: 'Delete saved item?',
      description: `“${item.title}” will be permanently removed.`,
      confirmLabel: 'Delete',
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await chatApi.deleteSavedItem(item.id);
      setSaved((xs) => xs.filter((x) => x.id !== item.id));
      toast.success('Saved item deleted');
    } catch (err) {
      toast.error('Delete failed', errorMessage(err));
    }
  };

  const logout = () => {
    clearToken();
    navigate('/login', { replace: true });
  };

  return (
    <Page className="max-w-4xl">
      <PageHeader title="Settings" description="Account, appearance and saved answers." />
      <div className="space-y-6">
        <Card>
          <CardHeader icon="user" title="Profile" />
          <CardBody>
            <dl className="grid gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-subtle">Email</dt>
                <dd className="mt-1 truncate text-sm font-medium text-fg">{me?.email ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-subtle">Workspace</dt>
                <dd className="mt-1 truncate text-sm text-fg">{me?.workspace != null ? String(me.workspace) : '—'}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-subtle">User ID</dt>
                <dd className="mt-1 font-mono text-sm text-fg">{me?.id ?? '—'}</dd>
              </div>
            </dl>
          </CardBody>
        </Card>

        <Card>
          <CardHeader icon="mail" title="Change email" description="Confirm with your current password." />
          <CardBody>
            <form onSubmit={changeEmail} className="grid gap-4 sm:max-w-md">
              <Field label="New email" htmlFor={emailId}>
                <Input id={emailId} type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} autoComplete="email" required />
              </Field>
              <Field label="Current password" htmlFor={pwId}>
                <PasswordInput id={pwId} value={password} onChange={setPassword} autoComplete="current-password" />
              </Field>
              {error ? (
                <p className="text-xs text-rose-600 dark:text-rose-400" role="alert">
                  {error}
                </p>
              ) : null}
              <div>
                <Button type="submit" variant="primary" loading={saving} disabled={!newEmail || !password}>
                  Update email
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader icon="sun" title="Appearance" description="Stored on this device." />
          <CardBody>
            <Segmented<Theme>
              label="Theme"
              value={theme}
              onChange={setTheme}
              options={[
                { value: 'dark', label: 'Dark', icon: 'moon' },
                { value: 'light', label: 'Light', icon: 'sun' },
              ]}
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader icon="bookmark" title="Saved items" description="Answers and documents you saved from chat." />
          {savedLoading ? (
            <div className="space-y-2 p-5">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : saved.length === 0 ? (
            <EmptyState icon="bookmark" title="Nothing saved yet" description="Use “Save” under any answer in Chat to keep it here." compact />
          ) : (
            <ul className="divide-y divide-line">
              {saved.map((item) => (
                <li key={item.id} className="px-4 py-3 sm:px-5">
                  <div className="flex items-start justify-between gap-3">
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => setExpanded((x) => (x === item.id ? null : item.id))}
                      aria-expanded={expanded === item.id}
                    >
                      <div className="flex items-center gap-2">
                        <Badge tone={item.type === 'document' ? 'info' : 'accent'}>{item.type ?? 'item'}</Badge>
                        <span className="truncate text-sm font-medium text-fg">{item.title}</span>
                      </div>
                      <p className={expanded === item.id ? 'mt-2 whitespace-pre-wrap text-sm text-muted' : 'mt-1 line-clamp-2 text-xs text-subtle'}>
                        {item.content}
                      </p>
                    </button>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="hidden text-xs text-subtle sm:inline">{relTime(item.created_at)}</span>
                      <Button variant="ghost" size="icon-sm" aria-label={`Delete ${item.title}`} onClick={() => removeSaved(item)} icon="trash" className="hover:!text-rose-500" />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader icon="lock" title="Session" />
          <CardBody className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted">Sign out of this browser. Your token is removed from local storage.</p>
            <Button variant="danger" icon="logout" onClick={logout}>
              Log out
            </Button>
          </CardBody>
        </Card>
      </div>
    </Page>
  );
}
