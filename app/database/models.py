import json
import logging
from datetime import datetime

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
                        create_engine, event, inspect, text)
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

engine = create_engine(settings.database_url, **_engine_kwargs)

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
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True)
    role = Column(String)  # user | assistant
    content = Column(Text)
    meta_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession")


class SavedItem(Base):
    __tablename__ = "saved_items"
    id = Column(Integer, primary_key=True, index=True)
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
    """Create/upgrade all tables. Safe to call repeatedly."""
    Base.metadata.create_all(bind=engine)
    _auto_migrate()
    logger.info("Database tables created/verified")
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
