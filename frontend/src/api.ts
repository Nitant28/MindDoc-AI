import axios, { type AxiosError, type AxiosProgressEvent } from 'axios';
import { clearToken, getCaseId, getToken } from './lib/storage';
import type {
  ApiErrorBody,
  Capabilities,
  ChatMessage,
  ChatQueryBody,
  ChatSession,
  Credentials,
  DocumentDetail,
  DocumentSummary,
  EvalRequest,
  EvalResult,
  ExtractionFields,
  ExtractResponse,
  GraphData,
  GraphQuery,
  Me,
  MessageResponse,
  Overview,
  PageImage,
  AuditEntry,
  TimelineItem,
  TimelineQuery,
  RagAnswer,
  SavedItem,
  StreamEvent,
  TokenResponse,
  UpdateEmailBody,
  UploadResponse,
  VisionAnalysis,
  DocumentStatus,
  StatementAnalysis,
  AAImportResponse,
  FlowGraph,
  PartyDetail,
  PartyReviewItem,
  PartySummary,
  ResolveResult,
  BankAccountView,
  FindingStatus,
  FindingSummary,
  FindingView,
  ReportSummary,
  ReportView,
  CaseDetail,
  CaseRole,
  CaseSummary,
  TeamInvite,
  TeamMember,
  TenantRole,
} from './types';

const envUrl = import.meta.env.VITE_API_URL?.trim();

export const API_BASE_URL = (envUrl ? envUrl : 'http://127.0.0.1:8000/api').replace(/\/+$/, '');

const api = axios.create({ baseURL: API_BASE_URL });

/** Requests whose 401 means "bad credentials", not "session expired". */
const AUTH_PATHS = ['/auth/login', '/auth/register', '/auth/update_email'];

export function handleUnauthorized(): void {
  clearToken();
  const path = window.location.pathname;
  if (path !== '/login' && path !== '/register') window.location.assign('/login');
}

/** Endpoints that work on one case: the selected case is sent as `case_id` unless the call sets its own. */
const CASE_SCOPED = ['/parties', '/accounts', '/findings', '/reports', '/documents/list', '/documents/upload', '/documents/import-aa'];

export function isCaseScoped(url: string): boolean {
  return CASE_SCOPED.some((p) => url === p || url.startsWith(`${p}/`) || url.startsWith(`${p}?`));
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const caseId = getCaseId();
  const url = config.url ?? '';
  if (caseId != null && isCaseScoped(url)) {
    config.params = { case_id: caseId, ...(config.params ?? {}) };
  }
  if (caseId != null && url === '/chat/query' && config.data && typeof config.data === 'object') {
    config.data = { case_id: caseId, ...(config.data as object) };
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? '';
    if (error.response?.status === 401 && !AUTH_PATHS.some((p) => url.includes(p))) {
      handleUnauthorized();
    }
    return Promise.reject(error);
  },
);

export default api;

// ───────────────────────────── Helpers ─────────────────────────────

export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data as ApiErrorBody | undefined;
    const detail = body?.detail;
    if (typeof detail === 'string' && detail) {
      if (detail === 'Not Found') return 'This feature is not available on the connected backend.';
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0 && detail[0]?.msg) return detail[0].msg;
    if (axios.isCancel(err)) return 'Request cancelled';
    if (!err.response) return 'Cannot reach the MindDoc API. Is the backend running?';
    return `${fallback} (HTTP ${err.response.status})`;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export function isAbortError(err: unknown): boolean {
  if (axios.isCancel(err)) return true;
  const name = (err as { name?: string } | null)?.name;
  return name === 'AbortError' || name === 'CanceledError';
}

export function httpStatus(err: unknown): number | null {
  return axios.isAxiosError(err) ? err.response?.status ?? null : null;
}

const arr = <T>(v: T[] | null | undefined): T[] => (Array.isArray(v) ? v : []);

/** Fills missing v2 fields so the UI never has to guard against `undefined` arrays. */
export function normalizeAnswer(raw: unknown): RagAnswer {
  const r = (raw && typeof raw === 'object' ? raw : {}) as Partial<RagAnswer>;
  return {
    answer: typeof r.answer === 'string' ? r.answer : '',
    session_id: typeof r.session_id === 'number' ? r.session_id : null,
    citations: arr(r.citations),
    confidence: typeof r.confidence === 'number' ? r.confidence : null,
    grounded: typeof r.grounded === 'boolean' ? r.grounded : null,
    groundedness: r.groundedness ?? null,
    sub_queries: arr(r.sub_queries),
    trace: arr(r.trace),
    provider: r.provider ?? null,
    model: r.model ?? null,
    latency_ms: typeof r.latency_ms === 'number' ? r.latency_ms : null,
    abstained: typeof r.abstained === 'boolean' ? r.abstained : null,
    prompt_hash: typeof r.prompt_hash === 'string' && r.prompt_hash ? r.prompt_hash : null,
  };
}

// ───────────────────────────── Auth ─────────────────────────────

export const authApi = {
  login: (body: Credentials) => api.post<TokenResponse>('/auth/login', body).then((r) => r.data),
  register: (body: Credentials) => api.post<TokenResponse>('/auth/register', body).then((r) => r.data),
  me: () => api.get<Me>('/auth/me').then((r) => r.data),
  updateEmail: (body: UpdateEmailBody) =>
    api.put<MessageResponse>('/auth/update_email', body).then((r) => r.data),
};

// ─────────────────────────── Documents ──────────────────────────

export const documentsApi = {
  list: () => api.get<DocumentSummary[]>('/documents/list').then((r) => arr(r.data)),
  /** Every document the user can see, in any case (ignores the selected case). */
  listAll: () => api.get<DocumentSummary[]>('/documents/list', { params: { case_id: undefined } }).then((r) => arr(r.data)),
  get: (id: number) => api.get<DocumentDetail>(`/documents/${id}`).then((r) => r.data),
  /** Import a decrypted Account Aggregator deposit payload (ReBIT JSON/XML) the customer already holds. */
  importAa: (file: File, consentRef?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (consentRef && consentRef.trim()) form.append('consent_ref', consentRef.trim());
    return api.post<AAImportResponse>('/documents/import-aa', form, { timeout: 300_000 }).then((r) => r.data);
  },
  upload: (file: File, onProgress?: (percent: number) => void, signal?: AbortSignal) => {
    const form = new FormData();
    form.append('file', file);
    return api
      .post<UploadResponse>('/documents/upload', form, {
        timeout: 300_000,
        signal,
        onUploadProgress: (e: AxiosProgressEvent) => {
          if (!onProgress) return;
          const total = e.total ?? file.size ?? 1;
          onProgress(Math.min(100, Math.round((e.loaded / Math.max(1, total)) * 100)));
        },
      })
      .then((r) => r.data);
  },
  status: (id: number) => api.get<DocumentStatus>(`/documents/${id}/status`).then((r) => r.data),
  statement: (id: number, refresh = false) =>
    api
      .get<StatementAnalysis>(`/documents/${id}/statement`, { params: { refresh: refresh || undefined }, timeout: 120_000 })
      .then((r) => r.data),
  reprocess: (id: number) => api.post<DocumentStatus>(`/documents/${id}/reprocess`).then((r) => r.data),
  remove: (id: number) => api.delete<MessageResponse>(`/documents/delete/${id}`).then((r) => r.data),
  rename: (id: number, filename: string) =>
    api.put<MessageResponse>(`/documents/edit/${id}`, null, { params: { filename } }).then((r) => r.data),
  /** v2.1 pixel-level citation. Caller must URL.revokeObjectURL(result.url) when done. */
  /** `box` = [x0, top, x1, bottom] in tenths of a point (from /statement) highlights that exact region. */
  pageImage: async (id: number, page: number, chunkId?: number | null, box?: number[] | null): Promise<PageImage> => {
    const r = await api.get<Blob>(`/documents/${id}/page/${page}/image`, {
      params: { chunk_id: chunkId ?? undefined, box: box && box.length === 4 ? box.join(',') : undefined },
      responseType: 'blob',
      timeout: 60_000,
    });
    const raw = r.headers['x-highlight-boxes'];
    const n = raw == null ? NaN : Number(raw);
    return { url: URL.createObjectURL(r.data), highlights: Number.isFinite(n) ? n : null };
  },
  save: (id: number) => api.post<MessageResponse>(`/documents/save/${id}`).then((r) => r.data),
  extract: (id: number, fields: ExtractionFields) =>
    api.post<ExtractResponse>(`/documents/${id}/extract`, { fields }, { timeout: 180_000 }).then((r) => r.data),
};

// ───────────────────────────── Chat ─────────────────────────────

export const chatApi = {
  query: (body: ChatQueryBody, signal?: AbortSignal) =>
    api.post<RagAnswer>('/chat/query', body, { signal }).then((r) => normalizeAnswer(r.data)),
  sessions: () => api.get<ChatSession[]>('/chat/sessions').then((r) => arr(r.data)),
  messages: (sessionId: number) => api.get<ChatMessage[]>(`/chat/messages/${sessionId}`).then((r) => arr(r.data)),
  renameSession: (id: number, title: string) =>
    api.put<ChatSession>(`/chat/sessions/${id}`, null, { params: { title } }).then((r) => r.data),
  deleteSession: (id: number) => api.delete<MessageResponse>(`/chat/sessions/${id}`).then((r) => r.data),
  saveResponse: (title: string, content: string) =>
    api.post<MessageResponse>('/chat/save_response', { title, content }).then((r) => r.data),
  savedItems: () => api.get<SavedItem[]>('/chat/saved_items').then((r) => arr(r.data)),
  deleteSavedItem: (id: number) => api.delete<MessageResponse>(`/chat/saved_items/${id}`).then((r) => r.data),
};

// ───────────────────────── Intelligence ─────────────────────────

export const intelApi = {
  graph: (query: GraphQuery = {}) =>
    api
      .get<GraphData>('/intel/graph', { params: { document_id: query.document_id ?? undefined, limit: query.limit } })
      .then((r): GraphData => ({ nodes: arr(r.data?.nodes), edges: arr(r.data?.edges) })),
  overview: () => api.get<Overview>('/intel/overview').then((r) => r.data),
  evaluate: (body: EvalRequest = {}) =>
    api.post<EvalResult>('/intel/eval', body, { timeout: 300_000 }).then((r) => r.data),
  capabilities: () => api.get<Capabilities>('/intel/capabilities').then((r) => r.data),
  timeline: (query: TimelineQuery = {}) =>
    api
      .get<TimelineItem[]>('/intel/timeline', {
        params: { document_id: query.document_id ?? undefined, upcoming_days: query.upcoming_days ?? undefined },
      })
      .then((r) => arr(r.data)),
  audit: (limit = 50) => api.get<AuditEntry[]>('/intel/audit', { params: { limit } }).then((r) => arr(r.data)),
};

// ─────────────────────────── Vision Lab ─────────────────────────

export const visionApi = {
  analyze: (file: File, signal?: AbortSignal) => {
    const form = new FormData();
    form.append('file', file);
    return api
      .post<VisionAnalysis>('/vision/analyze', form, { timeout: 180_000, signal })
      .then((r) => r.data);
  },
};

// ───────────────────────── Streaming chat ───────────────────────

/**
 * POST /chat/stream (SSE over fetch). Emits trace/token/final/error events as they arrive.
 * On any stream failure (network, non-2xx, error event, no `final`) it emits a client-side
 * `fallback` event and retries with POST /chat/query. Resolves with the final answer.
 * Rejects with an AbortError if `signal` is aborted.
 */
export async function streamChat(
  body: ChatQueryBody,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<RagAnswer> {
  // Mutable holder: TS does not track assignments made inside closures.
  const state: { final: RagAnswer | null; failure: string | null } = { final: null, failure: null };

  const dispatch = (rawEvent: string) => {
    const data = rawEvent
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).replace(/^ /, ''))
      .join('\n')
      .trim();
    if (!data || data === '[DONE]') return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(data);
    } catch {
      return;
    }
    if (!parsed || typeof parsed !== 'object') return;
    const e = parsed as Record<string, unknown>;
    switch (e.type) {
      case 'trace':
        onEvent({
          type: 'trace',
          step: typeof e.step === 'string' ? e.step : 'step',
          detail: typeof e.detail === 'string' ? e.detail : null,
          ms: typeof e.ms === 'number' ? e.ms : null,
        });
        break;
      case 'token':
        if (typeof e.text === 'string') onEvent({ type: 'token', text: e.text });
        break;
      case 'final': {
        const rest: Record<string, unknown> = { ...e };
        delete rest.type;
        const answer = normalizeAnswer(rest);
        state.final = answer;
        onEvent({ type: 'final', ...answer });
        break;
      }
      case 'error': {
        const detail = typeof e.detail === 'string' && e.detail ? e.detail : 'Stream error';
        state.failure = detail;
        onEvent({ type: 'error', detail });
        break;
      }
      default:
        break;
    }
  };

  try {
    const token = getToken();
    const res = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ case_id: getCaseId() ?? undefined, ...body }),
      signal,
    });

    if (res.status === 401) {
      handleUnauthorized();
      throw Object.assign(new Error('Your session has expired. Please sign in again.'), { name: 'AuthError' });
    }

    if (!res.ok || !res.body) {
      state.failure = `Stream unavailable (HTTP ${res.status})`;
    } else {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary = buffer.search(/\r?\n\r?\n/);
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary);
          const sep = /^\r?\n\r?\n/.exec(buffer.slice(boundary));
          buffer = buffer.slice(boundary + (sep ? sep[0].length : 2));
          dispatch(chunk);
          if (state.failure || state.final) break;
          boundary = buffer.search(/\r?\n\r?\n/);
        }
        if (state.failure || state.final) {
          try {
            await reader.cancel();
          } catch {
            /* ignore */
          }
          break;
        }
      }
      buffer += decoder.decode();
      if (buffer.trim() && !state.failure && !state.final) dispatch(buffer);
    }
  } catch (err) {
    if (signal?.aborted || isAbortError(err)) throw err;
    if ((err as { name?: string }).name === 'AuthError') throw err;
    state.failure = err instanceof Error ? err.message : 'Stream failed';
  }

  if (state.final) return state.final;
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');

  onEvent({ type: 'fallback', reason: state.failure ?? 'Stream ended without a final answer' });
  const answer = await chatApi.query(body, signal);
  onEvent({ type: 'final', ...answer });
  return answer;
}

/** Entity resolution, review queue, reversible merges and flow graph (R5). */
export const partiesApi = {
  resolve: () => api.post<ResolveResult>('/parties/resolve', null, { timeout: 180_000 }).then((r) => r.data),
  list: () => api.get<{ case_id: number; parties: PartySummary[] }>('/parties').then((r) => r.data.parties),
  detail: (id: number) => api.get<PartyDetail>(`/parties/${id}`).then((r) => r.data),
  reviews: (state: 'open' | 'merged' | 'kept_separate' = 'open') =>
    api.get<{ reviews: PartyReviewItem[] }>('/parties/reviews', { params: { state } }).then((r) => r.data.reviews),
  decide: (id: number, decision: 'merge' | 'keep_separate', reason: string, overrideConflict = false) =>
    api
      .post<{ id: number; state: string }>(`/parties/reviews/${id}`, { decision, reason, override_conflict: overrideConflict })
      .then((r) => r.data),
  unmerge: (eventId: number, reason: string) =>
    api.post<{ event_id: number; still_connected: boolean }>('/parties/unmerge', { event_id: eventId, reason }).then((r) => r.data),
  graph: () => api.get<FlowGraph>('/parties/graph').then((r) => r.data),
};

/** Bank accounts, findings and frozen reports (R5, design F §4). */
export const accountsApi = {
  list: () => api.get<{ accounts: BankAccountView[] }>('/accounts').then((r) => r.data.accounts),
  setHolder: (id: number, name: string, reason: string) =>
    api.put<{ id: number; holder: string; holder_source: string }>(`/accounts/${id}/holder`, { name, reason }).then((r) => r.data),
};

export const findingsApi = {
  list: () => api.get<{ findings: FindingSummary[] }>('/findings').then((r) => r.data.findings),
  get: (id: number) => api.get<FindingView>(`/findings/${id}`).then((r) => r.data),
  create: (title: string, statement: string, support: Array<{ claim_id: number; role?: string }>) =>
    api.post<FindingView>('/findings', { title, statement, support }).then((r) => r.data),
  revise: (id: number, body: { title?: string; statement?: string; status?: FindingStatus; note?: string }) =>
    api.post<FindingView>(`/findings/${id}/revise`, body).then((r) => r.data),
  refresh: (id: number) => api.post<FindingView>(`/findings/${id}/refresh`).then((r) => r.data),
};

export const reportsApi = {
  list: () => api.get<{ reports: ReportSummary[] }>('/reports').then((r) => r.data.reports),
  get: (id: number) => api.get<ReportView>(`/reports/${id}`).then((r) => r.data),
  issue: (title: string, findingIds: number[]) =>
    api.post<ReportView>('/reports', { title, finding_ids: findingIds }).then((r) => r.data),
  /** The frozen snapshot exactly as hashed. */
  export: (id: number) => api.get<Blob>(`/reports/${id}/export`, { responseType: 'blob' }).then((r) => r.data),
};

/** Cases (engagements) and their members (ADR-0012). Case ids are explicit here, never the selected case. */
export const casesApi = {
  list: () => api.get<CaseSummary[]>('/cases').then((r) => arr(r.data)),
  get: (id: number) => api.get<CaseDetail>(`/cases/${id}`).then((r) => r.data),
  create: (title: string) => api.post<CaseSummary>('/cases', { title }).then((r) => r.data),
  update: (id: number, body: { title?: string; status?: 'open' | 'closed' }) =>
    api.put<CaseSummary>(`/cases/${id}`, body).then((r) => r.data),
  addMember: (id: number, email: string, role: CaseRole) =>
    api.post(`/cases/${id}/members`, { email, role }).then((r) => r.data),
  setRole: (id: number, userId: number, role: CaseRole) =>
    api.put(`/cases/${id}/members/${userId}`, { role }).then((r) => r.data),
  removeMember: (id: number, userId: number) => api.delete(`/cases/${id}/members/${userId}`).then((r) => r.data),
  linkDocument: (id: number, documentId: number) =>
    api.post(`/cases/${id}/documents`, { document_id: documentId }).then((r) => r.data),
  unlinkDocument: (id: number, documentId: number) =>
    api.delete(`/cases/${id}/documents/${documentId}`).then((r) => r.data),
};

/** Organisation members and invitations. */
export const teamApi = {
  members: () =>
    api.get<{ me: number; is_admin: boolean; members: TeamMember[] }>('/team/members').then((r) => r.data),
  updateMember: (id: number, body: { tenant_role?: TenantRole; is_active?: boolean }) =>
    api.put<TeamMember>(`/team/members/${id}`, body).then((r) => r.data),
  invites: () => api.get<TeamInvite[]>('/team/invites').then((r) => arr(r.data)),
  invite: (body: { email?: string; tenant_role: TenantRole; days?: number }) =>
    api.post<TeamInvite>('/team/invites', body).then((r) => r.data),
  revoke: (id: number) => api.delete<TeamInvite>(`/team/invites/${id}`).then((r) => r.data),
};
