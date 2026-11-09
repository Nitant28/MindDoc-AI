import type { AnswerMeta, ChatMode, RagAnswer, TraceStep } from '../../types';

export interface UiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  meta?: AnswerMeta | null;
  status?: 'streaming' | 'done' | 'error' | 'stopped';
  liveTrace?: TraceStep[];
  error?: string;
  /** True when the SSE stream failed and the answer came from POST /chat/query. */
  fallback?: boolean;
  mode?: ChatMode;
}

export function answerToMeta(a: RagAnswer, liveTrace: TraceStep[] = []): AnswerMeta {
  return {
    citations: a.citations,
    confidence: a.confidence,
    grounded: a.grounded,
    groundedness: a.groundedness,
    sub_queries: a.sub_queries,
    trace: a.trace.length ? a.trace : liveTrace,
    provider: a.provider,
    model: a.model,
    latency_ms: a.latency_ms,
    abstained: a.abstained,
    prompt_hash: a.prompt_hash,
  };
}
