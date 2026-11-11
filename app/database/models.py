import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import (BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint,
                        create_engine, event, inspect, text)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_is_sqlite = settings.database_url.startswith("sqlite")
_engine_kwargs: dict = {"echo": False, "future": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    if ":memory:" in settings.database_url or settings.database_url.rstrip("/") == "sqlite:":
        _engine_kwargs["poolclass"] = StaticPool
    else:  # SQLite won't create a missing folder (e.g. a fresh container volume)
        _db_file = make_url(settings.database_url).database
        if _db_file:
            Path(_db_file).parent.mkdir(parents=True, exist_ok=True)

if settings.database_url.startswith("postgresql"):
    _engine_kwargs.update(pool_pre_ping=True, pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow,
                          pool_recycle=1800)

engine = create_engine(settings.database_url, **_engine_kwargs)
IS_POSTGRES = engine.dialect.name == "postgresql"
RLS_ACTIVE = {"value": False}  # True once connections run as the non-owner application role (row-level security)

if IS_POSTGRES:
    @event.listens_for(engine, "connect")
    def _use_app_role(dbapi_conn, connection_record):
        """Run every application connection as the non-owner role, so row-level security applies (ADR-0002)."""
        role = settings.db_app_role
        if not role:
            return
        cur = dbapi_conn.cursor()
        try:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            if cur.fetchone():
                cur.execute('SET ROLE "%s"' % role.replace('"', ''))
                RLS_ACTIVE["value"] = True
            else:
                logger.warning("database role %s not found: run migrations; row-level security is NOT active", role)
        finally:
            cur.close()

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine, expire_on_commit=False)
Base = declarative_base()


def _loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant = relationship("Tenant")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content = Column(Text)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String, index=True)
    source_path = Column(String)
    pages = Column(Integer)
    doc_type = Column(String)
    doc_type_confidence = Column(Float)
    summary = Column(Text)
    quality_score = Column(Float)
    keywords_json = Column(Text)
    stats_json = Column(Text)
    vision_json = Column(Text)
    pii_json = Column(Text)
    security_json = Column(Text)
    # ingestion lifecycle (async processing, design G 5.3): queued -> processing -> completed | failed
    status = Column(String, default="completed", index=True)
    status_detail = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tenant = relationship("Tenant")

    @property
    def keywords(self):
        return _loads(self.keywords_json, [])

    @property
    def stats(self):
        return _loads(self.stats_json, {})

    @property
    def vision(self):
        return _loads(self.vision_json, None)

    @property
    def pii(self):
        return _loads(self.pii_json, {"count": 0, "types": {}})

    @property
    def security_flags(self):
        return _loads(self.security_json, [])


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    chunk_text = Column(Text)
    embedding = Column(Text)  # JSON list[float]
    embedding_model = Column(String)
    page = Column(Integer)
    chunk_index = Column(Integer)
    document = relationship("Document")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True)
    role = Column(String)  # user | assistant
    content = Column(Text)
    meta_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession")


class SavedItem(Base):
    __tablename__ = "saved_items"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_type = Column(String)  # document | response
    title = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


# ---------------------------------------------------------------- Ontology / knowledge graph

class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("tenant_id", "norm_name", "type", name="uq_entity"),)
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    name = Column(String)
    norm_name = Column(String, index=True)
    type = Column(String)
    mention_count = Column(Integer, default=0)


class EntityMention(Base):
    __tablename__ = "entity_mentions"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True)
    count = Column(Integer, default=1)


class Relation(Base):
    __tablename__ = "relations"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    source_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    target_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    relation = Column(String, default="co_occurs")
    weight = Column(Float, default=1.0)


# ---------------------------------------------------------------- Audit / observability

class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(Integer)
    query = Column(Text)
    mode = Column(String)
    provider = Column(String)
    model = Column(String)
    latency_ms = Column(Integer)
    confidence = Column(Float)
    grounded = Column(Integer)
    n_citations = Column(Integer)
    prompt_hash = Column(String)
    chunk_ids_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- Cases, jobs, audit (R2 foundation)

class Case(Base):
    """An engagement inside a tenant (ADR-0012). Every tenant has a default case named "General"."""
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="open")
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CaseDocument(Base):
    __tablename__ = "case_documents"
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    added_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    """Durable background job (ADR-0003). Inserted in the same transaction as the state it acts on."""
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("tenant_id", "kind", "idempotency_key", name="uq_job_idempotency"),)
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    kind = Column(String, nullable=False)
    subject_id = Column(Integer, index=True)  # e.g. the document a job processes
    payload = Column(Text, nullable=False, default="{}")
    idempotency_key = Column(String, nullable=False)
    state = Column(String, nullable=False, default="queued", index=True)  # queued|running|succeeded|dead|cancelled
    priority = Column(Integer, nullable=False, default=0)
    run_after = Column(DateTime, nullable=False, default=datetime.utcnow)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    locked_by = Column(String)
    lease_until = Column(DateTime)
    last_error = Column(Text)
    progress = Column(Text)  # JSON: {"stage": ..., "detail": ...}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditEvent(Base):
    """Append-only, hash-chained audit trail (per tenant)."""
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    actor_id = Column(Integer, nullable=True)
    verb = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=True)
    payload_hash = Column(String, nullable=False)
    prev_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)



# ---------------------------------------------------------------- Bank statements (R3, ADR-0011; money per ADR-0010)

class Statement(Base):
    """Latest statement-engine result for one document. Amounts are integer minor units of `currency`."""
    __tablename__ = "statements"
    __table_args__ = (UniqueConstraint("document_id", name="uq_statement_document"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    engine_version = Column(String, nullable=False)
    status = Column(String, nullable=False)  # reconciled | reconciled_with_flags | needs_review | not_checkable | not_a_statement
    currency = Column(String(3), nullable=False, default="INR")
    ifsc = Column(String)
    account_masked = Column(String)
    opening_minor = Column(BigInteger)
    closing_minor = Column(BigInteger)
    period_start = Column(Date)
    period_end = Column(Date)
    pages = Column(Integer)
    n_txns = Column(Integer, nullable=False, default=0)
    total_debit_minor = Column(BigInteger, nullable=False, default=0)
    total_credit_minor = Column(BigInteger, nullable=False, default=0)
    failed_checks = Column(Integer, nullable=False, default=0)
    inferred_directions = Column(Integer, nullable=False, default=0)
    warnings = Column(Text)  # JSON list
    source = Column(String, nullable=False, default="pdf_text", server_default="pdf_text")  # pdf_text | pdf_ocr | aa_deposit
    source_ref = Column(String)       # e.g. the AA consent artefact reference supplied by the customer
    payload_sha256 = Column(String(64))
    schema_version = Column(String)   # ReBIT FI schema version for AA imports
    created_at = Column(DateTime, default=datetime.utcnow)


class StatementTxn(Base):
    """One transaction exactly as read. box_* = row position on its page, tenths of a point, top-left origin."""
    __tablename__ = "statement_txns"
    __table_args__ = (UniqueConstraint("statement_id", "seq", name="uq_statement_txn_seq"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id", ondelete="CASCADE"), index=True, nullable=False)
    seq = Column(Integer, nullable=False)
    txn_date = Column(Date, index=True, nullable=False)
    narration = Column(Text)
    debit_minor = Column(BigInteger, nullable=False)
    credit_minor = Column(BigInteger, nullable=False)
    balance_minor = Column(BigInteger)
    page = Column(Integer, nullable=False)
    box_x0 = Column(Integer)
    box_top = Column(Integer)
    box_x1 = Column(Integer)
    box_bottom = Column(Integer)
    direction_source = Column(String, nullable=False)
    amount_raw = Column(String)
    balance_raw = Column(String)
    value_date = Column(Date)
    reference = Column(String)
    external_id = Column(String)      # source transaction id (AA txnId)
    mode = Column(String)             # AA transaction mode (CASH, ATM, CARD, UPI, FT, OTHERS)


class ReconciliationCheck(Base):
    """A non-trivial reconciliation check (failure, flag or reversal pair) with its ranked hypotheses (JSON)."""
    __tablename__ = "reconciliation_checks"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id", ondelete="CASCADE"), index=True, nullable=False)
    scope = Column(String, nullable=False)
    seq = Column(Integer)
    status = Column(String, nullable=False)
    reason = Column(String)
    expected_minor = Column(BigInteger)
    observed_minor = Column(BigInteger)
    hypotheses = Column(Text)


# ---------------------------------------------------------------- Identity: parties and reversible merges (R5, ADR-0009)

class Party(Base):
    """One counterparty *record* within a case (a distinct printed name + identifier signature). Records are never
    renamed or deleted by resolution; identity events link them into canonical parties."""
    __tablename__ = "parties"
    __table_args__ = (UniqueConstraint("case_id", "signature", name="uq_party_signature"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    kind = Column(String, nullable=False, default="unknown")       # org | person | unknown
    name = Column(String, nullable=False)                          # as printed (first seen)
    name_norm = Column(String, nullable=False)
    signature = Column(String, nullable=False)                     # name_norm + identifiers, for de-duplication
    created_at = Column(DateTime, default=datetime.utcnow)


class PartyIdentifier(Base):
    __tablename__ = "party_identifiers"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), index=True, nullable=False)
    scheme = Column(String, nullable=False)                        # PAN | GSTIN | UPI_VPA | ACCOUNT_IFSC
    value = Column(String, nullable=False)
    valid_structure = Column(Boolean, nullable=False, default=True)


class PartyMention(Base):
    """Where a party record was seen: a statement transaction (counterparty) or a document."""
    __tablename__ = "party_mentions"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type = Column(String, nullable=False)                   # statement_txn | document
    source_id = Column(Integer, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    text = Column(Text)
    channel = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class IdentityEvent(Base):
    """Append-only log of merges and unmerges between two party records. Canonical parties at any time T are the
    connected components of merges decided by T and not reversed by T."""
    __tablename__ = "identity_events"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    kind = Column(String, nullable=False)                          # merge | unmerge
    a_party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    b_party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    reverses_event_id = Column(Integer, ForeignKey("identity_events.id"))
    method = Column(String, nullable=False)                        # rule:<scheme> | splink-... | human
    probability_bp = Column(Integer)                               # match probability in basis points (0-10000)
    reason = Column(Text, nullable=False)
    features = Column(Text)                                        # JSON "why linked"
    decided_by = Column(Integer, ForeignKey("users.id"))
    decided_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class PartyReview(Base):
    """Operational review queue for candidate merges; decisions are recorded as identity events."""
    __tablename__ = "party_reviews"
    __table_args__ = (UniqueConstraint("case_id", "a_party_id", "b_party_id", name="uq_party_review_pair"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    a_party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    b_party_id = Column(Integer, ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    method = Column(String, nullable=False)
    probability_bp = Column(Integer)
    reason = Column(Text, nullable=False)
    features = Column(Text)
    state = Column(String, nullable=False, default="open")         # open | merged | kept_separate
    decision_reason = Column(Text)
    decided_by = Column(Integer, ForeignKey("users.id"))
    decided_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- Claims with evidence (R5, ADR-0004, design F §2.3/§3)

class Claim(Base):
    """A versioned assertion built from observations, e.g. TRANSFERRED_TO(statement account -> party, amount, date).

    `claim_key` is the stable logical key; each row is one *version*. System time: a version is current from
    `recorded_at` until `superseded_at` (NULL = current). Versions are never edited except to close them; a change
    inserts a new version pointing at the old one (`supersedes_id`)."""
    __tablename__ = "claims"
    __table_args__ = (Index("uq_claims_current_version", "case_id", "claim_key", unique=True,
                            sqlite_where=text("superseded_at IS NULL"), postgresql_where=text("superseded_at IS NULL")),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    claim_key = Column(String, nullable=False, index=True)
    kind = Column(String, nullable=False)                    # TRANSFERRED_TO | RECEIVED_FROM
    subject_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))  # the statement account
    subject_label = Column(String)
    object_party_id = Column(Integer, ForeignKey("parties.id", ondelete="SET NULL"))     # a party *record*
    amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    valid_date = Column(Date)                                # valid time: the transaction date
    status = Column(String, nullable=False)                  # reconciled | extracted | needs_review
    method = Column(String, nullable=False)                  # e.g. statement-engine r4.0
    supersedes_id = Column(Integer, ForeignKey("claims.id"))
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    superseded_at = Column(DateTime, index=True)
    supersede_reason = Column(String)


class ClaimEvidence(Base):
    """Where a claim version comes from. Region fields are copied, so an old version still resolves to the exact
    page region after the statement is re-analysed."""
    __tablename__ = "claim_evidence"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String, nullable=False, default="supports")
    source_type = Column(String, nullable=False)             # statement_txn
    statement_txn_id = Column(Integer)                       # informational: may be replaced by re-analysis
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page = Column(Integer)
    seq = Column(Integer)
    box_x0 = Column(Integer)
    box_top = Column(Integer)
    box_x1 = Column(Integer)
    box_bottom = Column(Integer)
    quote = Column(Text)                                     # the narration as read
    external_id = Column(String)                             # e.g. AA txnId

def _auto_migrate():
    """Add columns introduced after a table was created (SQLite has no create_all upgrades)."""
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                coltype = col.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {coltype}'))
                logger.info("migrated: added %s.%s", table.name, col.name)


def create_tables():
    """Create/upgrade the schema. PostgreSQL: Alembic migrations under an advisory lock. SQLite (single-user dev
    fallback, no row-level security): create_all + additive column migration."""
    if IS_POSTGRES:
        from app.database.migrate import upgrade_head
        upgrade_head()
        # Connections opened before the migration created the application role run as the login (owner) role and
        # would bypass row-level security. Discard them; every new connection runs SET ROLE (see _use_app_role).
        engine.dispose()
    else:
        Base.metadata.create_all(bind=engine)
        _auto_migrate()
    logger.info("Database schema ready (%s)", engine.dialect.name)
    return True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_default_tenant(db: Session):
    default_tenant = db.query(Tenant).filter(Tenant.name == "default").first()
    if not default_tenant:
        default_tenant = Tenant(name="default")
        db.add(default_tenant)
        db.commit()
    return default_tenant
