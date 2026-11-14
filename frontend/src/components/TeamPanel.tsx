import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { errorMessage, teamApi } from '../api';
import { copyText } from '../lib/clipboard';
import type { TeamInvite, TeamMember, TenantRole } from '../types';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Card, CardBody, CardHeader } from './ui/Card';
import { Field, Input, Select } from './ui/Field';
import { useToast } from './ui/Toast';

/** Organisation members and invitations (ADR-0012). MindDoc sends no email: the admin copies the one-time link. */
export default function TeamPanel() {
  const toast = useToast();
  const [me, setMe] = useState<number | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invites, setInvites] = useState<TeamInvite[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<TenantRole>('member');
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const m = await teamApi.members();
      setMe(m.me);
      setIsAdmin(m.is_admin);
      setMembers(m.members);
      setInvites(m.is_admin ? await teamApi.invites() : []);
    } catch (e) {
      toast.error('Could not load the team', errorMessage(e));
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const invite = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const inv = await teamApi.invite({ email: email.trim() || undefined, tenant_role: role });
      setLink(`${window.location.origin}/register?invite=${encodeURIComponent(inv.token ?? '')}`);
      setEmail('');
      await load();
    } catch (err) {
      toast.error('Invitation not created', errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const update = async (m: TeamMember, body: { tenant_role?: TenantRole; is_active?: boolean }) => {
    try {
      await teamApi.updateMember(m.id, body);
      await load();
    } catch (err) {
      toast.error('Not changed', errorMessage(err));
    }
  };

  const revoke = async (i: TeamInvite) => {
    try {
      await teamApi.revoke(i.id);
      await load();
    } catch (err) {
      toast.error('Not revoked', errorMessage(err));
    }
  };

  return (
    <Card>
      <CardHeader icon="user" title="Organisation" description="Members of your organisation and invitations to join it." />
      <CardBody className="space-y-5 text-xs">
        <table className="w-full text-left">
          <thead className="text-[11px] uppercase tracking-wider text-subtle">
            <tr>
              <th className="py-1.5 font-medium">Email</th>
              <th className="py-1.5 font-medium">Role</th>
              <th className="py-1.5 font-medium">Status</th>
              {isAdmin && <th className="py-1.5" />}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-t border-line">
                <td className="py-2 text-fg">
                  {m.email}
                  {m.id === me ? <span className="ml-1 text-subtle">(you)</span> : null}
                </td>
                <td className="py-2">{m.tenant_role}</td>
                <td className="py-2">
                  <Badge tone={m.active ? 'success' : 'neutral'}>{m.active ? 'active' : 'deactivated'}</Badge>
                </td>
                {isAdmin && (
                  <td className="py-2 text-right">
                    {m.id !== me && (
                      <div className="flex justify-end gap-1.5">
                        <Button size="sm" variant="ghost" onClick={() => void update(m, { tenant_role: m.tenant_role === 'admin' ? 'member' : 'admin' })}>
                          {m.tenant_role === 'admin' ? 'Make member' : 'Make admin'}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => void update(m, { is_active: !m.active })}>
                          {m.active ? 'Deactivate' : 'Reactivate'}
                        </Button>
                      </div>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>

        {isAdmin ? (
          <>
            <form onSubmit={invite} className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
              <Field label="Invite by email (optional: limits the link to this address)" htmlFor="invite-email">
                <Input id="invite-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="colleague@firm.com" />
              </Field>
              <Field label="Organisation role" htmlFor="invite-role">
                <Select id="invite-role" value={role} onChange={(e) => setRole(e.target.value as TenantRole)}>
                  <option value="member">member</option>
                  <option value="admin">admin</option>
                </Select>
              </Field>
              <Button type="submit" variant="primary" icon="plus" loading={busy}>
                Create invitation
              </Button>
            </form>
            {link && (
              <div className="rounded-lg border border-accent/30 bg-accent/[0.06] p-3">
                <p className="mb-2 text-muted">
                  One-time link, shown only now. Send it to your colleague yourself; it expires in 7 days.
                </p>
                <div className="flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate rounded bg-surface px-2 py-1 font-mono text-[11px]">{link}</code>
                  <Button
                    size="sm"
                    icon="copy"
                    onClick={() => void copyText(link).then((ok) => (ok ? toast.success('Link copied') : toast.error('Copy failed')))}
                  >
                    Copy
                  </Button>
                </div>
              </div>
            )}
            {invites.length > 0 && (
              <ul className="divide-y divide-line">
                {invites.map((i) => (
                  <li key={i.id} className="flex items-center justify-between gap-3 py-2">
                    <span className="min-w-0 truncate">
                      {i.email ?? 'any email'} · {i.tenant_role} · expires {new Date(i.expires_at).toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-2">
                      <Badge tone={i.state === 'open' ? 'info' : 'neutral'}>{i.state}</Badge>
                      {i.state === 'open' && (
                        <Button size="sm" variant="ghost" onClick={() => void revoke(i)}>
                          Revoke
                        </Button>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <p className="text-subtle">Only an organisation admin can invite people or change roles.</p>
        )}
      </CardBody>
    </Card>
  );
}
