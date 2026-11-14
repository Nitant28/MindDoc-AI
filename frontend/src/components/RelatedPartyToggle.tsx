import { useState } from 'react';
import { errorMessage, partyTagsApi } from '../api';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Input } from './ui/Field';
import { useToast } from './ui/Toast';

/** Mark a party as related to the case subject (with the reason). The end-use detector uses it. */
export default function RelatedPartyToggle({
  partyId,
  reason: current,
  onChanged,
}: {
  partyId: number;
  reason?: string;
  onChanged?: (reason: string | undefined) => void;
}) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [value, setValue] = useState<string | undefined>(current);

  const save = async (related: boolean) => {
    setBusy(true);
    try {
      await partyTagsApi.setRelated(partyId, related, reason);
      const next = related ? reason.trim() : undefined;
      setValue(next);
      onChanged?.(next);
      setEditing(false);
      setReason('');
      toast.success(related ? 'Marked as related party' : 'No longer marked as related');
    } catch (e) {
      toast.error('Not saved', errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (value) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="warning">related party</Badge>
        <span className="text-muted">{value}</span>
        <Button size="xs" variant="ghost" loading={busy} onClick={() => void save(false)}>
          Remove mark
        </Button>
      </div>
    );
  }
  if (!editing) {
    return (
      <Button size="sm" variant="secondary" icon="tag" onClick={() => setEditing(true)}>
        Mark as related party
      </Button>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        aria-label="Why this party is related"
        className="h-9 min-w-[16rem] flex-1"
        placeholder="Why (e.g. director's relative, per the KYC file)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        autoFocus
      />
      <Button size="sm" variant="primary" loading={busy} disabled={reason.trim().length < 3} onClick={() => void save(true)}>
        Save
      </Button>
      <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
        Cancel
      </Button>
    </div>
  );
}
