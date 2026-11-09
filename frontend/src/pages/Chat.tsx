import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { chatApi, documentsApi, errorMessage, isAbortError, streamChat } from '../api';
import AssistantMessage from '../components/chat/AssistantMessage';
import Composer from '../components/chat/Composer';
import ScopePicker, { scopeLabel } from '../components/chat/ScopePicker';
import SessionList from '../components/chat/SessionList';
import { answerToMeta, type UiMessage } from '../components/chat/types';
import { LogoMark } from '../components/Logo';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useConfirm } from '../components/ui/Dialog';
import { Icon } from '../components/ui/Icon';
import { Segmented } from '../components/ui/Segmented';
import { Spinner } from '../components/ui/Spinner';
import { useToast } from '../components/ui/Toast';
import { cx } from '../lib/cx';
import { uid } from '../lib/format';
import { useTitle } from '../lib/useTitle';
import type { ChatMessage, ChatMode, ChatQueryBody, ChatSession, DocumentSummary } from '../types';

const EXAMPLES = [
  { icon: 'sparkles' as const, text: 'Summarize the key points across my documents.' },
  { icon: 'alert' as const, text: 'What risks, obligations or penalties are mentioned?' },
  { icon: 'user' as const, text: 'List the people and organizations involved and their roles.' },
  { icon: 'calendar' as const, text: 'Which dates and deadlines appear, and what do they relate to?' },
];

function toUi(m: ChatMessage): UiMessage {
  return {
    id: uid(),
    role: m.role === 'user' ? 'user' : 'assistant',
    content: m.content ?? '',
    meta: m.meta ?? null,
    status: 'done',
  };
}

function parseDocParam(v: string | null): number | null {
  if (!v || !/^\d+$/.test(v)) return null;
  const n = Number(v);
  return n > 0 ? n : null;
}

export default function Chat() {
  useTitle('Chat');
  const toast = useToast();
  const confirm = useConfirm();
  const [searchParams, setSearchParams] = useSearchParams();
  const docParam = parseDocParam(searchParams.get('document'));

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [scope, setScope] = useState<number[]>(() => (docParam ? [docParam] : []));
  const [mode, setMode] = useState<ChatMode>('fast');
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [atBottom, setAtBottom] = useState(true);

  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  // ── data loading ───────────────────────────────────────────────
  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await chatApi.sessions());
    } catch (e) {
      toast.error('Could not load chat history', errorMessage(e));
    } finally {
      setSessionsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void refreshSessions();
    documentsApi
      .list()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, [refreshSessions]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // ?document=ID → scope (honours links from Dashboard / Document page)
  useEffect(() => {
    if (docParam && !(scope.length === 1 && scope[0] === docParam)) setScope([docParam]);
  }, [docParam]);

  const changeScope = (ids: number[]) => {
    setScope(ids);
    const next = new URLSearchParams(searchParams);
    if (ids.length === 1) next.set('document', String(ids[0]));
    else next.delete('document');
    setSearchParams(next, { replace: true });
  };

  // ── scrolling ──────────────────────────────────────────────────
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const bottom = el.scrollHeight - el.scrollTop - el.clientHeight < 96;
    stickRef.current = bottom;
    if (bottom !== atBottom) setAtBottom(bottom);
  };

  const scrollToBottom = (smooth = false) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    stickRef.current = true;
    setAtBottom(true);
  };

  useLayoutEffect(() => {
    if (stickRef.current) {
      const el = scrollRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  // ── sessions ───────────────────────────────────────────────────
  const stopStreaming = () => {
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const openSession = async (id: number) => {
    setDrawer(false);
    if (id === sessionId && messages.length) return;
    stopStreaming();
    setSessionId(id);
    setLoadingMessages(true);
    setMessages([]);
    try {
      const msgs = await chatApi.messages(id);
      stickRef.current = true;
      setMessages(msgs.map(toUi));
    } catch (e) {
      toast.error('Could not load conversation', errorMessage(e));
    } finally {
      setLoadingMessages(false);
    }
  };

  const newChat = () => {
    stopStreaming();
    setSessionId(null);
    setMessages([]);
    setDrawer(false);
    window.setTimeout(() => composerRef.current?.focus(), 0);
  };

  const renameSession = async (id: number, title: string) => {
    const prev = sessions;
    setSessions((ss) => ss.map((s) => (s.id === id ? { ...s, title } : s)));
    try {
      await chatApi.renameSession(id, title);
      toast.success('Chat renamed');
    } catch (e) {
      setSessions(prev);
      toast.error('Rename failed', errorMessage(e));
    }
  };

  const deleteSession = async (s: ChatSession) => {
    const ok = await confirm({
      title: 'Delete conversation?',
      description: `“${s.title || 'Untitled chat'}” and all of its messages will be permanently deleted.`,
      confirmLabel: 'Delete',
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await chatApi.deleteSession(s.id);
      setSessions((ss) => ss.filter((x) => x.id !== s.id));
      if (sessionId === s.id) newChat();
      toast.success('Conversation deleted');
    } catch (e) {
      toast.error('Delete failed', errorMessage(e));
    }
  };

  // ── sending ────────────────────────────────────────────────────
  const send = async (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || streaming) return;
    setInput('');
    const asstId = uid();
    stickRef.current = true;
    setMessages((ms) => [
      ...ms,
      { id: uid(), role: 'user', content: q },
      { id: asstId, role: 'assistant', content: '', status: 'streaming', liveTrace: [], mode },
    ]);
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const patch = (fn: (m: UiMessage) => UiMessage) => setMessages((ms) => ms.map((m) => (m.id === asstId ? fn(m) : m)));
    const body: ChatQueryBody = {
      query: q,
      session_id: sessionId,
      document_id: scope.length === 1 ? scope[0] : null,
      document_ids: scope.length ? scope : null,
      mode,
    };

    try {
      const answer = await streamChat(
        body,
        (evt) => {
          switch (evt.type) {
            case 'trace':
              patch((m) => ({ ...m, liveTrace: [...(m.liveTrace ?? []), { step: evt.step, detail: evt.detail, ms: evt.ms }] }));
              break;
            case 'token':
              patch((m) => ({ ...m, content: m.content + evt.text }));
              break;
            case 'fallback':
              patch((m) => ({ ...m, content: '', fallback: true }));
              break;
            default:
              break;
          }
        },
        ctrl.signal,
      );
      patch((m) => ({ ...m, content: answer.answer || m.content, status: 'done', meta: answerToMeta(answer, m.liveTrace) }));
      if (answer.session_id != null && answer.session_id !== sessionId) {
        setSessionId(answer.session_id);
        void refreshSessions();
      } else if (sessionId == null) {
        void refreshSessions();
      }
    } catch (err) {
      if (isAbortError(err) || ctrl.signal.aborted) {
        patch((m) => ({ ...m, status: 'stopped', content: m.content || '_Generation stopped._' }));
      } else {
        const msg = errorMessage(err, 'The query failed');
        patch((m) => ({ ...m, status: 'error', error: msg }));
        toast.error('Query failed', msg);
      }
    } finally {
      if (abortRef.current === ctrl) abortRef.current = null;
      setStreaming(false);
    }
  };

  const retry = (asstId: string) => {
    const idx = messages.findIndex((m) => m.id === asstId);
    const question = idx > 0 ? messages[idx - 1] : null;
    if (!question || question.role !== 'user') return;
    setMessages((ms) => ms.filter((_m, i) => i !== idx && i !== idx - 1));
    void send(question.content);
  };

  // ── render ─────────────────────────────────────────────────────
  const activeSession = sessions.find((s) => s.id === sessionId);
  const scopeText = scopeLabel(documents, scope);
  const scopeChips = useMemo(
    () => scope.map((id) => ({ id, name: documents.find((d) => d.id === id)?.filename ?? `Document #${id}` })),
    [scope, documents],
  );

  const sessionPanel = (
    <SessionList
      sessions={sessions}
      activeId={sessionId}
      loading={sessionsLoading}
      onSelect={(id) => void openSession(id)}
      onNew={newChat}
      onRename={renameSession}
      onDelete={(s) => void deleteSession(s)}
    />
  );

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] min-h-0">
      {/* Sessions — desktop */}
      <aside className="hidden w-64 shrink-0 border-r border-line bg-surface/50 md:block" aria-label="Chat history">
        {sessionPanel}
      </aside>

      {/* Sessions — mobile drawer */}
      {drawer ? (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="Chat history">
          <div className="absolute inset-0 animate-fade-in bg-black/50" onClick={() => setDrawer(false)} aria-hidden="true" />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] animate-slide-up border-r border-line bg-surface shadow-2xl">
            <div className="flex h-12 items-center justify-between border-b border-line px-3">
              <span className="text-sm font-semibold">Conversations</span>
              <Button variant="ghost" size="icon-sm" aria-label="Close chat history" onClick={() => setDrawer(false)} icon="x" />
            </div>
            <div className="h-[calc(100%-3rem)]">{sessionPanel}</div>
          </div>
        </div>
      ) : null}

      <section className="flex min-w-0 flex-1 flex-col" aria-label="Conversation">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2 sm:px-4">
          <Button variant="ghost" size="icon-sm" className="md:hidden" aria-label="Show chat history" onClick={() => setDrawer(true)} icon="panel" />
          <h1 className="min-w-0 flex-1 truncate text-sm font-medium text-fg">{activeSession?.title || (sessionId ? 'Conversation' : 'New conversation')}</h1>
          <ScopePicker documents={documents} value={scope} onChange={changeScope} disabled={streaming} />
          <Segmented<ChatMode>
            label="Answer mode"
            value={mode}
            onChange={setMode}
            disabled={streaming}
            options={[
              { value: 'fast', label: 'Fast', icon: 'zap', hint: 'Hybrid BM25 + dense retrieval, single pass' },
              { value: 'deep', label: 'Deep', icon: 'brain', hint: 'Query decomposition, multi-query retrieval and LLM verification (slower, better)' },
            ]}
          />
        </div>

        {/* Messages */}
        <div className="relative min-h-0 flex-1">
          <div ref={scrollRef} onScroll={onScroll} className="h-full overflow-y-auto" aria-live="off">
            <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
              {loadingMessages ? (
                <div className="flex justify-center py-16 text-muted">
                  <Spinner size="lg" className="text-accent" label="Loading conversation" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-col items-center py-10 text-center sm:py-16">
                  <LogoMark size={40} />
                  <h2 className="mt-4 text-lg font-semibold tracking-tight text-fg">Ask anything about your documents</h2>
                  <p className="mt-1.5 max-w-md text-sm text-muted">
                    Every answer is glass-box: inline citations, a confidence score, a groundedness check and the full reasoning trace.
                  </p>
                  <p className="mt-3 text-xs text-subtle">
                    Searching <span className="font-medium text-muted">{scopeText}</span>
                    {scope.length === 0 && documents.length ? ` · ${documents.length} documents` : ''} · {mode === 'deep' ? 'Deep' : 'Fast'} mode
                  </p>
                  <div className="mt-8 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                    {EXAMPLES.map((ex) => (
                      <button
                        key={ex.text}
                        type="button"
                        onClick={() => void send(ex.text)}
                        className="flex items-start gap-2.5 rounded-xl border border-line bg-surface p-3 text-left text-sm text-muted transition-colors hover:border-line-strong hover:bg-elevated hover:text-fg"
                      >
                        <Icon name={ex.icon} className="mt-0.5 h-4 w-4 text-accent" />
                        {ex.text}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-8">
                  {messages.map((m, i) =>
                    m.role === 'user' ? (
                      <div key={m.id} className="flex justify-end">
                        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md border border-line bg-elevated px-4 py-2.5 text-sm text-fg">
                          {m.content}
                        </div>
                      </div>
                    ) : (
                      <AssistantMessage
                        key={m.id}
                        message={m}
                        question={i > 0 && messages[i - 1].role === 'user' ? messages[i - 1].content : undefined}
                        onRetry={m.status === 'error' ? () => retry(m.id) : undefined}
                      />
                    ),
                  )}
                </div>
              )}
            </div>
          </div>
          {!atBottom && messages.length > 0 ? (
            <Button
              variant="secondary"
              size="xs"
              icon="arrowDown"
              className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full shadow-lg"
              onClick={() => scrollToBottom(true)}
            >
              Jump to latest
            </Button>
          ) : null}
        </div>

        {/* Composer */}
        <div className="border-t border-line bg-bg/80 px-3 pb-3 pt-2 backdrop-blur sm:px-4">
          <div className="mx-auto w-full max-w-3xl">
            {scopeChips.length > 0 ? (
              <div className="mb-2 flex flex-wrap items-center gap-1.5 text-xs">
                <span className="text-subtle">Scope:</span>
                {scopeChips.map((c) => (
                  <span key={c.id} className="inline-flex max-w-[16rem] items-center gap-1 rounded-md border border-line bg-surface py-0.5 pl-2 pr-0.5 text-muted">
                    <span className="truncate">{c.name}</span>
                    <button
                      type="button"
                      onClick={() => changeScope(scope.filter((x) => x !== c.id))}
                      className="rounded p-0.5 hover:bg-elevated hover:text-fg"
                      aria-label={`Remove ${c.name} from scope`}
                      disabled={streaming}
                    >
                      <Icon name="x" className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            ) : null}
            <Composer
              ref={composerRef}
              value={input}
              onChange={setInput}
              onSubmit={() => void send()}
              onStop={stopStreaming}
              streaming={streaming}
              footer={
                <span className={cx('inline-flex items-center gap-1.5')}>
                  <Badge tone={mode === 'deep' ? 'accent' : 'neutral'}>{mode === 'deep' ? 'Deep' : 'Fast'}</Badge>
                  <span className="truncate">{scopeText}</span>
                </span>
              }
            />
          </div>
        </div>
      </section>
    </div>
  );
}
