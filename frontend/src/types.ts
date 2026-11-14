/**
 * Types for the MindDoc AI v2 API contract (docs/API_CONTRACT.md).
 * Everything added in v2 is optional/nullable: documents uploaded before v2 have no analysis fields.
 */

// ───────────────────────────── Auth ─────────────────────────────

export interface Credentials {
  email: string;
  password: string;
  /** Join an existing organisation (one-time invitation token). */
  invite_token?: string;
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
  tenant_role?: TenantRole;
}

// ─────────────────────────── Cases and team (ADR-0012) ──────────────────────────

export type CaseRole = 'viewer' | 'analyst' | 'reviewer' | 'lead';
export type TenantRole = 'admin' | 'member';

export interface CaseSummary {
  id: number;
  title: string;
  status: 'open' | 'closed';
  is_default: boolean;
  created_at: string | null;
  my_role: CaseRole | null;
  documents: number;
  /** null for the General case, which every organisation member can use */
  members: number | null;
}

export interface CaseMemberView {
  user_id: number;
  email: string;
  role: CaseRole;
  active: boolean;
  added_at: string;
}

export interface CaseDetail extends Omit<CaseSummary, 'members'> {
  members: CaseMemberView[];
  open_to_organisation: boolean;
  /** `cases`: how many cases hold the document (it cannot leave its last one) */
  document_list: Array<{ id: number; filename: string; status: string; doc_type: string | null; cases: number }>;
}

export interface TeamMember {
  id: number;
  email: string;
  tenant_role: TenantRole;
  active: boolean;
  created_at: string | null;
}

export interface TeamInvite {
  id: number;
  email: string | null;
  tenant_role: TenantRole;
  state: 'open' | 'used' | 'revoked' | 'expired';
  created_at: string;
  expires_at: string;
  used_by: number | null;
  used_at: string | null;
  /** only in the response that created it */
  token?: string;
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
  case_id?: number | null;
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
  /** v3 verifier: figures not printed in the source but recomputed from it, with the arithmetic. */
  derivations?: string[] | null;
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
  /** A weak signal (named in the same passage, or an account holder link), drawn dashed; never a relationship. */
  weak?: boolean;
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
  header?: {
    ifsc?: string | null;
    account?: string | null;
    bank_account_id?: number | null;
    holder?: string | null;
    holder_source?: 'statement_header' | 'analyst' | string | null;
  };
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

/* ------------------------------------------------------------------ Parties (R5 entity resolution) */
export interface PartyIdentifierView {
  scheme: 'PAN' | 'GSTIN' | 'UPI_VPA' | 'ACCOUNT_IFSC' | string;
  value: string;
}

export interface PartySummary {
  party_id: number;
  name: string;
  kind: 'org' | 'person' | 'unknown' | string;
  records: number;
  member_ids: number[];
  names: string[];
  identifiers: PartyIdentifierView[];
  transactions: number;
  debit_minor: number;
  credit_minor: number;
  documents: number[];
  /** Bank accounts this party holds (statement header or analyst). */
  accounts?: Array<{ id: number; masked: string; ifsc: string | null }>;
}

export interface IdentityEventView {
  id: number;
  kind: 'merge' | 'unmerge';
  a: { id: number; name: string | null };
  b: { id: number; name: string | null };
  method: string;
  probability: number | null;
  reason: string;
  features: Record<string, unknown>;
  decided_by: number | null;
  decided_at: string;
  reverses_event_id: number | null;
  reversed: boolean;
}

export interface PartyMentionView {
  party_record_id: number;
  source_type: string;
  source_id: number;
  document_id: number | null;
  channel: string | null;
  text: string | null;
  date: string | null;
  debit_minor: number | null;
  credit_minor: number | null;
  page: number | null;
  seq: number | null;
}

export interface ClaimView {
  id: number;
  claim_key: string;
  kind: 'TRANSFERRED_TO' | 'RECEIVED_FROM' | string;
  subject_document_id: number | null;
  subject_label: string | null;
  party_record_id: number | null;
  party_id: number | null;
  party_name: string | null;
  amount_minor: number;
  currency: string;
  date: string | null;
  status: 'reconciled' | 'extracted' | 'needs_review' | string;
  method: string;
  version: { recorded_at: string; superseded_at: string | null; supersedes_id: number | null };
  evidence: Array<{ document_id: number | null; page: number | null; seq: number | null; quote: string | null; box: number[] | null }>;
}

export interface PartyDetail extends PartySummary {
  canonical_id: number;
  claims: ClaimView[];
  mentions: PartyMentionView[];
  events: IdentityEventView[];
}

export interface PartyReviewItem {
  id: number;
  state: string;
  reason: string;
  method: string;
  probability: number | null;
  features: Record<string, unknown>;
  a: PartySummary | null;
  b: PartySummary | null;
  a_record_id: number;
  b_record_id: number;
}

export interface ResolveResult {
  case_id: number;
  parties_created: number;
  mentions_added: number;
  records: number;
  auto_merges: number;
  review_items: number;
  skipped_by_human_decision: number;
  model: string;
}

export interface FlowGraph {
  case_id: number;
  nodes: Array<{
    id: string;
    type: 'account' | 'party';
    label: string;
    kind?: string;
    party_id?: number;
    document_id?: number;
    document_ids?: number[];
    bank_account_id?: number | null;
    holder?: string | null;
    holds?: string[];
  }>;
  edges: Array<{
    source: string;
    target: string;
    /** flow: money between an account and a party; holds: a party holds the account. */
    kind: 'flow' | 'holds';
    evidence?: Array<{ source: string; document_id?: number; page?: number; set_by?: number | null; set_at?: string | null }>;
    out_minor: number;
    in_minor: number;
    transactions: number[];
    claims: Array<{
      id: number;
      kind: string;
      date: string | null;
      amount_minor: number;
      status: string;
      document_id: number | null;
      page: number | null;
      seq: number | null;
      quote: string | null;
    }>;
  }>;
}

// ------------------------------------------------------------------ R5: accounts, findings, frozen reports

export interface BankAccountView {
  id: number;
  account_masked: string;
  ifsc: string | null;
  account_type: string | null;
  hash_basis: 'full' | 'masked' | string;
  holder: string | null;
  holder_source: 'statement_header' | 'analyst' | string | null;
  holder_set_at: string | null;
  documents: number[];
}

export type FindingStatus = 'draft' | 'proposed' | 'approved' | 'rejected';

export interface FindingSupportView {
  role: 'supports' | 'contradicts' | 'context';
  claim: {
    id: number;
    claim_key: string;
    kind: string;
    subject: string | null;
    party: string | null;
    amount_minor: number;
    currency: string;
    date: string | null;
    status: string;
    method: string;
    recorded_at: string;
  };
  evidence: Array<{
    document_id: number | null;
    filename: string | null;
    source_sha256: string | null;
    page: number | null;
    seq: number | null;
    box: number[] | null;
    quote: string | null;
    external_id: string | null;
  }>;
  changed_since?: { superseded_at: string; reason: string | null; current_claim_id: number | null } | null;
}

export interface FindingView {
  id: number;
  finding_key: string;
  version: number;
  title: string;
  statement: string;
  status: FindingStatus;
  method: string;
  evidence_snapshot_at: string;
  created_at: string;
  created_by: number | null;
  change_note: string | null;
  supersedes_id: number | null;
  superseded_at?: string | null;
  stale?: boolean;
  support: FindingSupportView[];
  history?: Array<{ id: number; version: number; status: FindingStatus; change_note: string | null; created_at: string; superseded_at: string | null }>;
  /** Leave-one-source-out fragility (R8): on the finding page, and frozen into reports issued since R8. */
  robustness?: Robustness;
}

export interface Robustness {
  method: string;
  bound_type: 'exact' | 'upper' | 'lower';
  /** fewest independent sources whose removal leaves a supporting claim without evidence */
  k_fragility: number | null;
  loso_score: number;
  essential_sources: string[];
  responsibility: Record<string, number>;
  sources: Record<string, Array<{ document_id: number; filename: string | null }>>;
  facts: Array<{
    claim_id: number;
    providers: string[];
    own_source: string | null;
    corroborated_by: Array<{ claim_id: number; document_id: number; source: string }>;
    status: string | null;
  }>;
  contradicting_claims: number[];
  notes: string[];
  explanation: string;
}

export interface DisclosureParty {
  id: number;
  name: string;
  kind: 'org' | 'person' | 'unknown';
  default_subject: boolean;
}

export interface DisclosureView {
  id: number;
  report_id: number;
  recipient: string;
  created_at: string;
  created_by: number | null;
  content_hash: string;
  base_hash: string;
  subjects: Array<{ id: number; name: string }>;
  intact: boolean;
  /** issuer-only log: what was withheld, with the original values */
  withheld: Array<{ label: string; kind: string; reason: string; occurrences: number; values: string[] }>;
}

export interface FindingSummary {
  id: number;
  finding_key: string;
  version: number;
  title: string;
  status: FindingStatus;
  stale: boolean;
  created_at: string;
  claims: number;
}

export interface ReportSummary {
  id: number;
  title: string;
  frozen_at: string;
  content_hash: string;
  findings: number;
}

export interface ReportView {
  id: number;
  title: string;
  frozen_at: string;
  content_hash: string;
  intact: boolean;
  finding_ids: number[];
  new_evidence_since_report: Array<{ finding_id: number; title: string; claims_changed: boolean; newer_version_id: number | null }>;
  snapshot: {
    report: { title: string; case: { id: number; title: string | null }; frozen_at: string; issued_by: string | null };
    findings: FindingView[];
    notice: string;
  };
}
