import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { documentsApi, errorMessage, httpStatus } from '../../api';
import type { Citation } from '../../types';
import { Badge } from '../ui/Badge';
import { buttonClass } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Spinner } from '../ui/Spinner';
import { useToast } from '../ui/Toast';

/** Pages known to have no original image (404). Shared across messages for this browser session. */
const unavailable = new Set<string>();
const listeners = new Set<() => void>();

export const pageKey = (c: Citation): string => `${c.document_id}:${c.page}`;

export function isPageUnavailable(c: Citation): boolean {
  return unavailable.has(pageKey(c));
}

function markUnavailable(c: Citation): void {
  unavailable.add(pageKey(c));
  listeners.forEach((fn) => fn());
}

/** Re-render subscribers when a page is marked unavailable. */
export function useUnavailablePages(): number {
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const fn = () => setVersion((v) => v + 1);
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return version;
}

interface PageViewerProps {
  citation: Citation | null;
  onClose: () => void;
}

/** Lightbox showing the original page with the cited passage highlighted (GET /documents/{id}/page/{page}/image). */
export default function PageViewer({ citation, onClose }: PageViewerProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [highlights, setHighlights] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (!citation || citation.document_id == null || citation.page == null) return;
    let alive = true;
    let objectUrl: string | null = null;
    setLoading(true);
    setUrl(null);
    setHighlights(null);
    documentsApi
      .pageImage(citation.document_id, citation.page, citation.chunk_id)
      .then((res) => {
        objectUrl = res.url;
        if (!alive) {
          URL.revokeObjectURL(res.url);
          return;
        }
        setUrl(res.url);
        setHighlights(res.highlights);
      })
      .catch((e) => {
        if (!alive) return;
        if (httpStatus(e) === 404) {
          markUnavailable(citation);
          toast.info('Original page not available', 'Only PDFs uploaded after v2.1 have page images.');
        } else {
          toast.error('Could not load page image', errorMessage(e));
        }
        onClose();
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [citation]);

  const open = !!citation && (loading || !!url);

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="xl"
      title={
        citation ? (
          <span>
            [{citation.index}] {citation.filename ?? 'Source'} · page {citation.page}
          </span>
        ) : (
          'Source page'
        )
      }
      description={
        highlights == null ? (
          'Original page with the cited passage highlighted.'
        ) : highlights > 0 ? (
          <span className="inline-flex items-center gap-1.5">
            <Badge tone="warning">{highlights} highlighted region{highlights === 1 ? '' : 's'}</Badge>
            Amber boxes mark the cited passage.
          </span>
        ) : (
          'The passage could not be located visually; showing the page without highlight.'
        )
      }
      footer={
        citation?.document_id != null ? (
          <Link to={`/documents/${citation.document_id}`} className={buttonClass('secondary', 'sm')} onClick={onClose}>
            Open document analysis
          </Link>
        ) : null
      }
    >
      <div className="flex min-h-[50vh] items-start justify-center bg-elevated/50 p-3 sm:p-5">
        {loading || !url ? (
          <div className="flex h-[50vh] items-center justify-center text-muted">
            <Spinner size="lg" className="text-accent" label="Rendering page" />
          </div>
        ) : (
          <img
            src={url}
            alt={`Page ${citation?.page ?? ''} of ${citation?.filename ?? 'the source document'} with the cited passage highlighted`}
            className="max-w-full rounded-md border border-line bg-white shadow-lg"
          />
        )}
      </div>
    </Modal>
  );
}
