/**
 * Types for the MindDoc AI v2 API contract (docs/API_CONTRACT.md).
 * Everything added in v2 is optional/nullable: documents uploaded before v2 have no analysis fields.
 */

// ───────────────────────────── Auth ─────────────────────────────

export interface Credentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UpdateEmailBody {
  new_email: string;
  password: string;
}

export interface MessageResponse {
  message: string;
}

export interface Me {
  id: number;
  email: string;
  workspace?: string | number | null;
}

// ─────────────────────────── Documents ──────────────────────────

export const ACCEPTED_EXTENSIONS = [
  '.pdf',
  '.docx',
  '.txt',
  '.md',
  '.png',
  '.jpg',
  '.jpeg',
  '.tiff',
  '.bmp',
  '.gif',
  '.webp',
] as const;

export type EntityType =
  | 'PERSON'
  | 'ORG'
  | 'LOCATION'
  | 'DATE'
  | 'MONEY'
  | 'EMAIL'
  | 'URL'
  | 'PRODUCT'
  | 'LAW'
  | 'CONCEPT'
  | 'OTHER';

export interface Keyword {
  term: string;
  score: number;
}

export interface Entity {
  name: string;
  type: EntityType | string;
  count: number;
}

export interface PiiSummary {
  count: number;
  types: Record<string, number>;
}

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface SecurityFlag {
  type: 'prompt_injection' | string;
  severity: Severity | string;
  snippet?: string | null;
}

export type QualityLabel = 'good' | 'fair' | 'poor';

export interface VisionPage {
  page: number;
  method?: 'text' | 'ocr' | string | null;
  ocr_confidence?: number | null;
  blur_score?: number | null;
  quality?: QualityLabel | string | null;
  skew_angle?: number | null;
  tables_detected?: number | null;
  figures_detected?: number | null;
}

export interface DocumentVision {
  overall_quality?: number | null;
  ocr_pages?: number | null;
  pages?: VisionPage[] | null;
}

export interface DocumentStats {
  characters?: number | null;
  words?: number | null;
  chunks?: number | null;
  pages?: number | null;
  reading_time_min?: number | null;
  readability?: number | null;
}

/** Item of `GET /documents/list`. */
export interface DocumentSummary {
  id: number;
  filename: string;
  created_at?: string | null;
  doc_type?: string | null;
  summary?: string | null;
  pages?: number | null;
  chunk_count?: number | null;
  quality_score?: number | null;
  pii_count?: number | null;
  status?: string | null;
  status_detail?: string | null;
}

/** `GET /documents/{id}` and `analysis` of the upload response. */
export interface DocumentDetail {
  id: number;
  filename: string;
  created_at?: string | null;
  doc_type?: string | null;
  doc_type_confidence?: number | null;
  summary?: string | null;
  keywords?: Keyword[] | null;
  entities?: Entity[] | null;
  pii?: PiiSummary | null;
  security_flags?: SecurityFlag[] | null;
  vision?: DocumentVision | null;
  stats?: DocumentStats | null;
  preview?: string | null;
}

export interface UploadResponse {
  message: string;
  document_id: number;
  filename: string;
  /** queued | processing | completed | failed (asynchronous ingestion, v2.2) */
  status?: string | null;
  status_url?: string | null;
  characters_extracted?: number | null;
  preview?: string | null;
  analysis?: DocumentDetail | null;
}

export type ExtractionFields = Record<string, string>;

export interface ExtractRequest {
  fields: ExtractionFields;
}

export interface ExtractResponse {
  data: Record<string, unknown>;
  provider?: string | null;
  model?: string | null;
}

// ───────────────────────────── Chat ─────────────────────────────

export type ChatMode = 'fast' | 'deep';

export interface ChatQueryBody {
  query: string;
  session_id?: number | null;
  document_id?: number | null;
  document_ids?: number[] | null;
  mode?: ChatMode;
}

export interface Citation {
  index: number;
  document_id?: number | null;
  filename?: string | null;
  page?: number | null;
  chunk_id?: number | null;
  snippet?: string | null;
  score?: number | null;
}

export interface ClaimIssue {
  /** number | date | identifier | frequency | party | unsupported_content | negation | direction | roles | nli */
  kind: string;
  detail: string;
  /** contradiction = value check failed (sentence not supported); review = wording heuristic, ask a human. */
  severity?: 'contradiction' | 'review';
}

export interface ClaimCheck {
  text: string;
  supported: boolean;
  /** Similarity to the best-matching source sentence (relevance only, not correctness). */
  score?: number | null;
  sources?: number[] | null;
  /** v2.1 verifier: why the sentence was not supported, or what to check. */
  issues?: ClaimIssue[] | null;
  /** Supported by the value checks, but a wording heuristic asks a human to check it. */
  needs_review?: boolean | null;
  /** NLI model's max "unsupported" probability for the sentence, when the model ran. */
  nli?: number | null;
}

export interface Groundedness {
  supported: number;
  total: number;
  unsupported: string[];
  /** v2.1: claim-level verification. */
  claims?: ClaimCheck[] | null;
  /** Value checks that decide "supported", e.g. ["numbers", "dates", …]. */
  checks?: string[] | null;
  /** Wording heuristics that only ask for review, e.g. ["negation", "direction", "roles"]. */
  review_checks?: string[] | null;
  /** Number of supported sentences flagged for review. */
  review?: number | null;
}

export interface TraceStep {
  step: string;
  detail?: string | null;
  ms?: number | null;
}

/** Normalized `POST /chat/query` response (missing v2 fields filled with null/[]). */
export interface RagAnswer {
  answer: string;
  session_id: number | null;
  citations: Citation[];
  confidence: number | null;
  grounded: boolean | null;
  groundedness: Groundedness | null;
  sub_queries: string[];
  trace: TraceStep[];
  provider: string | null;
  model: string | null;
  latency_ms: number | null;
  /** v2.1: the model declined because the evidence was insufficient. */
  abstained: boolean | null;
  /** v2.1: provenance hash of the exact prompt sent to the model. */
  prompt_hash: string | null;
}

/** `meta` on stored assistant messages; same fields as RagAnswer, all optional. */
export type AnswerMeta = Partial<Omit<RagAnswer, 'answer' | 'session_id'>>;

export type StreamTraceEvent = { type: 'trace' } & TraceStep;
export interface StreamTokenEvent {
  type: 'token';
  text: string;
}
export type StreamFinalEvent = { type: 'final' } & RagAnswer;
export interface StreamErrorEvent {
  type: 'error';
  detail: string;
}
/** Client-side event: the SSE stream failed and we are retrying with POST /chat/query. */
export interface StreamFallbackEvent {
  type: 'fallback';
  reason: string;
}
export type StreamEvent =
  | StreamTraceEvent
  | StreamTokenEvent
  | StreamFinalEvent
  | StreamErrorEvent
  | StreamFallbackEvent;

export interface ChatSession {
  id: number;
  title: string;
  created_at?: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | string;
  content: string;
  meta?: AnswerMeta | null;
}

export interface SaveResponseBody {
  title: string;
  content: string;
}

export interface SavedItem {
  id: number;
  type?: string | null;
  title: string;
  content: string;
  created_at?: string | null;
}

// ───────────────────────── Intelligence ─────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: EntityType | string;
  weight: number;
  documents: number[];
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphQuery {
  document_id?: number | null;
  limit?: number;
}

export interface Topic {
  id: number;
  label: string;
  keywords: string[];
  document_ids: number[];
}

export interface RecentQuery {
  query: string;
  confidence?: number | null;
  latency_ms?: number | null;
  provider?: string | null;
  created_at?: string | null;
}

export interface Overview {
  documents?: number | null;
  chunks?: number | null;
  entities?: number | null;
  relations?: number | null;
  queries?: number | null;
  avg_latency_ms?: number | null;
  avg_confidence?: number | null;
  pii_total?: number | null;
  doc_types?: Record<string, number> | null;
  topics?: Topic[] | null;
  recent_queries?: RecentQuery[] | null;
}

export interface TimelineItem {
  date: string;
  text?: string | null;
  document_id?: number | null;
  filename?: string | null;
  page?: number | null;
  snippet?: string | null;
  upcoming?: boolean | null;
  days_from_now?: number | null;
}

export interface TimelineQuery {
  document_id?: number | null;
  upcoming_days?: number | null;
}

export interface AuditEntry {
  id: number;
  created_at?: string | null;
  query: string;
  mode?: string | null;
  provider?: string | null;
  model?: string | null;
  latency_ms?: number | null;
  confidence?: number | null;
  grounded?: boolean | null;
  n_citations?: number | null;
  prompt_hash?: string | null;
  chunk_ids?: number[] | null;
}

export interface PageImage {
  url: string;
  /** Value of `X-Highlight-Boxes` (0 = page shown without highlight). */
  highlights: number | null;
}

export interface EvalRequest {
  sample_size?: number;
}

export interface EvalResult {
  n: number;
  hit_rate_at_5: number;
  mrr: number;
  dense_only_hit_rate?: number | null;
  bm25_only_hit_rate?: number | null;
  ms?: number | null;
}

export interface LlmProvider {
  name: string;
  available: boolean;
  model?: string | null;
}

export interface Capabilities {
  llm_providers?: LlmProvider[] | null;
  embeddings?: string | null;
  reranker?: boolean | string | null;
  opencv?: boolean | null;
  ocr_engines?: string[] | null;
  vision_llm?: boolean | string | null;
}

// ─────────────────────────── Vision Lab ─────────────────────────

export interface ImageQuality {
  blur_score?: number | null;
  brightness?: number | null;
  contrast?: number | null;
  quality?: QualityLabel | string | null;
  score?: number | null;
}

export interface LayoutBlock {
  x: number;
  y: number;
  w: number;
  h: number;
  type: 'text' | 'table' | 'figure' | string;
}

export interface OcrResult {
  engine?: string | null;
  text?: string | null;
  confidence?: number | null;
  words?: number | null;
}

export interface VisionAnalysis {
  width?: number | null;
  height?: number | null;
  quality?: ImageQuality | null;
  skew_angle?: number | null;
  blocks?: LayoutBlock[] | null;
  ocr?: OcrResult | null;
  caption?: string | null;
  annotated_image?: string | null;
}

// ──────────────────────────── Errors ────────────────────────────

export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
}

/** Processing state of an uploaded document (GET /documents/{id}/status). */
export interface DocumentStatus {
  document_id: number;
  filename: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | string;
  detail?: string | null;
  job?: {
    id: number;
    state: 'queued' | 'running' | 'succeeded' | 'dead' | 'cancelled' | string;
    attempts: number;
    max_attempts: number;
    progress?: { stage?: string; detail?: string } | null;
    last_error?: string | null;
    updated_at?: string | null;
  } | null;
}

/** GET /documents/{id}/statement — bank-statement engine output (amounts in paise). */
export interface StatementTxn {
  seq: number;
  date: string;
  narration: string;
  debit_minor: number;
  credit_minor: number;
  balance_minor: number | null;
  page: number;
  direction_source: 'column' | 'suffix' | 'inferred_from_balance' | 'unknown' | string;
  /** x0, top, x1, bottom in tenths of a point (for the page highlight); null for structured (AA) data. */
  box: number[] | null;
  value_date?: string | null;
  reference?: string | null;
  /** Source transaction id (AA txnId). */
  external_id?: string | null;
  mode?: string | null;
}

export interface StatementCheck {
  scope: 'row' | 'statement' | 'opening' | string;
  seq: number | null;
  status: 'pass' | 'fail' | 'not_checkable' | string;
  reason: string;
  expected_minor: number | null;
  observed_minor: number | null;
  diff_minor: number | null;
  hypotheses: Array<{ code: string; detail: string; [k: string]: unknown }>;
}

export interface StatementAnalysis {
  document_id: number;
  is_statement: boolean;
  /** Statement-engine version that produced the stored result. */
  engine_version?: string;
  analysed_at?: string | null;
  period?: { start: string | null; end: string | null };
  source?: { type: 'pdf_text' | 'aa_deposit' | string; consent_ref: string | null; payload_sha256: string | null; schema_version: string | null };
  status?: 'reconciled' | 'reconciled_with_flags' | 'needs_review' | 'not_checkable' | string;
  currency?: string;
  header?: { ifsc?: string | null; account?: string | null };
  pages?: number;
  warnings?: string[];
  summary?: {
    opening_minor: number | null;
    closing_minor: number | null;
    transactions: number;
    total_debit_minor: number;
    total_credit_minor: number;
    failed_checks: number;
    inferred_directions: number;
  };
  transactions?: StatementTxn[];
  checks?: StatementCheck[];
}

/** POST /documents/import-aa */
export interface AAImportResponse {
  message: string;
  document_id: number;
  created: boolean;
  status: string;
  transactions: number;
  warnings: string[];
}
