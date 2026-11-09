import { useCallback, useEffect, useState } from 'react';
import { documentsApi, errorMessage } from '../api';
import { useConfirm } from '../components/ui/Dialog';
import { useToast } from '../components/ui/Toast';
import type { DocumentSummary } from '../types';

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const confirm = useConfirm();

  const reload = useCallback(async () => {
    try {
      setError(null);
      setDocuments(await documentsApi.list());
    } catch (e) {
      setError(errorMessage(e, 'Failed to load documents'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const remove = useCallback(
    async (doc: { id: number; filename: string }): Promise<boolean> => {
      const ok = await confirm({
        title: 'Delete document?',
        description: `“${doc.filename}” and its chunks, entities and embeddings will be permanently removed from this workspace. This cannot be undone.`,
        confirmLabel: 'Delete document',
        tone: 'danger',
      });
      if (!ok) return false;
      try {
        await documentsApi.remove(doc.id);
        setDocuments((ds) => ds.filter((d) => d.id !== doc.id));
        toast.success('Document deleted', doc.filename);
        return true;
      } catch (e) {
        toast.error('Delete failed', errorMessage(e));
        return false;
      }
    },
    [confirm, toast],
  );

  return { documents, setDocuments, loading, error, reload, remove };
}
